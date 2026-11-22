"""Unit: plan-cache port (Phase 4 item 13, ADR-0003 scope).

Properties: keys are normalized (identical requests → one key) and versioned
(version change → new key); the null cache always misses; the Redis adapter
round-trips payloads and degrades every failure to a miss (a cache loss must
never change a routing result).
"""

from __future__ import annotations

from typing import Any

import pytest

from app.modules.planner.cache import NullPlanCache, normalized_request_key
from app.platform.plan_cache import RedisPlanCache

_STOP = {
    "type": "stop",
    "stop_id": "6a1b3b7e-d0a3-4c1e-aebf-df4106fd4a84",
    "lon": None,
    "lat": None,
}
_PREFS = {
    "priority": "fastest",
    "max_walking_m": 1500,
    "max_transfers": 1,
    "allowed_modes": ["bus"],
    "require_verified_transfers": False,
}


def test_key_is_deterministic_and_normalized() -> None:
    first = normalized_request_key("net-1", _STOP, _STOP, _PREFS)
    second = normalized_request_key("net-1", dict(reversed(list(_STOP.items()))), _STOP, _PREFS)

    assert first == second  # key order in the payload does not matter


def test_key_changes_when_any_part_changes() -> None:
    base = normalized_request_key("net-1", _STOP, _STOP, _PREFS)

    assert normalized_request_key("net-2", _STOP, _STOP, _PREFS) != base
    assert (
        normalized_request_key(
            "net-1", _STOP, {**_STOP, "stop_id": "8911b222-1566-4b08-861b-6b1735a763ea"}, _PREFS
        )
        != base
    )
    assert normalized_request_key("net-1", _STOP, _STOP, {**_PREFS, "max_walking_m": 2000}) != base


async def test_null_cache_always_misses() -> None:
    cache = NullPlanCache()

    assert await cache.get_json("plan:net-1:abc") is None
    await cache.set_json("plan:net-1:abc", {"status": "ok"}, ttl_seconds=60)
    assert await cache.get_json("plan:net-1:abc") is None


class FakeRedis:
    """Minimal Redis-like double (async get/set with ex kwargs)."""

    def __init__(self, *, fail: bool = False) -> None:
        self.store: dict[str, str] = {}
        self.fail = fail

    async def get(self, key: str) -> str | None:
        if self.fail:
            raise ConnectionError("redis down")
        return self.store.get(key)

    async def set(self, key: str, value: str, ex: int | None = None) -> None:
        if self.fail:
            raise ConnectionError("redis down")
        self.store[key] = value


@pytest.mark.parametrize("fail", [False, True])
async def test_redis_adapter_roundtrip_and_degradation(fail: bool) -> None:
    client = FakeRedis(fail=fail)
    cache = RedisPlanCache(client, ttl_seconds=60)  # type: ignore[arg-type]
    payload: dict[str, Any] = {"status": "ok", "options": [1, 2, 3]}

    assert await cache.get_json("k") is None  # miss before write
    await cache.set_json("k", payload, ttl_seconds=60)  # must not raise on failure

    if fail:
        assert await cache.get_json("k") is None  # failure degrades to a miss
    else:
        assert await cache.get_json("k") == payload


async def test_redis_adapter_treats_unparsable_payload_as_miss() -> None:
    client = FakeRedis()
    cache = RedisPlanCache(client, ttl_seconds=60)  # type: ignore[arg-type]
    client.store["sljp:plan:k"] = "not-json{"

    assert await cache.get_json("k") is None
