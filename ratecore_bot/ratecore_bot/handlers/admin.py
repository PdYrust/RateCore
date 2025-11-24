from __future__ import annotations

import logging
from typing import Optional, Dict, Tuple

from aiogram import F, Router, types, Bot
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.exceptions import TelegramBadRequest

from ratecore_bot.api.ratecore_client import RateCoreClient
from ratecore_bot.config import Settings
from ratecore_bot.db.repository import (
    count_chats,
    ensure_chat_by_id,
    deactivate_chat,
    fetch_chat_with_settings,
    get_chat_settings_by_chat_id,
    get_or_create_global_settings,
    set_bot_enabled,
    list_chats,
    update_chat_settings,
)
from ratecore_bot.db.session import get_session
from ratecore_bot.ui.keyboards import (
    ADMIN_ADD_CHANNEL_CALLBACK,
    ADMIN_ADD_GROUP_CALLBACK,
    ADMIN_CHAT_DETAIL_CALLBACK,
    ADMIN_CHAT_INTERVAL_CALLBACK,
    ADMIN_CHAT_SENDMODE_CALLBACK,
    ADMIN_CHAT_TEST_CALLBACK,
    ADMIN_CHAT_TOGGLE_AUTO_CALLBACK,
    ADMIN_CHAT_REMOVE_CONFIRM_CALLBACK,
    ADMIN_CHAT_REMOVE_YES_CALLBACK,
    ADMIN_CHAT_REMOVE_CANCEL_CALLBACK,
    ADMIN_CHATS_PAGE_CALLBACK,
    ADMIN_MENU_CALLBACK,
    ADMIN_MANAGED_CHATS_CALLBACK,
    ADMIN_SETTINGS_MENU_CALLBACK,
    ADMIN_SETTINGS_BOT_POWER_CALLBACK,
    ADMIN_SETTINGS_BOT_TOGGLE_CALLBACK,
    ADMIN_SETTINGS_API_INFO_CALLBACK,
    ADMIN_SETTINGS_OPS_INFO_CALLBACK,
    admin_chat_detail_keyboard,
    admin_chats_list_keyboard,
    admin_main_menu_keyboard,
    admin_settings_menu_keyboard,
    admin_bot_power_keyboard,
    admin_back_to_settings_keyboard,
    admin_request_channel_keyboard,
    admin_request_group_keyboard,
    admin_chat_remove_confirm_keyboard,
    remove_reply_keyboard,
)
from ratecore_bot.ui.chat_hygiene import safe_delete_user_command, cleanup_temp_message, safe_delete_message
from ratecore_bot.ui.anchor import show_admin_menu_anchor
from ratecore_bot.ui.views import (
    MAIN_DASHBOARD_SYMBOLS,
    format_admin_add_channel_intro,
    format_admin_add_group_intro,
    format_admin_chat_added_success,
    format_admin_chat_detail,
    format_admin_chat_remove_confirm,
    format_admin_chat_removed_success,
    format_admin_chats_list,
    format_admin_main_menu,
    format_admin_settings_menu,
    format_admin_bot_power,
    format_admin_api_info,
    format_admin_ops_info,
    format_chat_not_managed,
    format_main_dashboard,
)

router = Router()
logger = logging.getLogger(__name__)
# Track last prompt message sent for chat selection per admin user
_pending_chat_prompt: Dict[int, Tuple[int, int]] = {}


def _parse_int_from_callback(data: str, prefix: str) -> Optional[int]:
    try:
        raw = data.removeprefix(prefix)
        return int(raw)
    except Exception as exc:
        logger.warning("Failed to parse int from callback '%s' with prefix '%s': %s", data, prefix, exc)
        return None


@router.message(Command("admin"))
async def cmd_admin(message: types.Message, settings: Settings) -> None:
    if message.from_user is None or message.from_user.id != settings.admin_id:
        denial = await message.answer("❌ Not authorized.")
        await cleanup_temp_message(denial, delay=5.0)
        return

    # Use anchor message for admin panel
    await show_admin_menu_anchor(message.bot, message.chat, settings)
    await safe_delete_user_command(message, settings)


