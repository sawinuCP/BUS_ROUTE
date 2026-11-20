# Field Verification Kit — Central Colombo Pilot (Phase 1.4)

How to run the Tier-1/Tier-3 field verification adopted for decision D-3
(approach: `docs/research/field-verification-approach.md`).

## Contents

| Path | Purpose |
|---|---|
| `forms/stop_verification_*.csv` | XLSForm sheets (survey/choices/settings) for the KoboToolbox **stop-verification form** |
| `exports/` (generated, not committed) | CSVs exported from our database for the field: `stops_survey.csv`, `patterns_ridecheck.csv`, `transfers_check.csv` |
| `imports/` (generated, not committed) | Submitted CSVs placed here for import + the generated corrections reports |

## Step 1 — Export today's stop list (inside the backend container)

```sh
python scripts/export_field_surveys.py --out data/field-verification/exports
```

Print `stops_survey.csv` (it is the worker's checklist: stop_id, name, coordinates).

## Step 2 — Build the Kobo form (once)

1. Open `forms/stop_verification_survey.csv`, `..._choices.csv`, `..._settings.csv`
   in Excel and save each as `.xlsx` (or use getodk.org/xlsform).
2. In KoboToolbox (free hosting): New project → Upload XLSForm → Deploy.
3. Fill the form with **ODK Collect** or Kobo's web form (Enketo) on the phone —
   both work offline; submissions sync when connectivity returns.

## Step 3 — Field days

**Walking day (Tier 1 + Tier 2):** pick a dense corridor (e.g. Pettah–Kollupitiya).
At each stop from the printed list: confirm/correct the name (+ any Sinhala/Tamil
signage), stand at the actual boarding point and capture the GPS question,
answer stop type/side/landmark, optional photo. **Privacy rule:** no faces or
number plates in photos; if a person must be in frame, get consent or skip.
While there, answer the equivalent OpenStop/StreetComplete questions so the
upstream OSM data improves too (needs an OSM account; public edits).

**Ride-along day (Tier 3):** for the key variants (candidates from the QA
queue: routes 100, 176, 138, 103…), ride with a GPS logger (OsmAnd/Organic
Maps/Strava → GPX) and the printed `patterns_ridecheck.csv` row; note the
destination-board wording as written, whether each listed stop was actually
served, and any stops served that are missing from our data.

## Step 4 — Import submissions (inside the backend container)

Export the Kobo submissions as CSV into `data/field-verification/imports/`, then:

```sh
python scripts/import_field_verifications.py --file data/field-verification/imports/<submissions>.csv --dry-run
python scripts/import_field_verifications.py --file data/field-verification/imports/<submissions>.csv
```

The script writes `verification_records` (method `field_check`) and a
**corrections report** (JSON). Corrections are then applied through the
review → candidate-version flow — **canonical data is never modified directly**.

## Step 5 — Track progress

- Verification counts: `GET /api/v1/admin/verifications?entity_type=stop`
- Review queue: `GET /api/v1/admin/qa-queue`
- Coverage scorecard: `GET /api/v1/admin/coverage-scorecard`
- Status: `docs/status/development-status-report.md` (§5, §6, §8, §10)
