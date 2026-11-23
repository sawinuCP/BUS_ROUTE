"""Active journey session endpoints (Phase 6 — active journey mode).

Thin route handlers per the API design doc: a session starts only from a
**saved, server-generated** plan (grounded data — nothing client-crafted is
executed); progress is **manual-first** (arrived/boarded/alighted/advanced,
pause, complete, cancel); GPS never drives backend state. Invalid state
transitions return 409 with the rule so the client can explain itself. No
location data is accepted or stored on any session endpoint (data model §6).
"""

from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.modules.journey_sessions import (
    InvalidTransition,
    apply_session_event,
    get_journey_session,
    replan_session,
    start_session,
)
from app.modules.pedestrian.router import get_walking_router
from app.platform.db import get_session
from app.platform.metrics import increment_counter

router = APIRouter(tags=["journey-sessions"])

SessionDep = Annotated[Any, Depends(get_session)]


class StartSessionRequest(BaseModel):
    journey_id: uuid.UUID = Field(description="A saved journey (server-generated plan).")
    option_id: str = Field(description="The option inside that saved plan to follow.")


class SessionEventRequest(BaseModel):
    event_type: str = Field(
        description="One of: started, step_advanced, paused, resumed, completed, cancelled."
    )
    step_index: int | None = Field(
        default=None,
        ge=0,
        description="For step_advanced: the step the traveller has now reached.",
    )
    note: str | None = Field(default=None, max_length=500)


class ReplanRequest(BaseModel):
    origin: dict[str, Any] | None = Field(
        default=None,
        description=(
            "Optional origin override for missed-stop recovery "
            '({"type": "stop", "stop_id": ...} or coordinates).'
        ),
    )


@router.post("/journey-sessions")
async def start_journey_session(session: SessionDep, request: StartSessionRequest) -> Any:
    """Start following one option of a saved plan (status derived from step 0)."""
    payload = await start_session(session, request.journey_id, request.option_id)
    if payload is None:
        raise HTTPException(
            status_code=404,
            detail="saved journey or option not found — save the plan first (save: true)",
        )
    await session.commit()
    increment_counter("sljp_journey_sessions_started_total")
    return payload


@router.get("/journey-sessions/{session_id}")
async def read_journey_session(session: SessionDep, session_id: uuid.UUID) -> Any:
    """Current session state — restore after background/restart."""
    payload = await get_journey_session(session, session_id)
    if payload is None:
        raise HTTPException(status_code=404, detail="journey session not found")
    return payload


@router.post("/journey-sessions/{session_id}/events")
async def post_session_event(
    session: SessionDep, session_id: uuid.UUID, request: SessionEventRequest
) -> Any:
    """Apply one manual progress event (boarding/alighting are step advances)."""
    try:
        payload = await apply_session_event(
            session, session_id, request.event_type, request.step_index, request.note
        )
    except InvalidTransition as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if payload is None:
        raise HTTPException(status_code=404, detail="journey session not found")
    await session.commit()
    increment_counter("sljp_journey_session_events_total", {"event": request.event_type})
    return payload


@router.post("/journey-sessions/{session_id}/replan")
async def replan_journey_session(
    session: SessionDep, session_id: uuid.UUID, request: ReplanRequest | None = None
) -> Any:
    """Re-plan the session against the current active dataset version.

    The body is optional: a bare replan (no origin override) needs no body.
    """
    try:
        payload = await replan_session(
            session, session_id, get_walking_router(), request.origin if request else None
        )
    except InvalidTransition as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if payload is None:
        raise HTTPException(status_code=404, detail="journey session not found")
    await session.commit()
    increment_counter(
        "sljp_journey_session_replans_total",
        {"outcome": "replanned" if payload.get("replanned") else "no_replacement"},
    )
    return payload
