"""Phase 9 item 4 — concurrency gate (deterministic load/race testing).

Real concurrency in-process: N asyncio tasks issue requests through one
httpx.AsyncClient over ASGITransport against the seeded test network —
exactly the concurrency shape uvicorn serves (same-loop tasks, shared
engine pool, shared limiter state).

Under test:
- **plan race**: identical concurrent plans all succeed, produce identical
  options (determinism) and share one computation via the cache;
- **report idempotency race**: concurrent submissions with the same
  `client_key` never duplicate a row;
- **rate-limit race**: concurrent submissions partition *exactly* (the
  limiter is atomic), success count == the configured budget;
- **session race**: concurrent terminal events serialize via row locking —
  exactly one acceptance, the rest 409 (this gate found the lost-update
  race fixed with FOR UPDATE);
- **mixed workload**: zero 5xx across concurrent mixed traffic.

All async; engine disposed in teardown (per-test event loop, I-13).
"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient  # noqa: F401  (kept for parity)
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.main import app
from app.platform.config import get_settings
from app.platform.db import dispose_engine
from tests.integration.conftest import _CLEANUP_ORDER
from tests.routing.test_plan_cache_and_saved import (
    FakeCacheStore,
    _plan_body,
    _seed_direct_committed,
)


@pytest.fixture
def fake_cache(monkeypatch: pytest.MonkeyPatch) -> FakeCacheStore:
    store = FakeCacheStore()
    monkeypatch.setattr("app.api.routes.journeys._cache", lambda: store)
    return store


@pytest.fixture
async def client() -> AsyncClient:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as async_client:
        yield async_client
    await dispose_engine()


async def _cleanup_tables() -> None:
    engine = create_async_engine(get_settings().database_url)
    try:
        async with engine.begin() as conn:
            for statement in _CLEANUP_ORDER:
                await conn.execute(text(statement))
    finally:
        await engine.dispose()


async def _report_count() -> int:
    engine = create_async_engine(get_settings().database_url)
    try:
        async with engine.connect() as conn:
            return int(
                (await conn.execute(text("SELECT count(*) FROM transport_reports"))).scalar_one()
            )
    finally:
        await engine.dispose()


async def test_concurrent_identical_plans_are_deterministic(
    fake_cache: FakeCacheStore, client: AsyncClient
) -> None:
    ids = await _seed_direct_committed()
    try:
        body = _plan_body(ids)

        async def worker(index: int) -> dict[str, Any]:
            response = await client.post("/api/v1/journeys/plan", json=body)
            assert response.status_code == 200
            return response.json()

        payloads = list(await __import__("asyncio").gather(*(worker(i) for i in range(12))))

        # Determinism: every concurrent request returns the same options.
        assert all(p["status"] == "ok" for p in payloads)
        assert all(p["options"] == payloads[0]["options"] for p in payloads)
        # The cache shared one computation: at least one hit, no gaps.
        hits = sum(1 for p in payloads if p["cache"] == "hit")
        misses = sum(1 for p in payloads if p["cache"] == "miss")
        assert hits >= 1
        assert hits + misses == 12
    finally:
        await _cleanup_tables()


async def test_concurrent_identical_reports_never_duplicate(client: AsyncClient) -> None:
    try:
        body = {
            "category": "wrong_stop",
            "description": "The 138 boards at the opposite side of the road here.",
            "consent": True,
            "client_key": "race-idempotent-1",
        }

        async def worker(index: int) -> dict[str, Any]:
            response = await client.post("/api/v1/reports", json=body)
            assert response.status_code == 201
            return response.json()

        payloads = list(await __import__("asyncio").gather(*(worker(i) for i in range(12))))
        created = [p for p in payloads if not p["duplicate"]]
        assert len(created) == 1, "exactly one request may create the report"
        assert await _report_count() == 1
    finally:
        await _cleanup_tables()


async def test_concurrent_reports_partition_exactly_by_rate_limit(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("REPORT_RATE_LIMIT_PER_MINUTE", "5")
    get_settings.cache_clear()
    try:

        async def worker(index: int) -> int:
            response = await client.post(
                "/api/v1/reports",
                json={
                    "category": "wrong_stop",
                    "description": "The 138 boards at the opposite side of the road here.",
                    "consent": True,
                    "client_key": f"race-rl-{index:04d}",
                },
            )
            return response.status_code

        statuses = list(await __import__("asyncio").gather(*(worker(i) for i in range(12))))
        created = statuses.count(201)
        limited = statuses.count(429)
        # Atomic limiter: the budget is respected exactly, no over-admission.
        assert created == 5
        assert limited == 7
        assert created + limited == 12
    finally:
        get_settings.cache_clear()
        await _cleanup_tables()


# --------------------------------------------------------------------------- #
# Session race: concurrent terminal events serialize (row locking)
# --------------------------------------------------------------------------- #


def _ai_payload() -> dict[str, Any]:
    return {
        "status": "ok",
        "dataset_version": "test-net-1",
        "language": "en",
        "notes": [],
        "options": [
            {
                "id": "opt-1",
                "labels": ["138"],
                "warnings": [],
                "summary": {
                    "estimated_duration_minutes": {"min": 10, "max": 20},
                    "walking_distance_m": 100,
                    "transfer_count": 0,
                    "confidence": "unverified",
                },
                "steps": [
                    {
                        "action": "BOARD_TRANSIT",
                        "text": "Board route 138 at Stop A.",
                        "facts": {"route_code": "138", "stop_name": "Stop A"},
                        "confidence": "unverified",
                    }
                ],
            }
        ],
    }


async def _seed_plan_and_session(
    fake_cache: FakeCacheStore, client: AsyncClient
) -> tuple[str, str]:
    """Seed the network, plan + save it, start a session; return ids."""
    ids = await _seed_direct_committed()
    plan = (
        await client.post("/api/v1/journeys/plan", json=_plan_body(ids) | {"save": True})
    ).json()
    journey_id = plan["journey_id"]
    option_id = plan["options"][0]["id"]
    started = await client.post(
        "/api/v1/journey-sessions",
        json={"journey_id": journey_id, "option_id": option_id},
    )
    assert started.status_code == 200
    return journey_id, started.json()["session_id"]


async def test_concurrent_terminal_events_serialize_exactly(
    fake_cache: FakeCacheStore, client: AsyncClient
) -> None:
    journey_id, session_id = await _seed_plan_and_session(fake_cache, client)
    try:

        async def worker(index: int) -> int:
            response = await client.post(
                f"/api/v1/journey-sessions/{session_id}/events",
                json={"event_type": "completed"},
            )
            return response.status_code

        statuses = list(await __import__("asyncio").gather(*(worker(i) for i in range(8))))
        # Row locking: exactly one traveller wins the terminal transition;
        # every other concurrent attempt is refused with the rule (409) —
        # never a silent double-completion.
        assert statuses.count(200) == 1
        assert statuses.count(409) == 7

        # The session is completed and terminal: replanning is refused too.
        final = await client.get(f"/api/v1/journey-sessions/{session_id}")
        assert final.json()["status"] == "completed"
        replan = await client.post(f"/api/v1/journey-sessions/{session_id}/replan")
        assert replan.status_code == 409
    finally:
        await _cleanup_tables()


async def test_concurrent_same_step_advances_are_idempotent(
    fake_cache: FakeCacheStore, client: AsyncClient
) -> None:
    journey_id, session_id = await _seed_plan_and_session(fake_cache, client)
    try:

        async def worker(index: int) -> int:
            response = await client.post(
                f"/api/v1/journey-sessions/{session_id}/events",
                json={"event_type": "step_advanced", "step_index": 1},
            )
            return response.status_code

        statuses = list(await __import__("asyncio").gather(*(worker(i) for i in range(6))))
        # Racing to the same step is allowed for every attempt (setting the
        # same index is idempotent) — no lost updates, no double-advance,
        # no 5xx.
        assert all(status == 200 for status in statuses)
        final = (await client.get(f"/api/v1/journey-sessions/{session_id}")).json()
        assert final["progress"]["current_step"] == 1
        assert journey_id  # keeps the seed alive for cleanup ordering
    finally:
        await _cleanup_tables()


# --------------------------------------------------------------------------- #
# Mixed workload: zero 5xx under concurrent traffic
# --------------------------------------------------------------------------- #


async def test_mixed_workload_has_no_server_errors(
    fake_cache: FakeCacheStore, client: AsyncClient
) -> None:
    ids = await _seed_direct_committed()
    try:
        plan_body = _plan_body(ids)
        report_body = {
            "category": "wrong_stop",
            "description": "The 138 boards at the opposite side of the road here.",
            "consent": True,
        }
        ai_body = {"mode": "why_route", "journey": _ai_payload()}

        async def worker(index: int) -> int:
            kind = index % 5
            if kind == 0:
                response = await client.post("/api/v1/journeys/plan", json=plan_body)
            elif kind == 1:
                response = await client.get("/api/v1/places/search?q=Stop")
            elif kind == 2:
                response = await client.get("/api/v1/health")
            elif kind == 3:
                response = await client.post(
                    "/api/v1/reports",
                    json=report_body | {"client_key": f"mixed-workload-{index:04d}"},
                )
            else:
                response = await client.post("/api/v1/ai/why-route", json=ai_body)
            # Reports share the 60/min budget — rate limiting is expected
            # under load; everything else must be a clean 200.
            if kind == 3:
                assert response.status_code in (201, 429)
            else:
                assert response.status_code == 200, response.text
            return response.status_code

        statuses = list(await __import__("asyncio").gather(*(worker(i) for i in range(30))))
        assert all(status < 500 for status in statuses)
    finally:
        await _cleanup_tables()
