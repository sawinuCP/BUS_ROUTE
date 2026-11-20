"""Trigram search indexes for place/alias search (Phase 2).

Enables pg_trgm similarity search over multilingual aliases and canonical
names. GIN + gin_trgm_ops supports both `%` similarity and ILIKE patterns.

Revision ID: 0005_trgm_search_indexes
Revises: 0004_pattern_stop_entity_type
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0005_trgm_search_indexes"
down_revision: str | None = "0004_pattern_stop_entity_type"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_INDEXES = (
    ("ix_entity_aliases_alias_trgm", "entity_aliases", "alias"),
    ("ix_stops_name_trgm", "stops", "name"),
    ("ix_places_name_trgm", "places", "name"),
    ("ix_localities_name_trgm", "localities", "name"),
)


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    for name, table, column in _INDEXES:
        op.execute(
            f"CREATE INDEX IF NOT EXISTS {name} ON {table} USING GIN ({column} gin_trgm_ops)"
        )


def downgrade() -> None:
    for name, _table, _column in _INDEXES:
        op.execute(f"DROP INDEX IF EXISTS {name}")
    op.execute("DROP EXTENSION IF EXISTS pg_trgm")
