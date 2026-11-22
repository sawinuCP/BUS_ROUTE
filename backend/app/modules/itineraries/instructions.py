"""Deterministic instruction generation (Phase 5 work items 1–6).

Converts planner itineraries into ordered, executable instruction steps. Rules
from the implementation plan §6.6 and the routing-engine doc §7:

- **Templates are deterministic** and consume **structured facts only**: a
  value absent from the facts (unverified direction label, unknown stop
  count, unmapped landmark) is omitted or phrased as "not confirmed" — a
  template can never emit a route/direction/landmark value that is not in the
  supplied facts.
- Step/action codes are stable per the API design doc: `WALK_TO_STOP`,
  `BOARD_TRANSIT`, `RIDE_TRANSIT`, `ALIGHT_TRANSIT`, `WALK_TRANSFER`,
  `WALK_TO_DESTINATION`.
- The intermediate-stop count is shown **only when the ordered stop sequence
  is reliable** (contiguous sequence numbers across the ride span); a gap
  means OSM data is incomplete and the count is rendered as "not confirmed".
- English only for now: si/ta rendering arrives after native review (D-7
  deferred); requests in other languages fall back to English with an explicit
  note — never machine-translated and presented as reviewed.
- No live-availability or waiting-time language, ever.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.modules.planner import RideLeg, WalkLeg
from app.modules.planner.network import TransitNetwork

WALK_TO_STOP = "WALK_TO_STOP"
BOARD_TRANSIT = "BOARD_TRANSIT"
RIDE_TRANSIT = "RIDE_TRANSIT"
ALIGHT_TRANSIT = "ALIGHT_TRANSIT"
WALK_TRANSFER = "WALK_TRANSFER"
WALK_TO_DESTINATION = "WALK_TO_DESTINATION"

SUPPORTED_LANGUAGES = ("en", "si", "ta")
_DEFAULT_LANGUAGE = "en"

_NOT_CONFIRMED = "not confirmed"


@dataclass(frozen=True)
class InstructionStep:
    """One executable instruction, text rendered from its own facts."""

    action: str
    text: str
    facts: dict[str, Any]
    confidence: str


def _stop_name(network: TransitNetwork, ref: dict[str, Any]) -> str:
    """Resolve a human stop name from an endpoint reference (facts only)."""
    if ref.get("name"):
        return str(ref["name"])
    stop_id = ref.get("stop_id")
    if stop_id is not None:
        from uuid import UUID

        try:
            stop = network.stops.get(UUID(str(stop_id)))
        except ValueError:
            stop = None
        if stop is not None:
            return stop.name
    return _NOT_CONFIRMED


def _target_coords(network: TransitNetwork, ref: dict[str, Any]) -> tuple[float, float] | None:
    """Target coordinates for a walk/board step, from canonical data only.

    Prefers the exact access point's mapped position; falls back to the
    stop's mapped position. Returns None when neither is mapped — the GPS
    assistant simply stays silent rather than guessing.
    """
    from uuid import UUID

    access_point_id = ref.get("id") if ref.get("kind") == "stop_access_point" else None
    stop_id_raw = ref.get("stop_id") or (ref.get("id") if ref.get("kind") == "stop" else None)
    if stop_id_raw is None:
        return None
    try:
        stop = network.stops.get(UUID(str(stop_id_raw)))
    except ValueError:
        return None
    if stop is None:
        return None
    if access_point_id is not None:
        try:
            ap_id = UUID(str(access_point_id))
        except ValueError:
            ap_id = None
        for access_point in stop.access_points:
            if access_point.id == ap_id:
                return access_point.lon, access_point.lat
    return stop.lon, stop.lat


def _walk_step(network: TransitNetwork, leg: WalkLeg) -> InstructionStep:
    metres = round(leg.distance_m)
    if leg.purpose == "access":
        to_name: str | None = None
        facts: dict[str, Any] = {
            "distance_m": metres,
            "duration_s": round(leg.duration_s),
        }
        if leg.to_ref.get("kind") == "stop":
            to_name = _stop_name(network, leg.to_ref)
            facts["to_stop_name"] = to_name
            text = f"Walk {metres} m to {to_name}."
        elif leg.to_ref.get("kind") == "stop_access_point":
            facts["to_access_point_id"] = str(leg.to_ref["id"])
            text = f"Walk {metres} m to the boarding point."
        else:
            text = f"Walk {metres} m to the bus stop."
        coords = _target_coords(network, leg.to_ref)
        if coords is not None:
            facts["target_lat"] = coords[1]
            facts["target_lon"] = coords[0]
        return InstructionStep(action=WALK_TO_STOP, text=text, facts=facts, confidence="unverified")
    if leg.purpose == "transfer":
        to_name = _stop_name(network, leg.to_ref)
        facts_t: dict[str, Any] = {
            "distance_m": metres,
            "duration_s": round(leg.duration_s),
            "to_stop_id": leg.to_ref.get("stop_id"),
            "to_stop_name": to_name,
            "next_boarding_point": to_name,
            "walking_provider": leg.provider,
        }
        coords = _target_coords(network, leg.to_ref)
        if coords is not None:
            facts_t["target_lat"] = coords[1]
            facts_t["target_lon"] = coords[0]
        return InstructionStep(
            action=WALK_TRANSFER,
            text=f"Walk {metres} m to {to_name} to change buses.",
            facts=facts_t,
            # The connector's own verification state is carried on the option;
            # the walk itself is an engine-routed path, not a verified fact.
            confidence="unverified",
        )
    facts = {"distance_m": metres, "duration_s": round(leg.duration_s)}
    if leg.to_ref.get("kind") == "stop":
        facts["to_stop_name"] = _stop_name(network, leg.to_ref)
    coords = _target_coords(network, leg.to_ref)
    if coords is not None:
        facts["target_lat"] = coords[1]
        facts["target_lon"] = coords[0]
    return InstructionStep(
        action=WALK_TO_DESTINATION,
        text=f"Walk {metres} m to your destination.",
        facts=facts,
        confidence="unverified",
    )


def _board_step(network: TransitNetwork, leg: RideLeg) -> InstructionStep:
    headsign = leg.destination_label
    text = f"Board route {leg.route_code} at {leg.board_stop_name}"
    facts: dict[str, Any] = {
        "route_id": leg.route_id,
        "route_code": leg.route_code,
        "pattern_id": leg.pattern_id,
        "pattern_code": leg.pattern_code,
        "direction_id": leg.direction_id,
        "stop_id": leg.board_stop_id,
        "stop_name": leg.board_stop_name,
    }
    coords = _target_coords(
        network, {"kind": "stop", "id": leg.board_stop_id, "name": leg.board_stop_name}
    )
    if coords is not None:
        facts["stop_lat"] = coords[1]
        facts["stop_lon"] = coords[0]
    if headsign:
        text += f" heading towards {headsign}"
        facts["headsign"] = headsign
    else:
        facts["headsign"] = _NOT_CONFIRMED
    if leg.pattern_code:
        facts["variant"] = leg.pattern_code
    return InstructionStep(
        action=BOARD_TRANSIT, text=text + ".", facts=facts, confidence=leg.verification_status
    )


def _ride_step(network: TransitNetwork, leg: RideLeg) -> InstructionStep:
    facts: dict[str, Any] = {
        "pattern_id": leg.pattern_id,
        "route_code": leg.route_code,
        "board_stop_id": leg.board_stop_id,
        "alight_stop_id": leg.alight_stop_id,
        "alight_stop_name": leg.alight_stop_name,
        "estimated_distance_m": leg.estimated_distance_m,
        "estimated_duration_minutes": {
            "min": round(leg.duration_min_s / 60.0),
            "max": round(leg.duration_max_s / 60.0),
        },
        "intermediate_stops": leg.intermediate_stops,
    }
    if leg.intermediate_stops is None:
        # Ordered stop sequence is not reliable (gap) — the count is withheld.
        facts["intermediate_stops"] = _NOT_CONFIRMED
        text = f"Stay on route {leg.route_code} and alight at {leg.alight_stop_name}."
    else:
        stops_ridden = leg.intermediate_stops + 1
        plural = "s" if stops_ridden != 1 else ""
        text = f"Ride {stops_ridden} stop{plural} to {leg.alight_stop_name}."
    return InstructionStep(
        action=RIDE_TRANSIT, text=text, facts=facts, confidence=leg.verification_status
    )


def _alight_step(network: TransitNetwork, leg: RideLeg) -> InstructionStep:
    return InstructionStep(
        action=ALIGHT_TRANSIT,
        text=f"Alight at {leg.alight_stop_name}.",
        facts={
            "stop_id": leg.alight_stop_id,
            "stop_name": leg.alight_stop_name,
            "alight_sequence": leg.alight_sequence,
        },
        confidence=leg.verification_status,
    )


def build_steps(
    network: TransitNetwork, legs: tuple[Any, ...], language: str = _DEFAULT_LANGUAGE
) -> list[InstructionStep]:
    """Expand itinerary legs into ordered instruction steps (English).

    Walk legs become one step each; ride legs become board → ride → alight.
    Non-English requests fall back to English (D-7: native review pending) —
    callers must surface that limitation rather than imply reviewed text.
    """
    del language  # English-only until D-7 native review; see module docstring.
    steps: list[InstructionStep] = []
    for leg in legs:
        if isinstance(leg, WalkLeg):
            steps.append(_walk_step(network, leg))
        elif isinstance(leg, RideLeg):
            steps.append(_board_step(network, leg))
            steps.append(_ride_step(network, leg))
            steps.append(_alight_step(network, leg))
    return steps
