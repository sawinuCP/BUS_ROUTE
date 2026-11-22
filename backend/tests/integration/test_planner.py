"""Phase 4 integration: deterministic planner over a seeded network.

Curated regression cases (plan §Phase 4): direct, one transfer via an explicit
connector, same-stop re-board, walk cap, honest no-route, walking-only
fallback, verified-rail rule and determinism. The walking router is faked
(exactly one routed 240 m / 180 s path) so no network is needed.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession

from app.modules.pedestrian.router import WalkPlan, WalkStep
from app.modules.planner import (
    Endpoint,
    JourneyPlanner,
    PlanningConstraints,
    load_network,
)

# Stops: A/B a close pair, C/D a close pair, ~15 km apart (like Homagama→Kollupitiya).
_STOPS: dict[str, tuple[float, float]] = {
    "A": (79.9777, 6.8440),
    "B": (79.9797, 6.8440),
    "C": (79.8483, 6.9107),
    "D": (79.8463, 6.9107),
    "F": (80.1000, 6.6000),  # far away, unserved
}


class FakeWalkingRouter:
    """Deterministic fake: routed path ≈ 1.2× straight-line, 1.4 m/s walk."""

    provider_name = "fake"

    def __init__(self) -> None:
        self.calls = 0

    async def route_walk(
        self, lon_from: float, lat_from: float, lon_to: float, lat_to: float
    ) -> WalkPlan | None:
        self.calls += 1
        from app.modules.planner.itinerary import haversine_m

        distance = haversine_m(lon_from, lat_from, lon_to, lat_to) * 1.2
        return WalkPlan(
            distance_m=distance,
            duration_s=distance / 1.4,
            steps=(WalkStep(distance, distance / 1.4, "Walk east.", "Galle Road", None),),
            provider=self.provider_name,
            coordinates=((lon_from, lat_from), (lon_to, lat_to)),
        )


async def _seed_base(db_conn: AsyncConnection) -> dict[str, Any]:
    """Dataset version (active) + stops + one default access point each."""
    ids: dict[str, Any] = {}
    version_id = (
        await db_conn.execute(
            text(
                "INSERT INTO dataset_versions (version_label, status)"
                " VALUES ('test-net-1', 'published') RETURNING id"
            )
        )
    ).scalar_one()
    await db_conn.execute(
        text(
            "INSERT INTO active_dataset (id, dataset_version_id, activated_at)"
            " VALUES (1, :v, now())"
        ),
        {"v": version_id},
    )
    for code, (lon, lat) in _STOPS.items():
        stop_id = (
            await db_conn.execute(
                text(
                    "INSERT INTO stops (name, mode, location)"
                    f" VALUES ('Stop {code}', 'bus', 'POINT({lon} {lat})') RETURNING id"
                )
            )
        ).scalar_one()
        access_id = (
            await db_conn.execute(
                text(
                    "INSERT INTO stop_access_points (stop_id, location)"
                    f" VALUES (:s, 'POINT({lon} {lat})') RETURNING id"
                ),
                {"s": stop_id},
            )
        ).scalar_one()
        ids[code] = stop_id
        ids[f"ap_{code}"] = access_id
    return ids


async def _add_pattern(
    db_conn: AsyncConnection,
    ids: dict[str, Any],
    route_code: str,
    calls: list[tuple[str, int]],
    *,
    mode: str = "bus",
    verification: str = "unverified",
    destination_label: str | None = None,
) -> str:
    route_id = (
        await db_conn.execute(
            text(
                "INSERT INTO transport_routes (route_code, mode) VALUES (:code, :mode) RETURNING id"
            ),
            {"code": route_code, "mode": mode},
        )
    ).scalar_one()
    pattern_id = (
        await db_conn.execute(
            text(
                "INSERT INTO route_patterns (route_id, pattern_code, direction_id,"
                " verification_status, destination_label)"
                " VALUES (:r, :code_d0, 0, :verification, :destination_label)"
                " RETURNING id"
            ),
            {
                "r": route_id,
                "code_d0": f"{route_code}-D0",
                "verification": verification,
                "destination_label": destination_label,
            },
        )
    ).scalar_one()
    for stop_code, sequence in calls:
        await db_conn.execute(
            text(
                "INSERT INTO route_pattern_stops (pattern_id, stop_id, sequence)"
                " VALUES (:p, :s, :seq)"
            ),
            {"p": pattern_id, "s": ids[stop_code], "seq": sequence},
        )
    return str(pattern_id)


async def _add_connector(
    db_conn: AsyncConnection,
    ids: dict[str, Any],
    from_code: str,
    to_code: str,
    *,
    status: str = "unverified",
) -> str:
    connector_id = (
        await db_conn.execute(
            text(
                "INSERT INTO transfer_connections"
                " (from_access_point_id, to_access_point_id, walk_distance_m,"
                "  estimated_walk_seconds, walk_geometry, verification_status)"
                " VALUES (:fa, :ta, 240, 180,"
                "  'MULTILINESTRING((79.8483 6.9107, 79.8490 6.9107, 79.9797 6.8440))',"
                "  :status) RETURNING id"
            ),
            {"fa": ids[f"ap_{from_code}"], "ta": ids[f"ap_{to_code}"], "status": status},
        )
    ).scalar_one()
    return str(connector_id)


@pytest.fixture
async def db_session(db_conn: AsyncConnection) -> AsyncIterator[AsyncSession]:
    """An ORM session over the test's own transaction (rolls back with it)."""
    session = AsyncSession(bind=db_conn)
    yield session
    await session.close()


