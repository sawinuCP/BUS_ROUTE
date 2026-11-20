"""Schema-invariant integration tests (Phase 1.1 acceptance checks)."""

from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from tests.integration.conftest import _seed_route


async def test_postgis_extension_enabled(db_conn) -> None:
    result = await db_conn.execute(
        text("SELECT count(*) FROM pg_extension WHERE extname = 'postgis'")
    )
    assert result.scalar_one() == 1


async def test_core_tables_exist(db_conn) -> None:
    expected = {
        "data_sources",
        "source_snapshots",
        "source_records",
        "sync_runs",
        "dataset_versions",
        "dataset_version_entities",
        "active_dataset",
        "transport_agencies",
        "transport_routes",
        "route_shapes",
        "localities",
        "stops",
        "stop_access_points",
        "route_patterns",
        "route_pattern_stops",
        "transfer_connections",
        "fare_rules",
        "places",
        "place_access_points",
        "entity_aliases",
        "verification_records",
        "data_change_audit",
    }
    result = await db_conn.execute(
        text(
            "SELECT table_name FROM information_schema.tables"
            " WHERE table_schema = 'public' AND table_type = 'BASE TABLE'"
        )
    )
    actual = {row[0] for row in result}
    missing = expected - actual
    assert not missing, f"canonical tables missing: {sorted(missing)}"


async def test_gist_indexes_on_geography_columns(db_conn) -> None:
    result = await db_conn.execute(
        text(
            "SELECT tablename, indexname FROM pg_indexes"
            " WHERE indexdef ILIKE '%USING gist%' AND schemaname = 'public'"
        )
    )
    indexed = {(row[0], row[1]) for row in result}
    for table in ("stops", "stop_access_points", "route_shapes", "transfer_connections"):
        assert any(t == table for t, _ in indexed), f"no GiST index on {table}"


async def test_pattern_stop_sequence_unique(db_conn) -> None:
    ids = await _seed_route(db_conn)
    await db_conn.execute(
        text("INSERT INTO route_pattern_stops (pattern_id, stop_id, sequence) VALUES (:p, :s, 1)"),
        {"p": ids["pattern_id"], "s": ids["stop_a"]},
    )
    savepoint = await db_conn.begin_nested()
    try:
        await db_conn.execute(
            text(
                "INSERT INTO route_pattern_stops (pattern_id, stop_id, sequence) VALUES (:p, :s, 1)"
            ),
            {"p": ids["pattern_id"], "s": ids["stop_b"]},
        )
    except IntegrityError:
        await savepoint.rollback()
    else:
        await savepoint.commit()
        pytest.fail("duplicate (pattern_id, sequence) was accepted — core invariant broken")


async def test_pattern_stop_sequence_must_be_positive(db_conn) -> None:
    ids = await _seed_route(db_conn)
    savepoint = await db_conn.begin_nested()
    try:
        await db_conn.execute(
            text(
                "INSERT INTO route_pattern_stops (pattern_id, stop_id, sequence) VALUES (:p, :s, 0)"
            ),
            {"p": ids["pattern_id"], "s": ids["stop_a"]},
        )
    except IntegrityError:
        await savepoint.rollback()
    else:
        await savepoint.commit()
        pytest.fail("sequence 0 was accepted")


async def test_transfer_cannot_connect_point_to_itself(db_conn) -> None:
    ids = await _seed_route(db_conn)
    access_id = (
        await db_conn.execute(
            text(
                "INSERT INTO stop_access_points (stop_id, access_type)"
                " VALUES (:s, 'roadside') RETURNING id"
            ),
            {"s": ids["stop_a"]},
        )
    ).scalar_one()
    savepoint = await db_conn.begin_nested()
    try:
        await db_conn.execute(
            text(
                "INSERT INTO transfer_connections"
                " (from_access_point_id, to_access_point_id)"
                " VALUES (:a, :a)"
            ),
            {"a": access_id},
        )
    except IntegrityError:
        await savepoint.rollback()
    else:
        await savepoint.commit()
        pytest.fail("self-transfer was accepted")


async def test_active_dataset_is_singleton(db_conn) -> None:
    version_id = (
        await db_conn.execute(
            text(
                "INSERT INTO dataset_versions (version_label, status)"
                " VALUES ('test-version-001', 'candidate') RETURNING id"
            )
        )
    ).scalar_one()
    await db_conn.execute(
        text("INSERT INTO active_dataset (dataset_version_id, activated_at) VALUES (:v, now())"),
        {"v": version_id},
    )
    savepoint = await db_conn.begin_nested()
    try:
        await db_conn.execute(
            text(
                "INSERT INTO active_dataset (id, dataset_version_id, activated_at)"
                " VALUES (2, :v, now())"
            ),
            {"v": version_id},
        )
    except IntegrityError:
        await savepoint.rollback()
    else:
        await savepoint.commit()
        pytest.fail("second active_dataset row was accepted")
