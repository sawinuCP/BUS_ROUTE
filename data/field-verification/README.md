# Field Verification Kit — Western Province Pilot (Phase 1.4, updated for D-8)

How to run the Tier-1/Tier-3 field verification adopted for decision D-3
(approach: `docs/research/field-verification-approach.md`).

**Scale after the D-8 widening:** 432 stops / 38 routes / 45 patterns. A walk of
everything is *not* the plan — the export tiers stops so you verify what
actually matters for routing first.

## Contents

| Path | Purpose |
|---|---|
| `forms/stop_verification_survey.csv` (+ `_choices`, `_settings`) | XLSForm authoring sheets for the **stop-verification form** (en/si/ta) |
| `forms/stop_verification.xlsx` | **Ready-to-upload XLSForm** (built from the CSVs by `backend/scripts/build_kobo_form.py` — no manual Excel step) |
| `exports/` (generated, not committed) | `stops_survey.csv` (with `tier` + `area` columns), `patterns_ridecheck.csv`, `transfers_check.csv` |
| `imports/` (generated, not committed) | Submitted CSVs placed here for import + generated corrections reports |

**Tier meanings** (in `stops_survey.csv`):
- **Tier A — 57 stops**: called at by at least one route pattern in our data.
  These are the stops that routing actually depends on → walk these first.
- **Tier B — 375 stops**: mapped but not referenced by any pattern (edge
  members, unmapped-line stops). Optional later sweeps.

**Area day-plan (from the current export):**

| Walk day | Area | Tier-A stops |
|---|---|---|
| 1 | Colombo city core (Fort/Pettah → Wellawatte) | 52 |
| 2 | Colombo north & Kelaniya (1) + south suburbs Nugegoda–Maharagama (4) | 5 |
| 3 | Ride-along day — key patterns from `patterns_ridecheck.csv` | — |

Remaining Tier-B sweep days are optional; do them opportunistically.

## Step 1 — Export today's stop list (from the repo root)

```sh
python backend/scripts/export_field_surveys.py --out data/field-verification/exports
```

`stops_survey.csv` is the worker's checklist (stop_id, name, lat/lon, tier,
area). Print/sort it for the day's area.

## Step 2 — Deploy the Kobo form (once)

1. Create a free account at **kf.kobotoolbox.org** (or eu.kobotoolbox.org).
2. New project → **Upload an XLSForm** → choose
   `data/field-verification/forms/stop_verification.xlsx` → **Deploy**.
3. On the phone install **ODK Collect** (Play Store): Configure → server =
   KoboToolbox, sign in with the Kobo account (or scan the project QR code).
   The form works **offline**; submissions sync when connectivity returns.
   Kobo's browser form (Enketo) also works if you prefer the web form.
4. If you edit the form CSVs later, rebuild the workbook:
   `python backend/scripts/build_kobo_form.py --forms-dir data/field-verification/forms
   --out data/field-verification/forms/stop_verification.xlsx`

## Step 3 — Field days

**Walking day (Tier 1 + Tier 2), tier-A stops of one area:** at each stop from
the printed list: confirm/correct the name (+ any Sinhala/Tamil signage), stand
at the actual boarding point and capture the GPS question, answer stop
type/side/landmark, optional photo. **Privacy rule:** no faces or number plates
in photos; if a person must be in frame, get consent or skip. While there,
answer the equivalent OpenStop/StreetComplete questions so the upstream OSM
data improves too (needs an OSM account; public edits).

**Ride-along day (Tier 3):** for the key variants (candidates from the QA
queue), ride with a GPS logger (OsmAnd/Organic Maps/Strava → GPX) and the
printed `patterns_ridecheck.csv` row; note the destination-board wording as
written, whether each listed stop was actually served, and any stops served
that are missing from our data. **Current best ride-along candidates** (most
resolved calls in the export): route **101** Moratuwa → Colombo Fort (23
calls), route **154** Kiribathgoda → Angulana (20 calls), then 141
(Wellawatte → Narahenpita) and 138.

## Step 4 — Import submissions (from the repo root)

Export the Kobo submissions as CSV into `data/field-verification/imports/`, then:

```sh
python backend/scripts/import_field_verifications.py --file data/field-verification/imports/<submissions>.csv --dry-run
python backend/scripts/import_field_verifications.py --file data/field-verification/imports/<submissions>.csv
```

The script writes `verification_records` (method `field_check`) and a
**corrections report** (JSON). Corrections are then applied through the
review → candidate-version flow — **canonical data is never modified directly**.

## Step 5 — Track progress

- Verification counts: `GET /api/v1/admin/verifications?entity_type=stop`
- Review queue: `GET /api/v1/admin/qa-queue`
- Coverage scorecard: `GET /api/v1/admin/coverage-scorecard`
- Status: `docs/status/development-status-report.md` (§5, §6, §8, §10)
