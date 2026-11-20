"""Canonical provenance and dataset-versioning models (canonical module: `data_ingestion`).

Design per docs/architecture/08_DATA_MODEL.md §4 and ADR-0006: canonical
working tables are the single source of truth; `dataset_versions` +
`dataset_version_entities` record what changed in each published network
version; `active_dataset` is the singleton pointer consumed by routing.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    TIMESTAMP,
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.platform.db import Base, Timestamped, UuidPk


class DataSource(Base, UuidPk, Timestamped):
    """A registered transport-data source (owner, licence, cadence, adapter)."""

    __tablename__ = "data_sources"

    name: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    owner: Mapped[str | None] = mapped_column(String(200))
    access_method: Mapped[str | None] = mapped_column(String(50))  # api | file | manual
    endpoint: Mapped[str | None] = mapped_column(Text)
    format: Mapped[str | None] = mapped_column(String(50))  # gtfs | osm | geojson | csv | pdf
    licence: Mapped[str | None] = mapped_column(Text)
    terms_note: Mapped[str | None] = mapped_column(Text)
    update_cadence: Mapped[str | None] = mapped_column(String(100))  # human-readable policy
    adapter_version: Mapped[str | None] = mapped_column(String(50))
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    last_fetch_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))


class SourceSnapshot(Base, UuidPk):
    """Immutable raw payload captured from a source (checksum-verified)."""

    __tablename__ = "source_snapshots"

    data_source_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("data_sources.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    fetched_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    storage_uri: Mapped[str] = mapped_column(Text, nullable=False)
    checksum_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    content_type: Mapped[str | None] = mapped_column(String(100))
    size_bytes: Mapped[int | None]
    extra_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSONB)


class SourceRecord(Base, UuidPk, Timestamped):
    """Mapping of one external record to its raw snapshot and normalised form."""

    __tablename__ = "source_records"

    data_source_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("data_sources.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    snapshot_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("source_snapshots.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    external_id: Mapped[str] = mapped_column(String(300), nullable=False)
    entity_hint: Mapped[str | None] = mapped_column(String(50))  # stop | route | pattern | place
    canonical_entity_type: Mapped[str | None] = mapped_column(String(40))
    canonical_entity_id: Mapped[uuid.UUID | None] = mapped_column()
    raw_ref: Mapped[str | None] = mapped_column(Text)  # locator inside the snapshot payload
    raw_payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    normalised: Mapped[dict[str, Any] | None] = mapped_column(JSONB)


# Idempotency contract: one external ID per source, across all snapshots.
Index(
    "uq_source_records_source_external",
    SourceRecord.data_source_id,
    SourceRecord.external_id,
    unique=True,
)


class SyncRun(Base, UuidPk, Timestamped):
    """One ingestion run of one source (idempotency is a run-level contract)."""

    __tablename__ = "sync_runs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('started','succeeded','failed','quarantined')",
            name="sync_run_status",
        ),
    )

    data_source_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("data_sources.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    started_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'started'")
    )
    snapshot_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("source_snapshots.id", ondelete="SET NULL")
    )
    parser_version: Mapped[str | None] = mapped_column(String(50))
    records_in: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    records_added: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    records_updated: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    records_failed: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    error: Mapped[str | None] = mapped_column(Text)


class DatasetVersion(Base, UuidPk, Timestamped):
    """A published (or candidate/rejected) version of the canonical network."""

    __tablename__ = "dataset_versions"
    __table_args__ = (
        CheckConstraint(
            "status IN ('candidate','published','rejected','superseded')",
            name="dataset_version_status",
        ),
    )

    version_label: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'candidate'")
    )
    published_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    validation_summary: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    notes: Mapped[str | None] = mapped_column(Text)


class DatasetVersionEntity(Base, UuidPk):
    """Entity membership/diff of one dataset version (what changed and when)."""

    __tablename__ = "dataset_version_entities"
    __table_args__ = (
        CheckConstraint(
            "entity_type IN ('agency','route','route_pattern','stop','stop_access_point',"
            "'route_shape','transfer_connection','place','place_access_point','locality',"
            "'entity_alias','fare_rule')",
            name="dve_entity_type",
        ),
        CheckConstraint("operation IN ('added','updated','removed')", name="dve_operation"),
    )

    dataset_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("dataset_versions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    entity_type: Mapped[str] = mapped_column(String(40), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    operation: Mapped[str] = mapped_column(String(10), nullable=False)
    changed_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)


Index("ix_dve_entity", DatasetVersionEntity.entity_type, DatasetVersionEntity.entity_id)


class ActiveDataset(Base):
    """Singleton pointer to the currently published dataset version (ADR-0006)."""

    __tablename__ = "active_dataset"
    __table_args__ = (CheckConstraint("id = 1", name="active_dataset_singleton"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, server_default=text("1"))
    dataset_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("dataset_versions.id", ondelete="RESTRICT"), unique=True, nullable=False
    )
    activated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
