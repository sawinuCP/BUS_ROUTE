"""Deterministic multimodal journey planning (Phase 4 work items 2–6, 8–10, 12).

Bounded, deterministic candidate generation over the network snapshot:

1. resolve pedestrian access to the network (origin) and egress (destination)
   through the walking-router adapter — a leg exists only if the engine routed
   it, never from straight-line guesses (ADR-0008, routing doc §1);
2. expand rides on exact patterns with board-before-alight enforced against
   the pattern's ordered calls, honouring boarding/alighting flags;
3. move between patterns only via **explicit** transfer connectors (stored
   routed paths; unverified ones downgrade or exclude per constraints) or a
   same-stop re-board (no walking claim — you change buses where you stand);
4. constrain: allowed modes, maximum total walking, maximum transfers, and
   rail only when station order is verified (routing doc §8);
5. deduplicate, Pareto-filter, compute ranking labels, cap the option count.

Every outcome is honest: when nothing connects, the result explains why
(missing coverage, walk cap, unverified rail) instead of inventing a journey.
Determinism: all iteration is in sorted/insertion order, so identical requests
over the same network version return identical options.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from app.modules.pedestrian.router import WalkingRouter
from app.modules.planner.itinerary import (
    ESTIMATE_BASIS_NOTE,
    STATIC_SERVICE_WARNING,
    Itinerary,
    Leg,
    RideLeg,
    WalkLeg,
    dedup_itineraries,
    haversine_m,
    pareto_filter,
    rank_labels,
    ride_estimate,
    sort_options,
)
from app.modules.planner.network import (
    PatternSpec,
    StopSpec,
    TransferEdge,
    TransitNetwork,
)

PRIORITY_DEFAULT = "fastest"
PRIORITIES = ("fastest", "least_walking", "fewest_transfers", "simplest")

_MAX_ACCESS_STOPS = 8  # nearest stops considered for coordinate endpoints
_MAX_FRONTIER = 200  # deterministic cap on states expanded per depth


@dataclass(frozen=True)
class Endpoint:
    """A planning endpoint: an exact stop or a coordinate."""

    kind: str  # stop | coordinates
    stop_id: uuid.UUID | None = None
    lon: float | None = None
    lat: float | None = None

    def validate(self) -> None:
        if self.kind == "stop" and self.stop_id is None:
            raise ValueError("stop endpoint requires stop_id")
        if self.kind == "coordinates" and (self.lon is None or self.lat is None):
            raise ValueError("coordinates endpoint requires lon and lat")
        if self.kind not in ("stop", "coordinates"):
            raise ValueError(f"unknown endpoint kind: {self.kind}")


@dataclass(frozen=True)
class PlanningConstraints:
    """User/configurable planning constraints (plan work item 8)."""

    allowed_modes: frozenset[str] = frozenset({"bus"})
    max_walking_m: float = 1500.0
    max_transfers: int = 1
    require_verified_transfers: bool = False
    max_candidates_considered: int = 60
    max_options: int = 4


@dataclass(frozen=True)
class _State:
    """A partial journey: where we are and how we got there."""

    stop_id: uuid.UUID
    walk_used_m: float
    legs: tuple[Leg, ...]
    transfers: int
    last_pattern_id: uuid.UUID | None
    unverified_transfer: bool = False
    stop: StopSpec | None = None


@dataclass(frozen=True)
class PlanningResult:
    """What the planner returns (options already deduped and Pareto-filtered)."""

    status: str  # ok | no_route
    version_label: str
    options: tuple[Itinerary, ...] = ()
    labels: dict[str, int | None] = field(default_factory=dict)
    notes: tuple[str, ...] = ()


class JourneyPlanner:
    """Deterministic candidate generation over one immutable network snapshot."""

    def __init__(self, network: TransitNetwork, walking_router: WalkingRouter) -> None:
        self._network = network
        self._walking_router = walking_router
        # Ride index: stop → patterns serving it (with call index), in
        # deterministic (route_code, pattern, sequence) order.
        self._patterns_by_stop: dict[uuid.UUID, list[tuple[PatternSpec, int]]] = {}
        for pattern in network.patterns:
            for index, call in enumerate(pattern.calls):
                if call.boarding_allowed:
                    self._patterns_by_stop.setdefault(call.stop_id, []).append((pattern, index))
        self._transfers_by_stop: dict[uuid.UUID, list[TransferEdge]] = {}
        for edge in network.transfers:
            self._transfers_by_stop.setdefault(edge.from_stop_id, []).append(edge)
        for edges in self._transfers_by_stop.values():
            edges.sort(key=lambda e: (e.walk_distance_m or 0, str(e.to_stop_id)))

    async def plan(
        self,
        origin: Endpoint,
        destination: Endpoint,
        constraints: PlanningConstraints,
        priority: str = PRIORITY_DEFAULT,
    ) -> PlanningResult:
        """Plan journeys; returns `ok` with options or `no_route` with reasons."""
        origin.validate()
        destination.validate()
        notes: list[str] = []

        access, access_notes = await self._resolve_end(origin, constraints, is_origin=True)
        notes.extend(access_notes)
        egress, egress_notes = await self._resolve_end(destination, constraints, is_origin=False)
        notes.extend(egress_notes)

        candidates: list[Itinerary] = []
        if access and egress:
            egress_index: dict[uuid.UUID, tuple[StopSpec, WalkLeg | None]] = {}
            for stop, walk_leg in egress:
                best = egress_index.get(stop.id)
                walk_m = walk_leg.distance_m if walk_leg else 0.0
                if best is None or walk_m < (best[1].distance_m if best[1] else 0.0):
                    egress_index[stop.id] = (stop, walk_leg)
            candidates = self._expand(access, egress_index, constraints, notes)

        if candidates:
            unique = dedup_itineraries(candidates)
            filtered = pareto_filter(unique)
            ordered = sort_options(filtered, priority)[: constraints.max_options]
            options = tuple(ordered)
            labels = rank_labels(list(options))
            notes.append(ESTIMATE_BASIS_NOTE)
            return PlanningResult(
                status="ok",
                version_label=self._network.version_label,
                options=options,
                labels=labels,
                notes=tuple(notes),
            )

        walk_only = await self._walk_only_fallback(origin, destination, constraints, notes)
        if walk_only is not None:
            options = (walk_only,)
            labels = rank_labels(list(options))
            notes.append(ESTIMATE_BASIS_NOTE)
            return PlanningResult(
                status="ok",
                version_label=self._network.version_label,
                options=options,
                labels=labels,
                notes=tuple(notes),
            )

        if not notes:
            notes.append("No journey found within the given constraints.")
        return PlanningResult(
            status="no_route",
            version_label=self._network.version_label,
            options=(),
            labels=rank_labels([]),
            notes=tuple(notes),
        )

    async def _resolve_end(
        self, endpoint: Endpoint, constraints: PlanningConstraints, *, is_origin: bool
    ) -> tuple[list[tuple[StopSpec, WalkLeg | None]], list[str]]:
        """Stops reachable on foot from an endpoint, with routed walk legs.

        Stop endpoints resolve to exactly that stop (no walking — the traveller
        is already there). Coordinate endpoints consider the nearest stops and
        route a real pedestrian path to each stop's closest access point.
        """
        role = "origin" if is_origin else "destination"
        notes: list[str] = []
        if endpoint.kind == "stop":
            stop = self._network.stops.get(endpoint.stop_id) if endpoint.stop_id else None
            if stop is None:
                notes.append(f"{role} stop is not present in the loaded network snapshot.")
                return [], notes
            return [(stop, None)], notes

        assert endpoint.lon is not None and endpoint.lat is not None  # validated
        lon, lat = endpoint.lon, endpoint.lat
        scored: list[tuple[float, StopSpec]] = []
        for stop in self._network.stops.values():
            distance = haversine_m(lon, lat, stop.lon, stop.lat)
            if distance <= constraints.max_walking_m:
                scored.append((distance, stop))
        scored.sort(key=lambda item: (item[0], str(item[1].id)))
        candidates = scored[:_MAX_ACCESS_STOPS]
        if not candidates:
            notes.append(
                f"No stops within the {constraints.max_walking_m:.0f} m walking cap of the {role}."
            )
            return [], notes

        results: list[tuple[StopSpec, WalkLeg | None]] = []
        unroutable = 0
        over_cap = 0
        for _distance, stop in candidates:
            anchor = stop.nearest_access_point(lon, lat)
            if anchor is None:
                anchor_lon, anchor_lat = stop.lon, stop.lat
                stop_ref: dict[str, Any] = {
                    "kind": "stop",
                    "id": str(stop.id),
                    "name": stop.name,
                }
            else:
                anchor_lon, anchor_lat = anchor.lon, anchor.lat
                stop_ref = {
                    "kind": "stop_access_point",
                    "id": str(anchor.id),
                    "stop_id": str(stop.id),
                }
            if is_origin:
                plan = await self._walking_router.route_walk(lon, lat, anchor_lon, anchor_lat)
                from_ref: dict[str, Any] = {"kind": "coordinates", "lon": lon, "lat": lat}
                to_ref = stop_ref
                purpose = "access"
            else:
                plan = await self._walking_router.route_walk(anchor_lon, anchor_lat, lon, lat)
                from_ref = stop_ref
                to_ref = {"kind": "coordinates", "lon": lon, "lat": lat}
                purpose = "egress"
            if plan is None:
                unroutable += 1
                continue
            if plan.distance_m > constraints.max_walking_m:
                over_cap += 1
                continue
            results.append(
                (
                    stop,
                    WalkLeg(
                        purpose=purpose,
                        distance_m=plan.distance_m,
                        duration_s=plan.duration_s,
                        from_ref=from_ref,
                        to_ref=to_ref,
                        provider=plan.provider,
                        coordinates=plan.coordinates,
                    ),
                )
            )
        if unroutable:
            notes.append(
                f"{unroutable} candidate {role} walk(s) could not be routed;"
                " no walking leg was fabricated for them."
            )
        if over_cap:
            notes.append(
                f"{over_cap} candidate {role} walk(s) exceeded the walking cap and were excluded."
            )
        if not results:
            notes.append(f"No walkable access to the network from the {role}.")
        return results, notes

    def _expand(
        self,
        access: list[tuple[StopSpec, WalkLeg | None]],
        egress_index: dict[uuid.UUID, tuple[StopSpec, WalkLeg | None]],
        constraints: PlanningConstraints,
        notes: list[str],
    ) -> list[Itinerary]:
        """Bounded breadth-first candidate generation (deterministic order)."""
        candidates: list[Itinerary] = []
        frontier: list[_State] = []
        for stop, walk_leg in access:
            legs: tuple[Leg, ...] = (walk_leg,) if walk_leg is not None else ()
            walk_used = walk_leg.distance_m if walk_leg is not None else 0.0
            frontier.append(
                _State(
                    stop_id=stop.id,
                    stop=stop,
                    walk_used_m=walk_used,
                    legs=legs,
                    transfers=0,
                    last_pattern_id=None,
                )
            )

        rail_excluded: set[str] = set()
        visited_by_depth: dict[int, set[uuid.UUID]] = {}
        for depth in range(constraints.max_transfers + 1):
            if not frontier or len(candidates) >= constraints.max_candidates_considered:
                break
            frontier = self._dedupe_frontier(frontier)
            visited = visited_by_depth.setdefault(depth, set())
            next_frontier: list[_State] = []
            for state in frontier[:_MAX_FRONTIER]:
                if state.stop_id in visited:
                    continue
                visited.add(state.stop_id)
                for pattern, index in self._patterns_by_stop.get(state.stop_id, []):
                    if pattern.mode not in constraints.allowed_modes:
                        continue
                    if pattern.mode == "rail" and pattern.verification_status != "verified":
                        # Routing doc §8 + plan item 7: rail only for segments
                        # with verified station order. Never ride unvalidated
                        # rail coverage.
                        if pattern.route_code not in rail_excluded:
                            rail_excluded.add(pattern.route_code)
                            notes.append(
                                f"Rail route {pattern.route_code} excluded:"
                                " station order is not verified."
                            )
                        continue
                    if depth > 0 and pattern.id == state.last_pattern_id:
                        continue  # same-stop re-board of the bus just left
                    for j in range(index + 1, len(pattern.calls)):
                        call = pattern.calls[j]
                        if not call.alighting_allowed:
                            continue
                        alight_stop = self._network.stops.get(call.stop_id)
                        if alight_stop is None:
                            continue
                        ride = self._ride_leg(pattern, index, j)
                        legs = state.legs + (ride,)
                        if call.stop_id in egress_index:
                            _stop, egress_leg = egress_index[call.stop_id]
                            egress_m = egress_leg.distance_m if egress_leg else 0.0
                            if state.walk_used_m + egress_m <= constraints.max_walking_m:
                                complete = legs + ((egress_leg,) if egress_leg else ())
                                candidates.append(
                                    self._build_itinerary(
                                        complete, state.transfers, state.unverified_transfer
                                    )
                                )
                                if len(candidates) >= constraints.max_candidates_considered:
                                    return candidates
                        if depth < constraints.max_transfers:
                            next_frontier.extend(
                                self._successor_states(
                                    state, legs, alight_stop, pattern, constraints
                                )
                            )
            frontier = next_frontier
        return candidates

    def _successor_states(
        self,
        state: _State,
        legs: tuple[Leg, ...],
        alight_stop: StopSpec,
        pattern: PatternSpec,
        constraints: PlanningConstraints,
    ) -> list[_State]:
        """States reachable after alighting: same-stop re-board + connectors."""
        successors: list[_State] = [
            _State(
                stop_id=alight_stop.id,
                stop=alight_stop,
                walk_used_m=state.walk_used_m,
                legs=legs,
                transfers=state.transfers + 1,
                last_pattern_id=pattern.id,
                unverified_transfer=state.unverified_transfer,
            )
        ]
        for edge in self._transfers_by_stop.get(alight_stop.id, []):
            if constraints.require_verified_transfers and edge.verification_status != "verified":
                continue
            if edge.walk_distance_m is None or edge.walk_seconds is None:
                continue  # connector without a routed path is unusable — no estimate
            new_walk = state.walk_used_m + edge.walk_distance_m
            if new_walk > constraints.max_walking_m:
                continue
            to_stop = self._network.stops.get(edge.to_stop_id)
            if to_stop is None:
                continue
            walk_leg = WalkLeg(
                purpose="transfer",
                distance_m=float(edge.walk_distance_m),
                duration_s=float(edge.walk_seconds),
                from_ref=self._access_ref(edge.from_access_point_id, alight_stop),
                to_ref={
                    "kind": "stop_access_point",
                    "id": str(edge.to_access_point_id),
                    "stop_id": str(to_stop.id),
                },
                provider="stored_connector",
                coordinates=edge.coordinates,
            )
            successors.append(
                _State(
                    stop_id=to_stop.id,
                    stop=to_stop,
                    walk_used_m=new_walk,
                    legs=legs + (walk_leg,),
                    transfers=state.transfers + 1,
                    last_pattern_id=pattern.id,
                    unverified_transfer=state.unverified_transfer
                    or edge.verification_status == "unverified",
                )
            )
        return successors

    def _access_ref(self, access_point_id: uuid.UUID, stop: StopSpec) -> dict[str, Any]:
        for access_point in stop.access_points:
            if access_point.id == access_point_id:
                return {
                    "kind": "stop_access_point",
                    "id": str(access_point.id),
                    "stop_id": str(stop.id),
                }
        return {"kind": "stop", "id": str(stop.id), "name": stop.name}

    def _dedupe_frontier(self, frontier: list[_State]) -> list[_State]:
        """One state per (stop, transfers): keep the least walking (deterministic)."""
        best: dict[tuple[uuid.UUID, int], _State] = {}
        for state in sorted(frontier, key=lambda s: (str(s.stop_id), s.walk_used_m, s.transfers)):
            best.setdefault((state.stop_id, state.transfers), state)
        return sorted(best.values(), key=lambda s: (str(s.stop_id), s.walk_used_m))

    def _ride_leg(self, pattern: PatternSpec, board_index: int, alight_index: int) -> RideLeg:
        board_call = pattern.calls[board_index]
        alight_call = pattern.calls[alight_index]
        board_stop = self._network.stops[board_call.stop_id]
        alight_stop = self._network.stops[alight_call.stop_id]
        straight = haversine_m(board_stop.lon, board_stop.lat, alight_stop.lon, alight_stop.lat)
        distance_m, duration_min_s, duration_max_s = ride_estimate(straight)
        return RideLeg(
            pattern_id=str(pattern.id),
            route_id=str(pattern.route_id),
            route_code=pattern.route_code,
            mode=pattern.mode,
            direction_id=pattern.direction_id,
            pattern_code=pattern.pattern_code,
            origin_label=pattern.origin_label,
            destination_label=pattern.destination_label,
            verification_status=pattern.verification_status,
            board_stop_id=str(board_stop.id),
            board_stop_name=board_stop.name,
            board_sequence=board_call.sequence,
            alight_stop_id=str(alight_stop.id),
            alight_stop_name=alight_stop.name,
            alight_sequence=alight_call.sequence,
            estimated_distance_m=round(distance_m, 1),
            duration_min_s=round(duration_min_s, 1),
            duration_max_s=round(duration_max_s, 1),
        )

    def _build_itinerary(
        self, legs: tuple[Leg, ...], transfers: int, unverified_transfer: bool
    ) -> Itinerary:
        walk_distance = sum(leg.distance_m for leg in legs if isinstance(leg, WalkLeg))
        walk_seconds = sum(leg.duration_s for leg in legs if isinstance(leg, WalkLeg))
        ride_min = sum(leg.duration_min_s for leg in legs if isinstance(leg, RideLeg))
        ride_max = sum(leg.duration_max_s for leg in legs if isinstance(leg, RideLeg))
        warnings: list[str] = [STATIC_SERVICE_WARNING]
        confidence = "verified"
        if unverified_transfer:
            warnings.append("A transfer path in this option is not field-verified yet.")
            confidence = "unverified_transfer"
        for leg in legs:
            if isinstance(leg, RideLeg) and leg.verification_status != "verified":
                label = leg.pattern_code or f"pattern of route {leg.route_code}"
                warnings.append(f"Route {leg.route_code} ({label}) has not been field-verified.")
                if confidence == "verified":
                    confidence = "unverified_pattern"
        # Preserve order, drop duplicates (deterministic).
        warnings = list(dict.fromkeys(warnings))
        return Itinerary(
            legs=legs,
            transfer_count=transfers,
            walk_distance_m=round(walk_distance, 1),
            duration_min_s=round(walk_seconds + ride_min, 1),
            duration_max_s=round(walk_seconds + ride_max, 1),
            warnings=tuple(warnings),
            confidence=confidence,
        )

    async def _walk_only_fallback(
        self,
        origin: Endpoint,
        destination: Endpoint,
        constraints: PlanningConstraints,
        notes: list[str],
    ) -> Itinerary | None:
        """Walking-only journey when no transit option exists (honest fallback)."""
        start = self._point_of(origin)
        end = self._point_of(destination)
        if start is None or end is None:
            return None
        plan = await self._walking_router.route_walk(start[0], start[1], end[0], end[1])
        if plan is None:
            notes.append("Walking-only fallback unavailable: the walking engine produced no path.")
            return None
        if plan.distance_m > constraints.max_walking_m:
            notes.append(
                f"Walking-only distance ({plan.distance_m:.0f} m) exceeds the walking"
                f" cap ({constraints.max_walking_m:.0f} m)."
            )
            return None
        walk_leg = WalkLeg(
            purpose="walk_only",
            distance_m=plan.distance_m,
            duration_s=plan.duration_s,
            from_ref={"kind": "origin"},
            to_ref={"kind": "destination"},
            provider=plan.provider,
            coordinates=plan.coordinates,
        )
        return Itinerary(
            legs=(walk_leg,),
            transfer_count=0,
            walk_distance_m=round(plan.distance_m, 1),
            duration_min_s=round(plan.duration_s, 1),
            duration_max_s=round(plan.duration_s, 1),
            warnings=(
                STATIC_SERVICE_WARNING,
                "No transit option within the constraints; walking-only journey returned.",
            ),
            confidence="verified",
        )

    def _point_of(self, endpoint: Endpoint) -> tuple[float, float] | None:
        if endpoint.kind == "stop" and endpoint.stop_id is not None:
            stop = self._network.stops.get(endpoint.stop_id)
            if stop is None:
                return None
            return stop.lon, stop.lat
        if endpoint.kind == "coordinates" and endpoint.lon is not None:
            assert endpoint.lat is not None  # validated by Endpoint.validate
            return endpoint.lon, endpoint.lat
        return None