@router.callback_query(F.data == ADMIN_MENU_CALLBACK)
async def on_admin_menu(callback: types.CallbackQuery, settings: Settings) -> None:
    if callback.from_user is None or callback.from_user.id != settings.admin_id:
        await callback.answer("Not authorized", show_alert=True)
        return
    try:
        await callback.message.edit_text(format_admin_main_menu(), reply_markup=admin_main_menu_keyboard())  # type: ignore[union-attr]
    except TelegramBadRequest:
        # Ignore if content is identical
        pass
    await callback.answer()


@router.callback_query(F.data == ADMIN_MANAGED_CHATS_CALLBACK)
async def on_admin_managed_chats(callback: types.CallbackQuery, settings: Settings) -> None:
    if callback.from_user is None or callback.from_user.id != settings.admin_id:
        await callback.answer("Not authorized", show_alert=True)
        return
    # Reuse page 0 listing
    limit = 10
    offset = 0
    async with get_session() as session:
        total = await count_chats(session)
        chats = await list_chats(session, limit=limit, offset=offset)
    has_next = (offset + limit) < total
    text = format_admin_chats_list(chats, page=0, total=total)
    kb = admin_chats_list_keyboard(chats, page=0, has_next=has_next)
    await callback.message.edit_text(text, reply_markup=kb)  # type: ignore[union-attr]
    await callback.answer()


@router.callback_query(F.data == ADMIN_SETTINGS_MENU_CALLBACK)
async def on_admin_settings_menu(callback: types.CallbackQuery, settings: Settings) -> None:
    if callback.from_user is None or callback.from_user.id != settings.admin_id:
        await callback.answer("Not authorized", show_alert=True)
        return
    await callback.message.edit_text(format_admin_settings_menu(), reply_markup=admin_settings_menu_keyboard())  # type: ignore[union-attr]
    await callback.answer()


@router.callback_query(F.data == ADMIN_SETTINGS_BOT_POWER_CALLBACK)
async def on_admin_bot_power(callback: types.CallbackQuery, settings: Settings) -> None:
    if callback.from_user is None or callback.from_user.id != settings.admin_id:
        await callback.answer("Not authorized", show_alert=True)
        return
    async with get_session() as session:
        gs = await get_or_create_global_settings(session)
    await callback.message.edit_text(format_admin_bot_power(gs), reply_markup=admin_bot_power_keyboard(gs))  # type: ignore[union-attr]
    await callback.answer()


@router.callback_query(F.data == ADMIN_SETTINGS_BOT_TOGGLE_CALLBACK)
async def on_admin_bot_toggle(callback: types.CallbackQuery, settings: Settings) -> None:
    if callback.from_user is None or callback.from_user.id != settings.admin_id:
        await callback.answer("Not authorized", show_alert=True)
        return
    async with get_session() as session:
        gs = await get_or_create_global_settings(session)
        new_state = not gs.bot_enabled
        gs = await set_bot_enabled(session, new_state)
        await session.commit()
    await callback.message.edit_text(format_admin_bot_power(gs), reply_markup=admin_bot_power_keyboard(gs))  # type: ignore[union-attr]
    await callback.answer(text=f"Bot {'enabled' if gs.bot_enabled else 'disabled'}")


@router.callback_query(F.data == ADMIN_SETTINGS_API_INFO_CALLBACK)
async def on_admin_api_info(callback: types.CallbackQuery, settings: Settings) -> None:
    if callback.from_user is None or callback.from_user.id != settings.admin_id:
        await callback.answer("Not authorized", show_alert=True)
        return
    text = format_admin_api_info(settings)
    await callback.message.edit_text(text, reply_markup=admin_back_to_settings_keyboard())  # type: ignore[union-attr]
    await callback.answer()


@router.callback_query(F.data == ADMIN_SETTINGS_OPS_INFO_CALLBACK)
async def on_admin_ops_info(callback: types.CallbackQuery, settings: Settings) -> None:
    if callback.from_user is None or callback.from_user.id != settings.admin_id:
        await callback.answer("Not authorized", show_alert=True)
        return
    text = format_admin_ops_info()
    await callback.message.edit_text(text, reply_markup=admin_back_to_settings_keyboard())  # type: ignore[union-attr]
    await callback.answer()


