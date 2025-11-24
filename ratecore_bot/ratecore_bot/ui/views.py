from __future__ import annotations

from datetime import datetime
from typing import Any, Iterable, List

from ratecore_bot.db import models

MAIN_DASHBOARD_SYMBOLS: list[str] = ["USD", "EUR", "GBP", "BTC", "ETH", "XAU"]
# TODO: load dashboard symbols from DB packages/package_items.


def format_price_message(symbol: str, data: dict[str, Any]) -> str:
    value_irr = data.get("value_irr") or data.get("ValueIRR")
    value_toman = data.get("value_toman") or data.get("ValueToman")
    provider = data.get("provider") or data.get("Provider")
    updated_at = data.get("updated_at") or data.get("UpdatedAt")

    lines = [
        f"Symbol: {symbol.upper()}",
        f"Provider: {provider or 'n/a'}",
    ]
    if value_irr is not None:
        lines.append(f"IRR: {value_irr}")
    if value_toman is not None:
        lines.append(f"Toman: {value_toman}")
    if updated_at:
        lines.append(f"Updated: {updated_at}")
    return "\n".join(lines)


def _format_number(val: float | None) -> str:
    if val is None:
        return "n/a"
    return f"{val:,.0f}"


def format_main_dashboard(
    items: Iterable[dict],
    *,
    title: str = "📊 RateCore – Main Dashboard",
) -> str:
    """Format main dashboard view for PV chats."""
    lines: List[str] = [title, ""]

    now = datetime.utcnow()
    latest_ts: datetime | None = None

    sections = {
        "forex": [],
        "crypto": [],
        "metal": [],
    }

    for item in items:
        symbol = (item.get("symbol") or item.get("Symbol") or "").upper()
        kind = (item.get("kind") or item.get("Kind") or "").lower()
        display = item.get("display") or item.get("Display")
        display_currency = (item.get("display_currency") or item.get("DisplayCurrency") or "").upper()
        updated = item.get("updated_at") or item.get("UpdatedAt")
        try:
            parsed_updated = datetime.fromisoformat(updated.replace("Z", "+00:00")) if updated else None
        except Exception:
            parsed_updated = None

        if parsed_updated:
            if latest_ts is None or parsed_updated > latest_ts:
                latest_ts = parsed_updated

        suffix = " تومان" if display_currency == "TOMAN" else " ﷼"
        value_str = _format_number(display) + suffix if display is not None else "n/a"

        if kind == "forex":
            emoji = "💵"
        elif kind == "crypto":
            emoji = "🪙"
        elif kind == "metal":
            emoji = "🥇"
        else:
            emoji = "💠"

        section_key = "forex" if kind == "forex" else "crypto" if kind == "crypto" else "metal"
        sections.setdefault(section_key, []).append(f"{emoji} {symbol}: {value_str}")

    if sections["forex"]:
        lines.append("\n".join(sections["forex"]))
        lines.append("")
    if sections["crypto"]:
        lines.append("\n".join(sections["crypto"]))
        lines.append("")
    if sections["metal"]:
        lines.append("\n".join(sections["metal"]))
        lines.append("")

    ts_str = (latest_ts or now).strftime("%Y-%m-%d %H:%M:%S UTC")
    lines.append(f"Last update: {ts_str}")

    return "\n".join(line for line in lines if line is not None)


def format_main_menu_text() -> str:
    return "👋 Welcome to RateCore Bot!\n\nUse the button below to view the main market dashboard."


def format_admin_main_menu() -> str:
    return (
        "🛠 RateCore Admin Panel\n\n"
        "Choose an option:\n"
        "- Manage chats (groups/channels)\n"
        "- View and edit settings for each chat\n"
        "- Add or remove chats from management\n"
        "- Access global settings and operations info"
    )


def format_admin_chats_list(chats, page: int, total: int) -> str:
    lines = [f"🗂 Chats (page {page + 1}, total {total})", ""]
    page_size = len(chats)
    start_idx = page * page_size + 1 if page_size else 1
    for idx, chat in enumerate(chats, start=start_idx):
        lines.append(f"{idx}. [{chat.type}] {chat.title or chat.tg_chat_id}")
    if not chats:
        lines.append("No chats found.")
    return "\n".join(lines)


def format_admin_chat_detail(chat, settings) -> str:
    lines = [
        "🗨️ Chat Details",
        f"Title: {chat.title or chat.tg_chat_id}",
        f"Type: {chat.type}",
        f"Chat ID: {getattr(chat, 'id', '?')} | Telegram ID: {getattr(chat, 'tg_chat_id', '?')}",
        f"Auto-post: {'ON' if settings.auto_post_enabled else 'OFF'}",
        f"Interval: {settings.interval_minutes} minutes",
        f"Send mode: {settings.send_mode.upper()}",
        f"Last message id: {settings.last_message_id or 'n/a'}",
        f"Last sent at: {settings.last_sent_at or 'n/a'}",
        "",
        "You can remove this chat from management if it should no longer receive posts.",
    ]
    return "\n".join(lines)


def format_admin_chat_removed_success(chat) -> str:
    return f"✅ Chat '{chat.title or chat.tg_chat_id}' has been removed from management."


def format_admin_chat_remove_confirm(chat) -> str:
    return (
        "⚠️ Remove chat from management?\n\n"
        f"{chat.title or chat.tg_chat_id} (id: {getattr(chat, 'tg_chat_id', '?')})\n\n"
        "This will stop auto-posting and hide it from the managed list."
    )


