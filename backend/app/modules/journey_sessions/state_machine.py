"""Journey-session state machine (Phase 6 work item 1) — pure domain code.

States follow the implementation plan: the execution states are **derived
from the current step's action** (overview → active_walk / active_ride /
transfer_walk / final_walk), with the explicit overrides `paused`,
`needs_confirmation`, `completed` and `cancelled`.

Design rules (plan §Phase 6):
- Manual progress is authoritative: every state change comes from an explicit
  traveller action or the server; there is no GPS-driven transition here at
  all (GPS is assistive-only and never stored by the backend).
- Terminal states are final: `completed` and `cancelled` accept no further
  events (a new session/replan is the way forward).
- `paused` accepts only resume/complete/cancel — progress cannot advance
  while paused.
- All transition rules live in one table so invalid transitions are a single
  testable property, not scattered conditionals.
"""

from __future__ import annotations

from typing import Any

# Stable execution states (subset stored on the session row).
STATUS_OVERVIEW = "overview"
STATUS_ACTIVE_WALK = "active_walk"
STATUS_ACTIVE_RIDE = "active_ride"
STATUS_TRANSFER_WALK = "transfer_walk"
STATUS_FINAL_WALK = "final_walk"
STATUS_NEEDS_CONFIRMATION = "needs_confirmation"
STATUS_PAUSED = "paused"
STATUS_REPLANNING = "replanning"
STATUS_COMPLETED = "completed"
STATUS_CANCELLED = "cancelled"

# Event types (mirror the journey_events check constraint).
EVENT_STARTED = "started"
EVENT_STEP_ADVANCED = "step_advanced"
EVENT_PAUSED = "paused"
EVENT_RESUMED = "resumed"
EVENT_COMPLETED = "completed"
EVENT_CANCELLED = "cancelled"
EVENT_REPLANNED = "replanned"

EVENT_TYPES = (
    EVENT_STARTED,
    EVENT_STEP_ADVANCED,
    EVENT_PAUSED,
    EVENT_RESUMED,
    EVENT_COMPLETED,
    EVENT_CANCELLED,
    EVENT_REPLANNED,
)

# Step action → execution state (routing-engine doc §7 action codes).
_ACTION_STATE: dict[str, str] = {
    "WALK_TO_STOP": STATUS_ACTIVE_WALK,
    "BOARD_TRANSIT": STATUS_ACTIVE_RIDE,
    "RIDE_TRANSIT": STATUS_ACTIVE_RIDE,
    "ALIGHT_TRANSIT": STATUS_ACTIVE_RIDE,
    "WALK_TRANSFER": STATUS_TRANSFER_WALK,
    "WALK_TO_DESTINATION": STATUS_FINAL_WALK,
}

# current status → allowed events → resulting status.
_TRANSITIONS: dict[str, dict[str, str]] = {
    STATUS_OVERVIEW: {
        EVENT_STEP_ADVANCED: "derived",
        EVENT_PAUSED: STATUS_PAUSED,
        EVENT_COMPLETED: STATUS_COMPLETED,
        EVENT_CANCELLED: STATUS_CANCELLED,
    },
    STATUS_ACTIVE_WALK: {
        EVENT_STEP_ADVANCED: "derived",
        EVENT_PAUSED: STATUS_PAUSED,
        EVENT_COMPLETED: STATUS_COMPLETED,
        EVENT_CANCELLED: STATUS_CANCELLED,
    },
    STATUS_ACTIVE_RIDE: {
        EVENT_STEP_ADVANCED: "derived",
        EVENT_PAUSED: STATUS_PAUSED,
        EVENT_COMPLETED: STATUS_COMPLETED,
        EVENT_CANCELLED: STATUS_CANCELLED,
    },
    STATUS_TRANSFER_WALK: {
        EVENT_STEP_ADVANCED: "derived",
        EVENT_PAUSED: STATUS_PAUSED,
        EVENT_COMPLETED: STATUS_COMPLETED,
        EVENT_CANCELLED: STATUS_CANCELLED,
    },
    STATUS_FINAL_WALK: {
        EVENT_STEP_ADVANCED: "derived",
        EVENT_PAUSED: STATUS_PAUSED,
        EVENT_COMPLETED: STATUS_COMPLETED,
        EVENT_CANCELLED: STATUS_CANCELLED,
    },
    STATUS_NEEDS_CONFIRMATION: {
        EVENT_STEP_ADVANCED: "derived",
        EVENT_PAUSED: STATUS_PAUSED,
        EVENT_COMPLETED: STATUS_COMPLETED,
        EVENT_CANCELLED: STATUS_CANCELLED,
    },
    STATUS_PAUSED: {
        EVENT_RESUMED: "derived",
        EVENT_COMPLETED: STATUS_COMPLETED,
        EVENT_CANCELLED: STATUS_CANCELLED,
    },
    STATUS_COMPLETED: {},
    STATUS_CANCELLED: {},
}


class InvalidTransition(Exception):
    """Raised when an event is not allowed from the current state."""


def status_for_step(steps: list[dict[str, Any]], step_index: int) -> str:
    """Derive the execution state from the action of the current step.

    Falls back to `overview` when the step list is exhausted (completion is an
    explicit traveller event, never an implicit one).
    """
    if 0 <= step_index < len(steps):
        action = str(steps[step_index].get("action", ""))
        return _ACTION_STATE.get(action, STATUS_OVERVIEW)
    return STATUS_OVERVIEW


def next_status(current: str, event_type: str, steps: list[dict[str, Any]], step_index: int) -> str:
    """Compute the status after an event; raises `InvalidTransition` if illegal.

    `derived` results come from the action of the step at `step_index`.
    """
    allowed = _TRANSITIONS.get(current)
    if allowed is None:
        raise InvalidTransition(f"unknown session state: {current}")
    target = allowed.get(event_type)
    if target is None:
        raise InvalidTransition(f"event '{event_type}' is not allowed from '{current}'")
    if target == "derived":
        return status_for_step(steps, step_index)
    return target
