"""Phase 3 integration: route shapes + stop access points through the sync service.

Shapes and access points are new Phase 3 canonical entities; this proves the
full fetch→parse→upsert→link flow against the real (test) database.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.data_ingestion.adapters.file import FileSourceAdapter
from app.modules.data_ingestion.archive import LocalFilesystemArchive
from app.modules.data_ingestion.service import IngestionService, SourceRegistry
from app.platform.db import dispose_engine, get_session_factory


def _records() -> list[dict[str, Any]]:
    return [
        {
            "external_id": "stop-james",
            "entity_hint": "stop",
            "payload": {"name": "James Pier", "lon": 79.8480, "lat": 6.9350},
        },
        {
            "external_id": "route-test",
            "entity_hint": "route",
            "payload": {"route_code": "101", "mode": "bus"},
        },
        {
            "external_id": "pattern-test",
            "entity_hint": "route_pattern",
            "payload": {
                "route_external_ref": "route-test",
                "pattern_code": "r200001",
                "direction_id": 0,
            },
        },
        {
            "external_id": "call-1",
            "entity_hint": "route_pattern_stop",
            "payload": {
                "pattern_external_ref": "pattern-test",
                "stop_external_ref": "stop-james",
                "sequence": 1,
            },
        },
        {
            "external_id": "shape-test",
            "entity_hint": "route_shape",
            "payload": {
                "pattern_external_ref": "pattern-test",
                "coordinates": [[79.857, 6.933], [79.855, 6.929], [79.853, 6.925]],
                "missing_way_nodes": 0,
            },
        },
        {
            "external_id": "access-point-test",
            "entity_hint": "stop_access_point",
            "payload": {"stop_external_ref": "stop-james", "lon": 79.8480, "lat": 6.9350},
        },
    ]


@pytest.fixture
async def db_session() -> AsyncSession:
    session = get_session_factory()()
    yield session
    await session.close()
    await dispose_engine()


async def test_sync_persists_shape_and_access_point(
    db_session: AsyncSession, tmp_path: Path
) -> None:
    fixture = tmp_path / "source.json"
    fixture.write_text(json.dumps(_records()), encoding="utf-8")
    registry = SourceRegistry()
    source = await registry.create_source(db_session, name="phase3-shapes-source", format="test")
    service = IngestionService(archive=LocalFilesystemArchive(tmp_path / "raw"))

    outcome = await service.run_sync(db_session, source, FileSourceAdapter(fixture))

    assert outcome.status == "succeeded"
    assert outcome.records_added == 6
    assert outcome.records_failed == 0

    shape = await db_session.execute(
        text(
            "SELECT ST_AsText(rs.geometry::geometry), rp.shape_id IS NOT NULL"
            " FROM route_shapes rs"
            " JOIN source_records sr ON sr.canonical_entity_id = rs.id"
            "  AND sr.canonical_entity_type = 'route_shape'"
            " JOIN route_patterns rp ON rp.shape_id = rs.id"
            " WHERE sr.external_id = 'shape-test'"
        )
    )
    row = shape.one()
    assert "MULTILINESTRING((79.857 6.933" in str(row[0])
    assert row[1] is True

    access_point = await db_session.execute(
        text(
            "SELECT ST_AsText(sap.location::geometry), s.name"
            " FROM stop_access_points sap"
            " JOIN source_records sr ON sr.canonical_entity_id = sap.id"
            "  AND sr.canonical_entity_type = 'stop_access_point'"
            " JOIN stops s ON s.id = sap.stop_id"
            " WHERE sr.external_id = 'access-point-test'"
        )
    )
    ap_row = access_point.one()
    assert "79.848 6.935" in str(ap_row[0])
    assert ap_row[1] == "James Pier"


async def test_shape_sync_is_idempotent_on_reparse(
    db_session: AsyncSession, tmp_path: Path
) -> None:
    fixture = tmp_path / "source.json"
    fixture.write_text(json.dumps(_records()), encoding="utf-8")
    # Different bytes → different snapshot checksum → the second run re-parses
    # and re-upserts the same records (the unchanged-checksum path would
    # short-circuit instead; both must leave exactly one row behind).
    reparsed_fixture = tmp_path / "source_reparse.json"
    reparsed_fixture.write_text(json.dumps(_records()) + "\n", encoding="utf-8")
    registry = SourceRegistry()
    source = await registry.create_source(
        db_session, name="phase3-shapes-idem-source", format="test"
    )
    service = IngestionService(archive=LocalFilesystemArchive(tmp_path / "raw"))

    first = await service.run_sync(db_session, source, FileSourceAdapter(fixture))
    second = await service.run_sync(db_session, source, FileSourceAdapter(reparsed_fixture))

    assert first.status == "succeeded"
    assert second.status == "succeeded"
    assert second.records_added == 0
    assert second.records_unchanged == 6
    shapes = await db_session.execute(text("SELECT count(*) FROM route_shapes"))
    assert shapes.scalar_one() == 1
    access_points = await db_session.execute(text("SELECT count(*) FROM stop_access_points"))
    assert access_points.scalar_one() == 1
