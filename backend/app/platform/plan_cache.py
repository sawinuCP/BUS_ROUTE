"""Redis-backed plan cache (ADR-0003: cache keyed by request + network version).

Structural implementation of `app.modules.planner.cache.PlanCache` — the
platform layer never imports domain code. All Redis failures degrade to cache
misses: the API recomputes from the canonical database and the routing result
never depends on Redis being up (ADR-0003 §5).
"""

from __future__ import annotations

import json
import logging
from typing import Any

from redis.asyncio import Redis

logger = logging.getLogger(__name__)

_KEY_PREFIX = "sljp:plan"


class RedisPlanCache:
    """Stores serialized plan payloads with a TTL (entries age out; keys embed
    the dataset version, so a version change is an implicit invalidation)."""

    def __init__(self, client: Redis, ttl_seconds: int = 3600) -> None:
        self._client = client
        self._ttl_seconds = ttl_seconds

    async def get_json(self, key: str) -> dict[str, Any] | None:
        try:
            raw = await self._client.get(f"{_KEY_PREFIX}:{key}")
        except Exception as exc:  # noqa: BLE001 - degrade to a miss, never raise
            logger.warning("plan cache read failed: %s", type(exc).__name__)
            return None
        if raw is None:
            return None
        try:
            return json.loads(str(raw))
        except ValueError:
            logger.warning("plan cache held an unparsable payload (treated as miss)")
            return None

    async def set_json(self, key: str, value: dict[str, Any], ttl_seconds: int) -> None:
        try:
            await self._client.set(
                f"{_KEY_PREFIX}:{key}", json.dumps(value, ensure_ascii=False), ex=ttl_seconds
            )
        except Exception as exc:  # noqa: BLE001 - cache writes are best-effort
            logger.warning("plan cache write failed: %s", type(exc).__name__)
