from __future__ import annotations

from aiogram import F, Router, types, Bot
from aiogram.filters import Command, CommandObject
from aiogram.types import CallbackQuery

from ratecore_bot.api.ratecore_client import RateCoreClient
from ratecore_bot.config import Settings
from ratecore_bot.db import repository
from ratecore_bot.db.session import get_session
from ratecore_bot.db.utils import sync_user_and_chat
from ratecore_bot.ui.keyboards import (
    MAIN_DASHBOARD_CALLBACK,
    MAIN_DASHBOARD_REFRESH_CALLBACK,
    BACK_TO_MAIN_MENU_CALLBACK,
    FAVORITES_OPEN_CALLBACK,
    FAVORITES_REFRESH_CALLBACK,
    FAVORITES_ADD_CALLBACK_PREFIX,
    FAVORITES_REMOVE_CALLBACK_PREFIX,
    ALERTS_OPEN_CALLBACK,
    ALERTS_REFRESH_CALLBACK,
    ALERT_DEACTIVATE_CALLBACK_PREFIX,
    ALERT_DELETE_CALLBACK_PREFIX,
    favorite_toggle_keyboard,
    favorites_overview_keyboard,
    alerts_overview_keyboard,
    main_dashboard_refresh_keyboard,
    main_menu_keyboard,
)
from ratecore_bot.ui.chat_hygiene import cleanup_temp_message, safe_delete_user_command
from ratecore_bot.ui.anchor import show_main_menu_anchor
from ratecore_bot.ui.views import (
    MAIN_DASHBOARD_SYMBOLS,
    format_main_dashboard,
    format_price_message,
    format_favorites_dashboard,
    format_favorites_empty,
    format_alerts_empty,
    format_alerts_list,
    format_main_menu_text,
)
from ratecore_bot.db.repository import clear_main_menu_anchor, get_bot_enabled, get_or_create_global_settings

router = Router()


async def _is_bot_enabled_for_user(user_id: int | None, settings: Settings) -> tuple[bool, str]:
    async with get_session() as session:
        enabled = await get_bot_enabled(session)
        gs = await get_or_create_global_settings(session)
        maintenance_text = gs.maintenance_message or "The bot is temporarily under maintenance. Please try again later."
    if enabled:
        return True, ""
    if user_id == settings.admin_id:
        return True, ""
    return False, maintenance_text


@router.message(Command("start"))
async def start(message: types.Message, settings: Settings, bot: Bot) -> None:
    ok, maint = await _is_bot_enabled_for_user(message.from_user.id if message.from_user else None, settings)
    if not ok:
        await message.answer(maint)
        return
    await sync_user_and_chat(message, settings)
    await show_main_menu_anchor(bot, message.chat, settings)
    await safe_delete_user_command(message, settings)


@router.message(Command("restart"))
async def restart(message: types.Message, settings: Settings, bot: Bot) -> None:
    """Recreate main menu anchor if it was deleted."""
    ok, maint = await _is_bot_enabled_for_user(message.from_user.id if message.from_user else None, settings)
    if not ok:
        await message.answer(maint)
        return
    await sync_user_and_chat(message, settings)
    async with get_session() as session:
        await clear_main_menu_anchor(session, message.chat.id)
        await session.commit()
    await show_main_menu_anchor(bot, message.chat, settings)
    await safe_delete_user_command(message, settings)


@router.message(Command("ping"))
async def ping(message: types.Message, settings: Settings) -> None:
    ok, maint = await _is_bot_enabled_for_user(message.from_user.id if message.from_user else None, settings)
    if not ok:
        await message.answer(maint)
        return
    await sync_user_and_chat(message, settings)
    await message.answer("pong")
    await safe_delete_user_command(message, settings)


@router.message(Command("price"))
async def price(message: types.Message, command: CommandObject, settings: Settings, ratecore_client: RateCoreClient) -> None:
    ok, maint = await _is_bot_enabled_for_user(message.from_user.id if message.from_user else None, settings)
    if not ok:
        await message.answer(maint)
        return
    await sync_user_and_chat(message, settings)
    if not command.args:
        usage_msg = await message.answer("Usage: /price SYMBOL")
        await safe_delete_user_command(message, settings)
        await cleanup_temp_message(usage_msg, delay=10.0)
        return
    symbol = command.args.strip().upper()
    try:
        data = await ratecore_client.get_price(symbol)
    except Exception as exc:  # noqa: BLE001
        err_msg = await message.answer(f"Failed to fetch price for {symbol}: {exc}")
        await safe_delete_user_command(message, settings)
        await cleanup_temp_message(err_msg, delay=10.0)
        return
    is_fav = False
    async with get_session() as session:
        user = await repository.get_user_by_tg_id(session, message.from_user.id) if message.from_user else None
        if user:
            is_fav = await repository.is_favorite(session, user, symbol)
    kb = favorite_toggle_keyboard(symbol, is_fav)
    await message.answer(format_price_message(symbol, data), reply_markup=kb)
    await safe_delete_user_command(message, settings)


