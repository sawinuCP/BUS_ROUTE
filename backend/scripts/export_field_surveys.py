"""Export field-survey inputs for the ratified pilot (Phase 1.4, Tier-1 ODK flow).

Produces CSV inputs for the ODK/KoboToolbox verification forms (see
`data/field-verification/README.md`):

- stops_survey.csv        — our canonical stops to walk and confirm, with a
                            walking `tier` (A = stop is called at by at least
                            one route pattern, B = not referenced by any
                            pattern) and an `area` corridor label so the owner
                            can plan walk days.
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
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text  # noqa: E402

from app.platform.db import get_session_factory  # noqa: E402

_STOPS_QUERY = text(
    """
    SELECT
        s.id,
        s.name,
        ST_Y(s.location::geometry) AS lat,
        ST_X(s.location::geometry) AS lon,
        s.stop_type,
        s.verification_status,
        CASE WHEN EXISTS (
            SELECT 1 FROM route_pattern_stops rps WHERE rps.stop_id = s.id
        ) THEN 'A' ELSE 'B' END AS tier,
        CASE
            WHEN ST_Y(s.location::geometry) >= 7.06
                THEN 'Negombo–Gampaha corridor'
            WHEN ST_Y(s.location::geometry) >= 6.97
                THEN 'Colombo north & Kelaniya'
            WHEN ST_X(s.location::geometry) >= 80.00
                THEN 'Eastern inland (Kottawa–Homagama–Avissawella)'
            WHEN ST_X(s.location::geometry) >= 79.92
                THEN 'Colombo south suburbs (Nugegoda–Maharagama)'
            WHEN ST_Y(s.location::geometry) >= 6.82
                THEN 'Colombo city core'
            ELSE 'Kalutara corridor'
        END AS area
    FROM stops s
    WHERE s.location IS NOT NULL
    ORDER BY area, tier, s.name
    """
)


def _write_csv(path: Path, header: list[str], rows: list[tuple]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        for row in rows:
            writer.writerow(
                [str(value) if isinstance(value, (int, float)) else value for value in row]
            )


async def export_surveys(out_dir: Path) -> dict[str, int]:
    session = get_session_factory()()
    counts: dict[str, int] = {}
    try:
        out_dir.mkdir(parents=True, exist_ok=True)

        result = await session.execute(_STOPS_QUERY)
        rows = result.all()
        stops_path = out_dir / "stops_survey.csv"
        _write_csv(
            stops_path,
            [
                "stop_id",
                "canonical_name",
                "lat",
                "lon",
                "stop_type",
                "current_verification",
                "tier",
                "area",
            ],
            rows,
        )
        counts["stops_survey"] = len(rows)

        tiers = Counter(row[6] for row in rows)
        areas = Counter((row[7], row[6]) for row in rows)
        for tier in ("A", "B"):
            counts[f"tier_{tier}"] = tiers[tier]
        for (area, tier), total in sorted(areas.items()):
            counts[f"{area} (tier {tier})"] = total

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
        rows = result.all()
        _write_csv(
            patterns_path,
            [
                "pattern_id",
                "pattern_code",
                "route_code",
                "origin",
                "destination",
                "expected_calls",
            ],
            rows,
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
        rows = result.all()
        _write_csv(
            transfers_path,
            [
                "transfer_id",
                "from_point",
                "to_point",
                "distance_m",
                "current_verification",
            ],
            rows,
        )
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
