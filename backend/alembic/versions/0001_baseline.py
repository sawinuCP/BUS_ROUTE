"""Empty baseline migration (Phase 0.3 skeleton).

Canonical transport schema (agencies, routes, route variants, stops, aliases,
sequences, shapes, transfers, places, provenance and versioning) is added in
Phase 1. This baseline exists to verify that the migration tooling is wired
end to end before any schema exists.
"""

from __future__ import annotations

from collections.abc import Sequence

revision: str = "0001_baseline"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
