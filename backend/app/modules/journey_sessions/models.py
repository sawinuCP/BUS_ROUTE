"""Saved-journey model (Phase 4 completion; data model doc §6)."""

from __future__ import annotations

from typing import Any

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.platform.db import Base, Timestamped, UuidPk


class SavedJourney(Base, UuidPk, Timestamped):
    """A saved plan: the exact request plus the response snapshot.

    `response` is the full serialized plan payload (status, dataset_version,
    options, notes) as returned at save time; `refresh` replaces it with a
    fresh plan against the current active dataset version.
    """

    __tablename__ = "saved_journeys"

    origin: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    destination: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    preferences: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    dataset_version_label: Mapped[str] = mapped_column(String(100), nullable=False)
    response: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)


class JourneySession(Base, UuidPk, Timestamped):
    """One traveller following one option of one saved plan (Phase 6).

    `plan_snapshot` holds the exact option payload (steps, summary, warnings)
    the session was started from, plus the dataset version it was grounded in.
    No location data is ever stored here (data model doc §6).
    """

    __tablename__ = "journey_sessions"

    journey_id: Mapped[object] = mapped_column(
        ForeignKey("saved_journeys.id", ondelete="CASCADE"), nullable=False, index=True
    )
    option_id: Mapped[str] = mapped_column(String(50), nullable=False)
    dataset_version_label: Mapped[str] = mapped_column(String(100), nullable=False)
    origin: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    destination: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    preferences: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    plan_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="overview")
    current_step_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class JourneyEvent(Base, UuidPk):
    """Append-only session event trail (no coordinates — data model §6)."""

    __tablename__ = "journey_events"

    session_id: Mapped[object] = mapped_column(
        ForeignKey("journey_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    event_type: Mapped[str] = mapped_column(String(20), nullable=False)
    step_index: Mapped[int | None] = mapped_column(Integer)
    note: Mapped[str | None] = mapped_column(Text)
