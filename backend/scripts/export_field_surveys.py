"""Export field-survey inputs for the ratified pilot (Phase 1.4, Tier-1 ODK flow).

Produces CSV inputs for the ODK/KoboToolbox verification forms (see
`data/field-verification/README.md`):

- stops_survey.csv        — our canonical stops to walk and confirm
- patterns_ridecheck.csv  — ordered call lists for ride-along audits
- transfers_check.csv     — candidate connectors to walk (usually empty today)

Run inside the backend container:
    python scripts/export_field_surveys.py --out data/field-verification/exports
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text  # noqa: E402

from app.platform.db import get_session_factory  # noqa: E402


async def export_surveys(out_dir: Path) -> dict[str, int]:
    session = get_session_factory()()
    counts: dict[str, int] = {}
    try:
        out_dir.mkdir(parents=True, exist_ok=True)

        stops_path = out_dir / "stops_survey.csv"
        result = await session.execute(
            text(
                "SELECT id, name, ST_Y(location::geometry) AS lat,"
                " ST_X(location::geometry) AS lon, stop_type, verification_status"
                " FROM stops WHERE location IS NOT NULL ORDER BY name"
            )
        )
        with stops_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(
                ["stop_id", "canonical_name", "lat", "lon", "stop_type", "current_verification"]
            )
            rows = result.all()
            for row in rows:
                writer.writerow([str(row[0]), row[1], row[2], row[3], row[4] or "", row[5]])
            counts["stops_survey"] = len(rows)

        patterns_path = out_dir / "patterns_ridecheck.csv"
        result = await session.execute(
            text(
                "SELECT rp.id, rp.pattern_code, r.route_code, rp.origin_label,"
                " rp.destination_label,"
                " string_agg(rps.sequence || ') ' || s.name, ' | ' ORDER BY rps.sequence)"
                " AS expected_calls"
                " FROM route_patterns rp"
                " JOIN transport_routes r ON r.id = rp.route_id"
                " LEFT JOIN route_pattern_stops rps ON rps.pattern_id = rp.id"
                " LEFT JOIN stops s ON s.id = rps.stop_id"
                " GROUP BY rp.id, rp.pattern_code, r.route_code,"
                " rp.origin_label, rp.destination_label"
                " ORDER BY r.route_code, rp.pattern_code"
            )
        )
        with patterns_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(
                [
                    "pattern_id",
                    "pattern_code",
                    "route_code",
                    "origin",
                    "destination",
                    "expected_calls",
                ]
            )
            rows = result.all()
            for row in rows:
                writer.writerow(
                    [str(row[0]), row[1] or "", row[2], row[3] or "", row[4] or "", row[5] or ""]
                )
            counts["patterns_ridecheck"] = len(rows)

        transfers_path = out_dir / "transfers_check.csv"
        result = await session.execute(
            text(
                "SELECT tc.id, sa.name AS from_point, sb.name AS to_point,"
                " tc.walk_distance_m, tc.verification_status"
                " FROM transfer_connections tc"
                " JOIN stop_access_points sa ON sa.id = tc.from_access_point_id"
                " JOIN stop_access_points sb ON sb.id = tc.to_access_point_id"
                " ORDER BY tc.id"
            )
        )
        with transfers_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(
                ["transfer_id", "from_point", "to_point", "distance_m", "current_verification"]
            )
            rows = result.all()
            for row in rows:
                writer.writerow([str(row[0]), row[1] or "", row[2] or "", row[3] or "", row[4]])
            counts["transfers_check"] = len(rows)
    finally:
        await session.close()
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description="Export field-survey inputs (Phase 1.4)")
    parser.add_argument("--out", default="data/field-verification/exports")
    args = parser.parse_args()

    counts = asyncio.run(export_surveys(Path(args.out)))
    print(f"exports written to {args.out}: {counts}")


if __name__ == "__main__":
    main()
