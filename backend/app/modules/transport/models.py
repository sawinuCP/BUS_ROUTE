"""Canonical transport-network models (canonical module: `transport`).

Design per docs/architecture/08_DATA_MODEL.md §1 and the implementation plan
§5.1. Route variants are first-class (`route_patterns`); ordered stop calls are
unique per (pattern, sequence); transfers are explicit, verified connections
between access points — never proximity-derived (architecture rules / ADR-0002).
"""

from __future__ import annotations

import uuid
from datetime import date

from geoalchemy2 import Geography
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.platform.db import Base, Timestamped, UuidPk


class TransportAgency(Base, UuidPk, Timestamped):
    """An operator (SLTB, private operator, railway, unknown)."""

    __tablename__ = "transport_agencies"
    __table_args__ = (
        CheckConstraint(
            "operator_type IN ('public','private','rail','unknown')",
            name="agency_operator_type",
        ),
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    operator_type: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'unknown'")
    )
    website: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)


class TransportRoute(Base, UuidPk, Timestamped):
    """Public-facing route identity (route number/label), not one unique path."""

    __tablename__ = "transport_routes"
    __table_args__ = (
        CheckConstraint("mode IN ('bus','rail')", name="route_mode"),
        CheckConstraint("status IN ('draft','active','inactive')", name="route_status"),
    )

    agency_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("transport_agencies.id", ondelete="SET NULL"), index=True
    )
    route_code: Mapped[str] = mapped_column(String(50), nullable=False)  # public ref/number
    route_name: Mapped[str | None] = mapped_column(String(300))
    mode: Mapped[str] = mapped_column(String(10), nullable=False, server_default=text("'bus'"))
    status: Mapped[str] = mapped_column(String(10), nullable=False, server_default=text("'draft'"))
    notes: Mapped[str | None] = mapped_column(Text)


Index("ix_transport_routes_code", TransportRoute.route_code)


class RouteShape(Base, UuidPk, Timestamped):
    """Route pattern geometry (MULTILINESTRING, WGS84). Unknown facts stay null."""

    __tablename__ = "route_shapes"
    __table_args__ = (
        CheckConstraint(
            "verification_status IN ('unverified','reported','verified')",
            name="route_shape_verification",
        ),
    )

    geometry = mapped_column(
        Geography(geometry_type="MULTILINESTRING", srid=4326, spatial_index=False), nullable=True
    )
    data_source_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("data_sources.id", ondelete="SET NULL")
    )
    verification_status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'unverified'")
    )


Index(
    "ix_route_shapes_geometry",
    RouteShape.geometry,
    postgresql_using="gist",
)


class Stop(Base, UuidPk, Timestamped):
    """A physical stop/station; coordinates may be unknown until verified."""

    __tablename__ = "stops"
    __table_args__ = (
        CheckConstraint("mode IN ('bus','rail')", name="stop_mode"),
        CheckConstraint(
            "stop_type IN ('roadside','bus_stand','terminal','bay','platform','station','other')",
            name="stop_type",
        ),
        CheckConstraint(
            "verification_status IN ('unverified','reported','verified')",
            name="stop_verification",
        ),
    )

    name: Mapped[str] = mapped_column(String(300), nullable=False)
    mode: Mapped[str] = mapped_column(String(10), nullable=False, server_default=text("'bus'"))
    location = mapped_column(
        Geography(geometry_type="POINT", srid=4326, spatial_index=False), nullable=True
    )
    locality_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("localities.id", ondelete="SET NULL"), index=True
    )
    stop_type: Mapped[str | None] = mapped_column(String(20))
    parent_station_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("stops.id", ondelete="SET NULL")
    )
    verification_status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'unverified'")
    )


Index("ix_stops_location", Stop.location, postgresql_using="gist")


class StopAccessPoint(Base, UuidPk, Timestamped):
    """A physical boarding/alighting point: roadside side, bay, platform, stand, entrance."""

    __tablename__ = "stop_access_points"
    __table_args__ = (
        CheckConstraint(
            "access_type IN ('roadside','bay','platform','entrance','stand','other')",
            name="access_point_type",
        ),
        CheckConstraint(
            "verification_status IN ('unverified','reported','verified')",
            name="access_point_verification",
        ),
    )

    stop_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("stops.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str | None] = mapped_column(String(300))
    access_type: Mapped[str | None] = mapped_column(String(20))
    location = mapped_column(
        Geography(geometry_type="POINT", srid=4326, spatial_index=False), nullable=True
    )
    side_or_platform: Mapped[str | None] = mapped_column(String(100))
    access_notes: Mapped[str | None] = mapped_column(Text)
    verification_status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'unverified'")
    )


Index("ix_stop_access_points_location", StopAccessPoint.location, postgresql_using="gist")


