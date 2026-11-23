"""Phase 1.4 integration tests: scorecard, QA queue, verifications, survey import."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from scripts.import_field_verifications import import_verifications
from sqlalchemy import text
from starlette.requests import Request

from app.api.routes.admin import (
    VerificationCreate,
    create_verification,
    list_verifications,
)
from app.modules.data_quality.queue import QAQueueService
from app.modules.data_quality.scorecard import CoverageScorecardService
from app.platform.db import dispose_engine, get_session_factory
from tests.integration.conftest import _seed_route


def _audit_request() -> Request:
    """A minimal Request so the direct service call can record its audit line."""
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/direct-call",
            "headers": [],
            "query_string": b"",
            "client": ("testclient", 0),
        }
    )


@pytest.fixture
async def db_session():
    session = get_session_factory()()
    yield session
    await session.close()
    await dispose_engine()


async def test_scorecard_scores_route_completeness(db_session) -> None:
    await _seed_route(db_session)
    report = await CoverageScorecardService().build(db_session)

    assert report["routes_scored"] == 1
    route = report["routes"][0]
    assert route["route_code"] == "138"
    assert route["variants"] == 1
    # Seeded: agency present, no calls yet → variants(10) + agency(15) = 25.
    assert route["score"] == 25
    assert route["score_parts"]["agency"] == 1.0
    assert report["scoring_weights"]["calls"] == 30
    markdown = await CoverageScorecardService.render_markdown(report)
    assert "138" in markdown and "Score" in markdown


async def test_qa_queue_lists_review_items(db_session) -> None:
    await _seed_route(db_session)
    queue = await QAQueueService().items(db_session)

    kinds = {item["id"].split(":")[0] for item in queue["items"]}
    assert "pattern-under-two" in kinds  # the seeded pattern has no calls
    assert queue["counts_by_severity"].get("warning", 0) >= 1


async def test_verification_records_against_real_entities(db_session) -> None:
    ids = await _seed_route(db_session)
    body = VerificationCreate(
        entity_type="stop",
        entity_id=ids["stop_a"],
        method="field_check",
        reviewer="test-walker",
        result="verified",
        evidence="GPS confirmed; signboard matches",
    )
    created = await create_verification(body, db_session, _audit_request())
    assert created["result"] == "verified"
    assert created["reviewer"] == "test-walker"

    listed = await list_verifications(db_session, entity_type="stop", entity_id=ids["stop_a"])
    assert len(listed) == 1
    assert listed[0]["method"] == "field_check"


async def test_verification_rejects_unknown_entity(db_session) -> None:
    from uuid import uuid4

    body = VerificationCreate(
        entity_type="stop",
        entity_id=uuid4(),
        method="field_check",
        result="verified",
    )
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc_info:
        await create_verification(body, db_session, _audit_request())
    assert exc_info.value.status_code == 404


async def test_field_submission_import(db_session, tmp_path: Path) -> None:
    ids = await _seed_route(db_session)
    # The import script uses its own session, so the seed must be committed.
    await db_session.commit()

    submissions = tmp_path / "stops_submitted.csv"
    header = (
        "stop_id,result,reviewer,corrected_name,name_si,side_notes,gps_lon,gps_lat,evidence_notes\n"
    )
    row_a = (
        f"{ids['stop_a']},corrected,walker,Homagama Town,හෝමාගම,"
        "opposite side near bank,79.9775,6.8439,signboard photo\n"
    )
    row_unknown = "00000000-0000-0000-0000-000000000000,verified,walker,,,,,,\n"
    submissions.write_text(header + row_a + row_unknown, encoding="utf-8")

    summary = await import_verifications(submissions)

    assert summary["records_written"] == 1
    assert summary["skipped"]  # the unknown stop_id was skipped, not guessed
    assert len(summary["corrections"]) == 1
    corrections = summary["corrections"][0]["corrections"]
    assert corrections["name"] == "Homagama Town"
    assert corrections["alias_si"] == "හෝමාගම"
    assert corrections["side_or_platform"] == "opposite side near bank"
    assert Path(str(summary["corrections_report"])).exists()

    # Canonical data untouched — corrections only recorded for review.
    name = await db_session.execute(
        text("SELECT name FROM stops WHERE id = :id"), {"id": ids["stop_a"]}
    )
    assert name.scalar_one() == "Homagama Junction"

    records = await list_verifications(db_session, entity_type="stop")
    assert len(records) == 1
    assert "corrections:" in (records[0]["evidence"] or "")

    # The corrections report is valid JSON with the review payload.
    payload = json.loads(Path(str(summary["corrections_report"])).read_text(encoding="utf-8"))
    assert payload["records_written"] == 1
