"""Data-quality models (canonical module: `data_quality`).

Verification is fact-level and auditable (architecture rules): a record states
who verified what, how, when, with what evidence. Change audit records the
before/after of material edits for dataset review and rollback context.
User reports and moderation queues are Phase 7 entities and are deliberately
not part of this migration.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    TIMESTAMP,
    CheckConstraint,
    ForeignKey,
    Index,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.platform.db import Base, UuidPk


class VerificationRecord(Base, UuidPk):
    """One verification event for one entity fact (method, reviewer, evidence, result)."""

    __tablename__ = "verification_records"
    __table_args__ = (
        CheckConstraint(
            "method IN ('field_check','official_source','source_crosscheck',"
            "'report_review','other')",
            name="verification_method",
        ),
        CheckConstraint(
            "result IN ('verified','rejected','uncertain')",
            name="verification_result",
        ),
        CheckConstraint(
            "entity_type IN ('agency','route','route_pattern','route_pattern_stop','stop',"
            "'stop_access_point','route_shape','transfer_connection','place',"
            "'place_access_point','locality','entity_alias','fare_rule')",
            name="verification_entity_type",
        ),
    )

    entity_type: Mapped[str] = mapped_column(String(40), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    method: Mapped[str] = mapped_column(String(30), nullable=False)
    reviewer: Mapped[str | None] = mapped_column(String(200))
    verified_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    result: Mapped[str] = mapped_column(String(20), nullable=False)
    evidence: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)


Index(
    "ix_verification_records_entity",
    VerificationRecord.entity_type,
    VerificationRecord.entity_id,
)


class DataChangeAudit(Base, UuidPk):
    """Before/after audit of a material change to a canonical entity."""

    __tablename__ = "data_change_audit"
    __table_args__ = (
        CheckConstraint(
            "operation IN ('create','update','deactivate','delete')", name="change_operation"
        ),
        CheckConstraint(
            "entity_type IN ('agency','route','route_pattern','route_pattern_stop','stop',"
            "'stop_access_point','route_shape','transfer_connection','place',"
            "'place_access_point','locality','entity_alias','fare_rule')",
            name="change_entity_type",
        ),
    )

    entity_type: Mapped[str] = mapped_column(String(40), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    operation: Mapped[str] = mapped_column(String(15), nullable=False)
    before_state: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    after_state: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    actor: Mapped[str | None] = mapped_column(String(200))
    reason: Mapped[str | None] = mapped_column(Text)
    dataset_version_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("dataset_versions.id", ondelete="SET NULL"), index=True
    )
    changed_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)


Index("ix_data_change_audit_entity", DataChangeAudit.entity_type, DataChangeAudit.entity_id)
