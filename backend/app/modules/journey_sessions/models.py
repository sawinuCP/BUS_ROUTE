"""Saved-journey model (Phase 4 completion; data model doc §6)."""

from __future__ import annotations

from typing import Any

from sqlalchemy import String, Text
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
