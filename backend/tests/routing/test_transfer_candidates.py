"""Phase 3 integration: candidate transfer-connector generation.

Proximity proposals are routed through the walking engine (faked here) into
`unverified` `transfer_connections`; no transfer is ever created without a
routed walk path, and pairs served by a shared pattern are never proposed.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession

from app.modules.pedestrian.router import WalkPlan, WalkStep
from app.modules.transfers import generate_transfer_candidates, propose_candidate_pairs
from tests.integration.conftest import _seed_route


class FakeWalkingRouter:
    """Deterministic fake: walks every request (asserted via `calls`)."""

    provider_name = "fake"

    def __init__(self) -> None:
        self.calls = 0

    async def route_walk(
        self,
        lon_from: float,
        lat_from: float,
        lon_to: float,
        lat_to: float,
    ) -> WalkPlan | None:
        self.calls += 1
        return WalkPlan(
            distance_m=240.0,
            duration_s=180.0,
            steps=(WalkStep(240.0, 180.0, "Walk east.", "Galle Road", None),),
            provider=self.provider_name,
            coordinates=(
                (lon_from, lat_from),
                ((lon_from + lon_to) / 2, (lat_from + lat_to) / 2),
                (lon_to, lat_to),
            ),
        )


class NoPathRouter:
    """The honest failure mode: the engine can produce no path."""

    provider_name = "fake"

    async def route_walk(
        self, lon_from: float, lat_from: float, lon_to: float, lat_to: float
    ) -> WalkPlan | None:
        return None


async def _seed_two_served_stops(
    session: AsyncSession, *, share_pattern: bool = False
) -> dict[str, uuid.UUID]:
    """Two stops ~222 m apart, each served by (different) route patterns."""
    ids = await _seed_route(await session.connection())
    # _seed_route gives stop_a (79.9777 6.8440) + stop_b (79.8483 6.9107) far
    # apart; add a near stop close to stop_a served by a second pattern.
    stop_c = (
        await session.execute(
            text(
                "INSERT INTO stops (name, mode, location)"
                " VALUES ('Near Homagama', 'bus', 'POINT(79.9797 6.8440)') RETURNING id"
            )
        )
    ).scalar_one()
    route2 = (
        await session.execute(
            text(
                "INSERT INTO transport_routes (route_code, mode) VALUES ('145', 'bus') RETURNING id"
            )
        )
    ).scalar_one()
    pattern2 = (
        await session.execute(
            text(
                "INSERT INTO route_patterns (route_id, pattern_code, direction_id)"
                " VALUES (:r, '145-A-D0', 0) RETURNING id"
            ),
            {"r": route2},
        )
    ).scalar_one()
    await session.execute(
        text(
            "INSERT INTO route_pattern_stops (pattern_id, stop_id, sequence)"
            " VALUES (:p1, :sa, 1), (:p1, :sb, 2), (:p2, :sc, 1)"
        ),
        {
            "p1": ids["pattern_id"],
            "sa": ids["stop_a"],
            "sb": ids["stop_b"],
            "p2": pattern2,
            "sc": stop_c,
        },
    )
    if share_pattern:
        await session.execute(
            text(
                "INSERT INTO route_pattern_stops (pattern_id, stop_id, sequence)"
                " VALUES (:p1, :sc, 3)"
            ),
            {"p1": ids["pattern_id"], "sc": stop_c},
        )
    access_a = (
        await session.execute(
            text(
                "INSERT INTO stop_access_points (stop_id, location)"
                " VALUES (:s, 'POINT(79.9777 6.8440)') RETURNING id"
            ),
            {"s": ids["stop_a"]},
        )
    ).scalar_one()
    access_c = (
        await session.execute(
            text(
                "INSERT INTO stop_access_points (stop_id, location)"
                " VALUES (:s, 'POINT(79.9797 6.8440)') RETURNING id"
            ),
            {"s": stop_c},
        )
    ).scalar_one()
    return {
        "stop_a": ids["stop_a"],
        "stop_b": ids["stop_b"],
        "stop_c": stop_c,
        "access_a": access_a,
        "access_c": access_c,
    }


@pytest.fixture
async def db_session(db_conn: AsyncConnection) -> AsyncIterator[AsyncSession]:
    """An ORM session over the test's own transaction (rolls back with it)."""
    session = AsyncSession(bind=db_conn)
    yield session
    await session.close()


async def test_close_unrelated_stops_become_routed_candidates(
    db_session: AsyncSession,
) -> None:
    ids = await _seed_two_served_stops(db_session)
    router = FakeWalkingRouter()

    pairs = await propose_candidate_pairs(db_session, radius_m=300.0)
    outcomes = await generate_transfer_candidates(db_session, router, radius_m=300.0)

    # stop_a (pattern 1) and stop_c (pattern 2) are ~222 m apart and share no
    # pattern; stop_b is far outside the radius. Pair orientation depends on
    # the stops' random UUID order, so compare unordered.
    assert {frozenset((p.from_stop_id, p.to_stop_id)) for p in pairs} == {
        frozenset((ids["stop_a"], ids["stop_c"]))
    }
    assert len(outcomes) == 1
    assert outcomes[0].result == "walk_routed"
    assert outcomes[0].walk_distance_m == 240
    assert outcomes[0].walk_seconds == 180

    row = (
        await db_session.execute(
            text(
                "SELECT tc.walk_distance_m, tc.estimated_walk_seconds,"
                " tc.verification_status, ds.name,"
                " ST_NumGeometries(tc.walk_geometry::geometry)"
                " FROM transfer_connections tc"
                " JOIN data_sources ds ON ds.id = tc.data_source_id"
                " WHERE :a IN (tc.from_access_point_id, tc.to_access_point_id)"
            ),
            {"a": str(ids["access_a"])},
        )
    ).one()
    assert row[0] == 240
    assert row[1] == 180
    assert row[2] == "unverified"  # a proposal — never pre-verified
    assert row[3] == "walking-engine-derived"
    assert row[4] == 1  # routed geometry, not a straight line


async def test_shared_pattern_pair_is_never_proposed(db_session: AsyncSession) -> None:
    await _seed_two_served_stops(db_session, share_pattern=True)

    pairs = await propose_candidate_pairs(db_session, radius_m=300.0)

    assert pairs == []


async def test_unreachable_pair_is_dropped_without_fabrication(
    db_session: AsyncSession,
) -> None:
    await _seed_two_served_stops(db_session)

    outcomes = await generate_transfer_candidates(db_session, NoPathRouter())

    assert len(outcomes) == 1
    assert outcomes[0].result == "no_walk_path"
    count = (
        await db_session.execute(text("SELECT count(*) FROM transfer_connections"))
    ).scalar_one()
    assert count == 0


async def test_regeneration_reports_existing_pair_not_duplicate(
    db_session: AsyncSession,
) -> None:
    await _seed_two_served_stops(db_session)
    router = FakeWalkingRouter()

    first = await generate_transfer_candidates(db_session, router)
    second = await generate_transfer_candidates(db_session, router)

    assert [o.result for o in first] == ["walk_routed"]
    assert [o.result for o in second] == ["already_connected"]
    count = (
        await db_session.execute(text("SELECT count(*) FROM transfer_connections"))
    ).scalar_one()
    assert count == 1
    assert router.calls == 1  # second pass short-circuits before the engine