def format_chat_not_managed() -> str:
    return "This chat is no longer managed. Re-add it from the Admin menu if needed."


def format_admin_add_group_intro() -> str:
    return "Select a group where I should post rates."


def format_admin_add_channel_intro() -> str:
    return "Select a channel where I should post rates."


def format_admin_chat_added_success(chat) -> str:
    return f"✅ Chat '{chat.title or chat.tg_chat_id}' added to managed chats."


def format_admin_settings_menu() -> str:
    return (
        "⚙ Global Settings\n\n"
        "Here you can:\n"
        "- Turn the bot ON/OFF (maintenance mode)\n"
        "- See API/provider configuration info\n"
        "- See how to run/update the bot (scripts, Docker)\n"
    )


def format_admin_bot_power(global_settings) -> str:
    status = "ON ✅" if getattr(global_settings, "bot_enabled", True) else "OFF 🔴 (maintenance)"
    note = (
        "When OFF: non-admin users see the maintenance message and the bot will not respond to normal commands. "
        "Admins can still use /admin to manage settings."
    )
    return f"🔌 Bot power\n\nCurrent status: {status}\n\n{note}"


def format_admin_api_info(settings) -> str:
    def mask(val: str | None) -> str:
        if not val:
            return "not set"
        if len(val) <= 6:
            return "***"
        return f"...{val[-4:]}"

    lines = [
        "🌐 API & Providers (read-only)",
        "",
        f"RateCore API base URL: {getattr(settings, 'ratecore_api_base_url', 'n/a')}",
        "",
        "Providers (env/config):",
        f"- Binance base URL: {getattr(settings, 'binance_base_url', 'n/a')}",
        f"- Metals base URL: {getattr(settings, 'metals_base_url', 'n/a')}",
        f"- Forex base URL: {getattr(settings, 'forex_base_url', 'n/a')}",
        f"- IRR base URL: {getattr(settings, 'irr_base_url', 'n/a')}",
        "",
        "Keys (masked):",
        f"- Binance key: {mask(getattr(settings, 'binance_api_key', None))}",
        f"- Metals key: {mask(getattr(settings, 'metals_api_key', None))}",
        f"- Forex key: {mask(getattr(settings, 'forex_api_key', None))}",
        f"- IRR key: {mask(getattr(settings, 'irr_api_key', None))}",
        "",
        "To change these values, update the environment/.env and restart the bot.",
    ]
    return "\n".join(lines)


def format_admin_ops_info() -> str:
    return (
        "📦 Operations & Scripts\n\n"
        "Local (without Docker):\n"
        "- Setup env:       ./scripts/setup.sh\n"
        "- Install/update:  ./scripts/install.sh\n"
        "- Run services:    ./scripts/run.sh\n"
        "- Check status:    ./scripts/check.sh\n"
        "- Update code:     ./scripts/update.sh\n"
        "- Uninstall:       ./scripts/uninstall.sh\n\n"
        "Makefile shortcuts:\n"
        "- make install     # build API + set up bot env\n"
        "- make run         # run API + bot locally\n"
        "- make up          # start Docker services\n"
        "- make down        # stop Docker services\n"
        "- make logs        # tail logs\n"
        "- make clean       # clean build artifacts\n"
        "- make update      # git pull + rebuild\n\n"
        "Docker:\n"
        "- docker compose up -d\n"
        "- docker compose down\n"
        "- docker compose logs -f\n\n"
        "These are informational only; the bot does not execute scripts or shell commands."
    )


def format_favorites_empty() -> str:
    return "⭐ You don't have any favorites yet.\n\nUse the 'Add to favorites' button on a price to add one."


def format_favorites_dashboard(items: list[dict]) -> str:
    now = datetime.utcnow()
    latest_ts: datetime | None = None
    lines = ["⭐ Your Favorites", ""]

    for item in items:
        symbol = (item.get("symbol") or item.get("Symbol") or "").upper()
        display = item.get("display") or item.get("Display")
        display_currency = (item.get("display_currency") or item.get("DisplayCurrency") or "").upper()
        updated = item.get("updated_at") or item.get("UpdatedAt")

        try:
            parsed_updated = datetime.fromisoformat(updated.replace("Z", "+00:00")) if updated else None
        except Exception:
            parsed_updated = None

        if parsed_updated:
            if latest_ts is None or parsed_updated > latest_ts:
                latest_ts = parsed_updated

        suffix = " تومان" if display_currency == "TOMAN" else " ﷼"
        value_str = _format_number(display) + suffix if display is not None else "n/a"
        lines.append(f"{symbol}: {value_str}")

    if not items:
        return format_favorites_empty()

    lines.append("")
    ts_str = (latest_ts or now).strftime("%Y-%m-%d %H:%M:%S UTC")
    lines.append(f"Last update: {ts_str}")

    return "\n".join(lines)


def format_alerts_empty() -> str:
    return "⏰ You don't have any alerts yet.\n\nUse /alert_add command to create one."


def format_alerts_list(alerts: list[models.Alert]) -> str:
    lines = ["⏰ Your Alerts", ""]
    if not alerts:
        return format_alerts_empty()
    for idx, alert in enumerate(alerts, start=1):
        status = "active" if alert.is_active else "inactive"
        lines.append(
            f"#{idx}: {alert.symbol} {alert.condition_type} {alert.value_from:,.0f} {alert.currency_mode} [{status}] "
            f"(triggered {alert.times_triggered}x)"
        )
    return "\n".join(lines)
