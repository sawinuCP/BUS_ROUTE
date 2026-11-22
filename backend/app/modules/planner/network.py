"""Planner network snapshot (Phase 4 work item 1: graph interfaces).

Loads an immutable, in-memory view of the canonical network for one planning
request: route patterns with their ordered stop calls, stops with access
points, and **explicit** transfer connectors only (data model doc §3: proximity
alone never creates a transfer). The network version label comes from
`active_dataset` (ADR-0006) and falls back to the newest dataset version so
candidate-dataset planning remains possible in the pilot; the label is part of
every result and (later) the plan cache key.

Domain rules encoded here:
- A ride edge is tied to a specific pattern and an ordered sequence span —
  never to a route number or to geographic closeness (routing doc §1).
- A transfer edge exists only if a `transfer_connections` row exists; its
  verification status travels with it so the planner can downgrade/exclude.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

UNKNOWN_VERSION_LABEL = "unknown"


@dataclass(frozen=True)
class AccessPointSpec:
    """A boarding/alighting point with coordinates (metres/seconds elsewhere)."""

    id: uuid.UUID
    stop_id: uuid.UUID
    lon: float
    lat: float


@dataclass(frozen=True)
class StopSpec:
    """A canonical stop; `access_points` may be empty (coordinates only)."""

    id: uuid.UUID
    name: str
    mode: str
    lon: float
    lat: float
    access_points: tuple[AccessPointSpec, ...] = ()

    def nearest_access_point(self, lon: float, lat: float) -> AccessPointSpec | None:
        """The access point closest to a coordinate, or None when unmapped."""
        if not self.access_points:
            return None
        return min(
            self.access_points,
            key=lambda ap: (ap.lon - lon) ** 2 + (ap.lat - lat) ** 2,
        )


@dataclass(frozen=True)
class PatternCall:
    """One ordered stop call of a pattern (core invariant: unique sequence)."""

    stop_id: uuid.UUID
    sequence: int
    boarding_allowed: bool
    alighting_allowed: bool


@dataclass(frozen=True)
class PatternSpec:
    """A specific ordered variant and direction — never merged by route number."""

    id: uuid.UUID
    route_id: uuid.UUID
    route_code: str
    mode: str
    direction_id: int
    pattern_code: str | None
    origin_label: str | None
    destination_label: str | None
    verification_status: str
    calls: tuple[PatternCall, ...]

    def call_index(self, stop_id: uuid.UUID) -> int | None:
        """First index of a stop in this pattern's ordered calls, if served."""
        for index, call in enumerate(self.calls):
            if call.stop_id == stop_id:
                return index
        return None


@dataclass(frozen=True)
class TransferEdge:
    """An explicit stored walking connector between two access points."""

    from_access_point_id: uuid.UUID
    to_access_point_id: uuid.UUID
    from_stop_id: uuid.UUID
    to_stop_id: uuid.UUID
    walk_distance_m: int | None
    walk_seconds: int | None
    verification_status: str
    coordinates: tuple[tuple[float, float], ...] = ()


@dataclass(frozen=True)
class TransitNetwork:
    """Immutable snapshot consumed by the planner (never mutated)."""

    version_label: str
    stops: dict[uuid.UUID, StopSpec] = field(default_factory=dict)
    patterns: tuple[PatternSpec, ...] = ()
    transfers: tuple[TransferEdge, ...] = ()


