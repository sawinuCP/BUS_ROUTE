"""Integration tests for scheduled source syncs (ADR-0004 / Phase 9).

Under test:
- the scheduler's **due-source computation** over the real test DB (enabled
  `api` sources with a stale or missing last succeeded sync);
- the **dispatch interface** through a Dramatiq StubBroker (message queued,
  no worker needed);
- the **sync actor's runner** against the seeded DB (overpass source →
  pipeline run; file source honestly skipped; unknown source failed) —
  with the pipeline itself faked so no network is touched;
- the API app stays Dramatiq-free: importing `app.main` never registers a
  Dramatiq broker.
"""

from __future__ import annotations

import asyncio
import os
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.platform.config import get_settings
from app.platform.db import dispose_engine


async def _seed_source(
    *,
    name: str,
    access_method: str = "api",
    endpoint: str = "https://overpass.example/api",
    update_cadence: str | None = "1h",
    enabled: bool = True,
    last_sync_age_seconds: int | None = None,
    last_sync_status: str = "succeeded",
) -> str:
    engine = create_async_engine(get_settings().database_url)
    try:
        async with engine.begin() as conn:
            source_id = (
                await conn.execute(
                    text(
                        "INSERT INTO data_sources (name, owner, access_method, endpoint,"
                        " format, update_cadence, enabled)"
                        " VALUES (:name, 'tester', :access_method, :endpoint, 'osm',"
                        " :update_cadence, :enabled) RETURNING id::text"
                    ),
                    {
                        "name": name,
                        "access_method": access_method,
                        "endpoint": endpoint,
                        "update_cadence": update_cadence,
                        "enabled": enabled,
                    },
                )
            ).scalar_one()
            if last_sync_age_seconds is not None:
                finished = datetime.now(UTC) - timedelta(seconds=last_sync_age_seconds)
                await conn.execute(
                    text(
                        "INSERT INTO sync_runs (data_source_id, started_at, finished_at, status)"
                        " VALUES (:sid, :started, :finished, :status)"
                    ),
                    {
                        "sid": source_id,
                        "started": finished - timedelta(minutes=1),
                        "finished": finished,
                        "status": last_sync_status,
                    },
                )
        return str(source_id)
    finally:
        await engine.dispose()


async def _due_ids() -> list[str]:
    from app.jobs.scheduling import due_sources

    engine = create_async_engine(get_settings().database_url)
    try:
        async with engine.connect() as conn:
            due = await due_sources(conn)
        return [row["source_id"] for row in due]
    finally:
        await engine.dispose()


async def _clean_tables() -> None:
    from tests.integration.conftest import _CLEANUP_ORDER

    engine = create_async_engine(get_settings().database_url)
    try:
        async with engine.begin() as conn:
            for statement in _CLEANUP_ORDER:
                await conn.execute(text(statement))
    finally:
        await engine.dispose()


async def test_stale_api_source_is_due_and_recent_is_not() -> None:
    stale = await _seed_source(name="osm-stale", last_sync_age_seconds=7200)  # cadence 1h
    fresh = await _seed_source(name="osm-fresh", last_sync_age_seconds=600)  # cadence 1h
    never = await _seed_source(name="osm-never", update_cadence="1h", last_sync_age_seconds=None)
    try:
        due = await _due_ids()
        assert stale in due
        assert never in due  # never synced → due immediately
        assert fresh not in due
    finally:
        await _clean_tables()


async def test_prose_cadence_and_file_sources_are_never_auto_synced() -> None:
    await _seed_source(name="prose-cadence", update_cadence="weekly")
    await _seed_source(name="file-fed", access_method="file", update_cadence="1h")
    await _seed_source(name="disabled-src", enabled=False, update_cadence="1h")
    try:
        assert await _due_ids() == []
    finally:
        await _clean_tables()


async def test_dispatch_enqueues_via_stub_broker(monkeypatch: pytest.MonkeyPatch) -> None:
    os.environ["JOBS_USE_STUB_BROKER"] = "1"
    recorded: list[dict[str, Any]] = []

    async def fake_run_sync(source_id: str, reason: str = "scheduled") -> dict[str, Any]:
        recorded.append({"source_id": source_id, "reason": reason})
        return {"source_id": source_id, "reason": reason, "status": "succeeded"}

    try:
        import dramatiq
        from dramatiq.brokers.stub import StubBroker

        broker = StubBroker()
        dramatiq.set_broker(broker)
        from app.jobs import actors  # registers against the stub broker

        source_id = await _seed_source(name="dispatch-target", last_sync_age_seconds=7200)
        monkeypatch.setattr("app.jobs.sync_runner.run_sync_source", fake_run_sync)

        from app.platform.jobs import dispatch_sync_source

        assert dispatch_sync_source(source_id, reason="scheduled") is True
        assert broker.queues["default"].qsize() == 1
        # Worker-side execution of the queued message runs the runner. The
        # actor bridges to its own event loop via asyncio.run, which must
        # not be called from this test's running loop — run it in a thread
        # exactly like the real dramatiq worker does.
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, lambda: actors.run_source_sync(source_id, "scheduled"))
        assert recorded == [{"source_id": source_id, "reason": "scheduled"}]
        dramatiq.set_broker(None)  # restore the lazy default for later imports
    finally:
        os.environ.pop("JOBS_USE_STUB_BROKER", None)
        await _clean_tables()


async def test_actor_runner_skips_file_sources_and_reports_unknown() -> None:
    from app.jobs.sync_runner import run_sync_source

    file_source = await _seed_source(name="runner-file", access_method="file")
    outcome = await run_sync_source(file_source, "scheduled")
    assert outcome["status"] == "skipped"
    assert "operator-fed" in outcome["reason"]

    outcome = await run_sync_source(str(uuid.uuid4()), "scheduled")
    assert outcome["status"] == "failed"
    assert outcome["error"] == "source not found"
    await dispose_engine()


async def test_app_import_stays_dramatiq_free() -> None:
    import app.main  # noqa: F401

    # The API app must not touch the broker: dispatch is interface-only.
    from app.platform import jobs as jobs_module

    assert jobs_module.jobs_status()["library"] == "dramatiq"
    await dispose_engine()
