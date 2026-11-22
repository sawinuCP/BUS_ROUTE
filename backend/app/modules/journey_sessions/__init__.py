"""Saved journey persistence (canonical module: `journey_sessions`).

Phase 4 completion: a planned journey can be saved with its exact request and
response snapshot, retrieved, and refreshed against the current active dataset
version. Anonymous by design for now (product rule: no account required for
basic planning); user association arrives with the Phase 6 account work.

This module owns journey state persistence. Plan *generation* lives in
`app.modules.planner`; this module calls it only for refresh.
"""

from __future__ import annotations

from app.modules.journey_sessions.models import SavedJourney
from app.modules.journey_sessions.service import (
    get_saved_journey,
    refresh_saved_journey,
    save_journey,
)

__all__ = ["SavedJourney", "get_saved_journey", "refresh_saved_journey", "save_journey"]
