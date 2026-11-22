"""Saved journeys for the planner (Phase 4 completion).

`saved_journeys` stores a plan request + the response snapshot so a journey can
be retrieved (`GET /journeys/{id}`) and re-planned against the current active
dataset (`POST /journeys/{id}/refresh`). No user accounts exist yet (product
rule: basic planning must not require an account), so rows are anonymous and
keyed by unguessable UUIDs; user association arrives with Phase 6 accounts.

Revision ID: 0006_saved_journeys
Revises: 0005_trgm_search_indexes
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0006_saved_journeys"
down_revision: str | None = "0005_trgm_search_indexes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE saved_journeys (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            origin JSONB NOT NULL,
            destination JSONB NOT NULL,
            preferences JSONB NOT NULL,
            dataset_version_label VARCHAR(100) NOT NULL,
            response JSONB NOT NULL,
            notes TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX ix_saved_journeys_created_at ON saved_journeys (created_at DESC)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_saved_journeys_created_at")
    op.execute("DROP TABLE IF EXISTS saved_journeys")
