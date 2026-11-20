"""Allow 'route_pattern_stop' in entity-type check constraints (Phase 1.3).

Ordered stop calls are first-class ingested entities (diffs recorded in
dataset_version_entities, verification and change audit apply to them too).

Revision ID: 0004_pattern_stop_entity_type
Revises: 0003_source_record_link
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0004_pattern_stop_entity_type"
down_revision: str | None = "0003_source_record_link"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_ENTITY_TYPES = (
    "'agency','route','route_pattern','route_pattern_stop','stop','stop_access_point',"
    "'route_shape','transfer_connection','place','place_access_point','locality',"
    "'entity_alias','fare_rule'"
)

# (table, original auto-named constraint, convention-named constraint)
_CONSTRAINT_TABLES = (
    (
        "dataset_version_entities",
        "dataset_version_entities_entity_type_check",
        "dve_entity_type",
    ),
    (
        "verification_records",
        "verification_records_entity_type_check",
        "verification_entity_type",
    ),
    ("data_change_audit", "data_change_audit_entity_type_check", "change_entity_type"),
)


def upgrade() -> None:
    for table, existing, named in _CONSTRAINT_TABLES:
        op.execute(f"ALTER TABLE {table} DROP CONSTRAINT IF EXISTS {existing}")
        op.execute(f"ALTER TABLE {table} DROP CONSTRAINT IF EXISTS {named}")
        op.execute(
            f"ALTER TABLE {table} ADD CONSTRAINT {named} CHECK (entity_type IN ({_ENTITY_TYPES}))"
        )


def downgrade() -> None:
    _ORIGINAL = (
        "'agency','route','route_pattern','stop','stop_access_point',"
        "'route_shape','transfer_connection','place','place_access_point','locality',"
        "'entity_alias','fare_rule'"
    )
    for table, existing, named in _CONSTRAINT_TABLES:
        op.execute(f"ALTER TABLE {table} DROP CONSTRAINT IF EXISTS {named}")
        op.execute(f"ALTER TABLE {table} DROP CONSTRAINT IF EXISTS {existing}")
        op.execute(
            f"ALTER TABLE {table} ADD CONSTRAINT {existing} CHECK (entity_type IN ({_ORIGINAL}))"
        )
