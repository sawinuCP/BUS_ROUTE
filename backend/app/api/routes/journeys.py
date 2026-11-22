"""Journey planning endpoints (Phase 4 — deterministic multimodal planner).

Thin route handlers per the API design doc: request validation, cache wiring
and serialisation here; all planning logic in `app.modules.planner`, journey
persistence in `app.modules.journey_sessions`. A plan is **network-feasible,
not live-confirmed**: every response carries the dataset version, availability
scope, and honest warnings (unverified transfers/patterns, static-service
caveat). `no_route` is a 200 with an explanation — missing data is never
papered over with a fabricated journey.

Caching (ADR-0003): plan payloads are cached in Redis keyed by the normalized
request + network dataset version — a version change produces a new key, so
invalidation is immediate; Redis failure degrades to recompute.
"""

from __future__ import annotations

import uuid
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.modules.journey_sessions import (
    get_saved_journey,
    refresh_saved_journey,
    save_journey,
)
from app.modules.pedestrian.router import get_walking_router
from app.modules.planner import (
    Endpoint,
    JourneyPlanner,
    PlanningConstraints,
    load_network,
    serialize_result,
)
from app.modules.planner.cache import normalized_request_key
from app.platform.config import get_settings
from app.platform.db import get_session
from app.platform.plan_cache import RedisPlanCache
from app.platform.redis_client import get_redis

router = APIRouter(tags=["journeys"])

SessionDep = Annotated[Any, Depends(get_session)]


def _cache() -> Any:
    """The plan cache for this process (monkeypatchable in tests)."""
    settings = get_settings()
    return RedisPlanCache(get_redis(), ttl_seconds=settings.plan_cache_ttl_seconds)


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
    language: Literal["en", "si", "ta"] = Field(
        default="en",
        description="Instruction language. si/ta fall back to English until native review (D-7).",
    )
    save: bool = Field(
        default=False,
        description="Persist the plan as a saved journey (retrievable/refreshable).",
    )


@router.post("/journeys/plan")
async def plan_journey(session: SessionDep, request: PlanRequest) -> Any:
    """Generate deterministic multimodal journey options (optionally saved)."""
    network = await load_network(session)
    key = normalized_request_key(
        network.version_label,
        request.origin.model_dump(mode="json"),
        request.destination.model_dump(mode="json"),
        # Language is part of the normalized request (instructions differ).
        {**request.preferences.model_dump(mode="json"), "language": request.language},
    )
    cache = _cache()
    cached = await cache.get_json(key)
    if cached is not None:
        # Same request over the same network version → identical options.
        snapshot = {k: v for k, v in cached.items() if k != "cache"}
        if request.save:
            journey_id = await save_journey(
                session,
                origin=request.origin.model_dump(mode="json"),
                destination=request.destination.model_dump(mode="json"),
                preferences={
                    **request.preferences.model_dump(mode="json"),
                    "language": request.language,
                },
                response=snapshot,
            )
            await session.commit()
            snapshot["journey_id"] = str(journey_id)
            snapshot["cache"] = "hit"
            return snapshot
        cached["cache"] = "hit"
        return cached

    planner = JourneyPlanner(network, get_walking_router())
    result = await planner.plan(
        request.origin.to_endpoint(),
        request.destination.to_endpoint(),
        request.preferences.to_constraints(),
        priority=request.preferences.priority,
    )
    payload = serialize_result(result, network=network, language=request.language)
    payload["cache"] = "miss"
    payload["language"] = request.language
    if request.language != "en":
        payload["notes"] = [
            *payload["notes"],
            "si/ta instruction text is rendered in English until native review"
            " is complete (deferred decision D-7).",
        ]
    payload["note"] = (
        "Plans are grounded in canonical, versioned transport data. No"
        " timetable, fare or live-availability claim is made; every option"
        " carries its verification state."
    )
    await cache.set_json(key, payload, get_settings().plan_cache_ttl_seconds)

    if request.save:
        journey_id = await save_journey(
            session,
            origin=request.origin.model_dump(mode="json"),
            destination=request.destination.model_dump(mode="json"),
            preferences={
                **request.preferences.model_dump(mode="json"),
                "language": request.language,
            },
            response=payload,
        )
        await session.commit()
        payload = {**payload, "journey_id": str(journey_id)}
    return payload


@router.get("/journeys/{journey_id}")
async def get_journey(session: SessionDep, journey_id: uuid.UUID) -> Any:
    """Retrieve a saved journey's request + response snapshot (no re-plan)."""
    row = await get_saved_journey(session, journey_id)
    if row is None:
        raise HTTPException(status_code=404, detail="saved journey not found")
    response = dict(row.response)
    response["journey_id"] = str(row.id)
    response["saved_at_dataset_version"] = row.dataset_version_label
    return response


@router.post("/journeys/{journey_id}/refresh")
async def refresh_journey(session: SessionDep, journey_id: uuid.UUID) -> Any:
    """Re-plan the saved request against the current active dataset version."""
    payload = await refresh_saved_journey(session, journey_id, get_walking_router())
    if payload is None:
        raise HTTPException(status_code=404, detail="saved journey not found")
    await session.commit()
    return payload
