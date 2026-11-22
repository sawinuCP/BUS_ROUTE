"""Itinerary model for the deterministic planner (Phase 4 work items 2–10).

Pure domain code: no FastAPI, SQLAlchemy, walking-engine or LLM imports.

Rules encoded here (routing-engine doc §4–§6, §8):
- In-vehicle time is a **conservative configured estimate** from network
  distance and an explicit speed band — never presented as timetable data.
  Walking time/distance come from the walking-router adapter (real network
  paths); a walking leg is never fabricated from straight-line distance here.
- Alternatives are compared on explicit, explainable dimensions: estimated
  duration, walking distance, transfer count. Pareto filtering removes only
  strictly dominated candidates ("no worse in all dimensions and better in at
  least one"), so meaningful trade-offs survive.
- Ranking labels (`fastest`, `least_walking`, `fewest_transfers`, `simplest`)
  are computed from the returned candidate set so a label always matches the
  metric it names.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

# Earth radius (metres) for the great-circle distance used in estimates.
EARTH_RADIUS_M = 6_371_000.0

# Routing doc §5: no timetables in the static MVP. In-vehicle time is derived
# from network distance with this explicit speed band (observed Colombo urban
# bus speeds sit inside it; conservative by construction).
VEHICLE_SPEED_MIN_KMH = 12.0
VEHICLE_SPEED_MAX_KMH = 18.0

# Straight-line distance underestimates road distance; this allowance keeps
# the in-vehicle estimate conservative without measuring shapes.
ROAD_DETOUR_FACTOR = 1.4

STATIC_SERVICE_WARNING = (
    "Static network data: service operation, frequencies and live availability are not checked."
)
ESTIMATE_BASIS_NOTE = (
    "In-vehicle times are conservative network estimates (speed band"
    f" {VEHICLE_SPEED_MIN_KMH:.0f}-{VEHICLE_SPEED_MAX_KMH:.0f} km/h), not"
    " timetable data; waiting times are unknown."
)


def haversine_m(lon_from: float, lat_from: float, lon_to: float, lat_to: float) -> float:
    """Great-circle distance in metres (WGS84 approximation)."""
    lon1, lat1, lon2, lat2 = map(math.radians, (lon_from, lat_from, lon_to, lat_to))
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(a))


def ride_estimate(straight_line_m: float) -> tuple[float, float, float]:
    """Estimated (distance_m, min_seconds, max_seconds) for a ride span."""
    distance_m = straight_line_m * ROAD_DETOUR_FACTOR
    seconds_per_m_fast = 3.6 / (VEHICLE_SPEED_MAX_KMH * 1000.0) * 1000.0
    seconds_per_m_slow = 3.6 / (VEHICLE_SPEED_MIN_KMH * 1000.0) * 1000.0
    return distance_m, distance_m * seconds_per_m_fast, distance_m * seconds_per_m_slow


@dataclass(frozen=True)
class WalkLeg:
    """A pedestrian leg with a real routed path (adapter) or stored connector."""

    purpose: str  # access | transfer | egress | walk_only
    distance_m: float
    duration_s: float
    from_ref: dict[str, Any]
    to_ref: dict[str, Any]
    provider: str | None = None
    coordinates: tuple[tuple[float, float], ...] = ()

    @property
    def instruction_code(self) -> str:
        if self.purpose == "access":
            return "WALK_TO_STOP"
        if self.purpose == "transfer":
            return "WALK_TRANSFER"
        return "WALK_TO_DESTINATION"

    @property
    def key(self) -> tuple[str, str, str]:
        return (self.purpose, _ref_key(self.from_ref), _ref_key(self.to_ref))


@dataclass(frozen=True)
class RideLeg:
    """A transit ride on one exact pattern between two ordered stop calls."""

    pattern_id: str
    route_id: str
    route_code: str
    mode: str
    direction_id: int
    pattern_code: str | None
    origin_label: str | None
    destination_label: str | None
    verification_status: str
    board_stop_id: str
    board_stop_name: str
    board_sequence: int
    alight_stop_id: str
    alight_stop_name: str
    alight_sequence: int
    estimated_distance_m: float
    duration_min_s: float
    duration_max_s: float

    @property
    def instruction_code(self) -> str:
        return "RIDE_TRANSIT"

    @property
    def key(self) -> tuple[str, str, str, str]:
        return ("ride", self.pattern_id, self.board_stop_id, self.alight_stop_id)


Leg = WalkLeg | RideLeg


def _ref_key(ref: dict[str, Any]) -> str:
    """Stable short key for an endpoint reference (used in dedup signatures)."""
    if ref.get("id") is not None:
        return f"{ref.get('kind')}:{ref['id']}"
    if ref.get("lon") is not None:
        return f"coord:{float(ref['lon']):.5f},{float(ref['lat']):.5f}"
    return str(ref.get("kind"))


@dataclass(frozen=True)
class Itinerary:
    """One complete candidate journey (legs in execution order)."""

    legs: tuple[Leg, ...]
    transfer_count: int
    walk_distance_m: float
    duration_min_s: float
    duration_max_s: float
    warnings: tuple[str, ...]
    confidence: str  # verified | unverified_pattern | unverified_transfer

    @property
    def ride_count(self) -> int:
        return sum(1 for leg in self.legs if isinstance(leg, RideLeg))

    @property
    def leg_count(self) -> int:
        return len(self.legs)

    @property
    def signature(self) -> tuple[tuple[str, ...], ...]:
        """Dedup signature: same route/stop chain = the same option."""
        return tuple(leg.key for leg in self.legs)


def dedup_itineraries(itineraries: list[Itinerary]) -> list[Itinerary]:
    """Keep the first candidate per signature (input order is deterministic)."""
    seen: set[tuple[tuple[str, ...], ...]] = set()
    kept: list[Itinerary] = []
    for itinerary in itineraries:
        if itinerary.signature in seen:
            continue
        seen.add(itinerary.signature)
        kept.append(itinerary)
    return kept


def _dominates(a: Itinerary, b: Itinerary) -> bool:
    """A dominates B when no worse in every dimension and better in one."""
    dims_a = (a.duration_max_s, a.walk_distance_m, a.transfer_count)
    dims_b = (b.duration_max_s, b.walk_distance_m, b.transfer_count)
    return all(x <= y for x, y in zip(dims_a, dims_b, strict=True)) and any(
        x < y for x, y in zip(dims_a, dims_b, strict=True)
    )


def pareto_filter(itineraries: list[Itinerary]) -> list[Itinerary]:
    """Remove dominated candidates; keep meaningful trade-offs (routing §6)."""
    return [
        candidate
        for candidate in itineraries
        if not any(other is not candidate and _dominates(other, candidate) for other in itineraries)
    ]


def sort_options(itineraries: list[Itinerary], priority: str) -> list[Itinerary]:
    """Deterministic ordering for a ranking profile (ties keep input order)."""
    keys: dict[str, Any] = {
        "fastest": lambda it: (it.duration_max_s, it.walk_distance_m, it.transfer_count),
        "least_walking": lambda it: (
            it.walk_distance_m,
            it.duration_max_s,
            it.transfer_count,
        ),
        "fewest_transfers": lambda it: (
            it.transfer_count,
            it.duration_max_s,
            it.walk_distance_m,
        ),
        "simplest": lambda it: (it.transfer_count, it.leg_count, it.duration_max_s),
    }
    key = keys.get(priority, keys["fastest"])
    return sorted(itineraries, key=key)


def rank_labels(itineraries: list[Itinerary]) -> dict[str, int | None]:
    """Compute labels from the final option set (label always matches metric)."""
    names = ("fastest", "least_walking", "fewest_transfers", "simplest")
    if not itineraries:
        return {name: None for name in names}

    def _first_min(key: Any) -> int:
        values = [key(it) for it in itineraries]
        return values.index(min(values))

    return {
        "fastest": _first_min(lambda it: it.duration_max_s),
        "least_walking": _first_min(lambda it: it.walk_distance_m),
        "fewest_transfers": _first_min(lambda it: (it.transfer_count, it.duration_max_s)),
        "simplest": _first_min(lambda it: (it.transfer_count, it.leg_count, it.duration_max_s)),
    }
