"""Minimal journey reconstruction test (Phase 1.1 acceptance check).

A route variant must be reconstructable in order, with multilingual aliases,
a transfer between access points, and geographic roundtrip fidelity — the data
the instruction generator will consume in Phase 5.
"""

from __future__ import annotations

from sqlalchemy import text

from tests.integration.conftest import _seed_route


async def test_ordered_journey_reconstruction(db_conn) -> None:
    ids = await _seed_route(db_conn)

    # Three ordered calls with the middle stop also having a boarding access point.
    for stop_id, sequence in (
        (ids["stop_a"], 1),
        (ids["stop_b"], 2),
        (ids["stop_a"], 3),  # loop back for test purposes
    ):
        await db_conn.execute(
            text(
                "INSERT INTO route_pattern_stops (pattern_id, stop_id, sequence)"
                " VALUES (:p, :s, :seq)"
            ),
            {"p": ids["pattern_id"], "s": stop_id, "seq": sequence},
        )

    ordered = await db_conn.execute(
        text(
            "SELECT s.name, rps.sequence"
            " FROM route_pattern_stops rps JOIN stops s ON s.id = rps.stop_id"
            " WHERE rps.pattern_id = :p ORDER BY rps.sequence"
        ),
        {"p": ids["pattern_id"]},
    )
    rows = [(row[0], row[1]) for row in ordered]
    assert rows == [
        ("Homagama Junction", 1),
        ("Kollupitiya Junction", 2),
        ("Homagama Junction", 3),
    ]


async def test_stop_coordinates_roundtrip(db_conn) -> None:
    await _seed_route(db_conn)
    row = await db_conn.execute(
        text(
            "SELECT ST_X(location::geometry), ST_Y(location::geometry)"
            " FROM stops WHERE name = 'Homagama Junction'"
        )
    )
    lon, lat = row.one()
    # Colombo-area coordinates: WGS84 lon/lat order preserved in storage.
    assert abs(lon - 79.9777) < 1e-4
    assert abs(lat - 6.8440) < 1e-4


async def test_multilingual_aliases_attach_to_stop(db_conn) -> None:
    ids = await _seed_route(db_conn)
    for language, alias in (
        ("si", "හෝමාගම හන්දිය"),
        ("ta", "ஹோமாகம சந்தி"),
        ("en", "Homagama Junction (Homagama Town)"),
    ):
        await db_conn.execute(
            text(
                "INSERT INTO entity_aliases (entity_type, entity_id, language, alias)"
                " VALUES ('stop', :e, :l, :a)"
            ),
            {"e": ids["stop_a"], "l": language, "a": alias},
        )
    stored = await db_conn.execute(
        text(
            "SELECT language, alias FROM entity_aliases"
            " WHERE entity_type = 'stop' AND entity_id = :e ORDER BY language"
        ),
        {"e": ids["stop_a"]},
    )
    aliases = {lang: name for lang, name in stored}
    assert set(aliases) == {"en", "si", "ta"}
    assert aliases["si"] == "හෝමාගම හන්දිය"


async def test_explicit_transfer_between_access_points(db_conn) -> None:
    ids = await _seed_route(db_conn)
    access_a = (
        await db_conn.execute(
            text(
                "INSERT INTO stop_access_points (stop_id, access_type, side_or_platform)"
                " VALUES (:s, 'roadside', 'towards Colombo') RETURNING id"
            ),
            {"s": ids["stop_a"]},
        )
    ).scalar_one()
    access_b = (
        await db_conn.execute(
            text(
                "INSERT INTO stop_access_points (stop_id, access_type, side_or_platform)"
                " VALUES (:s, 'bay', 'Bay 2') RETURNING id"
            ),
            {"s": ids["stop_b"]},
        )
    ).scalar_one()
    await db_conn.execute(
        text(
            "INSERT INTO transfer_connections"
            " (from_access_point_id, to_access_point_id, walk_distance_m,"
            " estimated_walk_seconds, verification_status)"
            " VALUES (:a, :b, 250, 190, 'verified')"
        ),
        {"a": access_a, "b": access_b},
    )
    transfer = await db_conn.execute(
        text(
            "SELECT walk_distance_m, verification_status FROM transfer_connections"
            " WHERE from_access_point_id = :a"
        ),
        {"a": access_a},
    )
    distance, status = transfer.one()
    assert distance == 250
    assert status == "verified"