@router.callback_query(F.data == ADMIN_ADD_GROUP_CALLBACK)
async def on_admin_add_group(callback: types.CallbackQuery, settings: Settings) -> None:
    if callback.from_user is None or callback.from_user.id != settings.admin_id:
        await callback.answer("Not authorized", show_alert=True)
        return
    await callback.answer()
    prompt = await callback.message.answer(
        format_admin_add_group_intro(),
        reply_markup=admin_request_group_keyboard(),
    )
    # Clean up prompt after a grace period (~2 minutes) to avoid stale prompts.
    await cleanup_temp_message(prompt, delay=120.0)
    if callback.from_user:
        _pending_chat_prompt[callback.from_user.id] = (prompt.chat.id, prompt.message_id)


@router.callback_query(F.data == ADMIN_ADD_CHANNEL_CALLBACK)
async def on_admin_add_channel(callback: types.CallbackQuery, settings: Settings) -> None:
    if callback.from_user is None or callback.from_user.id != settings.admin_id:
        await callback.answer("Not authorized", show_alert=True)
        return
    await callback.answer()
    prompt = await callback.message.answer(
        format_admin_add_channel_intro(),
        reply_markup=admin_request_channel_keyboard(),
    )
    # Clean up prompt after a grace period (~2 minutes) to avoid stale prompts.
    await cleanup_temp_message(prompt, delay=120.0)
    if callback.from_user:
        _pending_chat_prompt[callback.from_user.id] = (prompt.chat.id, prompt.message_id)


@router.callback_query(F.data.startswith(ADMIN_CHATS_PAGE_CALLBACK))
async def on_admin_chats_page(callback: types.CallbackQuery, settings: Settings) -> None:
    if callback.from_user is None or callback.from_user.id != settings.admin_id:
        await callback.answer("Not authorized", show_alert=True)
        return

    logger.info("Admin managed chats page callback data=%s", callback.data)
    page_str = callback.data.removeprefix(ADMIN_CHATS_PAGE_CALLBACK) if callback.data else "0"
    try:
        page = int(page_str)
    except ValueError:
        await callback.answer("Invalid page", show_alert=True)
        return

    limit = 10
    offset = page * limit

    async with get_session() as session:
        total = await count_chats(session)
        chats = await list_chats(session, limit=limit, offset=offset)

    has_next = (offset + limit) < total
    text = format_admin_chats_list(chats, page=page, total=total)
    kb = admin_chats_list_keyboard(chats, page=page, has_next=has_next)

    await callback.message.edit_text(text, reply_markup=kb)  # type: ignore[union-attr]
    await callback.answer()


@router.callback_query(F.data.regexp(r"^admin:chat:-?\d+$"))
async def on_admin_chat_detail(callback: types.CallbackQuery, settings: Settings) -> None:
    if callback.from_user is None or callback.from_user.id != settings.admin_id:
        await callback.answer("Not authorized", show_alert=True)
        return

    chat_key = _parse_int_from_callback(callback.data or "", ADMIN_CHAT_DETAIL_CALLBACK)
    if chat_key is None:
        await callback.answer("Invalid chat id", show_alert=True)
        return

    logger.info("Admin chat detail requested for key=%s", chat_key)
    try:
        async with get_session() as session:
            chat, chat_settings = await fetch_chat_with_settings(session, chat_key=chat_key)
            if not chat.is_active:
                await callback.answer(format_chat_not_managed(), show_alert=True)
                return
            if chat_settings is None:
                chat_settings = await update_chat_settings(session, chat, auto_post_enabled=False)
    except ValueError:
        logger.warning("Admin chat detail failed: chat not found for key=%s", chat_key)
        await callback.answer("Chat not found. Please re-add via admin menu.", show_alert=True)
        return

    text = format_admin_chat_detail(chat, chat_settings)
    kb = admin_chat_detail_keyboard(chat, chat_settings)
    await callback.message.edit_text(text, reply_markup=kb)  # type: ignore[union-attr]
    await callback.answer()


