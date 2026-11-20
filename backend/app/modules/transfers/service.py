"""Transfer-graph candidate generation (canonical module: `transfers`).

Architecture rule (data model doc §3, ADR-0002): **proximity alone never
creates a transfer connector** — a candidate may be *proposed* from proximity,
but it only becomes usable routing data once reviewed/verified. This module
implements the proposal half:

1. propose stop pairs that are walking-close, each stop already served by at
   least one route pattern, and the pair NOT served by one shared pattern
   (a shared pattern means you ride, not transfer);
2. for each pair, route the actual pedestrian path through the walking-router
   adapter (ADR-0008) — an *explicit* connector with real distance, duration
   and geometry, never a straight-line estimate;
3. persist rows as `verification_status='unverified'` in the **candidate**
   dataset only (D-1: nothing publishes until field verification), so the
   Phase 4 planner sees them downgraded per the confidence rules
   (routing-engine doc §8: unverified transfer access is suppressed/downgraded)
   and field walks upgrade them through the normal moderation flow.

Pairs for which the walking engine can produce no path are recorded as
outcomes — never guessed, never stored as approximate straight lines.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.data_ingestion.models import DataSource
from app.modules.pedestrian.router import WalkingRouter
from app.modules.transport.models import TransferConnection

logger = logging.getLogger(__name__)

DERIVED_SOURCE_NAME = "walking-engine-derived"
_DERIVED_SOURCE_NOTE = (
    "Candidate transfer connectors derived from the OSM pedestrian graph via the"
    " self-hosted walking engine (ADR-0008). ODbL 1.0 applies to the underlying"
    " OSM data; every row is a proposal until field-verified."
)


@dataclass(frozen=True)
class CandidatePair:
    """A proximity-proposed transfer pair of access points (a.stop_id < b.stop_id)."""

    from_access_point_id: uuid.UUID
    to_access_point_id: uuid.UUID
    from_stop_id: uuid.UUID
    to_stop_id: uuid.UUID
    straight_line_m: float


@dataclass(frozen=True)
class CandidateOutcome:
    """What happened to one candidate pair (honest per-pair accounting)."""

    pair: CandidatePair
    result: str  # walk_routed | already_connected | no_walk_path
    walk_distance_m: int | None = None
    walk_seconds: int | None = None


async def get_or_create_derived_source(session: AsyncSession) -> uuid.UUID:
    """The data source recorded on candidate connector rows (provenance)."""
    result = await session.execute(
        text("SELECT id FROM data_sources WHERE name = :n"), {"n": DERIVED_SOURCE_NAME}
    )
    existing = result.scalar_one_or_none()
    if existing is not None:
        return uuid.UUID(str(existing))
    source = DataSource(
        name=DERIVED_SOURCE_NAME,
        owner="OpenStreetMap contributors (derived data)",
        access_method="api",
        format="osm",
        licence="ODbL 1.0 (derived)",
        terms_note=_DERIVED_SOURCE_NOTE,
        update_cadence="re-derived after each candidate dataset refresh",
    )
    session.add(source)
    await session.flush()
    return source.id


async def propose_candidate_pairs(
    session: AsyncSession, radius_m: float = 300.0
) -> list[CandidatePair]:
    """Proximity proposals, closest first.

    Rules encoded here (never bypassed downstream):
    - both endpoints are access points of *served* stops (planning-relevant);
    - the two stops share no route pattern (a shared pattern is a ride, not a
      transfer);
    - straight-line distance is inside the interchange radius.
    """
    rows = await session.execute(
        text(
            "SELECT a.id, b.id, a.stop_id, b.stop_id, ST_Distance(a.location, b.location)"
            " FROM stop_access_points a"
            " JOIN stop_access_points b"
            "   ON a.stop_id < b.stop_id"
            "  AND ST_DWithin(a.location, b.location, :radius)"
            " WHERE a.location IS NOT NULL AND b.location IS NOT NULL"
            "   AND EXISTS (SELECT 1 FROM route_pattern_stops rps WHERE rps.stop_id = a.stop_id)"
            "   AND EXISTS (SELECT 1 FROM route_pattern_stops rps WHERE rps.stop_id = b.stop_id)"
            "   AND NOT EXISTS ("
            "     SELECT 1 FROM route_pattern_stops x"
            "     JOIN route_pattern_stops y ON x.pattern_id = y.pattern_id"
            "     WHERE x.stop_id = a.stop_id AND y.stop_id = b.stop_id)"
            " ORDER BY ST_Distance(a.location, b.location)"
        ),
        {"radius": radius_m},
    )
    return [
        CandidatePair(
            from_access_point_id=uuid.UUID(str(row[0])),
            to_access_point_id=uuid.UUID(str(row[1])),
            from_stop_id=uuid.UUID(str(row[2])),
            to_stop_id=uuid.UUID(str(row[3])),
            straight_line_m=float(row[4]),
        )
        for row in rows
    ]


async def generate_transfer_candidates(
    session: AsyncSession,
    walking_router: WalkingRouter,
    radius_m: float = 300.0,
    max_pairs: int = 500,
) -> list[CandidateOutcome]:
    """Route each proposal through the walking engine and store candidates.

    The caller owns the transaction/commit (mirrors `IngestionService.run_sync`).
    Idempotent per access-point pair: an existing connection in either direction
    is reported as `already_connected`, not duplicated. Proposals beyond
    `max_pairs` routed connections are left unprocessed (no half-facts).
    """
    pairs = await propose_candidate_pairs(session, radius_m)
    outcomes: list[CandidateOutcome] = []
    routed = 0
    for pair in pairs:
        if routed >= max_pairs:
            break
        existing = await session.execute(
            text(
                "SELECT 1 FROM transfer_connections"
                " WHERE (from_access_point_id = :a AND to_access_point_id = :b)"
                "    OR (from_access_point_id = :b AND to_access_point_id = :a)"
            ),
            {"a": str(pair.from_access_point_id), "b": str(pair.to_access_point_id)},
        )
        if existing.scalar_one_or_none() is not None:
            outcomes.append(CandidateOutcome(pair=pair, result="already_connected"))
            continue

        coordinates = await _access_point_coordinates(
            session, pair.from_access_point_id, pair.to_access_point_id
        )
        if coordinates is None:
            outcomes.append(CandidateOutcome(pair=pair, result="no_walk_path"))
            continue

        plan = await walking_router.route_walk(
            coordinates[0][0], coordinates[0][1], coordinates[1][0], coordinates[1][1]
        )
        if plan is None:
            # No walkable path (engine down, unreachable, outside coverage):
            # the candidate is dropped with an honest outcome — no estimate.
            outcomes.append(CandidateOutcome(pair=pair, result="no_walk_path"))
            continue

        geometry_wkt = None
        if len(plan.coordinates) >= 2:
            line = ", ".join(f"{lon} {lat}" for lon, lat in plan.coordinates)
            geometry_wkt = f"MULTILINESTRING(({line}))"

        session.add(
            TransferConnection(
                from_access_point_id=pair.from_access_point_id,
                to_access_point_id=pair.to_access_point_id,
                walk_distance_m=round(plan.distance_m),
                estimated_walk_seconds=round(plan.duration_s),
                walk_geometry=geometry_wkt,
                data_source_id=await get_or_create_derived_source(session),
                verification_status="unverified",
            )
        )
        await session.flush()
        routed += 1
        outcomes.append(
            CandidateOutcome(
                pair=pair,
                result="walk_routed",
                walk_distance_m=round(plan.distance_m),
                walk_seconds=round(plan.duration_s),
            )
        )
    return outcomes


async def _access_point_coordinates(
    session: AsyncSession,
    from_access_point_id: uuid.UUID,
    to_access_point_id: uuid.UUID,
) -> tuple[tuple[float, float], tuple[float, float]] | None:
    rows = await session.execute(
        text(
            "SELECT id, ST_X(location::geometry), ST_Y(location::geometry)"
            " FROM stop_access_points WHERE id IN (:a, :b) AND location IS NOT NULL"
        ),
        {"a": str(from_access_point_id), "b": str(to_access_point_id)},
    )
    by_id: dict[str, tuple[float, float]] = {
        str(row[0]): (float(row[1]), float(row[2])) for row in rows
    }
    a = by_id.get(str(from_access_point_id))
    b = by_id.get(str(to_access_point_id))
    if a is None or b is None:
        return None
    return a, b
