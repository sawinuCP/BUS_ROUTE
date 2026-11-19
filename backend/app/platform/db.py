"""Async SQLAlchemy engine/session wiring (canonical module: `platform`).

The engine is created lazily so the app can boot (and serve liveness checks)
without a database connection. The canonical database is PostgreSQL + PostGIS;
the URL is supplied by configuration and never constructed from user input.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.platform.config import get_settings

logger = logging.getLogger(__name__)

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    """Return the process-wide async engine, creating it on first use."""
    global _engine
    if _engine is None:
        settings = get_settings()
        if not settings.database_url.startswith("postgresql+asyncpg://"):
            raise ValueError("DATABASE_URL must use the postgresql+asyncpg:// scheme")
        _engine = create_async_engine(settings.database_url, pool_pre_ping=True, future=True)
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return the process-wide session factory, creating it on first use."""
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(bind=get_engine(), expire_on_commit=False)
    return _session_factory


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency yielding a transactional session."""
    async with get_session_factory()() as session:
        yield session


async def check_database() -> dict[str, Any]:
    """Ping the database. Returns a status dict; never raises to the caller."""
    try:
        async with get_engine().connect() as connection:
            result = await connection.execute(text("SELECT 1"))
            ok = result.scalar_one() == 1
        return {"ok": ok, "error": None}
    except Exception as exc:  # noqa: BLE001 - deliberately broad: health check must not raise
        logger.warning("Database health check failed", extra={"error_type": type(exc).__name__})
        return {"ok": False, "error": type(exc).__name__}


async def dispose_engine() -> None:
    """Dispose the engine on application shutdown."""
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _session_factory = None
