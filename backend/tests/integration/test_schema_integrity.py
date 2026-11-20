"""Referential-integrity and scope integration tests (Phase 1.1)."""

from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError


async def test_pattern_stop_requires_existing_pattern(db_conn) -> None:
    from uuid import uuid4

    savepoint = await db_conn.begin_nested()
    try:
        await db_conn.execute(
            text(
                "INSERT INTO route_pattern_stops (pattern_id, stop_id, sequence) VALUES (:p, :s, 1)"
            ),
            {"p": uuid4(), "s": uuid4()},
        )
    except IntegrityError:
        await savepoint.rollback()
    else:
        await savepoint.commit()
        pytest.fail("orphan pattern stop was accepted")


async def test_fare_requires_scope(db_conn) -> None:
    savepoint = await db_conn.begin_nested()
    try:
        await db_conn.execute(text("INSERT INTO fare_rules (amount) VALUES (50.00)"))
    except IntegrityError:
        await savepoint.rollback()
    else:
        await savepoint.commit()
        pytest.fail("fare without any scope was accepted")
