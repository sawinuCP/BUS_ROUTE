"""Redis client wiring (scope per ADR-0003: cache/rate-limiting/queue backing only).

Redis is never a source of truth. Connection creation is lazy so the app can
boot without Redis; a failed Redis must degrade service, not crash it.
"""

from __future__ import annotations

import logging
from typing import Any

import redis.asyncio as aioredis
from redis.asyncio import Redis

from app.platform.config import get_settings

logger = logging.getLogger(__name__)

_redis: Redis | None = None


def get_redis() -> Redis:
    """Return the process-wide Redis client, creating it on first use."""
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(get_settings().redis_url, decode_responses=True)
    return _redis


async def check_redis() -> dict[str, Any]:
    """Ping Redis. Returns a status dict; never raises to the caller."""
    try:
        pong = await get_redis().ping()
        return {"ok": bool(pong), "error": None}
    except Exception as exc:  # noqa: BLE001 - deliberately broad: health check must not raise
        logger.warning("Redis health check failed", extra={"error_type": type(exc).__name__})
        return {"ok": False, "error": type(exc).__name__}


async def close_redis() -> None:
    """Close the Redis client on application shutdown."""
    global _redis
    if _redis is not None:
        await _redis.aclose()
    _redis = None
