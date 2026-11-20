"""Pilot coverage scorecard (Phase 1.4).

Scores route-by-route data completeness for the ratified pilot corridor
(owner decision D-2: central Colombo). Weights are explicit and documented so
the score is transparent, never an invented "confidence" number. The scorecard
informs field-verification priorities; it does not measure service quality or
operational status.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

# Transparent scoring weights (sum = 100) per route:
#   ordered calls recorded for its variants (sequence completeness)
#   stops of those calls having coordinates
#   variants present (>=2 = full marks)
#   multilingual aliases recorded for its stops
#   agency attribution present
_WEIGHTS = {"calls": 30, "coordinates": 20, "variants": 20, "aliases": 15, "agency": 15}


class CoverageScorecardService:
    """Route-by-route completeness scoring for the pilot corridor."""

    async def build(self, session: AsyncSession) -> dict[str, Any]:
        routes = [
            dict(row._mapping)
            for row in await session.execute(
                text(
                    "SELECT r.id, r.route_code, r.route_name, r.mode, r.status,"
                    " a.name AS agency_name"
                    " FROM transport_routes r"
                    " LEFT JOIN transport_agencies a ON a.id = r.agency_id"
                    " ORDER BY r.route_code"
                )
            )
        ]
        rows: list[dict[str, Any]] = []
        for route in routes:
            variants = (
                await session.execute(
                    text("SELECT count(*) FROM route_patterns WHERE route_id = :id"),
                    {"id": route["id"]},
                )
            ).scalar_one()
            calls = (
                await session.execute(
                    text(
                        "SELECT count(*) FROM route_pattern_stops rps"
                        " JOIN route_patterns rp ON rp.id = rps.pattern_id"
                        " WHERE rp.route_id = :id"
                    ),
                    {"id": route["id"]},
                )
            ).scalar_one()
            stops_with_coords = (
                await session.execute(
                    text(
                        "SELECT count(*) FROM route_pattern_stops rps"
                        " JOIN route_patterns rp ON rp.id = rps.pattern_id"
                        " JOIN stops s ON s.id = rps.stop_id"
                        " WHERE rp.route_id = :id AND s.location IS NOT NULL"
                    ),
                    {"id": route["id"]},
                )
            ).scalar_one()
            aliases = (
                await session.execute(
                    text(
                        "SELECT count(*) FROM entity_aliases ea"
                        " WHERE ea.entity_type = 'stop' AND EXISTS ("
                        "   SELECT 1 FROM route_pattern_stops rps"
                        "   JOIN route_patterns rp ON rp.id = rps.pattern_id"
                        "   WHERE rp.route_id = :id AND rps.stop_id = ea.entity_id)"
                    ),
                    {"id": route["id"]},
                )
            ).scalar_one()

            parts = {
                "calls": min(1.0, calls / 10.0) if calls else 0.0,  # 10+ calls = full marks
                "coordinates": (stops_with_coords / calls) if calls else 0.0,
                "variants": min(1.0, variants / 2.0),  # >=2 variants = full marks
                "aliases": min(1.0, aliases / 4.0),
                "agency": 1.0 if route["agency_name"] else 0.0,
            }
            score = round(sum(_WEIGHTS[key] * value for key, value in parts.items()))

            rows.append(
                {
                    "route_code": route["route_code"],
                    "route_name": route["route_name"],
                    "mode": route["mode"],
                    "status": route["status"],
                    "agency": route["agency_name"],
                    "variants": variants,
                    "ordered_calls": calls,
                    "calls_with_coordinates": stops_with_coords,
                    "stop_aliases": aliases,
                    "score": score,
                    "score_parts": {key: round(value, 2) for key, value in parts.items()},
                }
            )

        rows.sort(key=lambda row: row["score"])
        average = round(sum(row["score"] for row in rows) / len(rows), 1) if rows else 0.0

        return {
            "report_type": "pilot_coverage_scorecard",
            "note": (
                "Scores measure IMPORTED DATA COMPLETENESS per route for the pilot"
                " corridor only. They do not measure service quality, operational"
                " status or real-world accuracy — field verification"
                " (docs/research/field-verification-approach.md) provides that."
            ),
            "scoring_weights": _WEIGHTS,
            "routes_scored": len(rows),
            "average_score": average,
            "routes": rows,
        }

    @staticmethod
    async def render_markdown(report: dict[str, Any]) -> str:
        lines = [
            "# Pilot coverage scorecard",
            "",
            f"*Routes scored:* {report['routes_scored']} · *average score:*"
            f" {report['average_score']}/100",
            "",
            f"> {report['note']}",
            "",
            "| Route | Variants | Calls | w/ coords | Aliases | Agency | Score |",
            "|---|---|---|---|---|---|---|",
        ]
        for row in report["routes"]:
            lines.append(
                f"| {row['route_code']} {row['route_name'] or ''} | {row['variants']}"
                f" | {row['ordered_calls']} | {row['calls_with_coordinates']}"
                f" | {row['stop_aliases']} | {row['agency'] or '—'} | {row['score']}/100 |"
            )
        lines.append("")
        return "\n".join(lines)
