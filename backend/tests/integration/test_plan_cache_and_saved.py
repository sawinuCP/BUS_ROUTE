"""Phase 4 completion integration: plan cache + saved journeys.

Cache: the endpoint serves a cache **hit** for an identical request over the
same network version, a **miss** after the version label changes (keyed
invalidation, ADR-0003). Saved journeys: `save: true` persists the request +
snapshot; `GET /journeys/{id}` returns the snapshot unchanged; `refresh`
re-plans against the current active version and records the previous version.
Redis is faked with an in-process store so tests are deterministic.
"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.main import app
from app.platform.config import get_settings
from tests.integration.conftest import _CLEANUP_ORDER
from tests.integration.test_planner import _add_pattern, _seed_base


class FakeCacheStore:
    """In-process PlanCache double (deterministic, no Redis)."""

    def __init__(self) -> None:
        self.store: dict[str, dict[str, Any]] = {}

    async def get_json(self, key: str) -> dict[str, Any] | None:
        return self.store.get(key)

    async def set_json(self, key: str, value: dict[str, Any], ttl_seconds: int) -> None:
        self.store[key] = value


@pytest.fixture
def fake_cache(monkeypatch: pytest.MonkeyPatch) -> FakeCacheStore:
    store = FakeCacheStore()
    monkeypatch.setattr("app.api.routes.journeys._cache", lambda: store)
    return store


async def _seed_direct_committed() -> dict[str, Any]:
    """Committed one-pattern network (the endpoint uses its own session)."""
    engine = create_async_engine(get_settings().database_url)
    try:
        async with engine.begin() as conn:
            ids: dict[str, Any] = await _seed_base(conn)
            await _add_pattern(conn, ids, "138", [("A", 1), ("C", 2)])
    finally:
        await engine.dispose()
    return ids


def _plan_body(ids: dict[str, Any]) -> dict[str, Any]:
    return {
        "origin": {"type": "stop", "stop_id": str(ids["A"])},
        "destination": {"type": "stop", "stop_id": str(ids["C"])},
    }


async def _set_version_label(label: str) -> None:
    engine = create_async_engine(get_settings().database_url)
    try:
        async with engine.begin() as conn:
            await conn.execute(
                text(
                    "UPDATE dataset_versions SET version_label = :l"
                    " WHERE version_label = 'test-net-1'"
                ),
                {"l": label},
            )
    finally:
        await engine.dispose()


async def _cleanup() -> None:
    engine = create_async_engine(get_settings().database_url)
    try:
        async with engine.begin() as conn:
            for statement in _CLEANUP_ORDER:
                await conn.execute(text(statement))
    finally:
        await engine.dispose()


async def test_cache_hit_then_version_change_invalidates(
    fake_cache: FakeCacheStore,
) -> None:
    ids = await _seed_direct_committed()
    try:
        with TestClient(app) as client:
            first = client.post("/api/v1/journeys/plan", json=_plan_body(ids)).json()
            second = client.post("/api/v1/journeys/plan", json=_plan_body(ids)).json()

            assert first["cache"] == "miss"
            assert second["cache"] == "hit"
            assert second["status"] == "ok"
            assert second["options"] == first["options"]

            await _set_version_label("test-net-2")
            third = client.post("/api/v1/journeys/plan", json=_plan_body(ids)).json()

            # Network-version change → new key → recompute (never a stale plan).
            assert third["cache"] == "miss"
            assert third["dataset_version"] == "test-net-2"
    finally:
        await _cleanup()


async def test_saved_journey_snapshot_get_and_refresh(
    fake_cache: FakeCacheStore,
) -> None:
    ids = await _seed_direct_committed()
    try:
        with TestClient(app) as client:
            plan = client.post(
                "/api/v1/journeys/plan", json={**_plan_body(ids), "save": True}
            ).json()
            journey_id = plan["journey_id"]
            assert plan["dataset_version"] == "test-net-1"

            saved = client.get(f"/api/v1/journeys/{journey_id}").json()
            assert saved["journey_id"] == journey_id
            assert saved["saved_at_dataset_version"] == "test-net-1"
            assert saved["options"] == plan["options"]  # the snapshot, unchanged

            refreshed = client.post(f"/api/v1/journeys/{journey_id}/refresh").json()
            assert refreshed["refreshed"] is True
            assert refreshed["journey_id"] == journey_id
            assert refreshed["dataset_version"] == "test-net-1"
            assert refreshed["previous_dataset_version"] == "test-net-1"
            assert refreshed["status"] == "ok"

            await _set_version_label("test-net-2")
            replanned = client.post(f"/api/v1/journeys/{journey_id}/refresh").json()
            assert replanned["dataset_version"] == "test-net-2"
            assert replanned["previous_dataset_version"] == "test-net-1"
            assert replanned["refreshed"] is True

            unknown = client.get("/api/v1/journeys/00000000-0000-0000-0000-000000000000")
            assert unknown.status_code == 404
    finally:
        await _cleanup()
