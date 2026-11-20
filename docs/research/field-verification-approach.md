# Research: Field Verification Approach for Pilot Transport Data

**Status:** Recommended approach for owner decision D-3 (recorded in `docs/status/development-status-report.md` §9)
**Date:** 2026-11-20 (desk research; web sources retrieved this date)
**Question:** What is the best way to physically verify our pilot transport data — stop identity/position/side, route variant/direction/stop order, and transfer walking paths?

## 1. Why verification is needed (recap)

Our Phase 1.3 OSM import produced 100 stops, 17 routes, 22 variants and 37 ordered stop calls for central Colombo — **all `unverified`**. OSM data cannot prove: the physical side/stand a traveller boards at, whether the mapped stop order matches reality, whether a short-working variant is currently operated, or whether a transfer path is walkable. Product rules forbid presenting unconfirmed facts as confirmed.

## 2. Approaches found in practice (web research)

| Approach | What it is | Strengths | Weaknesses | Sources |
|---|---|---|---|---|
| **ODK / KoboToolbox structured field forms** | Open-source offline form system (ODK Collect app or web forms): GPS capture, photos, skip logic, multi-language, pre-loaded record lists; exports to XLSX/GeoJSON/CSV. ODK is self-hostable free; hosted ODK Cloud is paid ($199/mo standard tier). KoboToolbox is an ODK-based server with free humanitarian-tier hosting (verify current terms at signup). | Verifies **our own entities** directly (we pre-load our stop/pattern list); offline-first; GPS + photo evidence; structured export feeds our `verification_records` table and a moderation → candidate-version flow; multi-language forms (en/si/ta) | Requires building/maintaining forms; a server (self-host free or cloud paid); one more tool for the field worker | getodk.org (retrieved 2026-11-20) |
| **StreetComplete** (OSM surveyor app; Android 7.1+ and iOS since v64) | Gamified OSM editor that asks simple on-site questions ("quests") and uploads answers directly to OSM; works online+offline; free | Zero-setup per-question UI; improves **upstream OSM** so future syncs import better data; established community tool | Answers go to OSM, not to us — our DB only benefits after the next sync; covers OSM-tag attributes, not our product-specific facts (boarding side, transfer path notes) | OSM wiki: StreetComplete (retrieved 2026-11-20) |
| **OpenStop** (cross-platform; PT-dedicated) | Free app focused on collecting public-transport stop attributes (waiting areas, displays, accessibility) into OSM; shows nearby stops missing info; uploads to OSM | Public-transport-specific question sets; beginner-friendly; offline-capable | Same "goes to OSM" limitation; accessibility focus (not boarding side/transfer paths) | OSM wiki: OpenStop (retrieved 2026-11-20) |
| **Ride-along route audits with GPS trace** | Ride the bus variant with GPS logging (OsmAnd/Organic Maps/Strava → GPX) and a printed/digital ordered stop list; note destination board wording, actual stop sequence, short-working behaviour, transfer points | The **only** method that validates our `route_pattern_stops` order and variant/direction claims against reality; produces GPX evidence | Time-consuming per variant; needs a comparator (our exported stop list) | Standard OSM field-survey practice (OSM PT wiki context) |
| **Field Papers (print-atlas workflow)** | Print a map atlas of the area, annotate on paper in the field, photograph/scan, transcribe later | No smartphone dependency; good for annotating map positions | Paper transcription is slow and error-prone for attribute-level data (stop side, shelter, names in 3 scripts) | fieldpapers.org (retrieved 2026-11-20) |
| **Full route import from official feeds (GTFS/NTC)** | Get government/operator data instead of field checking | Authoritative for route/stop patterns where it exists | **Rights unknown** in Sri Lanka (see `data/source-rights-register.md` §2); GTFS completeness for Sri Lanka unverified | audit + register |

## 3. Recommendation: a three-tier, phased approach (ODK-centred)

For our context — a small team, Colombo pilot, budget-conscious, smartphone-based, with our data model already carrying `verification_records` (method, reviewer, evidence, result) — the best approach is a **combination**, not a single tool:

**Tier 1 (primary) — ODK/KoboToolbox structured surveys over OUR data.**
- Build two offline forms: **Stop verification** (pre-loaded with our canonical stop list: internal ID, name, coordinates → the field worker walks to it, confirms/corrects name + local names, drops an on-site GPS pin, answers side/stop-type/shelter/access questions, optional photo) and **Transfer-path verification** (per candidate connector: walk the path, distance estimate, photo, hazards/notes).
- Submissions export (CSV/GeoJSON) → a small import script writes `verification_records` (method `field_check`, reviewer, evidence) and queues corrections through our existing moderation→candidate-version flow. **Nothing auto-publishes** (consistent with architecture rules).
- Why primary: it verifies *our* entities with *our* IDs, works offline, produces evidence, and the form design later graduates into our own in-app reporter (Phase 7 F27/F28).

