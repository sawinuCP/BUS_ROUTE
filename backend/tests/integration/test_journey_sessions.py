"""Phase 6 integration: active journey sessions over the real endpoints.

Lifecycle: save a plan → start a session → advance/pause/resume/complete via
manual events → invalid transitions are 409 with the rule → GET restores
state → replan (version change, origin override, no-route case) — progress
resets only when a new plan actually exists.
"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.main import app
from app.platform.config import get_settings
from app.platform.db import dispose_engine
from tests.integration.conftest import _CLEANUP_ORDER
from tests.integration.test_plan_cache_and_saved import FakeCacheStore
from tests.integration.test_planner import _add_pattern, _seed_base

_NA = "00000000-0000-0000-0000-000000000000"


async def _seed_with_saved_plan() -> dict[str, Any]:
    """Committed network + a saved plan (through the real plan endpoint)."""
    engine = create_async_engine(get_settings().database_url)
    try:
        async with engine.begin() as conn:
            ids = await _seed_base(conn)
            await _add_pattern(
                conn,
                ids,
                "138",
                [("A", 1), ("C", 2)],
                destination_label="Homagama",
            )
        with TestClient(app) as client:
            plan = client.post(
                "/api/v1/journeys/plan",
                json={
                    "origin": {"type": "stop", "stop_id": str(ids["A"])},
                    "destination": {"type": "stop", "stop_id": str(ids["C"])},
                    "save": True,
                },
            ).json()
        return {"ids": ids, "journey_id": plan["journey_id"]}
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
    # Endpoint requests ran on the process-global engine inside TestClient's
    # event loop — dispose it (I-13/I-24 pattern).
    await dispose_engine()


async def _relabel_version(label: str) -> None:
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


@pytest.fixture(autouse=True)
def _fake_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    # Endpoint tests must not touch the real Redis client (I-24: its pool
    # binds to one event loop).
    monkeypatch.setattr("app.api.routes.journeys._cache", lambda: FakeCacheStore())


def _start_session(client: TestClient, journey_id: str) -> dict[str, Any]:
    response = client.post(
        "/api/v1/journey-sessions",
        json={"journey_id": journey_id, "option_id": "option-1"},
    )
    assert response.status_code == 200
    return response.json()


async def test_session_lifecycle_manual_progress_to_completion() -> None:
    seeded = await _seed_with_saved_plan()
    try:
        with TestClient(app) as client:
            started = _start_session(client, seeded["journey_id"])
            session_id = started["session_id"]
            # Steps: board → ride → alight; step 0 derives active_ride.
            assert started["status"] == "active_ride"
            assert started["progress"] == {"current_step": 0, "step_count": 3}
            assert started["current_step"]["action"] == "BOARD_TRANSIT"
            assert started["current_step"]["text"] == (
                "Board route 138 at Stop A heading towards Homagama."
            )
            assert started["next_step"]["action"] == "RIDE_TRANSIT"

            # Manual progress: the traveller has boarded and rides (now at 2).
            advanced = client.post(
                f"/api/v1/journey-sessions/{session_id}/events",
                json={"event_type": "step_advanced", "step_index": 2},
            ).json()
            assert advanced["status"] == "active_ride"
            assert advanced["progress"]["current_step"] == 2
            assert advanced["current_step"]["action"] == "ALIGHT_TRANSIT"

            paused = client.post(
                f"/api/v1/journey-sessions/{session_id}/events",
                json={"event_type": "paused"},
            ).json()
            assert paused["status"] == "paused"

            blocked = client.post(
                f"/api/v1/journey-sessions/{session_id}/events",
                json={"event_type": "step_advanced", "step_index": 0},
            )
            assert blocked.status_code == 409  # progress cannot advance while paused

            resumed = client.post(
                f"/api/v1/journey-sessions/{session_id}/events",
                json={"event_type": "resumed"},
            ).json()
            assert resumed["status"] == "active_ride"
            assert resumed["progress"]["current_step"] == 2

            restored = client.get(f"/api/v1/journey-sessions/{session_id}").json()
            assert restored["status"] == "active_ride"
            assert restored["progress"] == {"current_step": 2, "step_count": 3}

            completed = client.post(
                f"/api/v1/journey-sessions/{session_id}/events",
                json={"event_type": "completed", "note": "reached the stop"},
            ).json()
            assert completed["status"] == "completed"

            after = client.post(
                f"/api/v1/journey-sessions/{session_id}/events",
                json={"event_type": "step_advanced", "step_index": 0},
            )
            assert after.status_code == 409  # terminal state
    finally:
        await _cleanup()


async def test_start_requires_a_saved_plan_and_known_option() -> None:
    seeded = await _seed_with_saved_plan()
    try:
        with TestClient(app) as client:
            unknown_journey = client.post(
                "/api/v1/journey-sessions",
                json={"journey_id": _NA, "option_id": "option-1"},
            )
            assert unknown_journey.status_code == 404

            unknown_option = client.post(
                "/api/v1/journey-sessions",
                json={"journey_id": seeded["journey_id"], "option_id": "option-9"},
            )
            assert unknown_option.status_code == 404
    finally:
        await _cleanup()


async def test_replan_resets_progress_and_records_version_change() -> None:
    seeded = await _seed_with_saved_plan()
    try:
        with TestClient(app) as client:
            started = _start_session(client, seeded["journey_id"])
            session_id = started["session_id"]
            client.post(
                f"/api/v1/journey-sessions/{session_id}/events",
                json={"event_type": "step_advanced", "step_index": 2},
            )

            await _relabel_version("test-net-2")
            replanned = client.post(f"/api/v1/journey-sessions/{session_id}/replan", json={}).json()
            assert replanned["replanned"] is True
            assert replanned["dataset_version"] == "test-net-2"
            assert replanned["previous_dataset_version"] == "test-net-1"
            assert replanned["progress"]["current_step"] == 0  # honest reset
            assert replanned["current_step"]["action"] == "BOARD_TRANSIT"
    finally:
        await _cleanup()


async def test_replan_with_origin_override_for_missed_stop() -> None:
    seeded = await _seed_with_saved_plan()
    try:
        with TestClient(app) as client:
            started = _start_session(client, seeded["journey_id"])
            session_id = started["session_id"]

            # Missed-stop recovery: "I am back at Stop A" — replan succeeds.
            replanned = client.post(
                f"/api/v1/journey-sessions/{session_id}/replan",
                json={"origin": {"type": "stop", "stop_id": str(seeded["ids"]["A"])}},
            ).json()
            assert replanned["replanned"] is True
            assert replanned["current_step"]["action"] == "BOARD_TRANSIT"
    finally:
        await _cleanup()


async def test_replan_without_a_route_is_honest_and_session_unchanged() -> None:
    seeded = await _seed_with_saved_plan()
    try:
        with TestClient(app) as client:
            started = _start_session(client, seeded["journey_id"])
            session_id = started["session_id"]
            client.post(
                f"/api/v1/journey-sessions/{session_id}/events",
                json={"event_type": "step_advanced", "step_index": 1},
            )

            # Stop F is far away and unserved — no replacement journey exists.
            failed = client.post(
                f"/api/v1/journey-sessions/{session_id}/replan",
                json={"origin": {"type": "stop", "stop_id": str(seeded["ids"]["F"])}},
            ).json()
            assert failed["replanned"] is False
            assert failed["status"] == "no_route"
            assert failed["notes"]

            restored = client.get(f"/api/v1/journey-sessions/{session_id}").json()
            assert restored["dataset_version"] == "test-net-1"  # unchanged
            assert restored["progress"]["current_step"] == 1  # progress preserved
    finally:
        await _cleanup()


async def test_replan_rejects_completed_session() -> None:
    seeded = await _seed_with_saved_plan()
    try:
        with TestClient(app) as client:
            started = _start_session(client, seeded["journey_id"])
            session_id = started["session_id"]
            client.post(
                f"/api/v1/journey-sessions/{session_id}/events",
                json={"event_type": "completed"},
            )
            response = client.post(f"/api/v1/journey-sessions/{session_id}/replan", json={})
            assert response.status_code == 409
    finally:
        await _cleanup()
