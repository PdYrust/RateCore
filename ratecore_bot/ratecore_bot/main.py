from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from aiogram import BaseMiddleware, Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand

from ratecore_bot.api.ratecore_client import RateCoreClient
from ratecore_bot.config import get_settings
from ratecore_bot.db import get_engine, get_session_factory, init_db
from ratecore_bot.db.session import set_session_factory
from ratecore_bot.handlers import admin_router, user_router
from ratecore_bot.logging_config import setup_logging
from ratecore_bot.scheduler import run_scheduler


@asynccontextmanager
async def lifespan(bot: Bot, client: RateCoreClient):
    # Startup tasks
    yield
    # Shutdown tasks
    await client.close()
    await bot.session.close()


async def main() -> None:
    settings = get_settings()
    setup_logging()
    logger = logging.getLogger("ratecore_bot")

    # Initialize DB
    engine = get_engine(str(getattr(settings, "database_url", "sqlite+aiosqlite:///./ratecore_bot.db")))
    await init_db(engine)
    session_factory = get_session_factory(engine)
    set_session_factory(session_factory)
    logger.info("Database initialized.")

    session = None
    if settings.telegram_proxy_url:
        session = AiohttpSession(proxy=settings.telegram_proxy_url)

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        session=session,
    )
    dp = Dispatcher(storage=MemoryStorage())

    client = RateCoreClient(base_url=str(settings.ratecore_api_base_url))

    class SettingsMiddleware(BaseMiddleware):
        def __init__(self, settings) -> None:
            super().__init__()
            self.settings = settings

        async def __call__(self, handler, event, data):
            data["settings"] = self.settings
            return await handler(event, data)

    class RateCoreClientMiddleware(BaseMiddleware):
        def __init__(self, client: RateCoreClient) -> None:
            super().__init__()
            self.client = client

        async def __call__(self, handler, event, data):
            data["ratecore_client"] = self.client
            return await handler(event, data)

    dp.message.middleware.register(SettingsMiddleware(settings))
    dp.callback_query.middleware.register(SettingsMiddleware(settings))
    dp.message.middleware.register(RateCoreClientMiddleware(client))
    dp.callback_query.middleware.register(RateCoreClientMiddleware(client))

    dp.include_router(user_router)
    dp.include_router(admin_router)

    async def setup_bot_commands() -> None:
        commands = [
            BotCommand(command="start", description="Show main menu"),
            BotCommand(command="restart", description="Recreate main menu anchor"),
            BotCommand(command="price", description="Get price for a symbol (/price BTC)"),
            BotCommand(command="ping", description="Health check"),
            BotCommand(command="admin", description="Open admin panel (admin only)"),
        ]
        await bot.set_my_commands(commands)

    logger.info("Starting RateCore Bot")
    asyncio.create_task(run_scheduler(settings, bot, client))
    async with lifespan(bot, client):
        await setup_bot_commands()
        await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
