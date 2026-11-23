"""Background job dispatch interface (ADR-0004, plan §3.1).

ADR-0004 (accepted) chose **Dramatiq** with a Redis broker, wrapped behind
a thin internal task-dispatch interface in `platform` so the library stays
replaceable. This module is that interface:

- The API app imports only `dispatch_*` functions — Dramatiq is imported
  lazily inside the dispatch call, so the app (and tests without the
  library) never depend on it.
- `jobs_enabled` (env `JOBS_ENABLED`, default true) turns dispatch into an
  honest no-op (`False`) — e.g. a deployment that runs no worker/scheduler.
- Actors live in `app.jobs.actors` (imported by the worker process and
  tests); the scheduler lives in `app.jobs.scheduler`.
- Deliberately single-node/simple per the MVP job profile (scheduled,
  moderate-volume, retry-sensitive pipeline work).

Failures to enqueue are logged and reported as `False` — dispatch is
fire-and-forget and must never break the caller.
"""

from __future__ import annotations

import logging
from typing import Any

from app.platform.config import get_settings

logger = logging.getLogger(__name__)


def jobs_available() -> bool:
    """True when background jobs are enabled for this deployment."""
    return get_settings().jobs_enabled


def dispatch_sync_source(source_id: str, *, reason: str = "manual") -> bool:
    """Enqueue one source-sync job. Returns True iff enqueued.

    `reason` is recorded in the job log line (scheduler | manual | report).
    """
    if not jobs_available():
        return False
    try:
        from app.jobs.actors import run_source_sync

        run_source_sync.send(source_id, reason)
        logger.info(
            "job dispatched",
            extra={"job": "run_source_sync", "source_id": source_id, "reason": reason},
        )
        return True
    except Exception as exc:  # noqa: BLE001 - dispatch must never break the caller
        logger.warning(
            "job dispatch failed",
            extra={
                "job": "run_source_sync",
                "source_id": source_id,
                "error_type": type(exc).__name__,
            },
        )
        return False


def jobs_status() -> dict[str, Any]:
    """Honest status for the health/dashboard surfaces."""
    return {
        "enabled": jobs_available(),
        "library": "dramatiq",
        "note": (
            "Jobs are dispatched via Dramatiq + Redis (ADR-0004). The worker"
            " and scheduler processes must be running for scheduled syncs."
        ),
    }
