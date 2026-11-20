"""Import field-verification submissions into verification_records (Phase 1.4).

Consumes the CSV exported from the ODK/KoboToolbox stop-verification form and:

1. writes one `verification_records` row per submission
   (method='field_check', reviewer, evidence notes);
2. collects any corrections (name, local names, position, stop type, side)
   into a **corrections report** for human review — canonical data is NEVER
   modified by this script (moderation → candidate version flow handles that).

Expected CSV columns (order-insensitive):
    stop_id, result (verified|corrected|not_found), reviewer,
    corrected_name, name_si, name_ta, side_notes, stop_type,
    gps_lon, gps_lat, evidence_notes

Run inside the backend container:
    python scripts/import_field_verifications.py \
        --file data/field-verification/imports/stops_submitted.csv
Add --dry-run to validate without writing.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text  # noqa: E402

from app.modules.data_quality.models import VerificationRecord  # noqa: E402
from app.platform.db import get_session_factory  # noqa: E402

_RESULT_MAP = {
    "verified": "verified",
    "corrected": "verified",  # the fact was checked and corrected → fact is verified
    "not_found": "rejected",
    "uncertain": "uncertain",
}


async def import_verifications(csv_path: Path, dry_run: bool = False) -> dict[str, object]:
    session = get_session_factory()()
    summary: dict[str, object] = {
        "file": str(csv_path),
        "imported_at": datetime.now(UTC).isoformat(),
        "records_written": 0,
        "skipped": [],
        "corrections": [],
    }
    try:
        with csv_path.open(newline="", encoding="utf-8-sig") as handle:
            rows = list(csv.DictReader(handle))

        for index, row in enumerate(rows, start=2):  # CSV line 1 = header
            raw_stop_id = (row.get("stop_id") or "").strip()
            raw_result = (row.get("result") or "").strip().lower()
            try:
                stop_id = uuid.UUID(raw_stop_id)
            except ValueError:
                summary["skipped"].append(f"line {index}: invalid stop_id '{raw_stop_id}'")  # type: ignore[index]
                continue
            mapped = _RESULT_MAP.get(raw_result)
            if mapped is None:
                summary["skipped"].append(f"line {index}: unknown result '{raw_result}'")  # type: ignore[index]
                continue

            exists = (
                await session.execute(text("SELECT 1 FROM stops WHERE id = :id"), {"id": stop_id})
            ).scalar_one_or_none()
            if exists is None:
                summary["skipped"].append(f"line {index}: stop {stop_id} not in canonical data")  # type: ignore[index]
                continue

            corrections = _collect_corrections(row)
            if corrections:
                summary["corrections"].append(  # type: ignore[index]
                    {"stop_id": str(stop_id), "result": raw_result, "corrections": corrections}
                )

            evidence_parts = [
                part
                for part in (
                    (row.get("evidence_notes") or "").strip(),
                    f"GPS: {row.get('gps_lon', '')},{row.get('gps_lat', '')}"
                    if row.get("gps_lon") and row.get("gps_lat")
                    else "",
                    "corrections: " + json.dumps(corrections, ensure_ascii=False)
                    if corrections
                    else "",
                )
                if part
            ]
            if not dry_run:
                session.add(
                    VerificationRecord(
                        entity_type="stop",
                        entity_id=stop_id,
                        method="field_check",
                        reviewer=(row.get("reviewer") or "").strip() or None,
                        verified_at=datetime.now(UTC),
                        result=mapped,
                        evidence="; ".join(evidence_parts) or None,
                        notes=(row.get("notes") or "").strip() or None,
                    )
                )
                await session.flush()
            summary["records_written"] += 1  # type: ignore[operator]

        if not dry_run:
            await session.commit()
        summary["corrections_report"] = str(_write_report(csv_path, summary))
    finally:
        await session.close()
    return summary


def _collect_corrections(row: dict[str, str]) -> dict[str, object]:
    """Any field the field worker changed relative to our canonical data."""
    corrections: dict[str, object] = {}
    corrected_name = (row.get("corrected_name") or "").strip()
    if corrected_name:
        corrections["name"] = corrected_name
    for language, column in (("si", "name_si"), ("ta", "name_ta")):
        value = (row.get(column) or "").strip()
        if value:
            corrections[f"alias_{language}"] = value
    stop_type = (row.get("stop_type") or "").strip()
    if stop_type:
        corrections["stop_type"] = stop_type
    side_notes = (row.get("side_notes") or "").strip()
    if side_notes:
        corrections["side_or_platform"] = side_notes
    lon = (row.get("gps_lon") or "").strip()
    lat = (row.get("gps_lat") or "").strip()
    if lon and lat:
        corrections["location"] = {"lon": float(lon), "lat": float(lat)}
        corrections["position_changed"] = True
    return corrections


def _write_report(csv_path: Path, summary: dict[str, object]) -> Path:
    imports_dir = csv_path.parent
    imports_dir.mkdir(parents=True, exist_ok=True)
    report_path = imports_dir / (f"corrections_{datetime.now(UTC).strftime('%Y%m%dT%H%M%S')}.json")
    report_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return report_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Import field verifications (Phase 1.4)")
    parser.add_argument("--file", required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    summary = asyncio.run(import_verifications(Path(args.file), args.dry_run))
    printable = {k: v for k, v in summary.items() if k != "corrections"}
    print(json.dumps(printable, indent=2))
    print(f"corrections pending review: {len(summary['corrections'])}")  # type: ignore[arg-type]


if __name__ == "__main__":
    main()
