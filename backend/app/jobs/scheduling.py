"""Per-source refresh scheduling (architecture doc 09 §4–§5).

Doc 09 §5: "Do not invent one universal refresh frequency. Configure per
source." The `data_sources.update_cadence` field is human-readable policy
text; scheduled syncs use a compact machine-readable subset of it:
`<N><m|h|d>` (e.g. `30m`, `12h`, `7d`). Sources without a parseable cadence
(or with `access_method != 'api'`) are never auto-synced — the operator
runs those explicitly through the admin endpoints.

A source is **due** when its latest succeeded sync run is older than its
cadence (or it has never been synced). Candidate syncs still produce
candidate dataset versions — nothing is ever auto-published (doc 09 §7).
"""

from __future__ import annotations

import logging
import re
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

logger = logging.getLogger(__name__)

_CADENCE = re.compile(r"^(\d+)([mhd])$", re.IGNORECASE)
_UNIT_SECONDS = {"m": 60, "h": 3600, "d": 86400}


def parse_cadence(value: str | None) -> int | None:
    """Parse `60m`/`12h`/`7d` into seconds; None when not schedulable."""
    if not value:
        return None
    match = _CADENCE.match(value.strip())
    if match is None:
        return None
    return int(match.group(1)) * _UNIT_SECONDS[match.group(2).lower()]


async def due_sources(
    conn: AsyncConnection, *, now: datetime | None = None
) -> list[dict[str, Any]]:
    """Enabled `api` sources whose cadence is parseable and stale."""
    current = now or datetime.now(UTC)
    rows = (
        (
            await conn.execute(
                text(
                    "SELECT ds.id::text AS id, ds.name, ds.update_cadence,"
                    " (SELECT MAX(sr.finished_at) FROM sync_runs sr"
                    "   WHERE sr.data_source_id = ds.id"
                    "     AND sr.status = 'succeeded') AS last_sync"
                    " FROM data_sources ds"
                    " WHERE ds.enabled = true AND ds.access_method = 'api'"
                )
            )
        )
        .mappings()
        .all()
    )
    due: list[dict[str, Any]] = []
    for row in rows:
        cadence = parse_cadence(row["update_cadence"])
        if cadence is None:
            continue
        last = row["last_sync"]
        if last is not None and current - last < timedelta(seconds=cadence):
            continue
        due.append(
            {
                "source_id": str(row["id"]),
                "name": row["name"],
                "cadence": cadence,
                "last_sync": last.isoformat() if last else None,
            }
        )
    return due
