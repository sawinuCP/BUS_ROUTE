"""Transport report model (Phase 7, plan items 4, 7 and 8)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import TIMESTAMP

from app.platform.db import Base, Timestamped, UuidPk

REPORT_CATEGORIES = (
    "wrong_stop",
    "route_variant",
    "direction",
    "transfer_path",
    "landmark_name",
    "fare",
    "access_attribute",
    "outdated_data",
    "other",
)

REPORT_STATUSES = ("submitted", "under_review", "accepted", "rejected", "needs_info")


class TransportReport(Base, UuidPk, Timestamped):
    """One traveller-reported data issue (append-only; moderation adds a trail).

    Idempotent per `client_key`: an offline-queued retry re-submits the same
    key and must never create a second row. **No location data is stored** —
    the subject is a canonical entity, never coordinates.
    """

    __tablename__ = "transport_reports"

    category: Mapped[str] = mapped_column(String(30), nullable=False)
    subject_type: Mapped[str | None] = mapped_column(String(20))
    subject_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    description: Mapped[str] = mapped_column(Text, nullable=False)
    consent: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    client_key: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="submitted")
    dataset_version_label: Mapped[str | None] = mapped_column(String(100))
    reviewed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    review_note: Mapped[str | None] = mapped_column(Text)
    candidate_version_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("dataset_versions.id", ondelete="SET NULL")
    )
