"""Async runner behind the sync actor (own event loop, own session)."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from app.platform.db import dispose_engine, get_session_factory

logger = logging.getLogger(__name__)


async def run_sync_source(source_id: str, reason: str = "scheduled") -> dict[str, Any]:
    """Run the ingestion pipeline for one source; commit; return the outcome.

    Mirrors the admin sync endpoint's logic (overpass endpoint per source
    with the configured fallback) but without an HTTP request. File-backed
    sources are skipped honestly: their payloads arrive via the operator
    (a file path cannot be re-fetched on a schedule).
    """
    from app.modules.data_ingestion.adapters.overpass import OverpassAdapter
    from app.modules.data_ingestion.archive import LocalFilesystemArchive
    from app.modules.data_ingestion.models import DataSource
    from app.modules.data_ingestion.service import IngestionService
    from app.platform.config import get_settings

    settings = get_settings()
    factory = get_session_factory()
    try:
        async with factory() as session:
            try:
                source = await session.get(DataSource, uuid.UUID(source_id))
                if source is None:
                    outcome = {
                        "source_id": source_id,
                        "status": "failed",
                        "error": "source not found",
                    }
                elif (source.access_method or "") != "api":
                    outcome = {
                        "source_id": source_id,
                        "status": "skipped",
                        "reason": (
                            f"access_method '{source.access_method or 'unset'}' is not"
                            " schedulable — file/manual sources are operator-fed"
                        ),
                    }
                else:
                    service = IngestionService(
                        archive=LocalFilesystemArchive(settings.raw_archive_dir)
                    )
                    adapter = OverpassAdapter(
                        bbox=settings.pilot_bbox,
                        endpoint=source.endpoint or settings.osm_overpass_endpoint,
                        fallback_endpoint=settings.osm_overpass_fallback,
                        timeout_seconds=settings.osm_overpass_timeout_seconds,
                    )
                    result = await service.run_sync(session, source, adapter)
                    await session.commit()
                    outcome = {
                        "source_id": source_id,
                        "reason": reason,
                        "run_id": str(result.run_id),
                        "status": str(result.status),
                        "records_added": str(result.records_added),
                        "records_updated": str(result.records_updated),
                        "records_failed": str(result.records_failed),
                    }
            except Exception as exc:  # noqa: BLE001 - the actor logs, dramatiq retries
                outcome = {
                    "source_id": source_id,
                    "reason": reason,
                    "status": "failed",
                    "error": type(exc).__name__,
                }
                logger.exception("scheduled sync failed", extra={"source_id": source_id})
    finally:
        # Own event loop per actor invocation (asyncio.run) — never leave
        # pooled connections attached to a dead loop (I-13 rule).
        await dispose_engine()
    return outcome
