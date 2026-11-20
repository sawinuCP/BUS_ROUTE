"""Fixtures for integration tests against the live canonical database.

These tests exercise real PostgreSQL/PostGIS behaviour (constraints, indexes,
geometry roundtrips) using the configured DATABASE_URL. They skip when the
database is unreachable so unit runs stay green without infrastructure.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, create_async_engine

from app.platform.config import get_settings

# Children first — used to reset canonical rows between tests that commit
# (API-level tests commit; service/schema tests roll back transactions).
_CLEANUP_ORDER: tuple[str, ...] = (
    "DELETE FROM active_dataset",
    "DELETE FROM dataset_version_entities",
    "DELETE FROM data_change_audit",
    "DELETE FROM verification_records",
    "DELETE FROM entity_aliases",
    "DELETE FROM place_access_points",
    "DELETE FROM places",
    "DELETE FROM fare_rules",
    "DELETE FROM transfer_connections",
    "DELETE FROM route_pattern_stops",
    "DELETE FROM route_patterns",
    "DELETE FROM stop_access_points",
    "DELETE FROM stops",
    "DELETE FROM route_shapes",
    "DELETE FROM transport_routes",
    "DELETE FROM transport_agencies",
    "DELETE FROM localities",
    "DELETE FROM source_records",
    "DELETE FROM source_snapshots",
    "DELETE FROM sync_runs",
    "DELETE FROM data_sources",
    "DELETE FROM dataset_versions",
)


@pytest.fixture(autouse=True)
async def clean_canonical_tables() -> AsyncIterator[None]:
    """Empty the canonical tables before each integration test.

    Guarantees tests are independent even when earlier tests (or manual API
    calls) committed rows. Runs before the test's own transaction opens.
    """
    engine = create_async_engine(get_settings().database_url)
    try:
        try:
            async with engine.begin() as conn:
                for statement in _CLEANUP_ORDER:
                    await conn.execute(text(statement))
        except Exception:  # noqa: BLE001 - unreachable infra must skip, not fail
            pytest.skip("canonical database not reachable — skipping integration tests")
        yield
    finally:
        await engine.dispose()


@pytest.fixture
async def db_conn() -> AsyncIterator[AsyncConnection]:
    """A connection wrapped in one transaction; every test rolls back cleanly."""
    engine = create_async_engine(get_settings().database_url)
    try:
        conn = await engine.connect()
        transaction = await conn.begin()
        try:
            yield conn
        finally:
            await transaction.rollback()
            await conn.close()
    finally:
        await engine.dispose()


async def _seed_route(db_conn: AsyncConnection) -> dict[str, object]:
    """Seed agency → route → pattern → two stops and return their IDs."""
    agency_id = (
        await db_conn.execute(
            text(
                "INSERT INTO transport_agencies (name, operator_type)"
                " VALUES ('Test SLTB', 'public') RETURNING id"
            )
        )
    ).scalar_one()
    route_id = (
        await db_conn.execute(
            text(
                "INSERT INTO transport_routes (agency_id, route_code, route_name, mode, status)"
                " VALUES (:agency, '138', 'Homagama–Kollupitiya', 'bus', 'draft')"
                " RETURNING id"
            ),
            {"agency": agency_id},
        )
    ).scalar_one()
    pattern_id = (
        await db_conn.execute(
            text(
                "INSERT INTO route_patterns (route_id, pattern_code, direction_id,"
                " origin_label, destination_label)"
                " VALUES (:route, '138-A-D0', 0, 'Homagama', 'Kollupitiya') RETURNING id"
            ),
            {"route": route_id},
        )
    ).scalar_one()
    stop_a = (
        await db_conn.execute(
            text(
                "INSERT INTO stops (name, mode, location, stop_type)"
                " VALUES ('Homagama Junction', 'bus', 'POINT(79.9777 6.8440)', 'roadside')"
                " RETURNING id"
            )
        )
    ).scalar_one()
    stop_b = (
        await db_conn.execute(
            text(
                "INSERT INTO stops (name, mode, location, stop_type)"
                " VALUES ('Kollupitiya Junction', 'bus', 'POINT(79.8483 6.9107)', 'roadside')"
                " RETURNING id"
            )
        )
    ).scalar_one()
    return {
        "agency_id": agency_id,
        "route_id": route_id,
        "pattern_id": pattern_id,
        "stop_a": stop_a,
        "stop_b": stop_b,
    }