def _stop(code: str, ids: dict[str, Any]) -> Endpoint:
    return Endpoint(kind="stop", stop_id=uuid.UUID(str(ids[code])))


def _coords(lon: float, lat: float) -> Endpoint:
    return Endpoint(kind="coordinates", lon=lon, lat=lat)


async def test_direct_candidate_board_before_alight(
    db_conn: AsyncConnection, db_session: AsyncSession
) -> None:
    ids = await _seed_base(db_conn)
    await _add_pattern(db_conn, ids, "138", [("A", 1), ("C", 2)])
    network = await load_network(db_session)
    planner = JourneyPlanner(network, FakeWalkingRouter())

    result = await planner.plan(_stop("A", ids), _stop("C", ids), PlanningConstraints())

    assert result.status == "ok"
    assert result.version_label == "test-net-1"
    assert len(result.options) == 1
    option = result.options[0]
    assert option.transfer_count == 0
    assert option.walk_distance_m == 0.0
    rides = [leg for leg in option.legs if type(leg).__name__ == "RideLeg"]
    assert len(rides) == 1
    assert rides[0].route_code == "138"
    # Invariant: board strictly before alight on the exact pattern.
    assert rides[0].board_sequence == 1
    assert rides[0].alight_sequence == 2
    assert rides[0].board_stop_name == "Stop A"
    assert rides[0].alight_stop_name == "Stop C"
    # Every pattern in the candidate dataset is unverified — flagged honestly.
    assert option.confidence == "unverified_pattern"
    assert any("not been field-verified" in warning for warning in option.warnings)


async def test_one_transfer_requires_explicit_connector(
    db_conn: AsyncConnection, db_session: AsyncSession
) -> None:
    ids = await _seed_base(db_conn)
    await _add_pattern(db_conn, ids, "138", [("A", 1), ("C", 2)])
    await _add_pattern(db_conn, ids, "145", [("B", 1), ("D", 2)])
    await _add_connector(db_conn, ids, "C", "B")  # unverified proposal
    network = await load_network(db_session)
    router = FakeWalkingRouter()
    planner = JourneyPlanner(network, router)

    result = await planner.plan(_stop("A", ids), _stop("D", ids), PlanningConstraints())

    assert result.status == "ok"
    assert len(result.options) == 1
    option = result.options[0]
    kinds = [type(leg).__name__ for leg in option.legs]
    assert kinds == ["RideLeg", "WalkLeg", "RideLeg"]
    assert option.transfer_count == 1
    walk = option.legs[1]
    assert walk.distance_m == 240.0  # from the stored routed connector, not guessed
    assert walk.provider == "stored_connector"
    assert walk.coordinates  # real stored geometry carried through
    assert option.confidence == "unverified_transfer"
    assert any("not field-verified" in warning for warning in option.warnings)

    # Constraint: verified transfers only → the unverified connector is unusable.
    strict = PlanningConstraints(require_verified_transfers=True)
    strict_result = await planner.plan(_stop("A", ids), _stop("D", ids), strict)
    assert strict_result.status == "no_route"


async def test_same_stop_reboard_needs_no_connector(
    db_conn: AsyncConnection, db_session: AsyncSession
) -> None:
    ids = await _seed_base(db_conn)
    await _add_pattern(db_conn, ids, "138", [("A", 1), ("C", 2)])
    await _add_pattern(db_conn, ids, "100", [("C", 1), ("D", 2)])
    network = await load_network(db_session)
    planner = JourneyPlanner(network, FakeWalkingRouter())

    result = await planner.plan(_stop("A", ids), _stop("D", ids), PlanningConstraints())

    assert result.status == "ok"
    assert len(result.options) == 1
    option = result.options[0]
    kinds = [type(leg).__name__ for leg in option.legs]
    assert kinds == ["RideLeg", "RideLeg"]  # zero-walk change where you stand
    assert option.transfer_count == 1
    assert option.walk_distance_m == 0.0
    assert option.legs[0].route_code == "138"
    assert option.legs[1].route_code == "100"


