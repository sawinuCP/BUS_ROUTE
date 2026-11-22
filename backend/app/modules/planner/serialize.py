"""Serialized plan payloads (pure functions; no framework imports).

Shared by the API route (`POST /journeys/plan`) and the saved-journey refresh
flow so the two response shapes cannot drift. Dict shapes follow the API
design doc's plan example.
"""

from __future__ import annotations

from typing import Any

from app.modules.planner.itinerary import Itinerary, RideLeg, WalkLeg
from app.modules.planner.service import PlanningResult


def serialize_leg(leg: RideLeg | WalkLeg) -> dict[str, Any]:
    if isinstance(leg, RideLeg):
        return {
            "type": "transit",
            "mode": leg.mode,
            "route_id": leg.route_id,
            "route_code": leg.route_code,
            "pattern_id": leg.pattern_id,
            "pattern_code": leg.pattern_code,
            "direction_id": leg.direction_id,
            "origin_label": leg.origin_label,
            "destination_label": leg.destination_label,
            "board_stop_id": leg.board_stop_id,
            "board_stop_name": leg.board_stop_name,
            "board_sequence": leg.board_sequence,
            "alight_stop_id": leg.alight_stop_id,
            "alight_stop_name": leg.alight_stop_name,
            "alight_sequence": leg.alight_sequence,
            "estimated_distance_m": leg.estimated_distance_m,
            "intermediate_stops": leg.intermediate_stops,
            "estimated_duration_minutes": {
                "min": round(leg.duration_min_s / 60.0, 1),
                "max": round(leg.duration_max_s / 60.0, 1),
            },
            "verification_status": leg.verification_status,
            "instruction_code": leg.instruction_code,
        }
    return {
        "type": "walk",
        "purpose": leg.purpose,
        "from": leg.from_ref,
        "to": leg.to_ref,
        "distance_m": round(leg.distance_m, 1),
        "duration_s": round(leg.duration_s, 1),
        "geometry": [[lon, lat] for lon, lat in leg.coordinates],
        "walking_provider": leg.provider,
        "instruction_code": leg.instruction_code,
    }


def serialize_result(
    result: PlanningResult,
    network: Any = None,
    language: str = "en",
) -> dict[str, Any]:
    """Full plan payload (without request-specific extras like journey IDs).

    When a network snapshot is supplied, each option also carries an ordered
    `steps` array of deterministic instruction templates (Phase 5).
    """
    from app.modules.itineraries.instructions import build_steps

    options = [
        {
            "id": f"option-{index + 1}",
            "summary": {
                "estimated_duration_minutes": {
                    "min": round(itinerary.duration_min_s / 60.0, 1),
                    "max": round(itinerary.duration_max_s / 60.0, 1),
                },
                "walking_distance_m": itinerary.walk_distance_m,
                "transfer_count": itinerary.transfer_count,
                "confidence": itinerary.confidence,
            },
            "labels": [label for label, position in result.labels.items() if position == index],
            "warnings": list(itinerary.warnings),
            "legs": [serialize_leg(leg) for leg in itinerary.legs],
            **(
                {
                    "steps": [
                        {
                            "action": step.action,
                            "text": step.text,
                            "facts": step.facts,
                            "confidence": step.confidence,
                        }
                        for step in build_steps(network, itinerary.legs, language)
                    ]
                }
                if network is not None
                else {}
            ),
        }
        for index, itinerary in enumerate(result.options)
    ]
    return {
        "status": result.status,
        "dataset_version": result.version_label,
        "availability_scope": "network_feasible_not_live_confirmed",
        "options": options,
        "labels": result.labels,
        "notes": list(result.notes),
    }


def itinerary_summary(itinerary: Itinerary) -> dict[str, Any]:
    """Compact summary for logs/benchmarks (never a user-facing shape)."""
    return {
        "duration_min_s": itinerary.duration_min_s,
        "duration_max_s": itinerary.duration_max_s,
        "walk_distance_m": itinerary.walk_distance_m,
        "transfer_count": itinerary.transfer_count,
        "confidence": itinerary.confidence,
    }
