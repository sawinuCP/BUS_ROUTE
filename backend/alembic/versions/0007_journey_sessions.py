"""Journey sessions and events (Phase 6 — active journey mode).

A session tracks one traveller following one option of one saved plan: the
current step, a derived execution state, and an append-only event trail.
Privacy rule (data model doc §6): no location history — events carry no
coordinates; the session is anonymous until accounts exist (Phase 6 accounts).

Revision ID: 0007_journey_sessions
Revises: 0006_saved_journeys
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0007_journey_sessions"
down_revision: str | None = "0006_saved_journeys"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE journey_sessions (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            journey_id UUID NOT NULL
                REFERENCES saved_journeys (id) ON DELETE CASCADE,
            option_id VARCHAR(50) NOT NULL,
            dataset_version_label VARCHAR(100) NOT NULL,
            origin JSONB NOT NULL,
            destination JSONB NOT NULL,
            preferences JSONB NOT NULL,
            plan_snapshot JSONB NOT NULL,
            status VARCHAR(30) NOT NULL DEFAULT 'overview'
                CHECK (status IN ('overview','active_walk','active_ride',
                                  'transfer_walk','final_walk','needs_confirmation',
                                  'paused','replanning','completed','cancelled')),
            current_step_index INTEGER NOT NULL DEFAULT 0
                CHECK (current_step_index >= 0),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX ix_journey_sessions_journey ON journey_sessions (journey_id)")
    op.execute(
        """
        CREATE TABLE journey_events (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            session_id UUID NOT NULL
                REFERENCES journey_sessions (id) ON DELETE CASCADE,
            event_type VARCHAR(20) NOT NULL
                CHECK (event_type IN ('started','step_advanced','paused','resumed',
                                      'completed','cancelled','replanned')),
            step_index INTEGER,
            note TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX ix_journey_events_session ON journey_events (session_id, created_at)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS journey_events")
    op.execute("DROP INDEX IF EXISTS ix_journey_sessions_journey")
    op.execute("DROP TABLE IF EXISTS journey_sessions")
