from __future__ import annotations

from functools import lru_cache
from pydantic import Field, AnyHttpUrl, AliasChoices
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Bot configuration loaded from environment."""

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    bot_token: str = Field(..., validation_alias=AliasChoices("BOT_TOKEN", "bot_token"))
    admin_id: int = Field(
        ...,
        validation_alias=AliasChoices("TELEGRAM_ADMIN_ID", "ADMIN_ID", "admin_id"),
    )
    ratecore_api_base_url: AnyHttpUrl = Field(
        ...,
        validation_alias=AliasChoices("RCORE_API_BASE_URL", "ratecore_api_base_url"),
    )
    telegram_proxy_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "TELEGRAM_PROXY_URL", "HTTPS_PROXY", "https_proxy", "ALL_PROXY", "all_proxy"
        ),
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
