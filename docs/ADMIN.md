# RateCore Admin Guide

## Access
- Admin is determined by `TELEGRAM_ADMIN_ID` in `.env`.
- Open the panel with `/admin` (shown as an anchor message in your private chat). Admin callbacks keep editing the same anchor.

## Admin Main Menu
- **📃 Chats**: list managed groups/channels with pagination; open chat detail.
- **⚙ Settings**: global controls:
  - Bot power (on/off maintenance).
  - API & provider info (read-only, from env/config).
  - Operations / scripts info (how to run/update; informational only).

## Managing Chats
- Add chats via the Telegram chat picker (Add group/channel). The bot must be present (admin recommended) in the target chat.
- **Chat list**: paginated; each entry opens details.
- **Chat detail**:
  - Toggle auto-post ON/OFF.
  - Cycle interval (minutes).
  - Switch send mode (EDIT/NEW).
  - Send test message.
  - Remove chat (soft delete) with confirmation.
- Removing a chat hides it from the list and stops scheduler posts.

## Global Settings / Maintenance
- Settings → Bot power:
  - ON: normal behavior.
  - OFF (maintenance):
    - Non-admin users see a maintenance message; user commands/features disabled.
    - Scheduler stops auto-posts.
    - Admin retains full access to /admin to turn it back ON.
- Settings → API & providers: shows current config (base URLs, masked keys) from env; edit via `.env` + restart.
- Settings → Operations: shows how to run/update via scripts/Make/Docker; informational only.

## Operations / Scripts (informational)
Shown under Settings → Operations:
- Local scripts: `./scripts/setup.sh`, `install.sh`, `run.sh`, `check.sh`, `update.sh`, `uninstall.sh`.
- Make targets: `make install`, `make run`, `make up`, `make down`, `make logs`, `make clean`, `make update`, plus API/bot-specific targets.
- Docker: `docker compose up -d`, `docker compose down`, `docker compose logs -f`.
- These are instructions only; commands must be run on the server/shell.

## Tips
- Anchors: Admin menu is an anchor message; callbacks edit in place. If deleted, use `/admin` to recreate.
- Hygiene: Command messages in private chats are auto-deleted; temporary helper messages may self-clean after a delay.
