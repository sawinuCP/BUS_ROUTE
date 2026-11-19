"""Application configuration (ADR-0001 canonical module: `platform`).

Values come from environment variables (12-factor style). `.env` files are
supported for local development; production must inject real environment
variables. Never place secrets in this file.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

AppEnv = Literal["local", "test", "staging", "production"]


class Settings(BaseSettings):
    """Typed application settings with safe local-development defaults."""

    model_config = SettingsConfigDict(
        # Local development may place `.env` at the repo root (../.env) or in
        # backend/ (.env). In containers, real environment variables win.
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "Sri Lanka Journey Planner API"
    app_env: AppEnv = "local"
    debug: bool = False
    log_level: str = "INFO"
    api_v1_prefix: str = "/api/v1"

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/journey_planner"
    redis_url: str = "redis://localhost:6379/0"

    cors_origins: list[str] = []

    @property
    def is_local(self) -> bool:
        return self.app_env == "local"


@lru_cache
def get_settings() -> Settings:
    """Return the cached Settings instance."""
    return Settings()
