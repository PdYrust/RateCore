# RateCore Operations / Runbook

Practical notes for operating the Go API + Telegram bot.

## Installer & lifecycle scripts (./scripts)
- `setup.sh` — interactively create/update `.env`.
- `install.sh` — check prerequisites, build Go API (`./bin/ratecore-api`), create `.venv`, install bot deps.
- `run.sh` — start API in background (`runtime/api.pid`, logs to `logs/api.log`), then run bot in foreground.
- `check.sh` — verify binary, API health, .venv import, required env vars.
- `update.sh` — `git pull`, `go mod tidy`, rebuild API, refresh Python deps.
- `uninstall.sh` — stop API, remove build artifacts, .venv, logs/runtime/data (optional `.env` removal).
- `stop.sh` — stop Docker stack (optional) and stop local API/bot processes (best-effort).

## Docker
```
docker compose up -d    # or make up
docker compose logs -f  # or make logs
docker compose down     # or make down
```
- Services: `api` (Dockerfile.api, port 8080, health `/api/v1/healthz`), `bot` (Dockerfile.bot, uses `.env`, `RCORE_API_BASE_URL=http://api:8080`).

## Makefile shortcuts
- `make install` — build API + bot env.
- `make build-api`, `make run-api`, `make run-bot`.
- `make run` — API+bot locally.
- `make up` / `make down` / `make logs` — Docker lifecycle.
- `make clean` — remove artifacts.
- `make update` — update stack.

## Maintenance mode
- Bot can run in maintenance without stopping the process:
  - Admin → Settings → Bot power OFF:
    - Non-admin users see maintenance message; bot features disabled.
    - Scheduler skips auto-posts.
    - Admin still accesses /admin to turn ON.
  - Bot power ON: normal operation.
- Stopping processes/containers is a hard-offline alternative.

## Healthchecks
- API liveness: `GET /api/v1/healthz`
- API readiness: `GET /api/v1/readyz`

## Logs & PIDs
- Local: `logs/api.log`, bot logs stdout; API pid at `runtime/api.pid`.
- Docker: `docker compose logs -f api` / `docker compose logs -f bot`.

## Troubleshooting
- API not responding: run `./scripts/check.sh`; verify `RCORE_HTTP_PORT`/binding; inspect `logs/api.log`.
- Bot fails to start: ensure `.venv`, `BOT_TOKEN`, `TELEGRAM_ADMIN_ID`, `RCORE_API_BASE_URL`; try `python -m ratecore_bot.main`.
- Missing env vars: re-run `./scripts/setup.sh` or copy `.env.example`.
- Provider issues: adjust `RCORE_BINANCE_BASE_URL`, `RCORE_FOREX_BASE_URL`, `RCORE_IRR_BASE_URL`, `RCORE_IRR_API_KEY`, `RCORE_METALS_BASE_URL`.
- Dependency drift: `./scripts/update.sh`.

## References
- Quick start: `README.md`
- Architecture: `docs/ARCHITECTURE.md`
- Admin flows: `docs/ADMIN.md`
