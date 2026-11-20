"""Overpass pipeline integration test (synthetic fixture; live DB)."""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.data_ingestion.adapters.base import FetchResult
from app.modules.data_ingestion.adapters.overpass import OverpassAdapter
from app.modules.data_ingestion.archive import LocalFilesystemArchive
from app.modules.data_ingestion.report import QualityReportService
from app.modules.data_ingestion.service import (
    IngestionService,
    SourceRegistry,
)
from app.platform.db import dispose_engine, get_session_factory

FIXTURE = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "overpass_sample.json"


class StubOverpassAdapter(OverpassAdapter):
    """Same parsing as the real adapter; fetch reads the committed fixture."""

    def fetch(self) -> FetchResult:  # noqa: D102
        return FetchResult(
            content=FIXTURE.read_bytes(),
            content_type="application/json",
            metadata={"bbox": "synthetic"},
        )


@pytest.fixture
async def db_session() -> AsyncSession:
    session = get_session_factory()()
    yield session
    await session.close()
    await dispose_engine()


async def test_overpass_pipeline_creates_ordered_variants(
    db_session: AsyncSession, tmp_path: Path
) -> None:
    registry = SourceRegistry()
    source = await registry.create_source(db_session, name="osm-fixture-source", format="osm")
    service = IngestionService(archive=LocalFilesystemArchive(tmp_path / "raw"))

    outcome = await service.run_sync(db_session, source, StubOverpassAdapter("synthetic"))

    # 2 named stops + 2 routes (refs 100, 101) + 3 patterns + 6 ordered calls
    # = 13 records; one call is unresolved (its stop node has no data).
    assert outcome.status == "succeeded"
    assert outcome.records_in == 13
    assert outcome.records_failed == 1  # osm-node/100003 has no stop data — honest failure

    stops = await db_session.execute(text("SELECT count(*) FROM stops"))
    assert stops.scalar_one() == 2

    routes = await db_session.execute(
        text("SELECT count(*) FROM transport_routes WHERE route_code = '100'")
    )
    assert routes.scalar_one() == 1  # variants share the route identity

    patterns = await db_session.execute(text("SELECT count(*) FROM route_patterns"))
    assert patterns.scalar_one() == 3

    calls = await db_session.execute(text("SELECT count(*) FROM route_pattern_stops"))
    assert calls.scalar_one() == 5  # the unresolved member ref is excluded, not guessed

    aliases = await db_session.execute(
        text("SELECT count(*) FROM entity_aliases WHERE language = 'si'")
    )
    assert aliases.scalar_one() == 1

    # Ordered reconstruction of the direction-0 pattern of relation 200001.
    ordered = await db_session.execute(
        text(
            "SELECT s.name, rps.sequence, rps.boarding_allowed, rps.alighting_allowed"
            " FROM route_pattern_stops rps"
            " JOIN route_patterns rp ON rp.id = rps.pattern_id"
            " JOIN stops s ON s.id = rps.stop_id"
            " WHERE rp.pattern_code = 'r200001' ORDER BY rps.sequence"
        )
    )
    assert [(row[0], row[1]) for row in ordered] == [
        ("Pettah Terminal", 1),
        ("Kollupitiya Junction", 2),
    ]

    # Idempotent: unchanged source → second run is a no-op.
    second = await service.run_sync(db_session, source, StubOverpassAdapter("synthetic"))
    assert second.unchanged is True

    # Quality report for the candidate version.
    version_id = (
        await db_session.execute(
            text("SELECT id FROM dataset_versions WHERE version_label = :l"),
            {"l": outcome.version_label},
        )
    ).scalar_one()
    report = await QualityReportService().build(db_session, version_id)
    assert report["coverage"]["route_patterns"] == 3
    assert report["coverage"]["aliases_by_language"].get("si") == 1
    no_calls_check = next(
        check
        for check in report["checks"]
        if check["check"] == "patterns with no stop calls at all"
    )
    assert no_calls_check["count"] == 0  # every pattern kept at least its resolvable calls
    under_two_check = next(
        check
        for check in report["checks"]
        if check["check"] == "patterns with fewer than 2 ordered calls"
    )
    assert under_two_check["count"] == 1  # the short-working variant, honestly reported

    written = await QualityReportService().write(db_session, version_id, tmp_path / "reports")
    assert Path(written["markdown"]).exists()
    assert Path(written["json"]).exists()