@router.callback_query(F.data.startswith(ADMIN_CHAT_TOGGLE_AUTO_CALLBACK))
async def on_admin_chat_toggle_auto(callback: types.CallbackQuery, settings: Settings) -> None:
    if callback.from_user is None or callback.from_user.id != settings.admin_id:
        await callback.answer("Not authorized", show_alert=True)
        return

    chat_key = _parse_int_from_callback(callback.data or "", ADMIN_CHAT_TOGGLE_AUTO_CALLBACK)
    if chat_key is None:
        await callback.answer("Invalid chat id", show_alert=True)
        return

    logger.info("Admin toggle auto-post for key=%s", chat_key)
    try:
        async with get_session() as session:
            chat, chat_settings = await fetch_chat_with_settings(session, chat_key=chat_key)
            if not chat.is_active:
                await callback.answer(format_chat_not_managed(), show_alert=True)
                return
            if chat_settings is None:
                chat_settings = await update_chat_settings(session, chat, auto_post_enabled=False)
            new_value = not chat_settings.auto_post_enabled
            chat_settings = await update_chat_settings(session, chat, auto_post_enabled=new_value)
            logger.info("Admin toggled auto_post_enabled=%s for chat_id=%s", new_value, chat_key)
    except ValueError:
        logger.warning("Admin toggle failed: chat not found for key=%s", chat_key)
        await callback.answer("Chat not found. Please re-add via admin menu.", show_alert=True)
        return

    text = format_admin_chat_detail(chat, chat_settings)
    kb = admin_chat_detail_keyboard(chat, chat_settings)
    await callback.message.edit_text(text, reply_markup=kb)  # type: ignore[union-attr]
    await callback.answer(text="Updated ✅")


@router.callback_query(F.data.startswith(ADMIN_CHAT_INTERVAL_CALLBACK))
async def on_admin_chat_interval(callback: types.CallbackQuery, settings: Settings) -> None:
    if callback.from_user is None or callback.from_user.id != settings.admin_id:
        await callback.answer("Not authorized", show_alert=True)
        return

    chat_key = _parse_int_from_callback(callback.data or "", ADMIN_CHAT_INTERVAL_CALLBACK)
    if chat_key is None:
        await callback.answer("Invalid chat id", show_alert=True)
        return

    logger.info("Admin interval toggle for key=%s", chat_key)
    intervals = [5, 10, 15, 30, 60]

    try:
        async with get_session() as session:
            chat, chat_settings = await fetch_chat_with_settings(session, chat_key=chat_key)
            if not chat.is_active:
                await callback.answer(format_chat_not_managed(), show_alert=True)
                return
            if chat_settings is None:
                chat_settings = await update_chat_settings(session, chat, interval_minutes=intervals[0])
            current = chat_settings.interval_minutes
            try:
                idx = intervals.index(current)
                new_interval = intervals[(idx + 1) % len(intervals)]
            except ValueError:
                new_interval = intervals[0]
            chat_settings = await update_chat_settings(session, chat, interval_minutes=new_interval)
            logger.info("Admin set interval_minutes=%s for chat_id=%s", new_interval, chat_key)
    except ValueError:
        logger.warning("Admin interval failed: chat not found for key=%s", chat_key)
        await callback.answer("Chat not found. Please re-add via admin menu.", show_alert=True)
        return

    text = format_admin_chat_detail(chat, chat_settings)
    kb = admin_chat_detail_keyboard(chat, chat_settings)
    await callback.message.edit_text(text, reply_markup=kb)  # type: ignore[union-attr]
    await callback.answer(text="Updated ✅")


