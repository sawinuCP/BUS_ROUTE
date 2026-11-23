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

    # Host-side default points at the Docker-published port 5433 (compose maps
    # db 5433:5432). 5432 on the host often collides with a local native
    # PostgreSQL service (I-20). Inside Docker, compose overrides DATABASE_URL
    # to the in-network db:5432.
    database_url: str = (
        "postgresql+asyncpg://postgres:change-me-local-only@localhost:5433/journey_planner"
    )
    redis_url: str = "redis://localhost:6379/0"

    # Immutable raw-source archive root (dev: local filesystem; staging/production:
    # object storage via the SnapshotArchive interface, ADR-0007).
    raw_archive_dir: str = "data/raw"

    # Data-quality reports are written here (committed as evidence; not raw data).
    validation_reports_dir: str = "data/validation_reports"

    # Configurable pilot coverage boundary (Overpass bbox: south,west,north,east).
    # D-8 (2026-11-20): widened to Western Province by owner approval.
    pilot_bbox: str = "6.60,79.75,7.30,80.25"

    # OSM Overpass endpoint (read-only public API; ODbL — see data source register).
    osm_overpass_endpoint: str = "https://overpass-api.de/api/interpreter"
    # Community mirror used when the primary returns transient errors.
    osm_overpass_fallback: str | None = "https://overpass.kumi.systems/api/interpreter"
    # Overpass query execution timeout — larger bboxes need longer.
    osm_overpass_timeout_seconds: int = 300

    cors_origins: list[str] = []

    # Walking engine (ADR-0008): local Valhalla /route service. Compose
    # overrides this to the in-network `valhalla:8002`.
    valhalla_base_url: str = "http://localhost:8002"
    valhalla_timeout_seconds: float = 10.0

    # Plan cache (Phase 4 item 13, ADR-0003): version-keyed plan payloads age
    # out after this TTL; a network-version change invalidates immediately.
    plan_cache_ttl_seconds: int = 3600

    # Grounded AI assistance (Phase 8). The provider adapter is chosen by the
    # factory in app.modules.ai_assistance.providers from `ai_provider`;
    # "none" keeps the feature fully deterministic (default: no key needed).
    # Any OpenAI-compatible chat endpoint works (e.g. CommandCode). The API
    # key is a secret: environment/.env only, never committed.
    ai_provider: Literal["none", "openai_compatible"] = "none"
    ai_base_url: str = ""
    ai_model: str = ""
    ai_api_key: str = ""
    ai_timeout_seconds: float = 20.0
    ai_max_output_tokens: int = 600
    ai_explanations_enabled: bool = True
    # Simple per-client throttle for AI calls (Phase 9 adds real limits).
    ai_requests_per_minute: int = 20

    # Phase 9 — pilot hardening:
    # Admin bearer token for /admin/* (secret: environment/.env only, never
    # committed). Unset fails closed outside local/test.
    admin_api_token: str = ""
    # Per-client throttle for traveller report submissions (abuse protection).
    report_rate_limit_per_minute: int = 60
    # Optional crash-reporting sink: unhandled exceptions post a minimal JSON
    # payload (no messages/stack traces) to this URL. Empty = disabled.
    error_webhook_url: str = ""
    error_webhook_timeout_seconds: float = 2.0

    # Background jobs (ADR-0004: Dramatiq + Redis broker, thin dispatch
    # interface in app/platform/jobs.py). `jobs_enabled` gates dispatch;
    # `scheduled_sync_enabled` gates the scheduler loop (off by default —
    # the pilot refreshes sources on demand via the admin endpoints).
    jobs_enabled: bool = True
    scheduled_sync_enabled: bool = False
    scheduled_sync_interval_seconds: int = 3600

    @property
    def is_local(self) -> bool:
        return self.app_env == "local"


@lru_cache
def get_settings() -> Settings:
    """Return the cached Settings instance."""
    return Settings()
