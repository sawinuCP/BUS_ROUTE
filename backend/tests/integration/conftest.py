"""Fixtures for integration tests against the dedicated test database (I-18/I-21).

Integration tests run against `journey_planner_test` (created + migrated
automatically below), so test cleanup never wipes development data. Tests skip
when the database is unreachable so unit runs stay green without infrastructure.

I-21: the test-DB override is applied here at conftest-import time — BEFORE any
test module (and therefore any app code) can call `get_settings()`. Without
this, Alembic's env.py and the cleanup fixture resolved the settings default
and migrated/wiped the development database instead of the test database.
"""

from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncIterator, Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config as alembic_config
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, create_async_engine

from app.platform.config import Settings, get_settings

# Route every settings read in this pytest process to the dedicated test DB.
# Must happen before any other module calls get_settings() (conftest imports
# always run first), and before Alembic's env.py resolves its URL.
_BASE_SETTINGS = Settings()
_TEST_DATABASE_URL = _BASE_SETTINGS.database_url.rsplit("/", 1)[0] + "/journey_planner_test"
os.environ["DATABASE_URL"] = _TEST_DATABASE_URL


@pytest.fixture(scope="session", autouse=True)
def _migrate_test_database() -> Iterator[None]:
    """Create (if needed) and migrate the dedicated test database once per run.

    Synchronous on purpose: a session-scoped async fixture would need a
    session-scoped event loop, which conflicts with per-test loops.
    """
    settings = get_settings()
    admin_url = settings.database_url.rsplit("/", 1)[0] + "/postgres"

    async def _ensure_database() -> None:
        admin_engine = create_async_engine(admin_url, isolation_level="AUTOCOMMIT")
        try:
            async with admin_engine.connect() as conn:
                exists = (
                    await conn.execute(
                        text("SELECT 1 FROM pg_database WHERE datname = 'journey_planner_test'")
                    )
                ).scalar_one_or_none()
                if exists is None:
                    await conn.execute(text("CREATE DATABASE journey_planner_test"))
        finally:
            await admin_engine.dispose()

    asyncio.run(_ensure_database())

    # Migrate the test DB via Alembic (env.py runs its own asyncio loop).
    alembic_ini = Path(__file__).resolve().parents[2] / "alembic.ini"
    alembic_cfg = alembic_config(str(alembic_ini))
    command.upgrade(alembic_cfg, "head")
    yield


# Children first — resets canonical rows between tests that commit
# (API-level tests commit; service/schema tests roll back transactions).
_CLEANUP_ORDER: tuple[str, ...] = (
    "DELETE FROM active_dataset",
    "DELETE FROM transport_reports",
    "DELETE FROM journey_events",
    "DELETE FROM journey_sessions",
    "DELETE FROM saved_journeys",
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
    """Empty the canonical tables before each integration test (test DB only)."""
    engine = create_async_engine(get_settings().database_url)
    try:
        try:
            async with engine.begin() as conn:
                for statement in _CLEANUP_ORDER:
                    await conn.execute(text(statement))
        except Exception:  # noqa: BLE001 - unreachable infra must skip, not fail
            pytest.skip("test database not reachable — skipping integration tests")
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
