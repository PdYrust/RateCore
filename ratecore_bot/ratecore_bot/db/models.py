from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from sqlalchemy import BigInteger, Boolean, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ratecore_bot.db.session import Base


def ts_now() -> datetime:
    return datetime.utcnow()


class User(Base):
    """Telegram user."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tg_user_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    first_name: Mapped[Optional[str]] = mapped_column(String(128))
    last_name: Mapped[Optional[str]] = mapped_column(String(128))
    username: Mapped[Optional[str]] = mapped_column(String(128))
    language: Mapped[Optional[str]] = mapped_column(String(8))
    currency_mode_pref: Mapped[Optional[str]] = mapped_column(String(8))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=ts_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=ts_now, onupdate=ts_now, nullable=False
    )
    last_seen_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    favorites: Mapped[List["Favorite"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    alerts: Mapped[List["Alert"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    templates: Mapped[List["Template"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class Chat(Base):
    """Telegram chat (private/group/channel)."""

    __tablename__ = "chats"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tg_chat_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    type: Mapped[str] = mapped_column(String(32), nullable=False)
    title: Mapped[Optional[str]] = mapped_column(String(256))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=ts_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=ts_now, onupdate=ts_now, nullable=False
    )

    settings: Mapped[Optional["ChatSettings"]] = relationship(
        back_populates="chat", uselist=False, cascade="all, delete-orphan"
    )
    alerts: Mapped[List["Alert"]] = relationship(back_populates="chat", cascade="all, delete-orphan")
    templates: Mapped[List["Template"]] = relationship(back_populates="chat", cascade="all, delete-orphan")


class ChatSettings(Base):
    """Per-chat auto-post settings."""

    __tablename__ = "chat_settings"

    chat_id: Mapped[int] = mapped_column(ForeignKey("chats.id"), primary_key=True)
    auto_post_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    package_id: Mapped[Optional[int]] = mapped_column(ForeignKey("packages.id"))
    interval_minutes: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    send_mode: Mapped[str] = mapped_column(String(16), default="edit", nullable=False)
    last_message_id: Mapped[Optional[int]] = mapped_column(BigInteger)
    last_sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    main_menu_message_id: Mapped[Optional[int]] = mapped_column(BigInteger)
    admin_menu_message_id: Mapped[Optional[int]] = mapped_column(BigInteger)
    error_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=ts_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=ts_now, onupdate=ts_now, nullable=False
    )

    chat: Mapped["Chat"] = relationship(back_populates="settings")
    package: Mapped[Optional["Package"]] = relationship(back_populates="chat_settings")


class GlobalSettings(Base):
    """Global (single-row) settings."""

    __tablename__ = "global_settings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    bot_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    maintenance_message: Mapped[Optional[str]] = mapped_column(String, nullable=True)


class Favorite(Base):
    """User favorite symbols."""

    __tablename__ = "favorites"
    __table_args__ = (UniqueConstraint("user_id", "symbol", name="uq_fav_user_symbol"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=ts_now, nullable=False)

    user: Mapped["User"] = relationship(back_populates="favorites")


class Alert(Base):
    """Price alerts."""

    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    chat_id: Mapped[int] = mapped_column(ForeignKey("chats.id"), nullable=False)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    condition_type: Mapped[str] = mapped_column(String(16), nullable=False)  # above, below, range
    value_from: Mapped[float] = mapped_column(Float, nullable=False)
    value_to: Mapped[Optional[float]] = mapped_column(Float)
    currency_mode: Mapped[str] = mapped_column(String(8), nullable=False)  # IRR or TOMAN
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=ts_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=ts_now, onupdate=ts_now, nullable=False
    )
    last_check_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    triggered_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    times_triggered: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    user: Mapped["User"] = relationship(back_populates="alerts")
    chat: Mapped["Chat"] = relationship(back_populates="alerts")


class Package(Base):
    """Predefined dashboard packages."""

    __tablename__ = "packages"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    code: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(512))
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    type: Mapped[Optional[str]] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=ts_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=ts_now, onupdate=ts_now, nullable=False
    )

    items: Mapped[List["PackageItem"]] = relationship(back_populates="package", cascade="all, delete-orphan")
    chat_settings: Mapped[List["ChatSettings"]] = relationship(back_populates="package")


class PackageItem(Base):
    """Items within a package."""

    __tablename__ = "package_items"
    __table_args__ = (UniqueConstraint("package_id", "symbol", name="uq_package_symbol"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    package_id: Mapped[int] = mapped_column(ForeignKey("packages.id"), nullable=False)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=ts_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=ts_now, onupdate=ts_now, nullable=False
    )

    package: Mapped["Package"] = relationship(back_populates="items")


class Template(Base):
    """Message templates with scope."""

    __tablename__ = "templates"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    scope: Mapped[str] = mapped_column(String(16), nullable=False)  # global, chat, user
    chat_id: Mapped[Optional[int]] = mapped_column(ForeignKey("chats.id"))
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"))
    content: Mapped[str] = mapped_column(String, nullable=False)
    variables_json: Mapped[Optional[str]] = mapped_column(String)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=ts_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=ts_now, onupdate=ts_now, nullable=False
    )

    chat: Mapped[Optional["Chat"]] = relationship(back_populates="templates")
    user: Mapped[Optional["User"]] = relationship(back_populates="templates")
