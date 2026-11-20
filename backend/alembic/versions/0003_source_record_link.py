"""Add canonical-entity link columns to source_records (Phase 1.2).

The ingestion framework records, per external record, which canonical entity
it was matched to (or created). This is the idempotency/matching bookkeeping
used by the upsert handlers: re-running the same source version updates the
linked canonical rows instead of creating duplicates.

Revision ID: 0003_source_record_link
Revises: 0002_canonical_schema
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0003_source_record_link"
down_revision: str | None = "0002_canonical_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE source_records
            ADD COLUMN canonical_entity_type VARCHAR(40),
            ADD COLUMN canonical_entity_id UUID
        """
    )
    op.execute(
        "CREATE INDEX ix_source_records_canonical_entity"
        " ON source_records (canonical_entity_type, canonical_entity_id)"
    )
    op.execute(
        "CREATE INDEX uq_source_records_source_external_type"
        " ON source_records (data_source_id, external_id, canonical_entity_type)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_source_records_source_external_type")
    op.execute("DROP INDEX IF EXISTS ix_source_records_canonical_entity")
    op.execute(
        """
        ALTER TABLE source_records
            DROP COLUMN IF EXISTS canonical_entity_id,
            DROP COLUMN IF EXISTS canonical_entity_type
        """
    )
