"""Seed the OSM/Overpass source into the registry (Phase 1.3).

Run inside the backend container:
    python scripts/seed_osm_source.py

Idempotent: updates licence/terms if the source already exists.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select  # noqa: E402

from app.modules.data_ingestion.models import DataSource  # noqa: E402
from app.platform.db import get_session_factory  # noqa: E402

SOURCE_FIELDS = {
    "name": "osm-overpass",
    "owner": "OpenStreetMap contributors (via Overpass API)",
    "access_method": "api",
    "endpoint": "https://overpass-api.de/api/interpreter",
    "format": "osm",
    "licence": "ODbL 1.0 (OpenStreetMap)",
    "terms_note": (
        "Attribution required: (c) OpenStreetMap contributors. Share-alike "
        "obligations may apply to derived databases — legal review required "
        "before public publishing. Data kept private in development. OSM does "
        "not guarantee operational status, complete stop sequences or "
        "boarding positions."
    ),
    "update_cadence": "manual during pilot; per-source policy to be defined",
}


async def main() -> None:
    session = get_session_factory()()
    try:
        result = await session.execute(
            select(DataSource).where(DataSource.name == SOURCE_FIELDS["name"])
        )
        source = result.scalar_one_or_none()
        if source is None:
            source = DataSource(**SOURCE_FIELDS, enabled=True)
            session.add(source)
            print("created source 'osm-overpass'")
        else:
            for key, value in SOURCE_FIELDS.items():
                setattr(source, key, value)
            source.enabled = True
            print("updated existing source 'osm-overpass'")
        await session.commit()
        print(f"id: {source.id}")
    finally:
        await session.close()


if __name__ == "__main__":
    asyncio.run(main())
