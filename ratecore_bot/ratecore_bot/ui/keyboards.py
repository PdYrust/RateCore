from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    KeyboardButtonRequestChat,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)

MAIN_DASHBOARD_CALLBACK = "main_dashboard:show"
MAIN_DASHBOARD_REFRESH_CALLBACK = "main_dashboard:refresh"
ADMIN_MENU_CALLBACK = "admin:menu"
ADMIN_ADD_GROUP_CALLBACK = "admin:add_group"
ADMIN_ADD_CHANNEL_CALLBACK = "admin:add_channel"
ADMIN_MANAGED_CHATS_CALLBACK = "admin:managed_chats"
ADMIN_CHATS_PAGE_CALLBACK = "admin:chats:page:"
ADMIN_CHAT_DETAIL_CALLBACK = "admin:chat:"
ADMIN_CHAT_TOGGLE_AUTO_CALLBACK = "admin:chat:auto:"
ADMIN_CHAT_INTERVAL_CALLBACK = "admin:chat:interval:"
ADMIN_CHAT_SENDMODE_CALLBACK = "admin:chat:sendmode:"
ADMIN_CHAT_TEST_CALLBACK = "admin:chat:test:"
ADMIN_CHAT_REMOVE_CONFIRM_CALLBACK = "admin:chat:remove:confirm:"
ADMIN_CHAT_REMOVE_YES_CALLBACK = "admin:chat:remove:yes:"
ADMIN_CHAT_REMOVE_CANCEL_CALLBACK = "admin:chat:remove:cancel:"
ADMIN_SETTINGS_MENU_CALLBACK = "admin:settings:menu"
ADMIN_SETTINGS_BOT_POWER_CALLBACK = "admin:settings:bot_power"
ADMIN_SETTINGS_BOT_TOGGLE_CALLBACK = "admin:settings:bot_toggle"
ADMIN_SETTINGS_API_INFO_CALLBACK = "admin:settings:api_info"
ADMIN_SETTINGS_OPS_INFO_CALLBACK = "admin:settings:ops_info"
FAVORITES_OPEN_CALLBACK = "favorites:open"
FAVORITES_REFRESH_CALLBACK = "favorites:refresh"
FAVORITES_ADD_CALLBACK_PREFIX = "favorites:add:"
FAVORITES_REMOVE_CALLBACK_PREFIX = "favorites:remove:"
ALERTS_OPEN_CALLBACK = "alerts:open"
ALERTS_REFRESH_CALLBACK = "alerts:refresh"
ALERT_DEACTIVATE_CALLBACK_PREFIX = "alerts:deactivate:"
ALERT_DELETE_CALLBACK_PREFIX = "alerts:delete:"
BACK_TO_MAIN_MENU_CALLBACK = "main:back"


def main_menu_kb() -> InlineKeyboardMarkup:
    return main_menu_keyboard()


def main_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📊 Main dashboard", callback_data=MAIN_DASHBOARD_CALLBACK),
            ],
            [
                InlineKeyboardButton(text="⭐ Favorites", callback_data=FAVORITES_OPEN_CALLBACK),
            ],
            [
                InlineKeyboardButton(text="⏰ Alerts", callback_data=ALERTS_OPEN_CALLBACK),
            ],
        ]
    )


def main_dashboard_keyboard() -> InlineKeyboardMarkup:
    kb = [
        [InlineKeyboardButton(text="📊 Show main prices", callback_data=MAIN_DASHBOARD_CALLBACK)],
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)


def main_dashboard_refresh_keyboard() -> InlineKeyboardMarkup:
    kb = [
        [InlineKeyboardButton(text="🔄 Refresh", callback_data=MAIN_DASHBOARD_REFRESH_CALLBACK)],
        [InlineKeyboardButton(text="⬅ Back", callback_data=BACK_TO_MAIN_MENU_CALLBACK)],
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)


def admin_main_menu_keyboard() -> InlineKeyboardMarkup:
    kb = [
        [
            InlineKeyboardButton(text="➕ Add group", callback_data=ADMIN_ADD_GROUP_CALLBACK),
            InlineKeyboardButton(text="➕ Add channel", callback_data=ADMIN_ADD_CHANNEL_CALLBACK),
        ],
        [InlineKeyboardButton(text="📃 Chats", callback_data=ADMIN_MANAGED_CHATS_CALLBACK)],
        [InlineKeyboardButton(text="⚙ Settings", callback_data=ADMIN_SETTINGS_MENU_CALLBACK)],
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)


