"""QA review queue (Phase 1.4).

Prioritized, read-only list of items that need human review — derived from the
same facts as the data-quality report. Items are actionable references
(entity type + id + suggested action); resolution happens through the
verification/moderation flow, never by silently mutating canonical data.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class QAQueueService:
    async def items(self, session: AsyncSession) -> dict[str, Any]:
        items: list[dict[str, Any]] = []

        # Patterns whose ordered calls are missing or incomplete.
        rows = await session.execute(
            text(
                "SELECT rp.id, rp.pattern_code, rp.origin_label, rp.destination_label,"
                " count(rps.id) AS calls"
                " FROM route_patterns rp"
                " LEFT JOIN route_pattern_stops rps ON rps.pattern_id = rp.id"
                " GROUP BY rp.id, rp.pattern_code, rp.origin_label, rp.destination_label"
                " HAVING count(rps.id) < 2"
            )
        )
        for row in rows:
            items.append(
                {
                    "id": f"pattern-under-two:{row[0]}",
                    "entity_type": "route_pattern",
                    "entity_id": str(row[0]),
                    "severity": "warning",
                    "description": (
                        f"Pattern {row[1] or '(no code)'}"
                        f" ({row[2] or '?'} → {row[3] or '?'}) has {row[4]} ordered"
                        " call(s); fewer than 2"
                    ),
                    "suggested_action": (
                        "field-verify the variant (ride-along) or resolve its member stops"
                        " in the source data; exclude from planning until fixed"
                    ),
                }
            )

        # Routes without agency attribution.
        rows = await session.execute(
            text("SELECT id, route_code FROM transport_routes WHERE agency_id IS NULL")
        )
        for row in rows:
            items.append(
                {
                    "id": f"route-agency:{row[0]}",
                    "entity_type": "route",
                    "entity_id": str(row[0]),
                    "severity": "info",
                    "description": f"Route {row[1]} has no agency attribution",
                    "suggested_action": (
                        "identify the operator during field verification; OSM"
                        " relations rarely carry operator data"
                    ),
                }
            )

        # Stops without coordinates.
        rows = await session.execute(text("SELECT id, name FROM stops WHERE location IS NULL"))
        for row in rows:
            items.append(
                {
                    "id": f"stop-coords:{row[0]}",
                    "entity_type": "stop",
                    "entity_id": str(row[0]),
                    "severity": "warning",
                    "description": f"Stop '{row[1]}' has no coordinates",
                    "suggested_action": "capture an on-site GPS pin during the field survey",
                }
            )

        severity_rank = {"warning": 0, "info": 1}
        items.sort(key=lambda item: (severity_rank.get(item["severity"], 9), item["id"]))

        counts: dict[str, int] = {}
        for item in items:
            counts[item["severity"]] = counts.get(item["severity"], 0) + 1

        return {
            "queue_type": "qa_review_queue",
            "note": (
                "Read-only review queue. Resolution flows through"
                " verification_records and the candidate-version pipeline —"
                " canonical data is never changed silently."
            ),
            "total": len(items),
            "counts_by_severity": counts,
            "items": items,
        }
