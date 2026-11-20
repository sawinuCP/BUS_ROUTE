"""Canonical transport schema (Phase 1.1).

Creates the canonical PostGIS schema per docs/architecture/08_DATA_MODEL.md,
implementation plan §5.1, and ADR-0006:
- provenance/versioning: data_sources, source_snapshots, source_records,
  sync_runs, dataset_versions, dataset_version_entities, active_dataset;
- transport network: transport_agencies, transport_routes, route_shapes,
  stops, stop_access_points, route_patterns, route_pattern_stops,
  transfer_connections, fare_rules (controlled/nullable);
- places/aliases: localities, places, place_access_points, entity_aliases;
- data quality: verification_records, data_change_audit.

Conventions: UUID PKs with gen_random_uuid(); timestamptz DEFAULT now();
explicit ck_*/fk_*/uq_*/ix_* names; GiST indexes on all geography columns;
core invariant — UNIQUE (pattern_id, sequence) on route_pattern_stops.
Reversible: downgrade drops in reverse dependency order.

Revision ID: 0002_canonical_schema
Revises: 0001_baseline
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0002_canonical_schema"
down_revision: str | None = "0001_baseline"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Extension is idempotent; also created by the container init script.
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")

    # ---- provenance & versioning (data_ingestion) -------------------------
    op.execute(
        """
        CREATE TABLE data_sources (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name VARCHAR(200) NOT NULL UNIQUE,
            owner VARCHAR(200),
            access_method VARCHAR(50),
            endpoint TEXT,
            format VARCHAR(50),
            licence TEXT,
            terms_note TEXT,
            update_cadence VARCHAR(100),
            adapter_version VARCHAR(50),
            enabled BOOLEAN NOT NULL DEFAULT true,
            last_fetch_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )

    op.execute(
        """
        CREATE TABLE source_snapshots (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            data_source_id UUID NOT NULL
                REFERENCES data_sources (id) ON DELETE RESTRICT,
            fetched_at TIMESTAMPTZ NOT NULL,
            storage_uri TEXT NOT NULL,
            checksum_sha256 VARCHAR(64) NOT NULL,
            content_type VARCHAR(100),
            size_bytes BIGINT,
            extra_metadata JSONB,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        "CREATE INDEX ix_source_snapshots_data_source_id ON source_snapshots (data_source_id)"
    )

    op.execute(
        """
        CREATE TABLE source_records (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            data_source_id UUID NOT NULL
                REFERENCES data_sources (id) ON DELETE RESTRICT,
            snapshot_id UUID NOT NULL
                REFERENCES source_snapshots (id) ON DELETE RESTRICT,
            external_id VARCHAR(300) NOT NULL,
            entity_hint VARCHAR(50),
            raw_ref TEXT,
            raw_payload JSONB,
            normalised JSONB,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX ix_source_records_data_source_id ON source_records (data_source_id)")
    op.execute("CREATE INDEX ix_source_records_snapshot_id ON source_records (snapshot_id)")
    op.execute(
        "CREATE UNIQUE INDEX uq_source_records_source_external"
        " ON source_records (data_source_id, external_id)"
    )
    op.execute(
        """
        CREATE TABLE sync_runs (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            data_source_id UUID NOT NULL
                REFERENCES data_sources (id) ON DELETE RESTRICT,
            started_at TIMESTAMPTZ NOT NULL,
            finished_at TIMESTAMPTZ,
            status VARCHAR(20) NOT NULL DEFAULT 'started'
                CHECK (status IN ('started','succeeded','failed','quarantined')),
            snapshot_id UUID
                REFERENCES source_snapshots (id) ON DELETE SET NULL,
            parser_version VARCHAR(50),
            records_in INTEGER NOT NULL DEFAULT 0,
            records_added INTEGER NOT NULL DEFAULT 0,
            records_updated INTEGER NOT NULL DEFAULT 0,
            records_failed INTEGER NOT NULL DEFAULT 0,
            error TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX ix_sync_runs_data_source_id ON sync_runs (data_source_id)")

    op.execute(
        """
        CREATE TABLE dataset_versions (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            version_label VARCHAR(100) NOT NULL UNIQUE,
            status VARCHAR(20) NOT NULL DEFAULT 'candidate'
                CHECK (status IN ('candidate','published','rejected','superseded')),
            published_at TIMESTAMPTZ,
            validation_summary JSONB,
            notes TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )

    op.execute(
        """
        CREATE TABLE dataset_version_entities (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            dataset_version_id UUID NOT NULL
                REFERENCES dataset_versions (id) ON DELETE CASCADE,
            entity_type VARCHAR(40) NOT NULL
                CHECK (entity_type IN ('agency','route','route_pattern','stop',
                    'stop_access_point','route_shape','transfer_connection',
                    'place','place_access_point','locality','entity_alias','fare_rule')),
            entity_id UUID NOT NULL,
            operation VARCHAR(10) NOT NULL
                CHECK (operation IN ('added','updated','removed')),
            changed_at TIMESTAMPTZ NOT NULL
        )
        """
    )
    op.execute(
        "CREATE INDEX ix_dataset_version_entities_dataset_version_id"
        " ON dataset_version_entities (dataset_version_id)"
    )
    op.execute("CREATE INDEX ix_dve_entity ON dataset_version_entities (entity_type, entity_id)")

    op.execute(
        """
        CREATE TABLE active_dataset (
            id INTEGER PRIMARY KEY DEFAULT 1 CHECK (id = 1),
            dataset_version_id UUID NOT NULL UNIQUE
                REFERENCES dataset_versions (id) ON DELETE RESTRICT,
            activated_at TIMESTAMPTZ NOT NULL
        )
        """
    )
    # ---- transport network (transport) ------------------------------------
    op.execute(
        """
        CREATE TABLE transport_agencies (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name VARCHAR(200) NOT NULL,
            operator_type VARCHAR(20) NOT NULL DEFAULT 'unknown'
                CHECK (operator_type IN ('public','private','rail','unknown')),
            website TEXT,
            notes TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )

    op.execute(
        """
        CREATE TABLE transport_routes (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            agency_id UUID REFERENCES transport_agencies (id) ON DELETE SET NULL,
            route_code VARCHAR(50) NOT NULL,
            route_name VARCHAR(300),
            mode VARCHAR(10) NOT NULL DEFAULT 'bus' CHECK (mode IN ('bus','rail')),
            status VARCHAR(10) NOT NULL DEFAULT 'draft'
                CHECK (status IN ('draft','active','inactive')),
            notes TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX ix_transport_routes_agency_id ON transport_routes (agency_id)")
    op.execute("CREATE INDEX ix_transport_routes_code ON transport_routes (route_code)")

    op.execute(
        """
        CREATE TABLE route_shapes (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            geometry GEOGRAPHY(MULTILINESTRING, 4326),
            data_source_id UUID REFERENCES data_sources (id) ON DELETE SET NULL,
            verification_status VARCHAR(20) NOT NULL DEFAULT 'unverified'
                CHECK (verification_status IN ('unverified','reported','verified')),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX ix_route_shapes_geometry ON route_shapes USING GIST (geometry)")

    op.execute(
        """
        CREATE TABLE localities (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name VARCHAR(300) NOT NULL,
            locality_type VARCHAR(20)
                CHECK (locality_type IN ('city','town','suburb','district','area','other')),
            parent_id UUID REFERENCES localities (id) ON DELETE SET NULL,
            location GEOGRAPHY(POINT, 4326),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX ix_localities_parent_id ON localities (parent_id)")
    op.execute("CREATE INDEX ix_localities_location ON localities USING GIST (location)")

    op.execute(
        """
        CREATE TABLE stops (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name VARCHAR(300) NOT NULL,
            mode VARCHAR(10) NOT NULL DEFAULT 'bus' CHECK (mode IN ('bus','rail')),
            location GEOGRAPHY(POINT, 4326),
            locality_id UUID REFERENCES localities (id) ON DELETE SET NULL,
            stop_type VARCHAR(20)
                CHECK (stop_type IN ('roadside','bus_stand','terminal','bay',
                    'platform','station','other')),
            parent_station_id UUID REFERENCES stops (id) ON DELETE SET NULL,
            verification_status VARCHAR(20) NOT NULL DEFAULT 'unverified'
                CHECK (verification_status IN ('unverified','reported','verified')),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX ix_stops_locality_id ON stops (locality_id)")
    op.execute("CREATE INDEX ix_stops_parent_station_id ON stops (parent_station_id)")
    op.execute("CREATE INDEX ix_stops_location ON stops USING GIST (location)")
    op.execute(
        """
        CREATE TABLE stop_access_points (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            stop_id UUID NOT NULL REFERENCES stops (id) ON DELETE CASCADE,
            name VARCHAR(300),
            access_type VARCHAR(20)
                CHECK (access_type IN ('roadside','bay','platform','entrance',
                    'stand','other')),
            location GEOGRAPHY(POINT, 4326),
            side_or_platform VARCHAR(100),
            access_notes TEXT,
            verification_status VARCHAR(20) NOT NULL DEFAULT 'unverified'
                CHECK (verification_status IN ('unverified','reported','verified')),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX ix_stop_access_points_stop_id ON stop_access_points (stop_id)")
    op.execute(
        "CREATE INDEX ix_stop_access_points_location ON stop_access_points USING GIST (location)"
    )

    op.execute(
        """
        CREATE TABLE route_patterns (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            route_id UUID NOT NULL
                REFERENCES transport_routes (id) ON DELETE CASCADE,
            pattern_code VARCHAR(100),
            direction_id SMALLINT NOT NULL DEFAULT 0 CHECK (direction_id IN (0, 1)),
            origin_label VARCHAR(300),
            destination_label VARCHAR(300),
            variant_description TEXT,
            service_type VARCHAR(50),
            shape_id UUID REFERENCES route_shapes (id) ON DELETE SET NULL,
            verification_status VARCHAR(20) NOT NULL DEFAULT 'unverified'
                CHECK (verification_status IN ('unverified','reported','verified')),
            valid_from DATE,
            valid_to DATE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT pattern_validity_range CHECK (
                valid_from IS NULL OR valid_to IS NULL OR valid_from <= valid_to
            )
        )
        """
    )
    op.execute("CREATE INDEX ix_route_patterns_route_id ON route_patterns (route_id)")
    op.execute("CREATE INDEX ix_route_patterns_shape_id ON route_patterns (shape_id)")
    op.execute(
        "CREATE UNIQUE INDEX uq_route_patterns_route_code"
        " ON route_patterns (route_id, pattern_code) WHERE pattern_code IS NOT NULL"
    )

    op.execute(
        """
        CREATE TABLE route_pattern_stops (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            pattern_id UUID NOT NULL
                REFERENCES route_patterns (id) ON DELETE CASCADE,
            stop_id UUID NOT NULL
                REFERENCES stops (id) ON DELETE RESTRICT,
            sequence INTEGER NOT NULL CHECK (sequence >= 1),
            boarding_allowed BOOLEAN NOT NULL DEFAULT true,
            alighting_allowed BOOLEAN NOT NULL DEFAULT true,
            source_record_id UUID
                REFERENCES source_records (id) ON DELETE SET NULL
        )
        """
    )
    op.execute("CREATE INDEX ix_route_pattern_stops_stop_id ON route_pattern_stops (stop_id)")
    op.execute(
        "CREATE UNIQUE INDEX uq_route_pattern_stops_pattern_seq"
        " ON route_pattern_stops (pattern_id, sequence)"
    )
    op.execute(
        "CREATE INDEX ix_route_pattern_stops_pattern_order"
        " ON route_pattern_stops (pattern_id, sequence)"
    )
    op.execute(
        """
        CREATE TABLE transfer_connections (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            from_access_point_id UUID NOT NULL
                REFERENCES stop_access_points (id) ON DELETE CASCADE,
            to_access_point_id UUID NOT NULL
                REFERENCES stop_access_points (id) ON DELETE CASCADE,
            walk_distance_m INTEGER CHECK (walk_distance_m IS NULL OR walk_distance_m > 0),
            estimated_walk_seconds INTEGER,
            walk_geometry GEOGRAPHY(MULTILINESTRING, 4326),
            accessibility_attributes JSONB,
            data_source_id UUID REFERENCES data_sources (id) ON DELETE SET NULL,
            verification_status VARCHAR(20) NOT NULL DEFAULT 'unverified'
                CHECK (verification_status IN ('unverified','reported','verified')),
            valid_from DATE,
            valid_to DATE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT transfer_distinct_endpoints
                CHECK (from_access_point_id <> to_access_point_id),
            CONSTRAINT transfer_validity_range CHECK (
                valid_from IS NULL OR valid_to IS NULL OR valid_from <= valid_to
            )
        )
        """
    )
    op.execute(
        "CREATE INDEX ix_transfer_connections_from_access_point_id"
        " ON transfer_connections (from_access_point_id)"
    )
    op.execute(
        "CREATE INDEX ix_transfer_connections_to_access_point_id"
        " ON transfer_connections (to_access_point_id)"
    )
    op.execute(
        "CREATE INDEX ix_transfer_connections_geometry"
        " ON transfer_connections USING GIST (walk_geometry)"
    )
    op.execute(
        """
        CREATE TABLE fare_rules (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            route_id UUID REFERENCES transport_routes (id) ON DELETE CASCADE,
            pattern_id UUID REFERENCES route_patterns (id) ON DELETE CASCADE,
            mode VARCHAR(10),
            fare_class VARCHAR(50),
            origin_stop_id UUID REFERENCES stops (id) ON DELETE CASCADE,
            destination_stop_id UUID REFERENCES stops (id) ON DELETE CASCADE,
            amount NUMERIC(10, 2) CHECK (amount IS NULL OR amount >= 0),
            currency VARCHAR(3) NOT NULL DEFAULT 'LKR',
            effective_from DATE,
            effective_to DATE,
            data_source_id UUID REFERENCES data_sources (id) ON DELETE SET NULL,
            verification_status VARCHAR(20) NOT NULL DEFAULT 'unverified'
                CHECK (verification_status IN ('unverified','reported','verified')),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT fare_has_scope CHECK (
                route_id IS NOT NULL OR pattern_id IS NOT NULL OR mode IS NOT NULL
                OR origin_stop_id IS NOT NULL
            ),
            CONSTRAINT fare_validity_range CHECK (
                effective_from IS NULL OR effective_to IS NULL
                OR effective_from <= effective_to
            )
        )
        """
    )
    op.execute("CREATE INDEX ix_fare_rules_route_id ON fare_rules (route_id)")
    op.execute("CREATE INDEX ix_fare_rules_pattern_id ON fare_rules (pattern_id)")
    op.execute("CREATE INDEX ix_fare_rules_origin_stop_id ON fare_rules (origin_stop_id)")

    # ---- places & aliases (places) ----------------------------------------
    op.execute(
        """
        CREATE TABLE places (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name VARCHAR(300) NOT NULL,
            category VARCHAR(50),
            locality_id UUID REFERENCES localities (id) ON DELETE SET NULL,
            location GEOGRAPHY(POINT, 4326),
            access_notes TEXT,
            verification_status VARCHAR(20) NOT NULL DEFAULT 'unverified'
                CHECK (verification_status IN ('unverified','reported','verified')),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX ix_places_locality_id ON places (locality_id)")
    op.execute("CREATE INDEX ix_places_location ON places USING GIST (location)")

    op.execute(
        """
        CREATE TABLE place_access_points (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            place_id UUID NOT NULL REFERENCES places (id) ON DELETE CASCADE,
            name VARCHAR(300),
            access_type VARCHAR(20)
                CHECK (access_type IN ('entrance','gate','pickup_dropoff',
                    'parking','other')),
            location GEOGRAPHY(POINT, 4326),
            notes TEXT,
            verification_status VARCHAR(20) NOT NULL DEFAULT 'unverified'
                CHECK (verification_status IN ('unverified','reported','verified')),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX ix_place_access_points_place_id ON place_access_points (place_id)")
    op.execute(
        "CREATE INDEX ix_place_access_points_location ON place_access_points USING GIST (location)"
    )
    op.execute(
        """
        CREATE TABLE entity_aliases (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            entity_type VARCHAR(30) NOT NULL
                CHECK (entity_type IN ('place','stop','route','route_pattern','locality')),
            entity_id UUID NOT NULL,
            language VARCHAR(2) NOT NULL CHECK (language IN ('en','si','ta')),
            alias TEXT NOT NULL,
            transliteration TEXT,
            is_colloquial BOOLEAN,
            data_source_id UUID REFERENCES data_sources (id) ON DELETE SET NULL,
            confidence VARCHAR(20) DEFAULT 'unverified',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX ix_entity_aliases_entity ON entity_aliases (entity_type, entity_id)")
    op.execute("CREATE INDEX ix_entity_aliases_alias ON entity_aliases (alias)")

    # ---- data quality (data_quality) ---------------------------------------
    op.execute(
        """
        CREATE TABLE verification_records (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            entity_type VARCHAR(40) NOT NULL
                CHECK (entity_type IN ('agency','route','route_pattern','stop',
                    'stop_access_point','route_shape','transfer_connection',
                    'place','place_access_point','locality','entity_alias','fare_rule')),
            entity_id UUID NOT NULL,
            method VARCHAR(30) NOT NULL
                CHECK (method IN ('field_check','official_source','source_crosscheck',
                    'report_review','other')),
            reviewer VARCHAR(200),
            verified_at TIMESTAMPTZ NOT NULL,
            result VARCHAR(20) NOT NULL
                CHECK (result IN ('verified','rejected','uncertain')),
            evidence TEXT,
            notes TEXT
        )
        """
    )
    op.execute(
        "CREATE INDEX ix_verification_records_entity"
        " ON verification_records (entity_type, entity_id)"
    )

    op.execute(
        """
        CREATE TABLE data_change_audit (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            entity_type VARCHAR(40) NOT NULL
                CHECK (entity_type IN ('agency','route','route_pattern','stop',
                    'stop_access_point','route_shape','transfer_connection',
                    'place','place_access_point','locality','entity_alias','fare_rule')),
            entity_id UUID NOT NULL,
            operation VARCHAR(15) NOT NULL
                CHECK (operation IN ('create','update','deactivate','delete')),
            before_state JSONB,
            after_state JSONB,
            actor VARCHAR(200),
            reason TEXT,
            dataset_version_id UUID
                REFERENCES dataset_versions (id) ON DELETE SET NULL,
            changed_at TIMESTAMPTZ NOT NULL
        )
        """
    )
    op.execute(
        "CREATE INDEX ix_data_change_audit_entity ON data_change_audit (entity_type, entity_id)"
    )
    op.execute(
        "CREATE INDEX ix_data_change_audit_dataset_version_id"
        " ON data_change_audit (dataset_version_id)"
    )


def downgrade() -> None:
    # Reverse dependency order (children first).
    for statement in (
        "DROP TABLE IF EXISTS data_change_audit",
        "DROP TABLE IF EXISTS verification_records",
        "DROP TABLE IF EXISTS entity_aliases",
        "DROP TABLE IF EXISTS place_access_points",
        "DROP TABLE IF EXISTS places",
        "DROP TABLE IF EXISTS fare_rules",
        "DROP TABLE IF EXISTS transfer_connections",
        "DROP TABLE IF EXISTS route_pattern_stops",
        "DROP TABLE IF EXISTS route_patterns",
        "DROP TABLE IF EXISTS stop_access_points",
        "DROP TABLE IF EXISTS stops",
        "DROP TABLE IF EXISTS localities",
        "DROP TABLE IF EXISTS route_shapes",
        "DROP TABLE IF EXISTS transport_routes",
        "DROP TABLE IF EXISTS transport_agencies",
        "DROP TABLE IF EXISTS active_dataset",
        "DROP TABLE IF EXISTS dataset_version_entities",
        "DROP TABLE IF EXISTS dataset_versions",
        "DROP TABLE IF EXISTS sync_runs",
        "DROP TABLE IF EXISTS source_records",
        "DROP TABLE IF EXISTS source_snapshots",
        "DROP TABLE IF EXISTS data_sources",
    ):
        op.execute(statement)
