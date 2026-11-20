"""Canonical place/alias models (canonical module: `places`).

Multilingual identity per architecture rules: canonical names are stored on the
entity; `entity_aliases` carries Sinhala/Tamil/English names, transliterations
and colloquial variants with language tags and provenance (final 08 §2, final 12 §6).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from geoalchemy2 import Geography
from sqlalchemy import (
    TIMESTAMP,
    CheckConstraint,
    ForeignKey,
    Index,
    String,
    Text,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.platform.db import Base, Timestamped, UuidPk


class Locality(Base, UuidPk, Timestamped):
    """Administrative/local area used for disambiguation (town, suburb, district)."""

    __tablename__ = "localities"
    __table_args__ = (
        CheckConstraint(
            "locality_type IN ('city','town','suburb','district','area','other')",
            name="locality_type",
        ),
    )

    name: Mapped[str] = mapped_column(String(300), nullable=False)
    locality_type: Mapped[str | None] = mapped_column(String(20))
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("localities.id", ondelete="SET NULL")
    )
    location = mapped_column(
        Geography(geometry_type="POINT", srid=4326, spatial_index=False), nullable=True
    )


class Place(Base, UuidPk, Timestamped):
    """A canonical public destination/landmark (hospital, campus, terminal, site)."""

    __tablename__ = "places"
    __table_args__ = (
        CheckConstraint(
            "verification_status IN ('unverified','reported','verified')",
            name="place_verification",
        ),
    )

    name: Mapped[str] = mapped_column(String(300), nullable=False)
    category: Mapped[str | None] = mapped_column(String(50))
    locality_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("localities.id", ondelete="SET NULL"), index=True
    )
    location = mapped_column(
        Geography(geometry_type="POINT", srid=4326, spatial_index=False), nullable=True
    )
    access_notes: Mapped[str | None] = mapped_column(Text)
    verification_status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'unverified'")
    )


class PlaceAccessPoint(Base, UuidPk, Timestamped):
    """A physical public entrance/access point of a place (never just the centroid)."""

    __tablename__ = "place_access_points"
    __table_args__ = (
        CheckConstraint(
            "access_type IN ('entrance','gate','pickup_dropoff','parking','other')",
            name="place_access_type",
        ),
        CheckConstraint(
            "verification_status IN ('unverified','reported','verified')",
            name="place_access_verification",
        ),
    )

    place_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("places.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str | None] = mapped_column(String(300))
    access_type: Mapped[str | None] = mapped_column(String(20))
    location = mapped_column(
        Geography(geometry_type="POINT", srid=4326, spatial_index=False), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(Text)
    verification_status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'unverified'")
    )


class EntityAlias(Base, UuidPk):
    """A searchable alias (name/variant) for a canonical entity, language-tagged."""

    __tablename__ = "entity_aliases"
    __table_args__ = (
        CheckConstraint(
            "entity_type IN ('place','stop','route','route_pattern','locality')",
            name="alias_entity_type",
        ),
        CheckConstraint("language IN ('en','si','ta')", name="alias_language"),
    )

    entity_type: Mapped[str] = mapped_column(String(30), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    language: Mapped[str] = mapped_column(String(2), nullable=False)
    alias: Mapped[str] = mapped_column(Text, nullable=False)
    transliteration: Mapped[str | None] = mapped_column(Text)
    is_colloquial: Mapped[bool | None]
    data_source_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("data_sources.id", ondelete="SET NULL")
    )
    confidence: Mapped[str | None] = mapped_column(String(20), server_default=text("'unverified'"))
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()"), nullable=False
    )


Index("ix_entity_aliases_entity", EntityAlias.entity_type, EntityAlias.entity_id)
Index("ix_entity_aliases_alias", EntityAlias.alias)
