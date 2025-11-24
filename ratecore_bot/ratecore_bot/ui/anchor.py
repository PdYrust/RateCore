from __future__ import annotations

import logging
from typing import Optional

from aiogram import Bot, types
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

from ratecore_bot.config import Settings
from ratecore_bot.db.repository import (
    ensure_chat_by_id,
    update_admin_menu_anchor,
    update_main_menu_anchor,
)
from ratecore_bot.db.session import get_session
from ratecore_bot.ui.keyboards import admin_main_menu_keyboard, main_menu_keyboard
from ratecore_bot.ui.views import format_admin_main_menu, format_main_menu_text

logger = logging.getLogger(__name__)


async def _edit_or_send_anchor(
    bot: Bot,
    chat: types.Chat,
    anchor_message_id: Optional[int],
    text: str,
    reply_markup,
    update_anchor_cb,
) -> int:
    """
    Try to edit anchor message; on failure send new one and update anchor.
    Returns the current anchor message id.
    """
    if anchor_message_id:
        try:
            await bot.edit_message_text(
                text=text,
                chat_id=chat.id,
                message_id=anchor_message_id,
                reply_markup=reply_markup,
            )
            return anchor_message_id
        except TelegramBadRequest as exc:
            # If content is identical, do nothing and keep anchor id.
            if "message is not modified" in str(exc):
                logger.debug(
                    "Anchor edit ignored (not modified) for chat %s message %s",
                    chat.id,
                    anchor_message_id,
                )
                return anchor_message_id
            if "message to edit not found" in str(exc):
                logger.info(
                    "Anchor edit failed (message missing) for chat %s message %s; will send new anchor.",
                    chat.id,
                    anchor_message_id,
                )
            else:
                logger.warning(
                    "Anchor edit failed for chat %s message %s: %s. Sending new anchor.",
                    chat.id,
                    anchor_message_id,
                    exc,
                )
        except TelegramForbiddenError as exc:
            logger.warning(
                "Anchor edit forbidden for chat %s message %s: %s. Sending new anchor.",
                chat.id,
                anchor_message_id,
                exc,
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("Unexpected anchor edit failure for chat %s: %s", chat.id, exc)

    msg = await bot.send_message(chat.id, text, reply_markup=reply_markup)
    async with get_session() as session:
        await update_anchor_cb(session, chat.id, msg.message_id)
        await session.commit()
    return msg.message_id


async def show_main_menu_anchor(bot: Bot, chat: types.Chat, settings: Settings) -> None:
    """Ensure the main menu anchor is present and updated for this chat."""
    text = format_main_menu_text()
    reply_markup = main_menu_keyboard()
    async with get_session() as session:
        chat_model, chat_settings = await ensure_chat_by_id(session, chat.id, chat)
        anchor_id = chat_settings.main_menu_message_id if chat_settings else None
    await _edit_or_send_anchor(
        bot=bot,
        chat=chat,
        anchor_message_id=anchor_id,
        text=text,
        reply_markup=reply_markup,
        update_anchor_cb=update_main_menu_anchor,
    )


async def show_admin_menu_anchor(bot: Bot, chat: types.Chat, settings: Settings) -> None:
    """Ensure the admin menu anchor is present and updated for this chat."""
    text = format_admin_main_menu()
    reply_markup = admin_main_menu_keyboard()
    async with get_session() as session:
        chat_model, chat_settings = await ensure_chat_by_id(session, chat.id, chat)
        anchor_id = chat_settings.admin_menu_message_id if chat_settings else None
    await _edit_or_send_anchor(
        bot=bot,
        chat=chat,
        anchor_message_id=anchor_id,
        text=text,
        reply_markup=reply_markup,
        update_anchor_cb=update_admin_menu_anchor,
    )