def admin_chats_list_keyboard(chats, page: int, has_next: bool) -> InlineKeyboardMarkup:
    buttons = []
    for chat in chats:
        label = f"🗨️ {chat.title or chat.tg_chat_id} [{chat.type}]"
        target_id = chat.tg_chat_id or chat.id
        buttons.append([InlineKeyboardButton(text=label, callback_data=f"{ADMIN_CHAT_DETAIL_CALLBACK}{target_id}")])

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="⬅ Prev", callback_data=f"{ADMIN_CHATS_PAGE_CALLBACK}{page-1}"))
    if has_next:
        nav.append(InlineKeyboardButton(text="➡ Next", callback_data=f"{ADMIN_CHATS_PAGE_CALLBACK}{page+1}"))
    back = InlineKeyboardButton(text="⬅ Back", callback_data=ADMIN_MENU_CALLBACK)
    if nav:
        buttons.append(nav)
    buttons.append([back])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def admin_chat_detail_keyboard(chat, settings) -> InlineKeyboardMarkup:
    auto_label = "⏯ Auto-post: ON" if settings.auto_post_enabled else "⏯ Auto-post: OFF"
    mode_label = "📝 Mode: EDIT" if settings.send_mode == "edit" else "📰 Mode: NEW"
    key = chat.tg_chat_id
    kb = [
        [InlineKeyboardButton(text=auto_label, callback_data=f"{ADMIN_CHAT_TOGGLE_AUTO_CALLBACK}{key}")],
        [
            InlineKeyboardButton(
                text=f"⏱ Interval: {settings.interval_minutes} min",
                callback_data=f"{ADMIN_CHAT_INTERVAL_CALLBACK}{key}",
            )
        ],
        [InlineKeyboardButton(text=mode_label, callback_data=f"{ADMIN_CHAT_SENDMODE_CALLBACK}{key}")],
        [InlineKeyboardButton(text="🧪 Send test", callback_data=f"{ADMIN_CHAT_TEST_CALLBACK}{key}")],
        [InlineKeyboardButton(text="❌ Remove chat", callback_data=f"{ADMIN_CHAT_REMOVE_CONFIRM_CALLBACK}{key}")],
        [InlineKeyboardButton(text="⬅ Back to chats", callback_data=f"{ADMIN_CHATS_PAGE_CALLBACK}0")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)


def admin_settings_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔌 Bot power", callback_data=ADMIN_SETTINGS_BOT_POWER_CALLBACK)],
            [InlineKeyboardButton(text="🌐 API & providers", callback_data=ADMIN_SETTINGS_API_INFO_CALLBACK)],
            [InlineKeyboardButton(text="📦 Operations / scripts", callback_data=ADMIN_SETTINGS_OPS_INFO_CALLBACK)],
            [InlineKeyboardButton(text="⬅ Back", callback_data=ADMIN_MENU_CALLBACK)],
        ]
    )


def admin_bot_power_keyboard(global_settings) -> InlineKeyboardMarkup:
    toggle_text = "🔴 Turn OFF (maintenance)" if getattr(global_settings, "bot_enabled", True) else "🟢 Turn ON"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=toggle_text, callback_data=ADMIN_SETTINGS_BOT_TOGGLE_CALLBACK)],
            [InlineKeyboardButton(text="⬅ Back", callback_data=ADMIN_SETTINGS_MENU_CALLBACK)],
        ]
    )


def admin_back_to_settings_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅ Back", callback_data=ADMIN_SETTINGS_MENU_CALLBACK)],
        ]
    )


def admin_request_group_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(
                    text="Select group…",
                    request_chat=KeyboardButtonRequestChat(
                        request_id=1001,
                        chat_is_channel=False,
                    ),
                )
            ]
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def admin_request_channel_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(
                    text="Select channel…",
                    request_chat=KeyboardButtonRequestChat(
                        request_id=1002,
                        chat_is_channel=True,
                    ),
                )
            ]
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def remove_reply_keyboard() -> ReplyKeyboardRemove:
    return ReplyKeyboardRemove()


def admin_chat_remove_confirm_keyboard(chat_key: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Yes, remove", callback_data=f"{ADMIN_CHAT_REMOVE_YES_CALLBACK}{chat_key}")],
            [InlineKeyboardButton(text="❌ Cancel", callback_data=f"{ADMIN_CHAT_REMOVE_CANCEL_CALLBACK}{chat_key}")],
        ]
    )


def favorites_overview_keyboard(has_items: bool) -> InlineKeyboardMarkup:
    buttons = []
    if has_items:
        buttons.append([InlineKeyboardButton(text="🔄 Refresh", callback_data=FAVORITES_REFRESH_CALLBACK)])
    buttons.append([InlineKeyboardButton(text="⬅ Back", callback_data=BACK_TO_MAIN_MENU_CALLBACK)])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def favorite_toggle_keyboard(symbol: str, is_favorite: bool) -> InlineKeyboardMarkup:
    if is_favorite:
        btn = InlineKeyboardButton(
            text="➖ Remove from favorites", callback_data=f"{FAVORITES_REMOVE_CALLBACK_PREFIX}{symbol.upper()}"
        )
    else:
        btn = InlineKeyboardButton(
            text="➕ Add to favorites", callback_data=f"{FAVORITES_ADD_CALLBACK_PREFIX}{symbol.upper()}"
        )
    return InlineKeyboardMarkup(inline_keyboard=[[btn]])


def alerts_overview_keyboard(has_items: bool) -> InlineKeyboardMarkup:
    buttons = []
    if has_items:
        buttons.append([InlineKeyboardButton(text="🔄 Refresh", callback_data=ALERTS_REFRESH_CALLBACK)])
    buttons.append([InlineKeyboardButton(text="⬅ Back", callback_data=BACK_TO_MAIN_MENU_CALLBACK)])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def alert_item_keyboard(alert_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🛑 Deactivate", callback_data=f"{ALERT_DEACTIVATE_CALLBACK_PREFIX}{alert_id}"
                ),
                InlineKeyboardButton(text="🗑 Delete", callback_data=f"{ALERT_DELETE_CALLBACK_PREFIX}{alert_id}"),
            ]
        ]
    )
