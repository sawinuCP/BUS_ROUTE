"""Unit: journey-session state machine (Phase 6 work item 1).

Covers derived execution states, explicit overrides, and — critically — the
invalid transitions: nothing may advance a completed/cancelled session, and
progress cannot advance while paused. Completion is always an explicit
traveller event, never an implicit side effect.
"""

from __future__ import annotations

import pytest

from app.modules.journey_sessions.state_machine import (
    EVENT_CANCELLED,
    EVENT_COMPLETED,
    EVENT_PAUSED,
    EVENT_RESUMED,
    EVENT_STEP_ADVANCED,
    STATUS_ACTIVE_RIDE,
    STATUS_ACTIVE_WALK,
    STATUS_CANCELLED,
    STATUS_COMPLETED,
    STATUS_FINAL_WALK,
    STATUS_OVERVIEW,
    STATUS_PAUSED,
    STATUS_TRANSFER_WALK,
    InvalidTransition,
    next_status,
    status_for_step,
)

# A representative option's ordered steps (same actions the backend emits).
_STEPS = [
    {"action": "WALK_TO_STOP", "text": "Walk 240 m to A."},
    {"action": "BOARD_TRANSIT", "text": "Board route 101 at A."},
    {"action": "RIDE_TRANSIT", "text": "Ride 3 stops to B."},
    {"action": "ALIGHT_TRANSIT", "text": "Alight at B."},
    {"action": "WALK_TRANSFER", "text": "Walk 140 m to C."},
    {"action": "BOARD_TRANSIT", "text": "Board route 145 at C."},
    {"action": "WALK_TO_DESTINATION", "text": "Walk 200 m to your destination."},
]


def test_status_is_derived_from_the_current_step_action() -> None:
    assert status_for_step(_STEPS, 0) == STATUS_ACTIVE_WALK
    assert status_for_step(_STEPS, 2) == STATUS_ACTIVE_RIDE
    assert status_for_step(_STEPS, 4) == STATUS_TRANSFER_WALK
    assert status_for_step(_STEPS, 6) == STATUS_FINAL_WALK
    # Beyond the last step: overview (completion is explicit, never implicit).
    assert status_for_step(_STEPS, 7) == STATUS_OVERVIEW
    assert status_for_step(_STEPS, -1) == STATUS_OVERVIEW


def test_step_advance_moves_through_execution_states() -> None:
    assert next_status(STATUS_OVERVIEW, EVENT_STEP_ADVANCED, _STEPS, 0) == STATUS_ACTIVE_WALK
    assert next_status(STATUS_ACTIVE_WALK, EVENT_STEP_ADVANCED, _STEPS, 2) == STATUS_ACTIVE_RIDE
    assert next_status(STATUS_ACTIVE_RIDE, EVENT_STEP_ADVANCED, _STEPS, 4) == STATUS_TRANSFER_WALK
    assert next_status(STATUS_ACTIVE_RIDE, EVENT_STEP_ADVANCED, _STEPS, 6) == STATUS_FINAL_WALK


def test_pause_and_resume_roundtrip() -> None:
    assert next_status(STATUS_ACTIVE_RIDE, EVENT_PAUSED, _STEPS, 2) == STATUS_PAUSED
    # Resume re-derives from the step where the traveller paused.
    assert next_status(STATUS_PAUSED, EVENT_RESUMED, _STEPS, 2) == STATUS_ACTIVE_RIDE


def test_completed_and_cancelled_are_terminal() -> None:
    assert next_status(STATUS_ACTIVE_WALK, EVENT_COMPLETED, _STEPS, 0) == STATUS_COMPLETED
    assert next_status(STATUS_ACTIVE_RIDE, EVENT_CANCELLED, _STEPS, 2) == STATUS_CANCELLED

    for terminal in (STATUS_COMPLETED, STATUS_CANCELLED):
        for event in (
            EVENT_STEP_ADVANCED,
            EVENT_PAUSED,
            EVENT_RESUMED,
            EVENT_COMPLETED,
            EVENT_CANCELLED,
        ):
            with pytest.raises(InvalidTransition):
                next_status(terminal, event, _STEPS, 0)


def test_progress_cannot_advance_while_paused() -> None:
    with pytest.raises(InvalidTransition):
        next_status(STATUS_PAUSED, EVENT_STEP_ADVANCED, _STEPS, 3)
    # …but pause/resume work from any execution state, including overview.
    assert next_status(STATUS_OVERVIEW, EVENT_PAUSED, _STEPS, 0) == STATUS_PAUSED


def test_unknown_state_rejected() -> None:
    with pytest.raises(InvalidTransition):
        next_status("mystery", EVENT_STEP_ADVANCED, _STEPS, 0)