@router.callback_query(F.data.startswith(ADMIN_CHAT_SENDMODE_CALLBACK))
async def on_admin_chat_sendmode(callback: types.CallbackQuery, settings: Settings) -> None:
    if callback.from_user is None or callback.from_user.id != settings.admin_id:
        await callback.answer("Not authorized", show_alert=True)
        return

    chat_key = _parse_int_from_callback(callback.data or "", ADMIN_CHAT_SENDMODE_CALLBACK)
    if chat_key is None:
        await callback.answer("Invalid chat id", show_alert=True)
        return

    logger.info("Admin sendmode toggle for key=%s", chat_key)
    try:
        async with get_session() as session:
            chat, chat_settings = await fetch_chat_with_settings(session, chat_key=chat_key)
            if not chat.is_active:
                await callback.answer(format_chat_not_managed(), show_alert=True)
                return
            if chat_settings is None:
                chat_settings = await update_chat_settings(session, chat, send_mode="edit")
            new_mode = "new" if chat_settings.send_mode == "edit" else "edit"
            chat_settings = await update_chat_settings(session, chat, send_mode=new_mode)
            logger.info("Admin set send_mode=%s for chat_id=%s", new_mode, chat_key)
    except ValueError:
        logger.warning("Admin sendmode failed: chat not found for key=%s", chat_key)
        await callback.answer("Chat not found. Please re-add via admin menu.", show_alert=True)
        return

    text = format_admin_chat_detail(chat, chat_settings)
    kb = admin_chat_detail_keyboard(chat, chat_settings)
    await callback.message.edit_text(text, reply_markup=kb)  # type: ignore[union-attr]
    await callback.answer(text="Updated ✅")


@router.callback_query(F.data.startswith(ADMIN_CHAT_TEST_CALLBACK))
async def on_admin_chat_test(
    callback: types.CallbackQuery,
    settings: Settings,
    ratecore_client: RateCoreClient,
) -> None:
    if callback.from_user is None or callback.from_user.id != settings.admin_id:
        await callback.answer("Not authorized", show_alert=True)
        return

    chat_key = _parse_int_from_callback(callback.data or "", ADMIN_CHAT_TEST_CALLBACK)
    if chat_key is None:
        await callback.answer("Invalid chat id", show_alert=True)
        return

    logger.info("Admin send test for key=%s", chat_key)
    try:
        async with get_session() as session:
            chat, chat_settings = await fetch_chat_with_settings(session, chat_key=chat_key)
            if not chat.is_active:
                await callback.answer(format_chat_not_managed(), show_alert=True)
                return
            if chat_settings is None:
                chat_settings = await update_chat_settings(session, chat, auto_post_enabled=False)
    except ValueError:
        logger.warning("Admin test failed: chat not found for key=%s", chat_key)
        await callback.answer("Chat not found. Please re-add via admin menu.", show_alert=True)
        return

    items = await ratecore_client.get_prices_batch(MAIN_DASHBOARD_SYMBOLS)
    text = format_main_dashboard(items)
    try:
        await callback.bot.send_message(chat.tg_chat_id, text)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to send test message to chat_id=%s: %s", chat.tg_chat_id, exc)
        await callback.answer("Failed to send test message", show_alert=True)
        return

    await callback.answer("Test message sent ✅", show_alert=True)


@router.message(F.chat_shared)
async def on_admin_chat_shared(message: types.Message, settings: Settings) -> None:
    shared = message.chat_shared
    if shared is None:
        return
    if message.from_user is None or message.from_user.id != settings.admin_id:
        return

    req_id = shared.request_id
    if req_id not in (1001, 1002):
        return

    try:
        tg_chat = await message.bot.get_chat(shared.chat_id)
    except TelegramBadRequest as exc:
        logger.warning("Failed to fetch chat %s: %s", shared.chat_id, exc)
        warn = await message.answer(
            "❌ I couldn't access that chat. Please add the bot as an admin to the selected chat and try again.",
            reply_markup=remove_reply_keyboard(),
        )
        await cleanup_temp_message(warn, delay=8.0)
        return
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to fetch chat %s: %s", shared.chat_id, exc)
        warn = await message.answer("Failed to fetch chat info.", reply_markup=remove_reply_keyboard())
        await cleanup_temp_message(warn, delay=8.0)
        return
    async with get_session() as session:
        chat, chat_settings = await ensure_chat_by_id(session, shared.chat_id, tg_chat)
        # If there is an existing admin anchor for the admin chat itself, remove it and clear stored id.
        admin_settings = await get_chat_settings_by_chat_id(session, message.chat.id)
        if admin_settings and admin_settings.admin_menu_message_id:
            try:
                await message.bot.delete_message(message.chat.id, admin_settings.admin_menu_message_id)
            except Exception:
                pass
            admin_settings.admin_menu_message_id = None
            await session.flush()
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Open settings", callback_data=f"{ADMIN_CHAT_DETAIL_CALLBACK}{chat.tg_chat_id}")],
            [InlineKeyboardButton(text="⬅ Back", callback_data=ADMIN_MENU_CALLBACK)],
        ]
    )
    ack_msg = await message.answer("✅ Chat received.", reply_markup=remove_reply_keyboard())
    await message.answer(
        format_admin_chat_added_success(tg_chat),
        reply_markup=kb,
    )
    # Remove the user-shared stub message after a short delay to keep the chat clean.
    await safe_delete_message(message, delay=2.0)
    await cleanup_temp_message(ack_msg, delay=2.0)
    # Delete the selection prompt if we still know it
    if message.from_user and message.from_user.id in _pending_chat_prompt:
        chat_id, msg_id = _pending_chat_prompt.pop(message.from_user.id)
        try:
            await message.bot.delete_message(chat_id, msg_id)
        except Exception:
            pass