**Tier 2 (complement) — OSM-native apps during the same field walks.**
- **OpenStop** for PT stop attributes and **StreetComplete** for bus-stop quests: the same walk also fixes upstream OSM, so the next sync imports better data into us for free. Requires an OSM account; edits are public (mind OSM community norms).

**Tier 3 (route variants) — ride-along audits with GPS traces.**
- For the 3–5 key pilot route variants (candidates: the multi-variant routes the QA report surfaced — e.g. route 176 with 3 variants), ride with a GPX logger + our exported ordered stop list; record destination-board wording, actual order, short-working behaviour, transfer points; deviations feed the same ODK form (pattern-level).

**Why this combination is the best available approach:**
1. It covers **all three verification needs**: stop identity/side (Tier 1), upstream data quality (Tier 2), and route-variant/direction/order truth (Tier 3) — no single tool covers all three.
2. It is **free or near-free** and **offline-first** — suited to Colombo connectivity gaps.
3. It produces **auditable evidence** (GPS + photos + GPX) that plugs directly into our existing `verification_records` schema and the moderation → candidate → publish pipeline built in Phases 1.2/1.3.
4. It follows how the two most relevant communities actually do it: OSM volunteers survey with purpose-built apps (StreetComplete/OpenStop), and professional field teams collect with ODK-style structured forms (used by WHO, Red Cross, HOT).

**Suggested effort for the central-Colombo pilot (first pass):** 2–3 field days — one walking day for dense stop clusters (e.g. Pettah–Kollupitiya), one ride-along day covering 3 key variants (e.g. 100, 176, 138), one review/import session. This is Phase 1.4 work.

## 4. Planned ODK form fields (mapped to our schema)

Stop form (pre-loaded fields in *italics* are read-only context; everything else is answered on site):
- *stop_id (internal UUID), *canonical name, *coordinates* — context
- Name confirmed? (yes / corrected name / local names si-ta found) → `entity_aliases`
- On-site GPS pin → compare with stored `stops.location` (displacement threshold for QA)
- Stop type (roadside / bus stand / terminal / bay / platform) → `stops.stop_type`
- Side/boarding point notes (toward which destination, landmark) → `stop_access_points`
- Shelter / bench / paved / lit (yes/no) → `stop_access_points.access_notes`
- Photo (optional, no faces/plates; consent notice shown) → `verification_records.evidence`
- Result: verified / corrected / not-found → `verification_records.result`

Transfer form: connector endpoints (*context*), walked path GPS trace, estimated distance/time, surface/hazard notes, photo, result.
Pattern (ride-along) form: *pattern_id + expected stop order*, actual order observed, destination-board wording as written, currently operated? (yes/no/unknown), deviations list, GPX trace attached.

Import path: submissions → CSV/GeoJSON → `backend/scripts/import_field_verifications.py` (Phase 1.4 deliverable) → `verification_records` rows + corrections queued as candidate-version changes for review.

## 5. Decision requested from the owner (D-3)

Adopt the three-tier approach with **ODK/KoboToolbox as the Tier-1 tool**. Sub-choices (can be deferred to Phase 1.4 start):
- **Hosting:** KoboToolbox free humanitarian server vs self-hosted ODK (we already have Docker; a small self-host is feasible) — recommend starting on KoboToolbox free hosting for speed, migrating later if needed.
- **Who walks:** still open (the original D-3 staffing question) — the approach above works for a single owner with a smartphone.

## 6. Sources

- OSM wiki — Public transport (PTv2 schema, roles, QA): https://wiki.openstreetmap.org/wiki/Public_transport (retrieved 2026-11-20)
- OSM wiki — StreetComplete: https://wiki.openstreetmap.org/wiki/StreetComplete (retrieved 2026-11-20; v64 Oct 2026 — Android + iOS)
- OSM wiki — OpenStop: https://wiki.openstreetmap.org/wiki/OpenStop (retrieved 2026-11-20)
- ODK: https://getodk.org/ (retrieved 2026-11-20; open-source, self-host free; ODK Cloud paid)
- Field Papers: https://fieldpapers.org/ (retrieved 2026-11-20)
- KoboToolbox: kobotoolbox.org (site returned HTTP 403 to automated fetch — features summarised from ODK-based documentation; verify terms at signup)
