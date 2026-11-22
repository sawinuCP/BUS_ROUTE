"""Itinerary rendering (canonical module: `itineraries`).

Phase 5: converts planner itineraries into a normalized journey response —
typed instruction steps with stable action codes, deterministic English
templates backed strictly by structured facts, and confidence summaries.
si/ta rendering arrives after native review (D-7); non-English requests fall
back to English with an explicit limitation note.
"""

from __future__ import annotations

from app.modules.itineraries.instructions import (
    ALIGHT_TRANSIT,
    BOARD_TRANSIT,
    RIDE_TRANSIT,
    SUPPORTED_LANGUAGES,
    WALK_TO_DESTINATION,
    WALK_TO_STOP,
    WALK_TRANSFER,
    InstructionStep,
    build_steps,
)

__all__ = [
    "ALIGHT_TRANSIT",
    "BOARD_TRANSIT",
    "RIDE_TRANSIT",
    "SUPPORTED_LANGUAGES",
    "WALK_TO_DESTINATION",
    "WALK_TO_STOP",
    "WALK_TRANSFER",
    "InstructionStep",
    "build_steps",
]
