"""Model registry: importing this module loads every canonical model's table
into `Base.metadata` for Alembic autogenerate/verification and for tests.

Canonical module ownership (ADR-0001):
- data_ingestion: provenance, snapshots, sync runs, dataset versioning
- transport: agencies, routes, patterns, stops, access points, sequences, shapes, transfers, fares
- places: localities, places, access points, entity aliases
- data_quality: verification records, change audit
"""

from __future__ import annotations

from app.platform.db import Base


def import_all_models() -> None:
    """Import every module's models so they register on Base.metadata."""
    from app.modules.data_ingestion import models as data_ingestion_models  # noqa: F401
    from app.modules.data_quality import models as data_quality_models  # noqa: F401
    from app.modules.places import models as places_models  # noqa: F401
    from app.modules.transport import models as transport_models  # noqa: F401


__all__ = ["Base", "import_all_models"]
