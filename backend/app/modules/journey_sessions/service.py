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

from app.modules.journey_sessions.models import (
    JourneyEvent,
    JourneySession,
    SavedJourney,
)
from app.modules.journey_sessions.state_machine import (
    InvalidTransition,
    next_status,
    status_for_step,
)
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


# ---------------------------------------------------------------------------
# Active journey sessions (Phase 6).
# ---------------------------------------------------------------------------


def _session_payload(row: JourneySession) -> dict[str, Any]:
    """The "Do this now" payload: current step, next step, progress."""
    steps = list(row.plan_snapshot.get("steps", []))
    index = row.current_step_index
    preferences = dict(row.preferences)
    return {
        "session_id": str(row.id),
        "journey_id": str(row.journey_id),
        "option_id": row.option_id,
        "status": row.status,
        "dataset_version": row.dataset_version_label,
        "language": str(preferences.get("language", "en")),
        "availability_scope": "network_feasible_not_live_confirmed",
        "progress": {"current_step": index, "step_count": len(steps)},
        # Current action + next action (plan item 2: "Do this now").
        "current_step": steps[index] if index < len(steps) else None,
        "next_step": steps[index + 1] if index + 1 < len(steps) else None,
    }


async def start_session(
    session: AsyncSession, journey_id: uuid.UUID, option_id: str
) -> dict[str, Any] | None:
    """Start an active session from a **saved** plan option (grounded only).

    Returns None when the saved journey or the option inside it does not
    exist. The session snapshots that exact option; nothing is accepted from
    the client that the server did not generate itself.
    """
    journey = await session.get(SavedJourney, journey_id)
    if journey is None:
        return None
    options = list(dict(journey.response).get("options", []))
    option = next((o for o in options if str(o.get("id")) == option_id), None)
    if option is None:
        return None

    row = JourneySession(
        journey_id=journey.id,
        option_id=option_id,
        dataset_version_label=journey.dataset_version_label,
        origin=dict(journey.origin),
        destination=dict(journey.destination),
        preferences=dict(journey.preferences),
        plan_snapshot=option,
        status=status_for_step(list(option.get("steps", [])), 0),
        current_step_index=0,
    )
    session.add(row)
    await session.flush()
    session.add(JourneyEvent(session_id=row.id, event_type="started", step_index=0))
    await session.flush()
    return _session_payload(row)


async def get_journey_session(
    session: AsyncSession, session_id: uuid.UUID
) -> dict[str, Any] | None:
    """Retrieve current session state (restore after restart/background)."""
    row = await session.get(JourneySession, session_id)
    return None if row is None else _session_payload(row)


async def apply_session_event(
    session: AsyncSession,
    session_id: uuid.UUID,
    event_type: str,
    step_index: int | None,
    note: str | None,
) -> dict[str, Any] | None:
    """Apply one manual progress event (caller commits).

    Raises `InvalidTransition` for events the state machine rejects — the API
    layer maps that to 409 so the client learns the rule, not just a failure.
    """
    # FOR UPDATE: concurrent duplicate events (two travellers' devices, or a
    # retried request racing a terminal transition) must serialize — the
    # second one must see the already-applied state and be refused (409),
    # never silently overwrite it.
    row = await session.get(JourneySession, session_id, with_for_update=True)
    if row is None:
        return None

    steps = list(row.plan_snapshot.get("steps", []))
    index = row.current_step_index
    if event_type == "step_advanced":
        if step_index is None or not 0 <= step_index < len(steps):
            raise InvalidTransition("step_advanced requires a step index inside the plan")
        index = step_index
    elif event_type == "resumed":
        index = row.current_step_index

    new_status = next_status(row.status, event_type, steps, index)
    row.status = new_status
    row.current_step_index = index
    session.add(
        JourneyEvent(session_id=row.id, event_type=event_type, step_index=step_index, note=note)
    )
    await session.flush()
    return _session_payload(row)


async def replan_session(
    session: AsyncSession,
    session_id: uuid.UUID,
    walking_router: WalkingRouter,
    origin_override: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Re-plan the session against the current active dataset (caller commits).

    Optional `origin_override` supports missed-stop recovery ("I am now at
    stop X"). Progress resets honestly when a new plan is found; when nothing
    connects, the session is left untouched and the no_route plan + notes are
    returned (`replanned: false`) — never a fabricated replacement.
    """
    row = await session.get(JourneySession, session_id, with_for_update=True)
    if row is None:
        return None
    if row.status in ("completed", "cancelled"):
        raise InvalidTransition(f"cannot replan a {row.status} session")

    preferences = dict(row.preferences)
    origin_payload = dict(origin_override) if origin_override else dict(row.origin)
    network = await load_network(session)
    planner = JourneyPlanner(network, walking_router)
    result = await planner.plan(
        _endpoint_from_payload(origin_payload),
        _endpoint_from_payload(dict(row.destination)),
        PlanningConstraints(
            allowed_modes=frozenset(preferences.get("allowed_modes", ["bus"])) | {"walk"},
            max_walking_m=float(preferences.get("max_walking_m", 1500.0)),
            max_transfers=int(preferences.get("max_transfers", 1)),
            require_verified_transfers=bool(preferences.get("require_verified_transfers", False)),
        ),
        priority=str(preferences.get("priority", "fastest")),
    )

    plan_payload = serialize_result(
        result, network=network, language=str(preferences.get("language", "en"))
    )
    plan_payload["language"] = str(preferences.get("language", "en"))
    if result.status != "ok":
        # No replacement exists — the session keeps its current plan and the
        # caller sees the honest reasons.
        plan_payload["replanned"] = False
        plan_payload["session_id"] = str(row.id)
        return plan_payload

    previous_version = row.dataset_version_label
    new_option = plan_payload["options"][0]
    row.plan_snapshot = new_option
    row.option_id = str(new_option["id"])
    row.dataset_version_label = result.version_label
    row.origin = origin_payload
    row.current_step_index = 0
    row.status = status_for_step(list(new_option.get("steps", [])), 0)
    session.add(
        JourneyEvent(
            session_id=row.id,
            event_type="replanned",
            step_index=0,
            note=f"re-planned against {result.version_label}; progress reset",
        )
    )
    await session.flush()
    payload = _session_payload(row)
    payload["replanned"] = True
    payload["previous_dataset_version"] = previous_version
    return payload
