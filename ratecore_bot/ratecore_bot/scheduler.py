from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Sequence

from aiogram import Bot

from ratecore_bot.api.ratecore_client import RateCoreClient
from ratecore_bot.config import Settings
from ratecore_bot.db import models, repository
from ratecore_bot.db.session import get_session
from ratecore_bot.ui.views import MAIN_DASHBOARD_SYMBOLS, format_main_dashboard

logger = logging.getLogger(__name__)


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _ensure_aware(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _should_send(settings: models.ChatSettings, now: datetime) -> bool:
    last = _ensure_aware(settings.last_sent_at)
    if last is None:
        return True
    return (now - last) >= timedelta(minutes=settings.interval_minutes)


async def _send_dashboard(
    bot: Bot,
    ratecore_client: RateCoreClient,
    chat: models.Chat,
    cs: models.ChatSettings,
    now: datetime,
) -> None:
    items = await ratecore_client.get_prices_batch(MAIN_DASHBOARD_SYMBOLS)
    text = format_main_dashboard(items)
    logger.info("Scheduler: Sending auto-post to chat %s", chat.tg_chat_id)

    if cs.send_mode == "edit" and cs.last_message_id:
        try:
            await bot.edit_message_text(
                chat_id=chat.tg_chat_id,
                message_id=cs.last_message_id,
                text=text,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Scheduler: edit mode failed for chat %s, fallback to new message: %s",
                chat.tg_chat_id,
                exc,
            )
            msg = await bot.send_message(chat.tg_chat_id, text)
            cs.last_message_id = msg.message_id
    else:
        msg = await bot.send_message(chat.tg_chat_id, text)
        cs.last_message_id = msg.message_id

    cs.last_sent_at = now
    cs.error_count = 0


async def process_auto_posts(bot: Bot, ratecore_client: RateCoreClient) -> None:
    async with get_session() as session:
        if not await repository.get_bot_enabled(session):
            return
        pairs: Sequence[tuple[models.Chat, models.ChatSettings]] = await repository.list_auto_post_chats(session)
        now = _now_utc()

        for chat, cs in pairs:
            if not _should_send(cs, now):
                continue
            try:
                await _send_dashboard(bot, ratecore_client, chat, cs, now)
                await session.flush()
                logger.info("Scheduler: updated settings for chat %s", chat.tg_chat_id)
            except Exception as exc:  # noqa: BLE001
                cs.error_count = (cs.error_count or 0) + 1
                logger.exception("Scheduler error for chat %s: %s", chat.tg_chat_id, exc)
                await session.flush()

        await session.commit()


async def process_alerts(bot: Bot, ratecore_client: RateCoreClient) -> None:
    now = _now_utc()
    async with get_session() as session:
        alerts = await repository.get_active_alerts_for_check(session)
        if not alerts:
            return

        symbols = sorted({a.symbol for a in alerts})
        try:
            price_items = await ratecore_client.get_prices_batch(list(symbols))
        except Exception as exc:  # noqa: BLE001
            logger.exception("Scheduler: failed to fetch prices for alerts: %s", exc)
            return

        price_map = {item.get("symbol") or item.get("Symbol"): item for item in price_items}

        for alert in alerts:
            data = price_map.get(alert.symbol) or price_map.get(alert.symbol.upper())
            await repository.mark_alert_checked(session, alert, now=now)
            if not data:
                continue

            display_val = data.get("display") or data.get("Display")
            toman_val = data.get("value_toman") or data.get("ValueToman")
            current_val = display_val if display_val is not None else toman_val
            if current_val is None:
                continue

            triggered = False
            if alert.condition_type == "above":
                triggered = current_val > alert.value_from
            elif alert.condition_type == "below":
                triggered = current_val < alert.value_from

            if not triggered:
                continue

            text = (
                "⏰ Price alert triggered!\n\n"
                f"{alert.symbol} is now {current_val:,.0f} {alert.currency_mode} "
                f"({alert.condition_type} {alert.value_from:,.0f})"
            )
            try:
                await bot.send_message(alert.chat.tg_chat_id, text)
            except Exception as exc:  # noqa: BLE001
                logger.exception("Scheduler: failed to send alert %s: %s", alert.id, exc)
            await repository.mark_alert_triggered(session, alert, now=now, deactivate=True)
            logger.info("Scheduler: alert %s for user %s triggered.", alert.id, alert.user_id)

        await session.commit()


async def run_scheduler(settings: Settings, bot: Bot, ratecore_client: RateCoreClient) -> None:
    """
    Background task that runs forever.
    """
    poll_interval_seconds = 60
    while True:
        try:
            await process_auto_posts(bot, ratecore_client)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Scheduler loop error (auto posts): %s", exc)
        try:
            await process_alerts(bot, ratecore_client)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Scheduler loop error (alerts): %s", exc)

        await asyncio.sleep(poll_interval_seconds)
