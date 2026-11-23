"""Scheduler loop (ADR-0004): dispatches due source syncs.

Run as its own process (compose service `scheduler`):
    python -m app.jobs.scheduler

Off by default (`SCHEDULED_SYNC_ENABLED=false`) — the pilot refreshes
sources on demand via the admin endpoints; enable per deployment. Every
interval it computes the due sources (per-source cadence, doc 09 §5) and
dispatches one `run_source_sync` job each through the platform dispatch
interface (Dramatiq + Redis). Dispatch failures are logged and skipped —
the next tick retries (due-ness is time-based, so nothing is lost).
"""

from __future__ import annotations

import asyncio
import logging

from app.platform.config import get_settings
from app.platform.db import dispose_engine, get_session_factory
from app.platform.jobs import dispatch_sync_source, jobs_available

logger = logging.getLogger(__name__)


async def dispatch_due_syncs() -> list[str]:
    """Compute and dispatch due source syncs; returns dispatched source ids."""
    from app.jobs.scheduling import due_sources

    if not jobs_available():
        logger.warning("jobs are disabled — scheduler cannot dispatch")
        return []
    factory = get_session_factory()
    dispatched: list[str] = []
    try:
        async with factory() as session:
            conn = await session.connection()
            due = await due_sources(conn)
        for source in due:
            if dispatch_sync_source(source["source_id"], reason="scheduled"):
                dispatched.append(source["source_id"])
                logger.info(
                    "scheduled sync dispatched",
                    extra={"source_id": source["source_id"], "name": source["name"]},
                )
    finally:
        await dispose_engine()
    return dispatched


async def main() -> None:
    settings = get_settings()
    logging.basicConfig(
        level=settings.log_level.upper(), format="%(asctime)s %(levelname)s %(name)s %(message)s"
    )
    if not settings.scheduled_sync_enabled:
        print(
            "scheduler disabled (SCHEDULED_SYNC_ENABLED=false) — nothing to do."
            " Enable it in the environment to start the per-source sync loop."
        )
        return
    logger.info(
        "scheduler started",
        extra={"interval_seconds": settings.scheduled_sync_interval_seconds},
    )
    while True:
        try:
            await dispatch_due_syncs()
        except Exception as exc:  # noqa: BLE001 - the loop must survive errors
            logger.exception("scheduler tick failed", extra={"error_type": type(exc).__name__})
        await asyncio.sleep(settings.scheduled_sync_interval_seconds)


if __name__ == "__main__":
    asyncio.run(main())
