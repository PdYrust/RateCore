from __future__ import annotations

import logging
from typing import Optional, Tuple

from aiogram import types
from sqlalchemy.ext.asyncio import AsyncSession

from ratecore_bot.config import Settings
from ratecore_bot.db import models
from ratecore_bot.db.repository import ensure_chat_settings, get_or_create_chat, get_or_create_user
from ratecore_bot.db.session import get_session

logger = logging.getLogger(__name__)


async def sync_user_and_chat(
    message: types.Message,
    settings: Settings,
    session_factory=None,
) -> Tuple[Optional[models.User], Optional[models.Chat]]:
    if not message.from_user:
        logger.debug("No from_user in message, skipping sync.")
        return None, None

    if session_factory is None:
        session_factory = getattr(settings, "session_factory", None)

    async with get_session(session_factory) as session:  # type: AsyncSession
        is_admin = message.from_user.id == settings.admin_id
        user = await get_or_create_user(session, message.from_user, is_admin=is_admin)

        chat_obj = None
        if message.chat:
            chat_obj = await get_or_create_chat(session, message.chat)
            if message.chat.type in {"group", "supergroup", "channel"}:
                await ensure_chat_settings(session, chat_obj)

        return user, chat_obj