async def load_network(session: AsyncSession) -> TransitNetwork:
    """Build the planning snapshot from the canonical tables (one request)."""
    version_label = await _active_version_label(session)

    stop_rows = (
        await session.execute(
            text(
                "SELECT s.id, s.name, s.mode,"
                " ST_X(s.location::geometry), ST_Y(s.location::geometry),"
                " ap.id, ST_X(ap.location::geometry), ST_Y(ap.location::geometry)"
                " FROM stops s"
                " LEFT JOIN stop_access_points ap"
                "   ON ap.stop_id = s.id AND ap.location IS NOT NULL"
                " WHERE s.location IS NOT NULL"
                " ORDER BY s.id, ap.id"
            )
        )
    ).all()
    stops: dict[uuid.UUID, StopSpec] = {}
    for row in stop_rows:
        stop_id = uuid.UUID(str(row[0]))
        stop = stops.get(stop_id)
        access_points = list(stop.access_points) if stop is not None else []
        if row[5] is not None:
            access_points.append(
                AccessPointSpec(
                    id=uuid.UUID(str(row[5])),
                    stop_id=stop_id,
                    lon=float(row[6]),
                    lat=float(row[7]),
                )
            )
        stops[stop_id] = StopSpec(
            id=stop_id,
            name=str(row[1]),
            mode=str(row[2]),
            lon=float(row[3]),
            lat=float(row[4]),
            access_points=tuple(access_points),
        )

    pattern_rows = (
        await session.execute(
            text(
                "SELECT p.id, p.route_id, r.route_code, r.mode, p.direction_id,"
                " p.pattern_code, p.origin_label, p.destination_label,"
                " p.verification_status,"
                " ps.stop_id, ps.sequence, ps.boarding_allowed, ps.alighting_allowed"
                " FROM route_patterns p"
                " JOIN transport_routes r ON r.id = p.route_id"
                " JOIN route_pattern_stops ps ON ps.pattern_id = p.id"
                " ORDER BY r.route_code, p.pattern_code NULLS LAST, p.id, ps.sequence"
            )
        )
    ).all()
    patterns_by_id: dict[uuid.UUID, dict[str, Any]] = {}
    ordered_pattern_ids: list[uuid.UUID] = []
    for row in pattern_rows:
        pattern_id = uuid.UUID(str(row[0]))
        spec = patterns_by_id.get(pattern_id)
        if spec is None:
            spec = {
                "id": pattern_id,
                "route_id": uuid.UUID(str(row[1])),
                "route_code": str(row[2]),
                "mode": str(row[3]),
                "direction_id": int(row[4]),
                "pattern_code": None if row[5] is None else str(row[5]),
                "origin_label": None if row[6] is None else str(row[6]),
                "destination_label": None if row[7] is None else str(row[7]),
                "verification_status": str(row[8]),
                "calls": [],
            }
            patterns_by_id[pattern_id] = spec
            ordered_pattern_ids.append(pattern_id)
        spec["calls"].append(
            PatternCall(
                stop_id=uuid.UUID(str(row[9])),
                sequence=int(row[10]),
                boarding_allowed=bool(row[11]),
                alighting_allowed=bool(row[12]),
            )
        )
    patterns = tuple(
        PatternSpec(
            id=pid,
            route_id=patterns_by_id[pid]["route_id"],
            route_code=patterns_by_id[pid]["route_code"],
            mode=patterns_by_id[pid]["mode"],
            direction_id=patterns_by_id[pid]["direction_id"],
            pattern_code=patterns_by_id[pid]["pattern_code"],
            origin_label=patterns_by_id[pid]["origin_label"],
            destination_label=patterns_by_id[pid]["destination_label"],
            verification_status=patterns_by_id[pid]["verification_status"],
            calls=tuple(patterns_by_id[pid]["calls"]),
        )
        for pid in ordered_pattern_ids
    )

    transfer_rows = (
        await session.execute(
            text(
                "SELECT fa.id, ta.id, fa.stop_id, ta.stop_id,"
                " tc.walk_distance_m, tc.estimated_walk_seconds,"
                " tc.verification_status,"
                " CASE WHEN tc.walk_geometry IS NULL THEN NULL"
                "      ELSE ST_AsGeoJSON(tc.walk_geometry::geometry) END"
                " FROM transfer_connections tc"
                " JOIN stop_access_points fa ON fa.id = tc.from_access_point_id"
                " JOIN stop_access_points ta ON ta.id = tc.to_access_point_id"
            )
        )
    ).all()
    transfers: list[TransferEdge] = []
    for row in transfer_rows:
        coordinates: tuple[tuple[float, float], ...] = ()
        if row[7] is not None:
            try:
                geometry = json.loads(str(row[7]))
                lines = geometry.get("coordinates") or []
                for line in lines:
                    coordinates = tuple((float(pt[0]), float(pt[1])) for pt in line)
            except (ValueError, TypeError, IndexError):
                coordinates = ()
        transfers.append(
            TransferEdge(
                from_access_point_id=uuid.UUID(str(row[0])),
                to_access_point_id=uuid.UUID(str(row[1])),
                from_stop_id=uuid.UUID(str(row[2])),
                to_stop_id=uuid.UUID(str(row[3])),
                walk_distance_m=None if row[4] is None else int(row[4]),
                walk_seconds=None if row[5] is None else int(row[5]),
                verification_status=str(row[6]),
                coordinates=coordinates,
            )
        )
    # Normalise both directions: a connector is walkable either way.
    transfers.extend(
        TransferEdge(
            from_access_point_id=t.to_access_point_id,
            to_access_point_id=t.from_access_point_id,
            from_stop_id=t.to_stop_id,
            to_stop_id=t.from_stop_id,
            walk_distance_m=t.walk_distance_m,
            walk_seconds=t.walk_seconds,
            verification_status=t.verification_status,
            coordinates=tuple(reversed(t.coordinates)),
        )
        for t in list(transfers)
    )

    return TransitNetwork(
        version_label=version_label,
        stops=stops,
        patterns=patterns,
        transfers=tuple(transfers),
    )


async def _active_version_label(session: AsyncSession) -> str:
    """Active published version, else newest version, else `unknown`."""
    label = (
        await session.execute(
            text(
                "SELECT v.version_label FROM active_dataset a"
                " JOIN dataset_versions v ON v.id = a.dataset_version_id"
            )
        )
    ).scalar_one_or_none()
    if label is None:
        label = (
            await session.execute(
                text(
                    "SELECT version_label FROM dataset_versions"
                    " ORDER BY created_at DESC, id LIMIT 1"
                )
            )
        ).scalar_one_or_none()
    return UNKNOWN_VERSION_LABEL if label is None else str(label)
