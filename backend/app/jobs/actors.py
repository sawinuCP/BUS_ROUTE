"""Background job actors (ADR-0004: Dramatiq + Redis broker).

Imported only by the worker process (`dramatiq app.jobs.actors`) and tests
— the API app stays Dramatiq-free (dispatch goes through
`app.platform.jobs`). The Redis broker is configured from settings at
import; tests opt into a StubBroker by setting `JOBS_USE_STUB_BROKER=1`
*before* importing this module and calling `dramatiq.set_broker(StubBroker())`.

The sync actor wraps the async ingestion pipeline (its own event loop via
`asyncio.run`, engine disposed afterwards so no pooled connection ever
crosses loops — the I-13 rule for any per-loop engine use).
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

import dramatiq
from dramatiq.brokers.redis import RedisBroker

from app.platform.config import get_settings

logger = logging.getLogger(__name__)


def configure_broker_from_settings() -> None:
    """Attach the settings-driven Redis broker (worker entry)."""
    dramatiq.set_broker(RedisBroker(url=get_settings().redis_url))


def set_stub_broker() -> Any:
    """Install a StubBroker (tests). Returns the broker."""
    from dramatiq.brokers.stub import StubBroker

    broker = StubBroker()
    dramatiq.set_broker(broker)
    return broker


if os.environ.get("JOBS_USE_STUB_BROKER") != "1":
    configure_broker_from_settings()


@dramatiq.actor(
    max_retries=3,
    min_backoff=60_000,
    max_backoff=3_600_000,
    time_limit=3_600_000,  # a full sync run can take minutes (Overpass timeout 300s+)
)
def run_source_sync(source_id: str, reason: str = "scheduled") -> None:
    """Sync one source through the ingestion pipeline (retry with backoff)."""
    from app.jobs.sync_runner import run_sync_source

    outcome = asyncio.run(run_sync_source(source_id, reason))
    logger.info("job finished", extra={"job": "run_source_sync", **outcome})