async def test_walk_cap_excludes_option_and_reports_no_route(
    db_conn: AsyncConnection, db_session: AsyncSession
) -> None:
    ids = await _seed_base(db_conn)
    await _add_pattern(db_conn, ids, "138", [("A", 1), ("C", 2)])
    await _add_pattern(db_conn, ids, "145", [("B", 1), ("D", 2)])
    await _add_connector(db_conn, ids, "C", "B")
    network = await load_network(db_session)
    planner = JourneyPlanner(network, FakeWalkingRouter())

    tight = PlanningConstraints(max_walking_m=200.0)
    result = await planner.plan(_stop("A", ids), _stop("D", ids), tight)

    assert result.status == "no_route"
    assert result.options == ()
    assert any("exceeds the walking cap" in note for note in result.notes)


async def test_no_route_is_honest_when_network_does_not_connect(
    db_conn: AsyncConnection, db_session: AsyncSession
) -> None:
    ids = await _seed_base(db_conn)
    await _add_pattern(db_conn, ids, "138", [("A", 1), ("C", 2)])
    network = await load_network(db_session)
    planner = JourneyPlanner(network, FakeWalkingRouter())

    result = await planner.plan(_stop("A", ids), _stop("D", ids), PlanningConstraints())

    assert result.status == "no_route"
    assert result.options == ()
    # The reason is stated, never fabricated away.
    assert any("Walking-only distance" in note for note in result.notes)


async def test_walking_only_fallback_within_cap(
    db_conn: AsyncConnection, db_session: AsyncSession
) -> None:
    ids = await _seed_base(db_conn)
    await _add_pattern(db_conn, ids, "138", [("A", 1), ("C", 2)])
    network = await load_network(db_session)
    planner = JourneyPlanner(network, FakeWalkingRouter())

    # Coordinates ~222 m apart (D → C); no transit option connects them.
    result = await planner.plan(
        _coords(79.8460, 6.9107), _coords(79.8483, 6.9107), PlanningConstraints()
    )

    assert result.status == "ok"
    assert len(result.options) == 1
    option = result.options[0]
    assert option.ride_count == 0
    # ~254 m straight-line × 1.2 fake detour — a real routed path, not a guess.
    assert 250.0 < option.walk_distance_m < 400.0
    assert option.legs[0].purpose == "walk_only"
    assert any("walking-only" in warning for warning in option.warnings)


async def test_rail_requires_verified_station_order(
    db_conn: AsyncConnection, db_session: AsyncSession
) -> None:
    ids = await _seed_base(db_conn)
    await _add_pattern(
        db_conn, ids, "RL", [("A", 1), ("C", 2)], mode="rail", verification="unverified"
    )
    network = await load_network(db_session)
    planner = JourneyPlanner(network, FakeWalkingRouter())
    modes = PlanningConstraints(allowed_modes=frozenset({"bus", "rail"}))

    blocked = await planner.plan(_stop("A", ids), _stop("C", ids), modes)
    assert blocked.status == "no_route"
    assert any("Rail route RL excluded" in note for note in blocked.notes)

    await db_conn.execute(text("UPDATE route_patterns SET verification_status = 'verified'"))
    network_verified = await load_network(db_session)
    planner_verified = JourneyPlanner(network_verified, FakeWalkingRouter())
    allowed = await planner_verified.plan(_stop("A", ids), _stop("C", ids), modes)
    assert allowed.status == "ok"
    rides = [leg for leg in allowed.options[0].legs if type(leg).__name__ == "RideLeg"]
    assert rides[0].mode == "rail"
    assert allowed.options[0].confidence == "verified"


async def test_planning_is_deterministic(
    db_conn: AsyncConnection, db_session: AsyncSession
) -> None:
    ids = await _seed_base(db_conn)
    await _add_pattern(db_conn, ids, "138", [("A", 1), ("C", 2)])
    await _add_pattern(db_conn, ids, "145", [("B", 1), ("D", 2)])
    await _add_connector(db_conn, ids, "C", "B")
    network = await load_network(db_session)
    planner = JourneyPlanner(network, FakeWalkingRouter())

    first = await planner.plan(_stop("A", ids), _stop("D", ids), PlanningConstraints())
    second = await planner.plan(_stop("A", ids), _stop("D", ids), PlanningConstraints())

    assert first.options == second.options
    assert first.labels == second.labels
    assert first.notes == second.notes


