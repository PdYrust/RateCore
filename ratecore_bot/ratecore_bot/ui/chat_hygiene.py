from __future__ import annotations

import asyncio
import logging
from typing import Optional

from aiogram import types
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError, TelegramRetryAfter

from ratecore_bot.config import Settings

logger = logging.getLogger(__name__)


async def safe_delete_message(msg: Optional[types.Message], delay: float | None = None) -> None:
    """Delete a message safely without raising exceptions."""
    if msg is None:
        return
    try:
        if delay is not None:
            await asyncio.sleep(delay)
        await msg.delete()
    except (TelegramBadRequest, TelegramForbiddenError, TelegramRetryAfter) as exc:
        logger.debug("safe_delete_message: could not delete message %s: %s", getattr(msg, "message_id", "?"), exc)
    except Exception as exc:  # noqa: BLE001
        logger.debug("safe_delete_message: unexpected error for message %s: %s", getattr(msg, "message_id", "?"), exc)


async def safe_delete_user_command(msg: types.Message, settings: Settings) -> None:
    """Delete the user's command message in private chats only."""
    if msg.chat.type == "private":
        await safe_delete_message(msg)


async def cleanup_temp_message(msg: Optional[types.Message], delay: float = 5.0) -> None:
    """Delete a temporary bot message after a short delay."""
    if msg is None:
        return
    await safe_delete_message(msg, delay=delay)
