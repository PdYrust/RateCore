from __future__ import annotations

import logging
from datetime import datetime
from typing import Literal, Optional

from aiogram import types
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import IntegrityError

from ratecore_bot.db import models

logger = logging.getLogger(__name__)

async def get_chat_settings_by_chat_id(session: AsyncSession, chat_id: int) -> Optional[models.ChatSettings]:
    stmt = select(models.ChatSettings).where(models.ChatSettings.chat_id == chat_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_or_create_user(
    session: AsyncSession,
    tg_user: types.User,
    *,
    is_admin: bool = False,
) -> models.User:
    stmt = select(models.User).where(models.User.tg_user_id == tg_user.id)
    result = await session.execute(stmt)
    user: Optional[models.User] = result.scalar_one_or_none()

    now = datetime.utcnow()
    if user is None:
        user = models.User(
            tg_user_id=tg_user.id,
            first_name=tg_user.first_name,
            last_name=tg_user.last_name,
            username=tg_user.username,
            language=tg_user.language_code,
            is_admin=is_admin,
            created_at=now,
            updated_at=now,
            last_seen_at=now,
        )
        session.add(user)
        try:
            await session.flush()
            logger.info("Created new user tg_user_id=%s", tg_user.id)
        except IntegrityError:
            await session.rollback()
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()
            if user is None:
                raise
            logger.debug("User already existed tg_user_id=%s, reused after integrity error", tg_user.id)
    else:
        user.first_name = tg_user.first_name
        user.last_name = tg_user.last_name
        user.username = tg_user.username
        user.language = tg_user.language_code
        user.is_admin = is_admin or user.is_admin
        user.last_seen_at = now
        user.updated_at = now
        await session.flush()
        logger.debug("Updated user tg_user_id=%s", tg_user.id)

    return user


async def get_or_create_chat(session: AsyncSession, tg_chat: types.Chat) -> models.Chat:
    stmt = select(models.Chat).where(models.Chat.tg_chat_id == tg_chat.id)
    result = await session.execute(stmt)
    chat: Optional[models.Chat] = result.scalar_one_or_none()
    now = datetime.utcnow()

    if chat is None:
        chat = models.Chat(
            tg_chat_id=tg_chat.id,
            type=tg_chat.type,
            title=tg_chat.title,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        session.add(chat)
        await session.flush()
        logger.info("Created new chat tg_chat_id=%s type=%s", tg_chat.id, tg_chat.type)
    else:
        chat.title = tg_chat.title
        chat.type = tg_chat.type
        chat.updated_at = now
        await session.flush()
        logger.debug("Updated chat tg_chat_id=%s", tg_chat.id)

    return chat


async def ensure_chat_settings(session: AsyncSession, chat: models.Chat) -> models.ChatSettings:
    stmt = select(models.ChatSettings).where(models.ChatSettings.chat_id == chat.id)
    result = await session.execute(stmt)
    settings = result.scalar_one_or_none()
    if settings:
        return settings

    settings = models.ChatSettings(
        chat_id=chat.id,
        auto_post_enabled=False,
        package_id=None,
        interval_minutes=10,
        send_mode="edit",
        error_count=0,
    )
    session.add(settings)
    await session.flush()
    logger.info("Created chat settings for chat_id=%s", chat.id)
    return settings


async def update_main_menu_anchor(session: AsyncSession, chat_id: int, message_id: int) -> None:
    chat, settings = await fetch_chat_with_settings(session, chat_key=chat_id)
    if settings is None:
        settings = await ensure_chat_settings(session, chat)
    settings.main_menu_message_id = message_id
    settings.updated_at = datetime.utcnow()
    await session.flush()


async def update_admin_menu_anchor(session: AsyncSession, chat_id: int, message_id: int) -> None:
    chat, settings = await fetch_chat_with_settings(session, chat_key=chat_id)
    if settings is None:
        settings = await ensure_chat_settings(session, chat)
    settings.admin_menu_message_id = message_id
    settings.updated_at = datetime.utcnow()
    await session.flush()


async def clear_main_menu_anchor(session: AsyncSession, chat_id: int) -> None:
    settings = await get_chat_settings_by_chat_id(session, chat_id)
    if settings is None:
        chat = await get_chat_by_tg_id(session, chat_id)
        if chat is None:
            return
        settings = await ensure_chat_settings(session, chat)
    settings.main_menu_message_id = None
    settings.updated_at = datetime.utcnow()
    await session.flush()


# Global settings helpers


async def get_or_create_global_settings(session: AsyncSession) -> models.GlobalSettings:
    stmt = select(models.GlobalSettings).limit(1)
    result = await session.execute(stmt)
    gs = result.scalar_one_or_none()
    if gs:
        return gs
    gs = models.GlobalSettings(bot_enabled=True, maintenance_message=None)
    session.add(gs)
    await session.flush()
    return gs


async def set_bot_enabled(session: AsyncSession, enabled: bool) -> models.GlobalSettings:
    gs = await get_or_create_global_settings(session)
    gs.bot_enabled = enabled
    gs.updated_at = datetime.utcnow() if hasattr(gs, "updated_at") else datetime.utcnow()
    await session.flush()
    return gs


async def set_maintenance_message(session: AsyncSession, message: str | None) -> models.GlobalSettings:
    gs = await get_or_create_global_settings(session)
    gs.maintenance_message = message
    gs.updated_at = datetime.utcnow() if hasattr(gs, "updated_at") else datetime.utcnow()
    await session.flush()
    return gs


async def get_bot_enabled(session: AsyncSession) -> bool:
    stmt = select(models.GlobalSettings).limit(1)
    result = await session.execute(stmt)
    gs = result.scalar_one_or_none()
    if gs is None:
        return True
    return bool(gs.bot_enabled)


async def list_auto_post_chats(session: AsyncSession):
    stmt = (
        select(models.ChatSettings)
        .join(models.Chat)
        .options(selectinload(models.ChatSettings.chat))
        .where(models.ChatSettings.auto_post_enabled.is_(True), models.Chat.is_active.is_(True))
    )
    result = await session.execute(stmt)
    settings = result.scalars().all()
    pairs = []
    for cs in settings:
        if cs.chat:
            pairs.append((cs.chat, cs))
    return pairs


# Favorites helpers


async def get_user_by_tg_id(session: AsyncSession, tg_user_id: int) -> Optional[models.User]:
    stmt = select(models.User).where(models.User.tg_user_id == tg_user_id)
    res = await session.execute(stmt)
    return res.scalar_one_or_none()


async def get_chat_by_tg_id(session: AsyncSession, tg_chat_id: int) -> Optional[models.Chat]:
    stmt = select(models.Chat).where(models.Chat.tg_chat_id == tg_chat_id)
    res = await session.execute(stmt)
    return res.scalar_one_or_none()

async def ensure_chat_by_id(session: AsyncSession, tg_chat_id: int, tg_chat: types.Chat) -> tuple[models.Chat, models.ChatSettings]:
    chat = await get_chat_by_tg_id(session, tg_chat_id)
    now = datetime.utcnow()
    if chat is None:
        chat = models.Chat(
            tg_chat_id=tg_chat_id,
            type=tg_chat.type,
            title=tg_chat.title,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        session.add(chat)
        await session.flush()
        logger.info("Created chat via admin picker tg_chat_id=%s type=%s", tg_chat_id, tg_chat.type)
    else:
        chat.title = tg_chat.title
        chat.type = tg_chat.type
        chat.is_active = True
        chat.updated_at = now
        await session.flush()

    settings = await ensure_chat_settings(session, chat)
    return chat, settings


async def deactivate_chat(session: AsyncSession, chat_key: int) -> Optional[models.Chat]:
    stmt = (
        select(models.Chat)
        .options(selectinload(models.Chat.settings))
        .where((models.Chat.id == chat_key) | (models.Chat.tg_chat_id == chat_key))
    )
    result = await session.execute(stmt)
    chat = result.scalar_one_or_none()
    if chat is None:
        return None
    chat.is_active = False
    if chat.settings:
        chat.settings.auto_post_enabled = False
    await session.flush()
    logger.info("Deactivated chat id=%s tg_chat_id=%s", chat.id, chat.tg_chat_id)
    return chat


async def get_favorites_for_user(session: AsyncSession, user: models.User) -> list[models.Favorite]:
    stmt = (
        select(models.Favorite)
        .where(models.Favorite.user_id == user.id)
        .order_by(models.Favorite.sort_order.asc(), models.Favorite.created_at.asc())
    )
    res = await session.execute(stmt)
    return list(res.scalars().all())


async def is_favorite(session: AsyncSession, user: models.User, symbol: str) -> bool:
    symbol = symbol.upper()
    stmt = select(models.Favorite).where(
        models.Favorite.user_id == user.id,
        models.Favorite.symbol == symbol,
    )
    res = await session.execute(stmt)
    return res.scalar_one_or_none() is not None


async def add_favorite_symbol(session: AsyncSession, user: models.User, symbol: str) -> models.Favorite:
    symbol = symbol.upper()
    stmt = select(models.Favorite).where(
        models.Favorite.user_id == user.id,
        models.Favorite.symbol == symbol,
    )
    res = await session.execute(stmt)
    fav = res.scalar_one_or_none()
    if fav:
        return fav

    fav = models.Favorite(
        user_id=user.id,
        symbol=symbol,
        sort_order=0,
        created_at=datetime.utcnow(),
    )
    session.add(fav)
    await session.flush()
    logger.info("Added favorite %s for user_id=%s", symbol, user.id)
    return fav


async def remove_favorite_symbol(session: AsyncSession, user: models.User, symbol: str) -> bool:
    symbol = symbol.upper()
    stmt = select(models.Favorite).where(
        models.Favorite.user_id == user.id,
        models.Favorite.symbol == symbol,
    )
    res = await session.execute(stmt)
    fav = res.scalar_one_or_none()
    if not fav:
        return False
    await session.delete(fav)
    await session.flush()
    logger.info("Removed favorite %s for user_id=%s", symbol, user.id)
    return True


async def list_chats(session: AsyncSession, *, limit: int = 10, offset: int = 0) -> list[models.Chat]:
    stmt = (
        select(models.Chat)
        .where(models.Chat.type != "private", models.Chat.is_active.is_(True))
        .order_by(models.Chat.id)
        .limit(limit)
        .offset(offset)
    )
    result = await session.execute(stmt)
    return result.scalars().all()


async def count_chats(session: AsyncSession) -> int:
    stmt = select(func.count()).select_from(models.Chat).where(models.Chat.type != "private", models.Chat.is_active.is_(True))
    result = await session.execute(stmt)
    return int(result.scalar_one() or 0)


async def get_chat_with_settings(
    session: AsyncSession, chat_id: int
) -> tuple[models.Chat, Optional[models.ChatSettings]]:
    stmt = (
        select(models.Chat)
        .options(selectinload(models.Chat.settings))
        .where(models.Chat.id == chat_id)
    )
    result = await session.execute(stmt)
    chat = result.scalar_one_or_none()
    if chat is None:
        # try fallback lookup by tg_chat_id
        stmt = (
            select(models.Chat)
            .options(selectinload(models.Chat.settings))
            .where(models.Chat.tg_chat_id == chat_id)
        )
        result = await session.execute(stmt)
        chat = result.scalar_one_or_none()
    if chat is None:
        raise ValueError(f"Chat id {chat_id} not found")
    return chat, chat.settings


async def fetch_chat_with_settings(
    session: AsyncSession, chat_key: int
) -> tuple[models.Chat, Optional[models.ChatSettings]]:
    logger.debug("Fetching chat with key=%s", chat_key)
    stmt = (
        select(models.Chat)
        .options(selectinload(models.Chat.settings))
        .where(models.Chat.id == chat_key)
    )
    result = await session.execute(stmt)
    chat = result.scalar_one_or_none()
    if chat is None:
        stmt = (
            select(models.Chat)
            .options(selectinload(models.Chat.settings))
            .where(models.Chat.tg_chat_id == chat_key)
        )
        result = await session.execute(stmt)
        chat = result.scalar_one_or_none()
    if chat is None:
        logger.warning("Chat not found for key=%s (id or tg_chat_id)", chat_key)
        raise ValueError(f"Chat id {chat_key} not found")
    logger.debug("Fetched chat id=%s tg_chat_id=%s", chat.id, chat.tg_chat_id)
    return chat, chat.settings


async def update_chat_settings(
    session: AsyncSession,
    chat: models.Chat,
    *,
    auto_post_enabled: bool | None = None,
    interval_minutes: int | None = None,
    send_mode: str | None = None,
    package_id: int | None = None,
) -> models.ChatSettings:
    settings = await ensure_chat_settings(session, chat)

    if auto_post_enabled is not None:
        settings.auto_post_enabled = auto_post_enabled
    if interval_minutes is not None:
        settings.interval_minutes = interval_minutes
    if send_mode is not None:
        settings.send_mode = send_mode
    if package_id is not None:
        settings.package_id = package_id
    settings.updated_at = datetime.utcnow()
    await session.flush()
    return settings


# Alerts helpers
ConditionType = Literal["above", "below"]
CurrencyMode = Literal["TOMAN", "IRR"]


async def create_alert(
    session: AsyncSession,
    user: models.User,
    chat: models.Chat,
    *,
    symbol: str,
    condition_type: ConditionType,
    threshold_value: float,
    currency_mode: CurrencyMode = "TOMAN",
) -> models.Alert:
    now = datetime.utcnow()
    alert = models.Alert(
        user_id=user.id,
        chat_id=chat.id,
        symbol=symbol.upper(),
        condition_type=condition_type,
        value_from=threshold_value,
        value_to=None,
        currency_mode=currency_mode,
        is_active=True,
        times_triggered=0,
        created_at=now,
        updated_at=now,
    )
    session.add(alert)
    await session.flush()
    logger.info("Created alert %s for user_id=%s", alert.id, user.id)
    return alert


async def list_alerts_for_user(session: AsyncSession, user: models.User) -> list[models.Alert]:
    stmt = select(models.Alert).where(models.Alert.user_id == user.id).order_by(models.Alert.id.desc())
    res = await session.execute(stmt)
    return list(res.scalars().all())


async def deactivate_alert(session: AsyncSession, alert_id: int, user: models.User) -> bool:
    stmt = select(models.Alert).where(models.Alert.id == alert_id, models.Alert.user_id == user.id)
    res = await session.execute(stmt)
    alert = res.scalar_one_or_none()
    if not alert:
        return False
    alert.is_active = False
    alert.updated_at = datetime.utcnow()
    await session.flush()
    logger.info("Deactivated alert %s for user_id=%s", alert_id, user.id)
    return True


async def delete_alert(session: AsyncSession, alert_id: int, user: models.User) -> bool:
    stmt = select(models.Alert).where(models.Alert.id == alert_id, models.Alert.user_id == user.id)
    res = await session.execute(stmt)
    alert = res.scalar_one_or_none()
    if not alert:
        return False
    await session.delete(alert)
    await session.flush()
    logger.info("Deleted alert %s for user_id=%s", alert_id, user.id)
    return True


async def get_active_alerts_for_check(session: AsyncSession) -> list[models.Alert]:
    stmt = select(models.Alert).where(models.Alert.is_active.is_(True))
    res = await session.execute(stmt)
    return list(res.scalars().all())


async def mark_alert_checked(session: AsyncSession, alert: models.Alert, *, now: datetime) -> None:
    alert.last_check_at = now
    alert.updated_at = now
    await session.flush()


async def mark_alert_triggered(
    session: AsyncSession,
    alert: models.Alert,
    *,
    now: datetime,
    deactivate: bool = False,
) -> None:
    alert.triggered_at = now
    alert.times_triggered += 1
    alert.updated_at = now
    if deactivate:
        alert.is_active = False
    await session.flush()
