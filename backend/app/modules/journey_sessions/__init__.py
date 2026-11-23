"""Saved journey persistence (canonical module: `journey_sessions`).

Phase 4 completion: a planned journey can be saved with its exact request and
response snapshot, retrieved, and refreshed against the current active dataset
version. Anonymous by design for now (product rule: no account required for
basic planning); user association arrives with the Phase 6 account work.

This module owns journey state persistence. Plan *generation* lives in
`app.modules.planner`; this module calls it only for refresh.
"""

from __future__ import annotations

from app.modules.journey_sessions.models import (
    JourneyEvent,
    JourneySession,
    SavedJourney,
)
from app.modules.journey_sessions.service import (
    apply_session_event,
    delete_saved_journey,
    get_journey_session,
    get_saved_journey,
    refresh_saved_journey,
    replan_session,
    save_journey,
    start_session,
)
from app.modules.journey_sessions.state_machine import (
    InvalidTransition,
    next_status,
    status_for_step,
)

__all__ = [
    "InvalidTransition",
    "JourneyEvent",
    "JourneySession",
    "SavedJourney",
    "apply_session_event",
    "delete_saved_journey",
    "get_journey_session",
    "get_saved_journey",
    "next_status",
    "refresh_saved_journey",
    "replan_session",
    "save_journey",
    "start_session",
    "status_for_step",
]