async def test_multi_transfer_chain_within_transfer_cap(
    db_conn: AsyncConnection, db_session: AsyncSession
) -> None:
    """max_transfers=2 allows an A → C → F → D chain (same-stop re-boards)."""
    ids = await _seed_base(db_conn)
    await _add_pattern(db_conn, ids, "138", [("A", 1), ("C", 2)])
    await _add_pattern(db_conn, ids, "100", [("C", 1), ("F", 2)])
    await _add_pattern(db_conn, ids, "120", [("F", 1), ("D", 2)])
    network = await load_network(db_session)
    planner = JourneyPlanner(network, FakeWalkingRouter())

    two = PlanningConstraints(max_transfers=2)
    result = await planner.plan(_stop("A", ids), _stop("D", ids), two)

    assert result.status == "ok"
    assert len(result.options) == 1
    option = result.options[0]
    assert option.ride_count == 3
    assert option.transfer_count == 2
    assert [leg.route_code for leg in option.legs] == ["138", "100", "120"]
    # Board-before-alight held across the whole chain.
    assert all(leg.board_sequence < leg.alight_sequence for leg in option.legs)

    # The same request with the default cap (1) must not produce this journey.
    one = PlanningConstraints()
    capped = await planner.plan(_stop("A", ids), _stop("D", ids), one)
    assert capped.status == "no_route"


async def test_plan_endpoint_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """API contract: POST /journeys/plan returns versioned, honest options.

    Uses its own engine + commit (the endpoint runs in its own session), and
    cleans the canonical tables afterwards.
    """
    from fastapi.testclient import TestClient
    from sqlalchemy.ext.asyncio import create_async_engine

    from app.main import app
    from app.platform.config import get_settings
    from app.platform.db import dispose_engine
    from tests.integration.conftest import _CLEANUP_ORDER
    from tests.integration.test_plan_cache_and_saved import FakeCacheStore

    # Endpoint tests must not touch the real Redis client (its connection pool
    # binds to one event loop; crossing loops corrupts teardown).
    monkeypatch.setattr("app.api.routes.journeys._cache", lambda: FakeCacheStore())

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
            response = client.post(
                "/api/v1/journeys/plan",
                json={
                    "origin": {"type": "stop", "stop_id": str(ids["A"])},
                    "destination": {"type": "stop", "stop_id": str(ids["C"])},
                },
            )
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "ok"
        assert payload["dataset_version"] == "test-net-1"
        assert payload["availability_scope"] == "network_feasible_not_live_confirmed"
        assert len(payload["options"]) == 1
        option = payload["options"][0]
        assert option["summary"]["transfer_count"] == 0
        assert option["labels"] == [
            "fastest",
            "least_walking",
            "fewest_transfers",
            "simplest",
        ]
        ride = option["legs"][0]
        assert ride["type"] == "transit"
        assert ride["instruction_code"] == "RIDE_TRANSIT"
        assert ride["board_sequence"] == 1
        assert ride["alight_sequence"] == 2
        assert ride["intermediate_stops"] == 0
        assert (
            ride["estimated_duration_minutes"]["min"] <= ride["estimated_duration_minutes"]["max"]
        )
        assert any("not been field-verified" in w for w in option["warnings"])

        # Phase 5: ordered, executable instruction steps with honest facts.
        assert payload["language"] == "en"
        steps = option["steps"]
        assert [s["action"] for s in steps] == [
            "BOARD_TRANSIT",
            "RIDE_TRANSIT",
            "ALIGHT_TRANSIT",
        ]
        assert steps[0]["text"] == "Board route 138 at Stop A heading towards Homagama."
        assert steps[1]["text"] == "Ride 1 stop to Stop C."
        assert steps[1]["facts"]["intermediate_stops"] == 0
        assert steps[2]["text"] == "Alight at Stop C."

        # si/ta fall back to English with an explicit limitation note (D-7).
        si_response = client.post(
            "/api/v1/journeys/plan",
            json={
                "origin": {"type": "stop", "stop_id": str(ids["A"])},
                "destination": {"type": "stop", "stop_id": str(ids["C"])},
                "language": "si",
            },
        )
        si_payload = si_response.json()
        assert si_payload["language"] == "si"
        assert any("native review" in note for note in si_payload["notes"])
        assert si_payload["options"][0]["steps"][1]["text"] == "Ride 1 stop to Stop C."
    finally:
        async with engine.begin() as conn:
            for statement in _CLEANUP_ORDER:
                await conn.execute(text(statement))
        await engine.dispose()
        # The endpoint ran on the process-global engine inside TestClient's
        # event loop; dispose it so later per-test loops never find stale
        # pooled connections (I-13 pattern).
        await dispose_engine()
