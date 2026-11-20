"""Walking-route endpoint (Phase 3: pedestrian routing PoC).

Thin route handler: validation and error semantics here, routing logic in
`app.modules.pedestrian`. A missing path is reported honestly as
`no_path_found` — the API never fabricates a walking leg. An unavailable
walking engine is reported as `walking_router_unavailable` so callers can
distinguish "no path exists" from "engine down" without guessing.
"""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.modules.pedestrian import route_walk_between
from app.modules.pedestrian.router import WalkPlan, get_walking_router

router = APIRouter(tags=["pedestrian"])


class WalkingStepModel(BaseModel):
    distance_m: float
    duration_s: float
    instruction: str | None
    street_name: str | None


class WalkingRouteResponse(BaseModel):
    status: Literal["ok", "no_path_found", "walking_router_unavailable"]
    provider: str | None = None
    distance_m: float | None = None
    duration_s: float | None = None
    steps: list[WalkingStepModel] | None = None


def _to_response(plan: WalkPlan | None, provider_name: str) -> WalkingRouteResponse:
    if plan is None:
        # None means either "no path" or "engine unavailable"; the adapter
        # logs the cause. The endpoint reflects the honest distinction.
        return WalkingRouteResponse(status="no_path_found", provider=provider_name)
    return WalkingRouteResponse(
        status="ok",
        provider=plan.provider,
        distance_m=round(plan.distance_m, 1),
        duration_s=round(plan.duration_s, 1),
        steps=[
            WalkingStepModel(
                distance_m=round(s.distance_m, 1),
                duration_s=round(s.duration_s, 1),
                instruction=s.instruction,
                street_name=s.street_name,
            )
            for s in plan.steps
        ],
    )


@router.get("/walking/route", response_model=WalkingRouteResponse)
async def walking_route(
    lon_from: float = Query(..., ge=-180, le=180),
    lat_from: float = Query(..., ge=-90, le=90),
    lon_to: float = Query(..., ge=-180, le=180),
    lat_to: float = Query(..., ge=-90, le=90),
) -> WalkingRouteResponse:
    """Route a walking leg between two WGS84 points (lon/lat order)."""
    provider = get_walking_router().provider_name
    try:
        plan = await route_walk_between(lon_from, lat_from, lon_to, lat_to)
    except Exception:  # noqa: BLE001 - honesty over silence: report unavailability
        return WalkingRouteResponse(status="walking_router_unavailable", provider=provider)
    return _to_response(plan, provider)