class RoutePattern(Base, UuidPk, Timestamped):
    """A specific ordered variant and direction of a route (never merged by route number)."""

    __tablename__ = "route_patterns"
    __table_args__ = (
        CheckConstraint("direction_id IN (0, 1)", name="pattern_direction"),
        CheckConstraint(
            "verification_status IN ('unverified','reported','verified')",
            name="pattern_verification",
        ),
        CheckConstraint(
            "valid_from IS NULL OR valid_to IS NULL OR valid_from <= valid_to",
            name="pattern_validity_range",
        ),
    )

    route_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("transport_routes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    pattern_code: Mapped[str | None] = mapped_column(String(100))
    direction_id: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, server_default=text("0")
    )
    origin_label: Mapped[str | None] = mapped_column(String(300))
    destination_label: Mapped[str | None] = mapped_column(String(300))
    variant_description: Mapped[str | None] = mapped_column(Text)
    service_type: Mapped[str | None] = mapped_column(String(50))  # ordinary/express/semi-luxury/ac
    shape_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("route_shapes.id", ondelete="SET NULL")
    )
    verification_status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'unverified'")
    )
    valid_from: Mapped[date | None] = mapped_column(Date)
    valid_to: Mapped[date | None] = mapped_column(Date)


Index(
    "uq_route_patterns_route_code",
    RoutePattern.route_id,
    RoutePattern.pattern_code,
    unique=True,
    postgresql_where=text("pattern_code IS NOT NULL"),
)


class RoutePatternStop(Base, UuidPk):
    """An ordered stop call of a pattern; uniqueness (pattern, sequence) is the core invariant."""

    __tablename__ = "route_pattern_stops"
    __table_args__ = (CheckConstraint("sequence >= 1", name="pattern_stop_sequence_positive"),)

    pattern_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("route_patterns.id", ondelete="CASCADE"), nullable=False
    )
    stop_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("stops.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    boarding_allowed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )
    alighting_allowed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )
    source_record_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("source_records.id", ondelete="SET NULL")
    )


Index(
    "uq_route_pattern_stops_pattern_seq",
    RoutePatternStop.pattern_id,
    RoutePatternStop.sequence,
    unique=True,
)
Index(
    "ix_route_pattern_stops_pattern_order", RoutePatternStop.pattern_id, RoutePatternStop.sequence
)


class TransferConnection(Base, UuidPk, Timestamped):
    """An explicit, verified walking connection between two access points.

    Proximity alone never creates one: candidate generation may propose, but the
    canonical row exists only after review/verification (architecture rules).
    """

    __tablename__ = "transfer_connections"
    __table_args__ = (
        CheckConstraint(
            "from_access_point_id <> to_access_point_id", name="transfer_distinct_endpoints"
        ),
        CheckConstraint(
            "walk_distance_m IS NULL OR walk_distance_m > 0", name="transfer_distance_positive"
        ),
        CheckConstraint(
            "verification_status IN ('unverified','reported','verified')",
            name="transfer_verification",
        ),
        CheckConstraint(
            "valid_from IS NULL OR valid_to IS NULL OR valid_from <= valid_to",
            name="transfer_validity_range",
        ),
    )

    from_access_point_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("stop_access_points.id", ondelete="CASCADE"), nullable=False, index=True
    )
    to_access_point_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("stop_access_points.id", ondelete="CASCADE"), nullable=False, index=True
    )
    walk_distance_m: Mapped[int | None]
    estimated_walk_seconds: Mapped[int | None]
    walk_geometry = mapped_column(
        Geography(geometry_type="MULTILINESTRING", srid=4326, spatial_index=False), nullable=True
    )
    accessibility_attributes: Mapped[dict | None] = mapped_column(JSONB)
    data_source_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("data_sources.id", ondelete="SET NULL")
    )
    verification_status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'unverified'")
    )
    valid_from: Mapped[date | None] = mapped_column(Date)
    valid_to: Mapped[date | None] = mapped_column(Date)


Index("ix_transfer_connections_geometry", TransferConnection.walk_geometry, postgresql_using="gist")


class FareRule(Base, UuidPk, Timestamped):
    """Effective-dated fare rule. Disabled in the MVP until rights/applicability verified."""

    __tablename__ = "fare_rules"
    __table_args__ = (
        CheckConstraint("amount IS NULL OR amount >= 0", name="fare_amount_non_negative"),
        CheckConstraint(
            "route_id IS NOT NULL OR pattern_id IS NOT NULL OR mode IS NOT NULL "
            "OR origin_stop_id IS NOT NULL",
            name="fare_has_scope",
        ),
        CheckConstraint(
            "effective_from IS NULL OR effective_to IS NULL OR effective_from <= effective_to",
            name="fare_validity_range",
        ),
        CheckConstraint(
            "verification_status IN ('unverified','reported','verified')",
            name="fare_verification",
        ),
    )

    route_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("transport_routes.id", ondelete="CASCADE"), index=True
    )
    pattern_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("route_patterns.id", ondelete="CASCADE"), index=True
    )
    mode: Mapped[str | None] = mapped_column(String(10))
    fare_class: Mapped[str | None] = mapped_column(String(50))  # ordinary/semi-luxury/ac/...
    origin_stop_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("stops.id", ondelete="CASCADE"), index=True
    )
    destination_stop_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("stops.id", ondelete="CASCADE"), index=True
    )
    amount: Mapped[float | None] = mapped_column(Numeric(10, 2))
    currency: Mapped[str] = mapped_column(String(3), nullable=False, server_default=text("'LKR'"))
    effective_from: Mapped[date | None] = mapped_column(Date)
    effective_to: Mapped[date | None] = mapped_column(Date)
    data_source_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("data_sources.id", ondelete="SET NULL")
    )
    verification_status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'unverified'")
    )
