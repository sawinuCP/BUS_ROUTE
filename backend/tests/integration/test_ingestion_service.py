"""Ingestion service integration tests (live DB; everything rolls back)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.data_ingestion.adapters.file import FileSourceAdapter
from app.modules.data_ingestion.archive import LocalFilesystemArchive
from app.modules.data_ingestion.service import (
    DatasetVersionService,
    IngestionService,
    SourceRegistry,
)
from app.platform.db import dispose_engine, get_session_factory


def _write_fixture(path: Path, records: list[dict[str, Any]]) -> None:
    path.write_text(json.dumps(records), encoding="utf-8")


def _records() -> list[dict[str, Any]]:
    return [
        {
            "external_id": "stop-homagama",
            "entity_hint": "stop",
            "payload": {
                "name": "Homagama Junction",
                "lon": 79.9777,
                "lat": 6.8440,
                "stop_type": "roadside",
                "aliases": [{"language": "si", "alias": "හෝමාගම හන්දිය"}],
            },
        },
        {
            "external_id": "route-138",
            "entity_hint": "route",
            "payload": {
                "route_code": "138",
                "route_name": "Homagama–Kollupitiya",
                "mode": "bus",
                "agency_name": "Test SLTB",
            },
        },
        {
            "external_id": "place-nawaloka",
            "entity_hint": "place",
            "payload": {
                "name": "Nawaloka Hospital",
                "category": "hospital",
                "lon": 79.8612,
                "lat": 6.9271,
            },
        },
    ]


@pytest.fixture
async def db_session() -> AsyncSession:
    session = get_session_factory()()
    yield session
    await session.close()
    # pytest-asyncio gives every test a fresh event loop; the process-global
    # engine/session factory must be reset so the next test rebinds to its own.
    await dispose_engine()


@pytest.fixture
def archive(tmp_path: Path) -> LocalFilesystemArchive:
    return LocalFilesystemArchive(tmp_path / "raw")


async def test_full_sync_creates_entities_and_candidate_version(
    db_session: AsyncSession, tmp_path: Path, archive: LocalFilesystemArchive
) -> None:
    fixture = tmp_path / "source.json"
    _write_fixture(fixture, _records())
    registry = SourceRegistry()
    source = await registry.create_source(db_session, name="integration-test-source", format="test")
    service = IngestionService(archive=archive)

    outcome = await service.run_sync(db_session, source, FileSourceAdapter(fixture))

    assert outcome.status == "succeeded"
    assert outcome.records_in == 3
    assert outcome.records_added == 3
    assert outcome.records_failed == 0
    assert outcome.version_label

    stops = await db_session.execute(
        text("SELECT name FROM stops WHERE name = 'Homagama Junction'")
    )
    assert stops.scalar_one() == "Homagama Junction"

    link = await db_session.execute(
        text(
            "SELECT canonical_entity_type FROM source_records"
            " WHERE data_source_id = :s AND external_id = 'stop-homagama'"
        ),
        {"s": source.id},
    )
    assert link.scalar_one() == "stop"

    alias_count = await db_session.execute(
        text("SELECT count(*) FROM entity_aliases WHERE alias = 'හෝමාගම හන්දිය'")
    )
    assert alias_count.scalar_one() == 1

    version_status = await db_session.execute(
        text("SELECT status FROM dataset_versions WHERE version_label = :l"),
        {"l": outcome.version_label},
    )
    assert version_status.scalar_one() == "candidate"

    dve = await db_session.execute(
        text(
            "SELECT count(*) FROM dataset_version_entities dve"
            " JOIN dataset_versions dv ON dv.id = dve.dataset_version_id"
            " WHERE dv.version_label = :l AND dve.operation = 'added'"
        ),
        {"l": outcome.version_label},
    )
    assert dve.scalar_one() == 3


async def test_unchanged_source_short_circuits(
    db_session: AsyncSession, tmp_path: Path, archive: LocalFilesystemArchive
) -> None:
    fixture = tmp_path / "source.json"
    _write_fixture(fixture, _records())
    registry = SourceRegistry()
    source = await registry.create_source(db_session, name="idem-source", format="test")
    service = IngestionService(archive=archive)

    first = await service.run_sync(db_session, source, FileSourceAdapter(fixture))
    second = await service.run_sync(db_session, source, FileSourceAdapter(fixture))

    assert first.status == "succeeded"
    assert second.status == "succeeded"
    assert second.unchanged is True
    assert second.records_in == 0

    stop_count = await db_session.execute(
        text("SELECT count(*) FROM stops WHERE name = 'Homagama Junction'")
    )
    assert stop_count.scalar_one() == 1  # no duplicates

    run_count = await db_session.execute(
        text("SELECT count(*) FROM sync_runs WHERE data_source_id = :s AND status = 'succeeded'"),
        {"s": source.id},
    )
    assert run_count.scalar_one() == 2


async def test_changed_source_records_updates(
    db_session: AsyncSession, tmp_path: Path, archive: LocalFilesystemArchive
) -> None:
    fixture = tmp_path / "source.json"
    records = _records()
    _write_fixture(fixture, records)
    registry = SourceRegistry()
    source = await registry.create_source(db_session, name="update-source", format="test")
    service = IngestionService(archive=archive)
    await service.run_sync(db_session, source, FileSourceAdapter(fixture))

    records[0]["payload"]["name"] = "Homagama Town Junction"
    _write_fixture(fixture, records)
    outcome = await service.run_sync(db_session, source, FileSourceAdapter(fixture))

    assert outcome.status == "succeeded"
    assert outcome.records_updated == 1
    assert outcome.records_added == 0

    names = await db_session.execute(text("SELECT name FROM stops"))
    assert {row[0] for row in names} == {"Homagama Town Junction"}


async def test_invalid_records_quarantine_the_run(
    db_session: AsyncSession, tmp_path: Path, archive: LocalFilesystemArchive
) -> None:
    fixture = tmp_path / "bad.json"
    _write_fixture(
        fixture,
        [
            {
                "external_id": "bad-stop",
                "entity_hint": "stop",
                "payload": {"name": "Bad", "lon": 2.35, "lat": 48.85},
            }
        ],
    )
    registry = SourceRegistry()
    source = await registry.create_source(db_session, name="quarantine-source", format="test")
    service = IngestionService(archive=archive)

    outcome = await service.run_sync(db_session, source, FileSourceAdapter(fixture))

    assert outcome.status == "quarantined"
    assert outcome.quarantine_errors
    stop_count = await db_session.execute(text("SELECT count(*) FROM stops"))
    assert stop_count.scalar_one() == 0  # canonical data untouched


async def test_publish_then_rollback_flips_active_pointer(
    db_session: AsyncSession, tmp_path: Path, archive: LocalFilesystemArchive
) -> None:
    fixture = tmp_path / "source.json"
    _write_fixture(fixture, _records())
    registry = SourceRegistry()
    source = await registry.create_source(db_session, name="publish-source", format="test")
    service = IngestionService(archive=archive)
    versions = DatasetVersionService()

    async def _version_id(label: str) -> Any:
        result = await db_session.execute(
            text("SELECT id FROM dataset_versions WHERE version_label = :l"), {"l": label}
        )
        return result.scalar_one()

    first = await service.run_sync(db_session, source, FileSourceAdapter(fixture))
    first_version_id = await _version_id(first.version_label)

    # Version 1 is published so it is a valid rollback target later.
    await versions.publish(db_session, first_version_id)

    records = _records()
    records.append(
        {
            "external_id": "stop-extra",
            "entity_hint": "stop",
            "payload": {"name": "Extra Stop", "lon": 79.9, "lat": 6.95},
        }
    )
    _write_fixture(fixture, records)
    second = await service.run_sync(db_session, source, FileSourceAdapter(fixture))
    second_version_id = await _version_id(second.version_label)

    # Publishing version 2 supersedes version 1.
    await versions.publish(db_session, second_version_id)
    active = await versions.active_version(db_session)
    assert active is not None and active.id == second_version_id

    # Rolling back flips the pointer back to the still-published version 1.
    await versions.rollback(db_session, first_version_id)
    active = await versions.active_version(db_session)
    assert active is not None and active.id == first_version_id


async def test_duplicate_source_name_rejected(db_session: AsyncSession) -> None:
    registry = SourceRegistry()
    await registry.create_source(db_session, name="dup-source", format="test")
    with pytest.raises(ValueError):
        await registry.create_source(db_session, name="dup-source", format="test")
