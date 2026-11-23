"""Grounded AI explanation endpoints (Phase 8, plan items 1–3, 6–8).

AI is optional and never required: a request always answers 200 with either
a validated AI explanation (`source: "ai"`) or the deterministic fallback
(`source: "deterministic_fallback"`) — provider outages, misconfiguration,
rate limiting and ungrounded outputs never become 5xx.

Two sources for the journey payload:
- `journey_id` — the saved journey snapshot is fetched server-side (preferred:
  the client sends only an ID);
- `journey` — an inline plan-response snapshot (e.g. from the offline cache).
Coordinates are stripped from both before anything reaches the provider.
"""

from __future__ import annotations

import uuid
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from app.modules.ai_assistance import explain
from app.modules.journey_sessions import get_saved_journey
from app.platform.config import get_settings
from app.platform.db import get_session
from app.platform.metrics import increment_counter

router = APIRouter(tags=["ai"])

SessionDep = Annotated[Any, Depends(get_session)]


class AIExplanationRequest(BaseModel):
    mode: Literal["explain_step", "why_route"] = "explain_step"
    journey_id: uuid.UUID | None = Field(
        default=None, description="Saved journey to explain (server fetches the snapshot)."
    )
    journey: dict[str, Any] | None = Field(
        default=None, description="Inline plan-response snapshot (offline-cache path)."
    )
    option_index: int = Field(default=0, ge=0)
    step_index: int | None = Field(default=None, ge=0)


async def _resolve_payload(session: Any, request: AIExplanationRequest) -> dict[str, Any]:
    """Load the plan snapshot from the saved journey or accept the inline one."""
    if (request.journey_id is None) == (request.journey is None):
        raise HTTPException(
            status_code=400,
            detail="Provide exactly one of journey_id or journey (the plan snapshot).",
        )
    if request.journey_id is not None:
        row = await get_saved_journey(session, request.journey_id)
        if row is None:
            raise HTTPException(status_code=404, detail="saved journey not found")
        return dict(row.response)
    payload = request.journey or {}
    if not isinstance(payload.get("options"), list) or not payload["options"]:
        raise HTTPException(
            status_code=400,
            detail="journey must be a plan response with at least one option.",
        )
    return payload


def _client_key(request: Request) -> str:
    """Throttle key: the client host (no user identity exists yet)."""
    return request.client.host if request.client else "unknown"


@router.post("/ai/explain-step")
async def explain_step(session: SessionDep, request: Request, body: AIExplanationRequest) -> Any:
    """Explain one journey step (grounded; deterministic fallback)."""
    if body.mode == "explain_step" and body.step_index is None:
        raise HTTPException(status_code=400, detail="mode explain_step requires step_index.")
    payload = await _resolve_payload(session, body)
    try:
        result = await explain(
            payload,
            body.mode,
            body.option_index,
            body.step_index,
            get_settings(),
            _client_key(request),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    payload_out = result.serialize()
    increment_counter(
        "sljp_ai_explanations_total",
        {"mode": payload_out["mode"], "source": payload_out["source"]},
    )
    return payload_out


@router.post("/ai/why-route")
async def why_route(session: SessionDep, request: Request, body: AIExplanationRequest) -> Any:
    """Explain why the planner offers this option (grounded; fallback)."""
    payload = await _resolve_payload(session, body)
    try:
        result = await explain(
            payload,
            "why_route",
            body.option_index,
            None,
            get_settings(),
            _client_key(request),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    payload_out = result.serialize()
    increment_counter(
        "sljp_ai_explanations_total",
        {"mode": payload_out["mode"], "source": payload_out["source"]},
    )
    return payload_out
