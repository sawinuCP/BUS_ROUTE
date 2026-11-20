"""Data-quality report builder (plan Phase 1: data-quality report).

Builds a structured report for one dataset version from database facts only:
candidate diffs, network coverage stats and QA checks. Every gap is stated
honestly (unknown stays unknown); the report never implies operational status
or verification that has not happened.
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.data_ingestion.models import DatasetVersion


class QualityReportService:
    """Builds QA reports per dataset version; write() emits JSON + Markdown."""

    async def _collect_stats(self, session: AsyncSession) -> dict[str, Any]:
        async def _scalar(sql: str) -> Any:
            return (await session.execute(text(sql))).scalar_one()

        async def _rows(sql: str) -> list[tuple]:
            return [(row[0], row[1]) for row in await session.execute(text(sql))]

        stops_total = await _scalar("SELECT count(*) FROM stops")
        stops_with_coords = await _scalar("SELECT count(*) FROM stops WHERE location IS NOT NULL")
        stop_verification = await _rows(
            "SELECT verification_status, count(*) FROM stops"
            " GROUP BY verification_status ORDER BY verification_status"
        )
        return {
            "stops_total": stops_total,
            "stops_with_coords": stops_with_coords,
            "stop_verification": stop_verification,
            "routes_total": await _scalar("SELECT count(*) FROM transport_routes"),
            "patterns_total": await _scalar("SELECT count(*) FROM route_patterns"),
            "calls_total": await _scalar("SELECT count(*) FROM route_pattern_stops"),
            "aliases": await _rows(
                "SELECT language, count(*) FROM entity_aliases GROUP BY language ORDER BY language"
            ),
            "transfers_total": await _scalar("SELECT count(*) FROM transfer_connections"),
            "places_total": await _scalar("SELECT count(*) FROM places"),
            "patterns_under_two": await _scalar(
                "SELECT count(*) FROM (SELECT pattern_id FROM route_pattern_stops"
                " GROUP BY pattern_id HAVING count(*) < 2) s"
            ),
            "patterns_without_calls": await _scalar(
                "SELECT count(*) FROM route_patterns rp WHERE NOT EXISTS"
                " (SELECT 1 FROM route_pattern_stops rps WHERE rps.pattern_id = rp.id)"
            ),
            "routes_without_agency": await _scalar(
                "SELECT count(*) FROM transport_routes WHERE agency_id IS NULL"
            ),
            "patterns_without_shape": await _scalar(
                "SELECT count(*) FROM route_patterns WHERE shape_id IS NULL"
            ),
        }

    async def build(self, session: AsyncSession, version_id: uuid.UUID) -> dict[str, Any]:
        version = await session.get(DatasetVersion, version_id)
        if version is None:
            raise HTTPException(status_code=404, detail="dataset version not found")
        stats = await self._collect_stats(session)

        diff_rows = [
            (row[0], row[1])
            for row in await session.execute(
                text(
                    "SELECT entity_type, count(*) FROM dataset_version_entities"
                    " WHERE dataset_version_id = :v GROUP BY entity_type ORDER BY entity_type"
                ),
                {"v": version_id},
            )
        ]

        checks: list[dict[str, Any]] = [
            {
                "check": "patterns with fewer than 2 ordered calls",
                "count": stats["patterns_under_two"],
                "severity": "warning" if stats["patterns_under_two"] else "pass",
                "note": "variants with <2 calls cannot be planned against",
            },
            {
                "check": "patterns with no stop calls at all",
                "count": stats["patterns_without_calls"],
                "severity": "warning" if stats["patterns_without_calls"] else "pass",
                "note": "usually unresolved member references at ingestion",
            },
            {
                "check": "routes without an agency attribution",
                "count": stats["routes_without_agency"],
                "severity": "info",
                "note": "OSM relations rarely carry operator data; field-verify",
            },
            {
                "check": "stops without coordinates",
                "count": stats["stops_total"] - stats["stops_with_coords"],
                "severity": "warning"
                if stats["stops_total"] != stats["stops_with_coords"]
                else "pass",
                "note": "coordinates unknown until resolved/verified",
            },
            {
                "check": "patterns without geometry (shape)",
                "count": stats["patterns_without_shape"],
                "severity": "info",
                "note": "shapes not imported in this phase",
            },
        ]

        return {
            "report_type": "data_quality_report",
            "generated_at": datetime.now(UTC).isoformat(),
            "dataset_version": {
                "id": str(version.id),
                "label": version.version_label,
                "status": version.status,
                "notes": version.notes,
            },
            "caveats": [
                "All facts in this version are 'unverified' until field-checked.",
                "OSM data does not prove operational status of any service.",
                "direction_id is not derivable from OSM alone; boarding side is unknown.",
                "Network feasibility only: no timetable or live availability claims.",
            ],
            "diff_by_entity_type": dict(diff_rows),
            "coverage": {
                "stops": {
                    "total": stats["stops_total"],
                    "with_coordinates": stats["stops_with_coords"],
                },
                "stop_verification_status": dict(stats["stop_verification"]),
                "routes": stats["routes_total"],
                "route_patterns": stats["patterns_total"],
                "route_pattern_stops": stats["calls_total"],
                "aliases_by_language": dict(stats["aliases"]),
                "transfer_connections": stats["transfers_total"],
                "places": stats["places_total"],
            },
            "checks": checks,
        }

    async def write(
        self, session: AsyncSession, version_id: uuid.UUID, output_dir: str | Path
    ) -> dict[str, str]:
        """Write `<label>.json` and `<label>.md` into output_dir; returns paths."""
        report = await self.build(session, version_id)
        directory = Path(output_dir)
        directory.mkdir(parents=True, exist_ok=True)
        label = report["dataset_version"]["label"].replace("/", "-")

        json_path = directory / f"{label}.json"
        json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

        md_path = directory / f"{label}.md"
        md_path.write_text(self._render_markdown(report), encoding="utf-8")
        return {"json": str(json_path), "markdown": str(md_path)}

    @staticmethod
    def _render_markdown(report: dict[str, Any]) -> str:
        version = report["dataset_version"]
        coverage = report["coverage"]
        lines = [
            f"# Data-quality report — {version['label']}",
            "",
            f"*Generated:* {report['generated_at']}  ",
            f"*Version status:* `{version['status']}`",
            "",
            "## Caveats",
            *(f"- {caveat}" for caveat in report["caveats"]),
            "",
            "## Diff by entity type",
            "",
            "| Entity type | Changes |",
            "|---|---|",
            *(f"| {entity} | {count} |" for entity, count in report["diff_by_entity_type"].items()),
            "",
            "## Coverage",
            "",
            f"- Stops: {coverage['stops']['total']}"
            f" ({coverage['stops']['with_coordinates']} with coordinates)",
            f"- Routes: {coverage['routes']}; patterns: {coverage['route_patterns']};"
            f" ordered calls: {coverage['route_pattern_stops']}",
            "- Aliases by language: "
            + ", ".join(
                f"{lang}: {count}" for lang, count in coverage["aliases_by_language"].items()
            ),
            f"- Transfer connections: {coverage['transfer_connections']}",
            f"- Places: {coverage['places']}",
            "",
            "## Checks",
            "",
            "| Check | Count | Severity | Note |",
            "|---|---|---|---|",
            *(
                f"| {check['check']} | {check['count']} | {check['severity']} | {check['note']} |"
                for check in report["checks"]
            ),
            "",
        ]
        return "\n".join(lines)
