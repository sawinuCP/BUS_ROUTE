"""Transport reports: category, append-only submission, moderation trail.

Phase 7 work items 4, 7 and 8 (implementation plan): travellers can report
data issues with **explicit consent**; submissions are append-only and
idempotent per `client_key` (a queued-offline retry never duplicates a
report); moderators triage via the admin queue — acceptance records a new
**candidate** dataset version (never the active one), rejection and
needs-info change nothing outside the report row.

Categories (plan item 7): wrong_stop, route_variant, direction, transfer_path,
landmark_name, fare, access_attribute, outdated_data, other.

The table stores **no location data** — a report is tied to canonical
entities (stop/route/pattern/transfer/journey), never coordinates.

Revision ID: 0008_reports
Revises: 0007_journey_sessions
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0008_reports"
down_revision: str | None = "0007_journey_sessions"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE transport_reports (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            category VARCHAR(30) NOT NULL
                CHECK (category IN ('wrong_stop','route_variant','direction',
                    'transfer_path','landmark_name','fare','access_attribute',
                    'outdated_data','other')),
            subject_type VARCHAR(20)
                CHECK (subject_type IN ('stop','route','pattern','transfer','journey')),
            subject_id UUID,
            description TEXT NOT NULL,
            consent BOOLEAN NOT NULL DEFAULT FALSE,
            client_key VARCHAR(64) NOT NULL,
            status VARCHAR(20) NOT NULL DEFAULT 'submitted'
                CHECK (status IN ('submitted','under_review','accepted',
                    'rejected','needs_info')),
            dataset_version_label VARCHAR(100),
            reviewed_at TIMESTAMPTZ,
            review_note TEXT,
            candidate_version_id UUID REFERENCES dataset_versions (id)
                ON DELETE SET NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_transport_reports_client_key"
        " ON transport_reports (client_key)"
    )
    op.execute(
        "CREATE INDEX ix_transport_reports_status"
        " ON transport_reports (status, created_at)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS transport_reports")
