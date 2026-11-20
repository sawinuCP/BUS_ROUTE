"""Search API integration tests (Phase 2; live DB with trigram indexes)."""

from __future__ import annotations

import pytest
from sqlalchemy import text

from app.modules.places.search import SearchService
from app.platform.db import dispose_engine, get_session_factory
from tests.integration.conftest import _seed_route


@pytest.fixture
async def db_session():
    session = get_session_factory()()
    yield session
    await session.close()
    await dispose_engine()


async def _seed_aliases(db_session) -> None:
    ids = await _seed_route(db_session)
    await db_session.execute(
        text(
            "INSERT INTO entity_aliases (entity_type, entity_id, language, alias)"
            " VALUES ('stop', :sid, 'si', 'à·„à·à¶¸à·à¶œà¶¸ à·„à¶±à·Šà¶¯à·’à¶º'),"
            "        ('stop', :sid, 'ta', 'à®¹à¯‹à®®à®¾à®•à®® à®šà®¨à¯à®¤à®¿')"
        ),
        {"sid": ids["stop_a"]},
    )
    # A second, unrelated stop that also matches a generic query (ambiguity case).
    other = (
        await db_session.execute(
            text(
                "INSERT INTO stops (name, mode, location)"
                " VALUES ('Homagama Bus Stand', 'bus', 'POINT(79.9770 6.8445)')"
                " RETURNING id"
            )
        )
    ).scalar_one()
    await db_session.commit()
    return ids, other


async def test_search_finds_canonical_prefix_and_route_code(db_session) -> None:
    await _seed_aliases(db_session)
    service = SearchService()

    hits = await service.search(db_session, "homagama")
    assert hits
    names = {hit.name for hit in hits}
    assert "Homagama Junction" in names

    route_hits = await service.search(db_session, "138", entity_types={"route"})
    assert any(
        hit.entity_type == "route" and hit.matched_text.startswith("138") for hit in route_hits
    )


async def test_search_finds_sinhala_and_tamil_aliases(db_session) -> None:
    await _seed_aliases(db_session)
    service = SearchService()

    sinhala = await service.search(db_session, "à·„à·à¶¸à·à¶œà¶¸")
    assert any(hit.entity_type == "stop" and hit.language == "si" for hit in sinhala)

    tamil = await service.search(db_session, "à®¹à¯‹à®®à®¾à®•à®®")
    assert any(hit.entity_type == "stop" and hit.language == "ta" for hit in tamil)


async def test_ambiguous_results_are_all_listed(db_session) -> None:
    await _seed_aliases(db_session)
    service = SearchService()

    hits = await service.search(db_session, "homagama")
    stop_hits = [hit for hit in hits if hit.entity_type == "stop"]
    assert len(stop_hits) >= 2  # Junction + Bus Stand listed together, never auto-selected


async def test_search_result_carries_verification_status(db_session) -> None:
    await _seed_aliases(db_session)
    service = SearchService()
    hits = await service.search(db_session, "homagama")
    assert all(hit.verification_status == "unverified" for hit in hits if hit.entity_type == "stop")


async def test_empty_query_returns_nothing(db_session) -> None:
    service = SearchService()
    assert await service.search(db_session, "   ") == []
