"""Build the Kobo-ready XLSForm from the CSV sheets (Phase 1.4 / D-3).

XLSForm = a workbook with `survey`, `choices` and `settings` sheets. The
authoring source of truth stays the versioned CSVs in
`data/field-verification/forms/`; this script assembles them into one
`stop_verification.xlsx` that can be uploaded to KoboToolbox directly
(no manual Excel conversion step).

Run inside the backend container:
    python scripts/build_kobo_form.py
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from openpyxl import Workbook

_FORMS_DIR = Path("data/field-verification/forms")
_SHEETS = ("survey", "choices", "settings")


def build_xlsform(forms_dir: Path, out_path: Path) -> None:
    workbook = Workbook()
    workbook.remove(workbook.active)
    for sheet_name in _SHEETS:
        csv_path = forms_dir / f"stop_verification_{sheet_name}.csv"
        if not csv_path.exists():
            raise SystemExit(f"missing form sheet: {csv_path}")
        with csv_path.open(encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.reader(handle))
        worksheet = workbook.create_sheet(title=sheet_name)
        for row in rows:
            worksheet.append(row)
    workbook.save(out_path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build Kobo XLSForm from CSV sheets")
    parser.add_argument("--forms-dir", default=str(_FORMS_DIR))
    parser.add_argument("--out", default=str(_FORMS_DIR / "stop_verification.xlsx"))
    args = parser.parse_args()

    build_xlsform(Path(args.forms_dir), Path(args.out))
    print(f"XLSForm written: {args.out}")


if __name__ == "__main__":
    main()