@router.callback_query(F.data == MAIN_DASHBOARD_CALLBACK)
async def on_main_dashboard_show(callback: CallbackQuery, settings: Settings, ratecore_client: RateCoreClient) -> None:
    ok, maint = await _is_bot_enabled_for_user(callback.from_user.id if callback.from_user else None, settings)
    if not ok:
        if callback.message:
            await callback.message.answer(maint)
        await callback.answer()
        return
    if callback.message:
        await sync_user_and_chat(callback.message, settings)
    items = await ratecore_client.get_prices_batch(MAIN_DASHBOARD_SYMBOLS)
    text = format_main_dashboard(items)
    await callback.message.edit_text(text, reply_markup=main_dashboard_refresh_keyboard())  # type: ignore[union-attr]
    await callback.answer()


@router.callback_query(F.data == MAIN_DASHBOARD_REFRESH_CALLBACK)
async def on_main_dashboard_refresh(callback: CallbackQuery, settings: Settings, ratecore_client: RateCoreClient) -> None:
    ok, maint = await _is_bot_enabled_for_user(callback.from_user.id if callback.from_user else None, settings)
    if not ok:
        if callback.message:
            await callback.message.answer(maint)
        await callback.answer()
        return
    if callback.message:
        await sync_user_and_chat(callback.message, settings)
    items = await ratecore_client.get_prices_batch(MAIN_DASHBOARD_SYMBOLS)
    text = format_main_dashboard(items)
    await callback.message.edit_text(text, reply_markup=main_dashboard_refresh_keyboard())  # type: ignore[union-attr]
    await callback.answer(text="Refreshed ✅")


@router.callback_query(F.data == BACK_TO_MAIN_MENU_CALLBACK)
async def on_back_to_main_menu(callback: CallbackQuery, settings: Settings) -> None:
    ok, maint = await _is_bot_enabled_for_user(callback.from_user.id if callback.from_user else None, settings)
    if not ok:
        if callback.message:
            await callback.message.answer(maint)
        await callback.answer()
        return
    if callback.message is None:
        await callback.answer()
        return
    await sync_user_and_chat(callback.message, settings)
    await callback.message.edit_text(
        format_main_menu_text(),
        reply_markup=main_menu_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == FAVORITES_OPEN_CALLBACK)
async def on_favorites_open(callback: CallbackQuery, settings: Settings, ratecore_client: RateCoreClient) -> None:
    if callback.message is None or callback.from_user is None:
        await callback.answer()
        return

    await sync_user_and_chat(callback.message, settings)

    async with get_session() as session:
        user = await repository.get_user_by_tg_id(session, callback.from_user.id)
        if user is None:
            await callback.answer("User not found.", show_alert=True)
            return
        favorites = await repository.get_favorites_for_user(session, user)

    if not favorites:
        text = format_favorites_empty()
        kb = favorites_overview_keyboard(has_items=False)
        await callback.message.edit_text(text, reply_markup=kb)
        await callback.answer()
        return

    symbols = [fav.symbol for fav in favorites]
    items = await ratecore_client.get_prices_batch(symbols)
    text = format_favorites_dashboard(items)
    kb = favorites_overview_keyboard(has_items=True)
    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data == FAVORITES_REFRESH_CALLBACK)
async def on_favorites_refresh(callback: CallbackQuery, settings: Settings, ratecore_client: RateCoreClient) -> None:
    if callback.message is None or callback.from_user is None:
        await callback.answer()
        return

    async with get_session() as session:
        user = await repository.get_user_by_tg_id(session, callback.from_user.id)
        if user is None:
            await callback.answer("User not found.", show_alert=True)
            return
        favorites = await repository.get_favorites_for_user(session, user)

    if not favorites:
        text = format_favorites_empty()
        kb = favorites_overview_keyboard(has_items=False)
        await callback.message.edit_text(text, reply_markup=kb)
        await callback.answer("No favorites yet.", show_alert=False)
        return

    symbols = [fav.symbol for fav in favorites]
    items = await ratecore_client.get_prices_batch(symbols)
    text = format_favorites_dashboard(items)
    kb = favorites_overview_keyboard(has_items=True)
    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer("Refreshed ✅", show_alert=False)


