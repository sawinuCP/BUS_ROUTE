"""Journey planning endpoint (Phase 4 — deterministic multimodal planner).

Thin route handler per the API design doc (`POST /journeys/plan`): request
validation and serialisation here, all planning logic in
`app.modules.planner`. A plan is **network-feasible, not live-confirmed**:
every response carries the dataset version, availability scope, and honest
warnings (unverified transfers/patterns, static-service caveat). `no_route`
is a 200 with an explanation — missing data is never papered over with a
fabricated journey.
"""

from __future__ import annotations

import uuid
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.modules.pedestrian.router import get_walking_router
from app.modules.planner import (
    Endpoint,
    JourneyPlanner,
    PlanningConstraints,
    RideLeg,
    WalkLeg,
    load_network,
)
from app.platform.db import get_session

router = APIRouter(tags=["journeys"])

SessionDep = Annotated[Any, Depends(get_session)]


class EndpointModel(BaseModel):
    type: Literal["stop", "coordinates"]
    stop_id: uuid.UUID | None = None
    lon: float | None = Field(default=None, ge=-180, le=180)
    lat: float | None = Field(default=None, ge=-90, le=90)

    def to_endpoint(self) -> Endpoint:
        if self.type == "stop" and self.stop_id is None:
            raise HTTPException(
                status_code=400, detail="origin/destination type 'stop' requires stop_id"
            )
        if self.type == "coordinates" and (self.lon is None or self.lat is None):
            raise HTTPException(
                status_code=400,
                detail="origin/destination type 'coordinates' requires lon and lat",
            )
        return Endpoint(kind=self.type, stop_id=self.stop_id, lon=self.lon, lat=self.lat)


class PreferencesModel(BaseModel):
    priority: Literal["fastest", "least_walking", "fewest_transfers", "simplest"] = "fastest"
    max_walking_m: int = Field(default=1500, ge=200, le=10000)
    max_transfers: int = Field(default=1, ge=0, le=3)
    allowed_modes: list[Literal["bus", "rail"]] = ["bus"]
    require_verified_transfers: bool = False

    def to_constraints(self) -> PlanningConstraints:
        return PlanningConstraints(
            allowed_modes=frozenset(self.allowed_modes) | {"walk"},
            max_walking_m=float(self.max_walking_m),
            max_transfers=self.max_transfers,
            require_verified_transfers=self.require_verified_transfers,
        )


class PlanRequest(BaseModel):
    origin: EndpointModel
    destination: EndpointModel
    preferences: PreferencesModel = PreferencesModel()


def _serialize_leg(leg: RideLeg | WalkLeg) -> dict[str, Any]:
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


@router.post("/journeys/plan")
async def plan_journey(
    session: SessionDep,
    request: PlanRequest,
) -> Any:
    """Generate deterministic multimodal journey options."""
    network = await load_network(session)
    planner = JourneyPlanner(network, get_walking_router())
    result = await planner.plan(
        request.origin.to_endpoint(),
        request.destination.to_endpoint(),
        request.preferences.to_constraints(),
        priority=request.preferences.priority,
    )
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
            "legs": [_serialize_leg(leg) for leg in itinerary.legs],
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
        "note": (
            "Plans are grounded in canonical, versioned transport data. No"
            " timetable, fare or live-availability claim is made; every option"
            " carries its verification state."
        ),
    }
