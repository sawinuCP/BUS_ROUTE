"""Saved-journey lifecycle: save, retrieve, refresh (Phase 4 completion).

Rules encoded here:
- A saved journey stores the **exact request** and the **response snapshot**
  generated at save time; retrieval returns that snapshot unchanged (with the
  dataset version it was planned against), never a re-derived plan.
- `refresh` re-plans the stored request against the **current** active dataset
  version (fresh computation — the cache is bypassed) and records both the
  previous and new version labels, so the caller can see what changed.
- Writes are caller-committed (mirrors the admin endpoints); this module only
  flushes.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.journey_sessions.models import SavedJourney
from app.modules.pedestrian.router import WalkingRouter
from app.modules.planner import (
    Endpoint,
    JourneyPlanner,
    PlanningConstraints,
    load_network,
)
from app.modules.planner.serialize import serialize_result


async def save_journey(
    session: AsyncSession,
    origin: dict[str, Any],
    destination: dict[str, Any],
    preferences: dict[str, Any],
    response: dict[str, Any],
    notes: str | None = None,
) -> uuid.UUID:
    """Persist one saved journey (caller owns the commit)."""
    row = SavedJourney(
        origin=origin,
        destination=destination,
        preferences=preferences,
        dataset_version_label=str(response.get("dataset_version", "unknown")),
        response=response,
        notes=notes,
    )
    session.add(row)
    await session.flush()
    return row.id


async def get_saved_journey(session: AsyncSession, journey_id: uuid.UUID) -> SavedJourney | None:
    return await session.get(SavedJourney, journey_id)


def _endpoint_from_payload(payload: dict[str, Any]) -> Endpoint:
    stop_id = payload.get("stop_id")
    lon = payload.get("lon")
    lat = payload.get("lat")
    return Endpoint(
        kind=str(payload.get("type", payload.get("kind", "stop"))),
        stop_id=uuid.UUID(str(stop_id)) if stop_id is not None else None,
        lon=None if lon is None else float(lon),
        lat=None if lat is None else float(lat),
    )


def _constraints_from_payload(payload: dict[str, Any]) -> PlanningConstraints:
    return PlanningConstraints(
        allowed_modes=frozenset(payload.get("allowed_modes", ["bus"])) | {"walk"},
        max_walking_m=float(payload.get("max_walking_m", 1500.0)),
        max_transfers=int(payload.get("max_transfers", 1)),
        require_verified_transfers=bool(payload.get("require_verified_transfers", False)),
    )


async def refresh_saved_journey(
    session: AsyncSession,
    journey_id: uuid.UUID,
    walking_router: WalkingRouter,
) -> dict[str, Any] | None:
    """Re-plan the stored request against the current active dataset version.

    The stored row is updated with the fresh response (caller commits). The
    returned payload carries `journey_id`, `refreshed: true` and the
    `previous_dataset_version`, or None when the journey does not exist.
    """
    row = await session.get(SavedJourney, journey_id)
    if row is None:
        return None

    network = await load_network(session)
    planner = JourneyPlanner(network, walking_router)
    stored_preferences = dict(row.preferences)
    result = await planner.plan(
        _endpoint_from_payload(dict(row.origin)),
        _endpoint_from_payload(dict(row.destination)),
        _constraints_from_payload(stored_preferences),
        priority=str(stored_preferences.get("priority", "fastest")),
    )

    previous_version = row.dataset_version_label
    payload = serialize_result(
        result, network=network, language=str(stored_preferences.get("language", "en"))
    )
    payload["language"] = str(stored_preferences.get("language", "en"))
    payload["journey_id"] = str(row.id)
    payload["refreshed"] = True
    payload["previous_dataset_version"] = previous_version

    row.response = payload
    row.dataset_version_label = result.version_label
    await session.flush()
    return payload
