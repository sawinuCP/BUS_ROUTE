"""Plan cache port (Phase 4 work item 13; scope per ADR-0003).

The planner never touches Redis directly (domain code must not depend on
infrastructure); it consumes this structural port, and the API layer wires a
Redis-backed adapter (`app.platform.plan_cache.RedisPlanCache`) or the null
implementation.

ADR-0003 rules encoded here:
- **Invalidation is tied to the network dataset version**: the cache key embeds
  the version label, so a version change produces a new key — old entries can
  only age out, never serve a new network (plan regression: "network-version
  change produces a new plan/cache key").
- **Losing Redis must not change a routing result**: a cache miss simply
  recomputes from the canonical database; failures are logged and treated as
  misses by the adapter. Redis is never a source of truth.
- Keys are derived from the **normalized** request (sorted, canonical JSON), so
  logically identical requests hit one entry.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Protocol


class PlanCache(Protocol):
    """Structural port for plan caching (implement without importing this)."""

    async def get_json(self, key: str) -> dict[str, Any] | None:
        """Return the cached payload or None (miss/failure/unavailable)."""

    async def set_json(self, key: str, value: dict[str, Any], ttl_seconds: int) -> None:
        """Store a payload; failures must be swallowed (cache is optional)."""


class NullPlanCache:
    """Always-miss cache: every request recomputes (also the offline fallback)."""

    async def get_json(self, key: str) -> dict[str, Any] | None:
        return None

    async def set_json(self, key: str, value: dict[str, Any], ttl_seconds: int) -> None:
        return None


def normalized_request_key(
    version_label: str,
    origin: dict[str, Any],
    destination: dict[str, Any],
    preferences: dict[str, Any],
) -> str:
    """Deterministic cache key: normalized request + network version."""
    canonical = json.dumps(
        {
            "version": version_label,
            "origin": origin,
            "destination": destination,
            "preferences": preferences,
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:32]
    return f"plan:{version_label}:{digest}"
