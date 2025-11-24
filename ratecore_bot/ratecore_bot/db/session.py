from __future__ import annotations

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator, Optional

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

engine: Optional[AsyncEngine] = None
async_session_factory: Optional[async_sessionmaker[AsyncSession]] = None


class Base(DeclarativeBase):
    """Base class for all ORM models."""


def get_engine(database_url: str) -> AsyncEngine:
    """Create async engine for SQLite."""
    global engine
    engine = create_async_engine(
        database_url,
        echo=False,
        future=True,
    )
    return engine


def get_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    global async_session_factory
    async_session_factory = async_sessionmaker(
        engine,
        expire_on_commit=False,
        autoflush=False,
    )
    return async_session_factory


def set_session_factory(factory: async_sessionmaker[AsyncSession]) -> None:
    global async_session_factory
    async_session_factory = factory


async def init_db(engine: AsyncEngine) -> None:
    """Create all tables."""
    from ratecore_bot.db import models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@asynccontextmanager
async def get_session(session_factory: Optional[async_sessionmaker[AsyncSession]] = None) -> AsyncIterator[AsyncSession]:
    factory = session_factory or async_session_factory
    if factory is None:
        raise RuntimeError("Session factory is not configured")
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
