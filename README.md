# RateCore

IRR price aggregator API and Telegram bot.

Version: v1.0.0  
Created by: https://github.com/YrustPd

RateCore is a Cortex-style stack with a Go API that aggregates FX, crypto, metals (and IRR) prices and a Python Telegram bot that serves dashboards, favorites, alerts, and an admin panel. Prices are normalized to IRR/TOMAN. The repo ships with installer scripts, Docker, and a Makefile for repeatable setup.

## Features
- **Go API**
  - Multi-provider architecture (crypto, metals, forex, IRR) with fallback: try providers in order until one succeeds.
  - Normalizes to IRR/TOMAN; USD→IRR conversion and caching.
  - Health endpoints and structured logging.
- **Telegram Bot**
  - User: main dashboard (anchor message), favorites, alerts.
  - Admin: manage chats (add via chat picker, configure interval/send mode, test, remove), global settings (bot power ON/OFF maintenance), read-only API/provider info, operations/scripts info.
  - Technical: anchor messages (main/admin menus), chat hygiene (delete commands in private chats), scheduler respects maintenance mode.
- **Tooling**
  - Scripts: `install.sh`, `setup.sh`, `run.sh`, `check.sh`, `update.sh`, `uninstall.sh`.
  - Docker: `Dockerfile.api`, `Dockerfile.bot`, `docker-compose.yml`.
  - Makefile: `install`, `build-api`, `run-api`, `run-bot`, `run`, `up`, `down`, `logs`, `clean`, `update`.

## Architecture Overview
- **Go**: `cmd/ratecore-api` entrypoint; `internal/core` (price model, registry, display config), `internal/adapters` (binance, metalsapi, exchangerateapi, irr), `internal/api` (handlers/router), telemetry/logging, `pkg/config`.
- **Bot**: `ratecore_bot` with Pydantic settings, DB models/repo/session, handlers (user/admin), UI (views/keyboards/anchor/hygiene), scheduler, async API client.
- **Flow**: providers → Go API → bot `/api/v1` calls → Telegram users/chats.

ASCII sketch:
```
[Providers (crypto/forex/metals/irr)]
        │
        ▼
  Go API (ProviderRegistry + PriceService)
        │  /api/v1
        ▼
  Telegram Bot (client + scheduler)
        │
        ▼
  Telegram users/chats
```

## Installation (Cortex-style)
Requirements: Go 1.22+, Python 3.11+, Bash. Docker optional.

```bash
# Configure env
./scripts/setup.sh

# Build API + venv + deps
./scripts/install.sh
# or
make install
```

## Running & Maintenance
- **Without Docker**: `./scripts/run.sh` (API bg → `logs/api.log`, bot fg) or `make run`.
- **With Docker**: `docker compose up -d` / `make up`; logs: `docker compose logs -f` / `make logs`.
- **Stop/cleanup**: `./scripts/stop.sh` (optional Docker down) or `make down`; remove artifacts with `make clean`.
- **Maintenance mode**: Admin → Settings → Bot power.
  - OFF: non-admin users see maintenance message; scheduler pauses auto-posts; admin retains full access to /admin to turn ON again.
  - ON: normal behavior.
See `docs/ADMIN.md` and `docs/OPERATIONS.md` for details.

## API (short)
- Price endpoints under `/api/v1` (e.g., `/price`, `/prices/batch`, health `/healthz`).
- Intended for bot and external consumers (e.g., a WordPress site).

## Environment Variables
See `./.env.example`. Key vars:
- API: `RCORE_HTTP_PORT`, `RCORE_LOG_LEVEL`, provider URLs/keys (`RCORE_BINANCE_BASE_URL`, `RCORE_FOREX_BASE_URL`, `RCORE_IRR_BASE_URL`, `RCORE_IRR_API_KEY`, `RCORE_METALS_BASE_URL`).
- Bot: `BOT_TOKEN`, `TELEGRAM_ADMIN_ID`, `RCORE_API_BASE_URL`, optional `BOT_LOG_LEVEL`, `TELEGRAM_PROXY_URL`.

## Project layout
```
cmd/ratecore-api/         # Go API entrypoint
internal/                 # core logic, adapters, API, telemetry
pkg/config/               # env-driven config
ratecore_bot/             # Telegram bot
  ui/anchor.py            # anchor message helpers
  ui/chat_hygiene.py      # command cleanup helpers
scripts/                  # install/run/check/update/uninstall
docs/                     # architecture, operations, admin
Dockerfile.api, Dockerfile.bot, docker-compose.yml
Makefile
```

## Development notes
- Build API: `make build-api`
- Run API only: `make run-api`
- Run bot only: `make run-bot` (API running + venv active)
- Checks: `./scripts/check.sh`
- Update deps: `./scripts/update.sh`
- Docker up/down: `make up` / `make down`