@router.callback_query(F.data.startswith(FAVORITES_ADD_CALLBACK_PREFIX))
async def on_favorite_add(callback: CallbackQuery, settings: Settings) -> None:
    if callback.from_user is None or callback.message is None:
        await callback.answer()
        return

    symbol = callback.data.removeprefix(FAVORITES_ADD_CALLBACK_PREFIX).upper().strip()

    async with get_session() as session:
        user = await repository.get_user_by_tg_id(session, callback.from_user.id)
        if user is None:
            await callback.answer("Please send /start first.", show_alert=True)
            return
        await repository.add_favorite_symbol(session, user, symbol)

    kb = favorite_toggle_keyboard(symbol, is_favorite=True)
    try:
        await callback.message.edit_reply_markup(reply_markup=kb)
    except Exception:
        pass

    await callback.answer(f"Added {symbol} to favorites ⭐", show_alert=False)


@router.callback_query(F.data.startswith(FAVORITES_REMOVE_CALLBACK_PREFIX))
async def on_favorite_remove(callback: CallbackQuery, settings: Settings) -> None:
    if callback.from_user is None or callback.message is None:
        await callback.answer()
        return

    symbol = callback.data.removeprefix(FAVORITES_REMOVE_CALLBACK_PREFIX).upper().strip()

    async with get_session() as session:
        user = await repository.get_user_by_tg_id(session, callback.from_user.id)
        if user is None:
            await callback.answer("Please send /start first.", show_alert=True)
            return
        await repository.remove_favorite_symbol(session, user, symbol)

    kb = favorite_toggle_keyboard(symbol, is_favorite=False)
    try:
        await callback.message.edit_reply_markup(reply_markup=kb)
    except Exception:
        pass

    await callback.answer(f"Removed {symbol} from favorites", show_alert=False)


@router.message(Command("alerts"))
async def cmd_alerts(message: types.Message, settings: Settings) -> None:
    await sync_user_and_chat(message, settings)
    async with get_session() as session:
        user = await repository.get_user_by_tg_id(session, message.from_user.id) if message.from_user else None
        if user is None:
            await message.answer("User not found.")
            return
        alerts = await repository.list_alerts_for_user(session, user)
    if not alerts:
        text = format_alerts_empty()
        kb = alerts_overview_keyboard(has_items=False)
    else:
        text = format_alerts_list(alerts)
        kb = alerts_overview_keyboard(has_items=True)
    await message.answer(text, reply_markup=kb)


@router.callback_query(F.data == ALERTS_OPEN_CALLBACK)
async def on_alerts_open(callback: CallbackQuery, settings: Settings) -> None:
    if callback.message is None or callback.from_user is None:
        await callback.answer()
        return
    await sync_user_and_chat(callback.message, settings)
    async with get_session() as session:
        user = await repository.get_user_by_tg_id(session, callback.from_user.id)
        if user is None:
            await callback.answer("User not found.", show_alert=True)
            return
        alerts = await repository.list_alerts_for_user(session, user)

    if not alerts:
        text = format_alerts_empty()
        kb = alerts_overview_keyboard(has_items=False)
    else:
        text = format_alerts_list(alerts)
        kb = alerts_overview_keyboard(has_items=True)
    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data == ALERTS_REFRESH_CALLBACK)
async def on_alerts_refresh(callback: CallbackQuery, settings: Settings) -> None:
    if callback.message is None or callback.from_user is None:
        await callback.answer()
        return

    async with get_session() as session:
        user = await repository.get_user_by_tg_id(session, callback.from_user.id)
        if user is None:
            await callback.answer("User not found.", show_alert=True)
            return
        alerts = await repository.list_alerts_for_user(session, user)

    if not alerts:
        text = format_alerts_empty()
        kb = alerts_overview_keyboard(has_items=False)
    else:
        text = format_alerts_list(alerts)
        kb = alerts_overview_keyboard(has_items=True)
    await callback.message.edit_text(text, reply_markup=kb)  # type: ignore[union-attr]
    await callback.answer("Refreshed ✅")
