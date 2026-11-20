"""One-off helper: reparse the latest archived Overpass snapshot (Phase 3).

Used when the live endpoint is unavailable but a checksum-verified snapshot is
already archived: the raw content is re-parsed with the current adapter version
(0.2.0 adds route shapes + stop access points) and upserted into the canonical
tables. New entities attach to the candidate dataset version created by the
snapshot's original run (candidate versions evolve until published — D-1), and
the reparse is recorded as its own SyncRun with parser_version
'0.2.0-reparse' so provenance stays exact: every new fact links to the same
archived snapshot bytes it was parsed from.

Run from backend/ (dev DB):  python scripts/reparse_latest_snapshot.py
"""

from __future__ import annotations

import asyncio
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text  # noqa: E402

from app.modules.data_ingestion.adapters.overpass import OverpassAdapter  # noqa: E402
from app.modules.data_ingestion.models import (  # noqa: E402
    DatasetVersion,
    DatasetVersionEntity,
    SyncRun,
)
from app.modules.data_ingestion.quality import validate_records  # noqa: E402
from app.modules.data_ingestion.service import UPSERTERS  # noqa: E402
from app.platform.config import get_settings  # noqa: E402
from app.platform.db import get_session_factory  # noqa: E402

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPARSE_PARSER_VERSION = "0.2.0-reparse"


async def reparse() -> int:
    session = get_session_factory()()
    try:
        row = (
            await session.execute(
                text(
                    "SELECT r.id, r.data_source_id, s.storage_uri, s.checksum_sha256,"
                    " s.id, s.extra_metadata"
                    " FROM sync_runs r"
                    " JOIN source_snapshots s ON s.id = r.snapshot_id"
                    " WHERE r.status = 'succeeded'"
                    " ORDER BY r.finished_at DESC LIMIT 1"
                )
            )
        ).one()
        run_id, source_id, storage_uri, _checksum, snapshot_id, extra_metadata = row
        version_row = (
            await session.execute(
                text("SELECT id FROM dataset_versions WHERE version_label = :l"),
                {"l": f"osm-overpass-{uuid.UUID(str(run_id)).hex[:8]}"},
            )
        ).scalar_one_or_none()
        if version_row is None:
            raise SystemExit("candidate version of the last successful run not found")

        content = (BACKEND_DIR / storage_uri).read_bytes()
        adapter = OverpassAdapter(bbox=get_settings().pilot_bbox)
        metadata = dict(extra_metadata or {})
        records = adapter.parse(content, metadata)

        reports = validate_records(records)
        failures = [report for report in reports if not report.passed]
        if failures:
            raise SystemExit(
                f"validation failed for {len(failures)} record(s); aborting (quarantine semantics)"
            )

        run = SyncRun(
            data_source_id=uuid.UUID(str(source_id)),
            started_at=datetime.now(UTC),
            status="started",
            snapshot_id=uuid.UUID(str(snapshot_id)),
            parser_version=REPARSE_PARSER_VERSION,
        )
        session.add(run)
        await session.flush()

        version = await session.get(DatasetVersion, uuid.UUID(str(version_row)))
        assert version is not None

        added = updated = unchanged = failed = 0
        for record in records:
            upserter = UPSERTERS.get(record.entity_hint)
            if upserter is None:
                failed += 1
                continue
            try:
                async with session.begin_nested():
                    result = await upserter.upsert(
                        session,
                        # A minimal stand-in: the upserters only read `.id`;
                        # the real source row already exists.
                        type("_Source", (), {"id": uuid.UUID(str(source_id))})(),  # type: ignore[arg-type]
                        uuid.UUID(str(snapshot_id)),
                        record,
                    )
                    if result.operation != "unchanged":
                        session.add(
                            DatasetVersionEntity(
                                dataset_version_id=version.id,
                                entity_type=result.entity_type,
                                entity_id=result.entity_id,
                                operation=result.operation,
                                changed_at=datetime.now(UTC),
                            )
                        )
            except Exception:  # noqa: BLE001 - record-level failure, run continues
                failed += 1
                continue
            if result.operation == "added":
                added += 1
            elif result.operation == "updated":
                updated += 1
            else:
                unchanged += 1

        run.status = "succeeded"
        run.records_in = len(records)
        run.records_added = added
        run.records_updated = updated
        run.records_unchanged = unchanged
        run.records_failed = failed
        run.finished_at = datetime.now(UTC)
        version.validation_summary = {
            **(version.validation_summary or {}),
            "reparse": {
                "parser_version": REPARSE_PARSER_VERSION,
                "snapshot_checksum": str(_checksum),
                "records_in": len(records),
                "records_added": added,
                "records_failed": failed,
                "reason": (
                    "live endpoint unavailable; shapes + access points imported"
                    " from the archived snapshot"
                ),
            },
        }
        await session.flush()
        await session.commit()
        print(
            f"reparse: in={len(records)} added={added} updated={updated}"
            f" unchanged={unchanged} failed={failed} version={version.version_label}"
        )
        return 0
    finally:
        await session.close()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(reparse()))