@router.callback_query(F.data.startswith(ADMIN_CHAT_REMOVE_CONFIRM_CALLBACK))
async def on_admin_chat_remove_confirm(callback: types.CallbackQuery, settings: Settings) -> None:
    if callback.from_user is None or callback.from_user.id != settings.admin_id:
        await callback.answer("Not authorized", show_alert=True)
        return

    chat_key = _parse_int_from_callback(callback.data or "", ADMIN_CHAT_REMOVE_CONFIRM_CALLBACK)
    if chat_key is None:
        await callback.answer("Invalid chat id", show_alert=True)
        return

    try:
        async with get_session() as session:
            chat, _ = await fetch_chat_with_settings(session, chat_key=chat_key)
            if not chat.is_active:
                await callback.answer(format_chat_not_managed(), show_alert=True)
                return
    except ValueError:
        await callback.answer("Chat not found.", show_alert=True)
        return

    text = format_admin_chat_remove_confirm(chat)
    kb = admin_chat_remove_confirm_keyboard(chat.tg_chat_id)
    await callback.message.edit_text(text, reply_markup=kb)  # type: ignore[union-attr]
    await callback.answer()


@router.callback_query(F.data.startswith(ADMIN_CHAT_REMOVE_YES_CALLBACK))
async def on_admin_chat_remove_yes(callback: types.CallbackQuery, settings: Settings) -> None:
    if callback.from_user is None or callback.from_user.id != settings.admin_id:
        await callback.answer("Not authorized", show_alert=True)
        return

    chat_key = _parse_int_from_callback(callback.data or "", ADMIN_CHAT_REMOVE_YES_CALLBACK)
    if chat_key is None:
        await callback.answer("Invalid chat id", show_alert=True)
        return

    async with get_session() as session:
        chat = await deactivate_chat(session, chat_key)
        if chat is None:
            await callback.answer("Chat not found.", show_alert=True)
            return
        await session.commit()
    logger.info("Admin removed chat key=%s", chat_key)

    text = format_admin_chat_removed_success(chat)
    await callback.message.edit_text(text, reply_markup=admin_main_menu_keyboard())  # type: ignore[union-attr]
    await callback.answer("Removed")


@router.callback_query(F.data.startswith(ADMIN_CHAT_REMOVE_CANCEL_CALLBACK))
async def on_admin_chat_remove_cancel(callback: types.CallbackQuery, settings: Settings) -> None:
    if callback.from_user is None or callback.from_user.id != settings.admin_id:
        await callback.answer("Not authorized", show_alert=True)
        return

    chat_key = _parse_int_from_callback(callback.data or "", ADMIN_CHAT_REMOVE_CANCEL_CALLBACK)
    if chat_key is None:
        await callback.answer("Invalid chat id", show_alert=True)
        return

    try:
        async with get_session() as session:
            chat, chat_settings = await fetch_chat_with_settings(session, chat_key=chat_key)
            if chat_settings is None:
                chat_settings = await update_chat_settings(session, chat, auto_post_enabled=False)
            text = format_admin_chat_detail(chat, chat_settings)
            kb = admin_chat_detail_keyboard(chat, chat_settings)
            await callback.message.edit_text(text, reply_markup=kb)  # type: ignore[union-attr]
    except ValueError:
        await callback.answer("Chat not found.", show_alert=True)
        return

    await callback.answer("Cancelled")
