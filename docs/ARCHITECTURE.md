# RateCore Architecture

This document dives into how the Go API and Python bot are composed. For quick start, see `README.md`.

## High-level
```
[Providers: crypto/forex/metals/irr] -> Go ProviderRegistry -> PriceService -> /api/v1
                                                                |
                                                                v
                                           Telegram bot (client + scheduler + DB)
                                                                |
                                                                v
                                                Telegram users & admin panel
```

## Go API layers
- **cmd/ratecore-api**: Composition root; loads env, wires logging, display config, ProviderRegistry, PriceService, and HTTP router/server.
- **internal/core**
  - `price`: TickerProvider interface, ProviderRegistry (crypto/metals/forex/irr slices), first-success fallback, normalization to IRR/TOMAN, FX cache.
  - `config`: Display settings (IRR vs TOMAN).
- **internal/adapters**
  - `crypto/binance`, `metals/metalsapi`, `forex/exchangerateapi`, `forex/irr`: concrete providers implementing the ticker interface.
- **internal/api**
  - handlers (`/api/v1/healthz`, `/readyz`, `/price/{symbol}`, `/prices/batch`), middleware (logging), router/server.
- **internal/telemetry**: slog wrapper.
- **pkg/config**: env-driven config; ProvidersConfig preferred, legacy single-provider fields still respected.

### Provider architecture
- `ProviderRegistry` holds providers per category; order defines priority.
- `PriceService` iterates providers until one succeeds (simple fallback).
- Normalization:
  - Base IRR: pass-through.
  - Base USD/USDT: multiply by USD→IRR; TOMAN = IRR/10.
  - Metals/crypto/forex use category providers; IRR provider supplies USD→IRR.

### Request lifecycle
```
Client -> /api/v1/price/{symbol}
        -> Router -> PriceHandler
        -> PriceService (cache? else fetch)
        -> ProviderRegistry (first success)
        -> Normalize to IRR/TOMAN
        -> DTO response
```

## Python bot components
- **Config**: `ratecore_bot/config.py` (Pydantic `Settings`, `.env`).
- **API client**: async `RateCoreClient` wraps `/api/v1/price` and `/prices/batch`.
- **DB models**: `User`, `Chat`, `ChatSettings` (auto-post, interval, send_mode, anchors), `GlobalSettings` (bot_enabled, maintenance_message), `Favorite`, `Alert`, `Package`, `Template`.
- **Handlers/UI**: user/admin routers; keyboards/views; anchor helpers (`ui/anchor.py`); chat hygiene (`ui/chat_hygiene.py`).
- **Scheduler**: `scheduler.py` runs auto-post and alerts; skips when `bot_enabled` is false.
- **Logging**: `logging_config.py`.

### Bot control flow
```
Telegram update
    │
    ▼
 Middlewares inject Settings + RateCoreClient
    │
    ▼
 Routers (user/admin) -> DB + API client
    │
    └─ Scheduler (background) uses DB + API client
```

## Anchor messages
- Stored in `ChatSettings`: `main_menu_message_id`, `admin_menu_message_id`.
- `ui/anchor.py`:
  - `/start` → `show_main_menu_anchor` (edit existing or send new).
  - `/admin` → `show_admin_menu_anchor`.
- Inline callbacks continue to `edit_text` the anchor.

## Chat hygiene
- `ui/chat_hygiene.py` deletes command messages in private chats; temp messages can auto-delete after a delay.
- Keeps chats clean while preserving inline edit flows.

## Scheduler & maintenance
- Scheduler selects active chats with auto_post enabled.
- Global `bot_enabled` in `GlobalSettings`:
  - `False` → scheduler skips posts; non-admin commands return maintenance text; admin still fully functional.

## Extensibility
- Add providers by implementing the ticker interface and wiring into `ProviderRegistry` with config.
- Extend normalization for new bases in `internal/core/price/service.go`.
- Add bot features by extending Settings/DB models and UI handlers; use anchors for stable menus. 
