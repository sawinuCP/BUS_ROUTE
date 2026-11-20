# Development Status Report — Sri Lanka Journey Planner

**Report ID:** `docs/status/development-status-report.md`
**Last updated:** 2026-11-20 (after Phase 1.3)
**Maintained by:** coding agent + product owner
**Companion documents:** `docs/product/11_IMPLEMENTATION_PLAN.md` (control document), `docs/audits/phase-0-repository-audit.md`, `docs/adr/ADR-0001…0007`, `data/source-rights-register.md`

---

## 1. Purpose and maintenance protocol

This is the **single, continuously-maintained engineering status report** for the whole project. Its job is to make the development track verifiable: which phase we are in, what was delivered, what was tested and how, what issues occurred and how they were fixed, what remains, and what decisions are pending.

**Maintenance rules (binding for every coding-agent task, see `AGENTS.md` §5):**

1. **Before each task:** confirm the "Current position" marker (§5) matches reality; read the phase's expected outcomes below.
2. **After each task:** update (a) the status dashboard (§5), (b) the phase record (§6), (c) the issue log (§7) with any problem encountered and its fix, (d) the verification log (§8) with the exact commands and results, and (e) "Remaining path" (§10) if the plan changed.
3. **Append-only history:** §6/§7/§8 entries are never rewritten — corrections are added as new dated entries.
4. **Truthfulness:** test results are recorded only when actually executed; never claim a pass that did not run (implementation plan §0 rule 6).
5. **Product decisions** (owner choices) are recorded in ADRs and echoed here under §9; this report never silently resolves a conflict.

---

## 2. Product snapshot (what we are building)

- **Product promise:** a Sri Lankan multimodal journey planner that discovers practical travel options and converts each into **clear, detailed, step-by-step instructions** (walk → board correct route/direction → alight → transfer → final walk), grounded in validated, versioned transport data.
- **Core principle:** a route suggestion is not a successful journey plan unless the traveller can understand and carry out every leg. Unknown facts are displayed as unknown — **the app never invents stops, routes, directions, fares, timetables, landmarks or service availability**.
- **MVP scope (P0):** origin/destination search with Sinhala/Tamil/English aliases; walking access/egress on a pedestrian network; bus planning on validated pilot corridors (rail only where station order is validated); distinct route **variants** and directions; explicit transfer connectors; several practical non-dominated alternatives; deterministic leg-by-leg instructions; active-journey mode with manual progress; coverage/no-route/low-confidence states; basic moderated reporting; offline itinerary cache; **no account required**.
- **Explicitly deferred:** timetables/arrive-by, live tracking, ticketing, nationwide-coverage claims, crowding, safety certification, AI-generated route facts. AI may only explain/translate planner output with a deterministic fallback; RAG/vector databases are excluded from routing (ADR-0002).
- **Authoritative sources:** `docs/product/11_IMPLEMENTATION_PLAN.md` (Phases 0–10), `docs/architecture/` package 00–17, `docs/product/00–09` (research grounding).

---

## 3. Baseline stack and decision records

**Stack (ADR-0002, ratified):** React Native + TypeScript + Expo (Expo Router, TanStack Query + Zustand, SQLite, MapLibre React Native) · Python 3.12+ (Docker-pinned, ADR-0005) / FastAPI / Pydantic / SQLAlchemy 2.x / Alembic · PostgreSQL 16 + PostGIS 3.4 · Redis (scoped, ADR-0003) · Dramatiq (ADR-0004, accepted) · deterministic multimodal transit graph · Valhalla walking adapter pending prototype · REST + OpenAPI · modular monolith · pytest, Ruff + mypy, Jest + RNTL, Maestro. Prohibited in MVP: Kubernetes, Kafka, vector databases, microservices.

**ADR index:**

| ADR | Title | Status |
|---|---|---|
| 0001 | Docs layout, canonical phase numbering (plan Phases 0–10) & story register (`docs/architecture/04`) | Accepted |
| 0002 | Ratified baseline technology stack | Accepted |
| 0003 | Redis scope in the MVP (cache/rate-limit/queue backing; never source of truth) | Accepted |
| 0004 | Background job library — Dramatiq | Accepted (owner-confirmed) |
| 0005 | Docker-first local development (pinned `python:3.12-slim`) | Accepted |
| 0006 | Canonical schema, dataset-versioning strategy, PostGIS conventions | Accepted |
| 0007 | Ingestion framework: adapters, archive, idempotency, publish/rollback | Accepted |

**Data governance:** source-rights register at `data/source-rights-register.md` — OSM/Overpass (ODbL 1.0) registered; NSDI/NTC/GTFS/SL-Railways remain **unknown** and must not be ingested until registered.

---

## 4. Master phase and task plan (expected outcomes & exit criteria)

Canonical phase numbering: `docs/product/11_IMPLEMENTATION_PLAN.md` §7 (Phases 0–10). Phases are sequential gates; a phase is complete only after verification, never because code was generated.

| Phase | Purpose | Key expected outcomes | Exit criteria (summary) |
|---|---|---|---|
| **0.1** Audit | Baseline of repo/docs/environment | Audit report with gaps & readiness classification | Trustworthy baseline; no silent conflicts |
| **0.2** ADRs & conventions | Governance foundation | ADR template + baseline ADRs; docs layout; canonical registers; AGENTS.md | Decisions recorded; agents resolve docs deterministically |
| **0.3** Infra + backend skeleton | Reproducible local environment | Compose (PostGIS+Redis+backend); FastAPI skeleton with health/ready; Alembic wired; env templates; logging | Fresh-clone setup works; containers healthy; CI-able checks |
| **0.4** Mobile skeleton + CI | App shell + automation | Expo/TS skeleton with navigation & env config; Jest/RNTL; CI workflow | Type-check/lint/tests green; app launches on a device path (owner) |
| **1.1** Canonical schema | Transport data foundation | 22 canonical PostGIS tables; ordered-stop invariant; provenance/versioning entities | Migrations reversible; invariants test-verified |
| **1.2** Ingestion framework | §5.2 lifecycle machinery | Source registry; adapter contract; snapshot archive; quality quarantine; idempotent upserts; diff recording; publish/rollback | Idempotent re-runs proven; publish/rollback demonstrated |
| **1.3** First source adapter + QA report | Real data, legally | OSM/Overpass adapter (ODbL registered); variant grouping; ordered calls; quality report | Rights recorded before ingest; live ingest verified; QA report produced |
| **1.4** Pilot coverage audit + field-verification workflow | Coverage decision data | Coverage scorecard for pilot bbox; field-verification checklist/workflow; QA queue | Pilot corridor documented; critical items field-checked; rollback demonstrated |
| **2** Place search + map | Findability | Place/alias search API (trigram/full-text); MapLibre map screen; geocoder behind adapter; current-location with manual fallback | Pilot places searchable in en/si/ta; ambiguous results never auto-selected |
| **3** Pedestrian routing + transfers | First/last mile | Valhalla proof of concept on Sri Lankan OSM data; walking adapter; explicit transfer paths | Access/transfer/egress as explicit path legs; field-checked pilot paths |
| **4** Deterministic planner | Multi-leg journeys | Graph interfaces; direct + multi-leg candidates; constraints; Pareto filtering; ranking profiles; regression suite | Curated pilot journeys correct; no fabricated candidates; performance baselined |
| **5** Instructions + itinerary UX | Executable journeys | Deterministic templates per step type; itinerary overview; en/si/ta templates (native-reviewed) | Users identify board/direction/alight/transfer in usability tests |
| **6** Active journey mode | Execution support | Journey state machine; manual confirmations; GPS assistive-only; replan entry points | Full pilot trip followable manually; GPS never auto-advances critical steps |
| **7** Offline, recovery, reports | Resilience + feedback loop | SQLite itinerary cache; recovery flows; moderated report workflow; preferences | Offline followable; reports moderated before affecting data |
| **8** Grounded AI assistance | Comprehension | Provider-agnostic adapter; grounded explanations/translation; deterministic fallback | AI optional; grounding tests pass; no critical hallucination |
| **9** Pilot hardening + release | Release readiness | Field journeys; usability sessions; security/privacy reviews; monitoring; runbooks | Pilot release checklist signed off |
| **10** Coverage expansion + schedule awareness (future) | Growth | More corridors/modes; timetables only where validated | Each capability: own source contract, rights review, tests |

---

## 5. Status dashboard (current position)

> **▸ CURRENT POSITION: Phase 2 complete · next task: Phase 3 (pedestrian routing & transfer graph) — awaiting owner go-ahead**
>
> **Owner decisions 2026-11-20:** pilot candidate stays **unpublished** (D-1=A); pilot corridor **central Colombo** ratified (D-2=A); D-4–D-7 deferred by owner.
> **D-3 resolved (2026-11-20):** three-tier field-verification approach **adopted** (`docs/research/field-verification-approach.md`); Tier-1 tooling default = **KoboToolbox free hosting**; field staffing = **owner with smartphone** (single-person workflow supported).
> **Field kit ready:** 100-stop survey list, 22-pattern ride-check list exported; ODK form CSVs + import pipeline live (see `data/field-verification/README.md`).
> **Phase 2 note:** map renderer (MapLibre) screen deferred pending the dev-client/device spike (owner tooling); search flow + manual-coordinate fallback shipped.

| Phase / task | Status | Commit | Headline outcome | Verification result |
|---|---|---|---|---|
| 0.1 Repository & documentation audit | ✅ Done | (pre-VCS) | `docs/audits/phase-0-repository-audit.md`; **READY WITH CONDITIONS**; 14 gaps (GAP-001…014) | 32/32 docs reviewed; env profiled |
| 0.1b Git baseline | ✅ Done | `c66df09` | Git initialized on `main`; `.gitignore`; baseline commit of 34 files | `git log`/`status` verified |
| 0.2 ADRs & conventions | ✅ Done | `dd72aaa`+`616f43a`+`c568729` | ADR-0001…0004; docs consolidated under `docs/`; `AGENTS.md`; README index; supersession note on `product/06` | All files re-read/verified |
| 0.3 Infra + backend skeleton | ✅ Done | `757fd2d` | Compose stack; FastAPI skeleton; health/ready; Alembic baseline; `.env.example`; JSON logging | **12/12 tests**; live `/health` 200, `/ready` 200; PostGIS 3.4.3; Redis PONG |
| 0.4 Mobile skeleton + CI | ✅ Done* | `0fb57bd` | Expo 58 / TS skeleton + Expo Router; Jest+RNTL; `ci.yml`; ADR-0004 accepted | **7/7 mobile tests**; lint 0 problems; tsc 0 errors; *device-launch pending owner tooling* |
| 1.1 Canonical schema | ✅ Done | `b8dd456` | 22 PostGIS tables; `UNIQUE(pattern, sequence)` invariant; provenance/versioning; ADR-0006 | **25/25 tests** (13 new integration); up/down reversible |
| 1.2 Ingestion framework | ✅ Done | `8b3ece9` | Adapter contract; checksum archive; quarantine; idempotent upserts; diffs; publish/rollback; admin API; ADR-0007 | **40/40 tests**; live publish/rollback smoke |
| 1.3 First adapter + QA report | ✅ Done | `3f36d01` | OSM/Overpass adapter (ODbL registered); variant grouping; ordered calls; QA reports; rights register | **46/46 tests**; **live ingest: 230 records → 176 added / 54 failed**; QA report committed |
| 1.4 Coverage scorecard + field-verification workflow | ✅ Done | `5d31006` | Coverage scorecard (17 routes, avg 23/100); QA review queue (35 items); ODK form kit + export/import scripts; verification recording API | **51/51 tests**; live: scorecard/queue/exports generated against pilot data |
| 2 Place search + local names + map | ✅ Done* | (this phase) | Trigram search over aliases (en/si/ta) + canonical names; `GET /places/search`, `GET /stops?bbox=`, reverse-geocode adapter (none configured — honest); mobile search UI + manual-coordinate fallback; migration `0005` | **60/60 backend** · **11/11 mobile** · live: 'pettah' → stop hit, '176' → route hit, bbox → 54 stops; *MapLibre screen pending device spike* |
| **3 — Pedestrian routing & transfer graph** | ⬜ Next | — | Valhalla PoC; walking adapter; shapes import | — |
| 2 … 10 | ⬜ Not started | — | See §4 | — |

**Current quality gate totals:** backend `pytest` **60 passed** · `ruff format --check`/`check` clean · `mypy` clean · mobile `jest` **11 passed** · mobile `tsc --noEmit` + `eslint` clean · Docker stack healthy (postgres/redis/backend).

---

## 6. Phase records (detailed)

### Phase 0.1 — Repository and documentation audit (2026-11-19)

- **Deliverable:** `docs/audits/phase-0-repository-audit.md` — the repository was documentation-only (32 files: 10 research drafts + 19-file architecture package + README/IMPLEMENTATION_PLAN), **not a Git repository**, zero code/tests/CI.
- **Classification:** READY WITH CONDITIONS. Gap register GAP-001…GAP-014 (P0: no VCS; docs split + README index gap; three conflicting phase-numbering schemes. P1: superseded tech content in `product/06`; two story registers; undecided tech selections; Python 3.11 vs 3.12; no ADRs. P2: pilot corridor undecided; source rights unevidenced; owners unresolved; retention/legal deferred. P3: providers/hosting; deferred features).
- **Documentation conflicts found (C1–C9):** Redis optional vs baseline; job library; nav/E2E tool choices; three phase schemes; story-ID collision; old draft's Flutter option; data-strategy phrasing (resolved by final `09`).

### Phase 0.1b — Git baseline (commit `c66df09`)

- Owner decisions: Git **yes**; consolidate docs **yes**; architecture baseline **yes**; mobile **both platforms**.
- `.gitignore` (Python/Node/Expo/env/secrets); `git init`; all 34 files committed as the untouched baseline.

### Phase 0.2 — ADRs and project conventions (commits `dd72aaa`, `616f43a`, `c568729`)

- Docs consolidated with `git mv`: `docs/product/` (00–09 **plus** `11_IMPLEMENTATION_PLAN.md`), `docs/architecture/` (00–17), `docs/adr/`, `docs/audits/`; `Docs` folder removed; index casing normalized.
- **ADR-0001** canonical: docs layout; **phase numbering = plan Phases 0–10** with mapping to the other schemes; backend module map (`places`, `transport`, `pedestrian`, `transfers`, `routing`, `itineraries`, `journey_sessions`, `data_ingestion`, `data_quality`, `reports`, `ai_assistance`, `platform`); **story register = `docs/architecture/04_USER_STORIES.md` (US-001–039)** with old→new ID mapping.
- **ADR-0002** stack ratified (Expo Router, Maestro, TanStack Query + Zustand, i18next, Python ≥3.12); **ADR-0003** Redis scoped; **ADR-0004** job library (later confirmed Dramatiq by owner).
- `AGENTS.md` created (required reading, precedence, critical product rules, working protocol, conventions); root README rewritten as the full index; supersession note added to `docs/product/06_TECHNICAL_ARCHITECTURE.md` (Flutter/OTP options no longer open).

### Phase 0.3 — Infrastructure and backend skeleton (commit `757fd2d`)

- `infra/docker/compose.yaml`: `postgis/postgis:16-3.4` (+ init script enabling PostGIS), `redis:7-alpine`, `backend` service (hot reload) — one `.env` serves host and container (service-name overrides).
- Backend: app factory; `platform/` (typed config via pydantic-settings, single-stream **JSON logging**, stable error envelope `{code,message,details,request_id}`, lazy async SQLAlchemy engine/session, lazy Redis client); `GET /api/v1/health` + `GET /api/v1/ready` (component checks, 503 degraded); request-ID middleware (logs method/path only — never query strings).
- Alembic async env reading `DATABASE_URL` from settings; empty baseline migration `0001_baseline`.
- **ADR-0005** Docker-first (host lacks Python 3.12): pinned `python:3.12-slim`.
- Verified live: `/ready` 200 (db+redis ok), PostGIS 3.4.3, Redis PONG.

### Phase 0.4 — Mobile skeleton and CI (commit `0fb57bd`)

- `apps/mobile/` via `create-expo-app` (SDK 58: RN 0.88.1, React 19.3, TS 6), trimmed: `src/app/_layout.tsx` (typed Stack: Home + Journey), Home screen, journey placeholder, `lib/config.ts` (`EXPO_PUBLIC_*`), `lib/api.ts` (typed client mirroring the backend error envelope); app identity `sljp-mobile`/scheme `sljp`/Android package `lk.sljp.mobile`.
- Tooling: jest-expo + @testing-library/react-native, eslint-config-expo; scripts `lint`/`typecheck`/`test`; `apps/mobile/.env.example`.
- **CI created:** `.github/workflows/ci.yml` — backend job (format/lint/types/tests + Alembic up/down/up in compose) and mobile job (`npm ci` → lint → typecheck → tests). CI execution requires a git remote (pending owner).

### Phase 1.1 — Canonical transport schema (commit `b8dd456`)

- **ADR-0006**: versioning = canonical working tables + `dataset_versions`/`dataset_version_entities` diffs + singleton `active_dataset` pointer; UUID PKs (`gen_random_uuid()`); `timestamptz`/UTC; PostGIS `geography` SRID 4326 with GiST everywhere; CHECK-constraint enums; verification states `unverified`/`reported`/`verified`; models owned by their canonical modules; Alembic registry.
- Migration `0002_canonical_schema` (hand-written, reversible): 22 tables — provenance (`data_sources`, `source_snapshots`, `source_records`, `sync_runs`), versioning (`dataset_versions`, `dataset_version_entities`, `active_dataset`), transport (`transport_agencies`, `transport_routes`, `route_patterns`, `stops`, `stop_access_points`, `route_pattern_stops`, `route_shapes`, `transfer_connections`, `fare_rules`), places (`localities`, `places`, `place_access_points`, `entity_aliases`), quality (`verification_records`, `data_change_audit`). Core invariant `UNIQUE (pattern_id, sequence)`.
- Integration tests introduced (live DB; skip when unreachable).

### Phase 1.2 — Ingestion framework (commit `8b3ece9`)

- **ADR-0007** (supersedes ADR-0006's rollback clause): pointer-flip rollback + re-materialisation runbook; adapter contract; content-addressed snapshot archive; whole-run quarantine; no-op updates recorded as `unchanged` (no diff rows); admin API mounted **only outside production**.
- `IngestionService.run_sync`: fetch → sha256 short-circuit → archive → parse → validate → idempotent upsert (stop/route/place) → per-record diffs → candidate version. `DatasetVersionService.publish/rollback`; `SourceRegistry`.
- Migration `0003_source_record_link`: `source_records.canonical_entity_type/id` bookkeeping.
- Admin endpoints: sources CRUD-lite, sync trigger, run detail, versions list/publish/rollback/active.

### Phase 1.3 — First source adapter and QA report (commit `3f36d01`)

- `data/source-rights-register.md` — OSM/Overpass registered (ODbL 1.0, attribution/share-alike obligations, private snapshots); NSDI/NTC/GTFS/SL-Railways explicitly NOT registered (rights unknown).
- `adapters/overpass.py`: configurable pilot bbox; stops from tagged named nodes (`name:si`/`name:ta` → aliases); relations grouped **by `ref` into one route with per-relation variants**; ordered calls with role-derived boarding/alighting; unnamed nodes excluded (counted as diagnostics); unresolvable refs fail that record only.
- New handlers `PatternUpsert` / `PatternStopUpsert` (cross-record matching via source-record links; change detection → `unchanged` records produce no diff rows).
- `report.py` `QualityReportService` → JSON + Markdown per version; admin endpoints `GET/POST /admin/dataset-versions/{id}/quality-report[/write]`.
- Migration `0004_pattern_stop_entity_type` (`route_pattern_stop` allowed in DVE/verification/change-audit checks; also reconciled constraint-name drift from the raw-SQL migration).
- **Live pilot ingest (one read-only Overpass request, central Colombo bbox):** run `d4d4a724` → **230 records: 176 added, 54 failed (unresolved member refs)** → candidate version `osm-overpass-d4d4a724` (**kept as candidate; not published**). Committed QA report: 100 stops (all `unverified`, all with coordinates), 17 routes, 22 patterns, 37 ordered calls; checks honestly show 15 patterns without calls and 3 with <2 calls; live route 176 has 3 variants, 103/187/49 have 2.

---

### Phase 1.4 — Coverage scorecard and field-verification workflow (2026-11-20)

- **Coverage scorecard** (`data_quality/scorecard.py`, `GET /admin/coverage-scorecard`): transparent route-by-route completeness scoring (weights documented in code: calls 30, coordinates 20, variants 20, aliases 15, agency 15). Live result: **17 routes scored, average 23.0/100** — honestly low, reflecting missing calls/aliases/agencies. Evidence committed: `backend/data/validation_reports/pilot-coverage-scorecard.md`.
- **QA review queue** (`data_quality/queue.py`, `GET /admin/qa-queue`): prioritized actionable review items — live: **35 items** (patterns under 2 calls, routes without agency, etc.), each with entity refs and suggested action.
- **Verification recording** (`POST /admin/verifications`, `GET /admin/verifications`): entity-existence-checked writes to `verification_records` (method/reviewer/evidence/result) — the API the field import and future in-app reporter use.
- **Field kit committed** (`data/field-verification/`): `README.md` (procedure: walking day, ride-along day, import, progress tracking) + XLSForm CSVs (`forms/stop_verification_{survey,choices,settings}.csv`, trilingual labels) → convert to XLSX → deploy on KoboToolbox free hosting (adopted default).
- **Scripts**: `scripts/export_field_surveys.py` (live output: **100 stops, 22 patterns, 0 transfers**) and `scripts/import_field_verifications.py` (writes `verification_records`, produces corrections report; canonical data never modified directly; `--dry-run` supported).
- **Issue I-18 discovered:** integration-test cleanup wipes dev canonical data (tests share the dev DB) → pilot re-ingested identically (`osm-overpass-4e442b17`, 230/176/54 — deterministic). Proper fix recorded as tech-debt: dedicated test database.


### Phase 2 — Place search, local names and map foundation (2026-11-20)

- **Migration `0005_trgm_search_indexes`**: `pg_trgm` extension + GIN trigram indexes on `entity_aliases.alias`, `stops.name`, `places.name`, `localities.name`.
- **Normalization** (`places/normalize.py`): casefold + punctuation/symbol folding via Unicode **general categories** — critical fix: Python's `\w` does not match Indic combining marks (U+0DDD/U+0DCF are `isalnum()==False`), so regex-class normalization was destroying Sinhala words; combining marks (M*) are preserved, NFKC folding removed (it decomposes native-script marks — documented trade-off: full-width Latin is not folded to ASCII).
- **Search service + API** (`places/search.py`, `GET /api/v1/places/search`): unified search over stops/places/localities/routes across canonical names and en/si/ta aliases; transparent scoring (exact 1.0 / prefix 0.9 / substring 0.8 / alias trigram ≥0.5); deduped per entity; every hit carries verification status and matched language; ambiguous candidates always listed, never auto-selected.
- **Map-data endpoint** `GET /api/v1/stops?bbox=` (validated bbox; live: 54 stops returned for Fort/Pettah).
- **Geocoder adapter** (`places/geocoder.py`): provider interface + `NoGeocoder` default that honestly reports "no provider configured" — provider selection remains an open owner decision (public Nominatim is not production-eligible per the knowledge base).
- **Mobile**: Home screen became the search experience (input → results with type + matched-language + "not field-checked yet" badge → selection only on user tap; manual lat/lon fallback for no-location/no-result); `searchPlaces()` typed client; tests use RNTL v14 `userEvent` (async state updates).
- **Live verification**: 'pettah' → 1 stop hit; '176' (types=route) → route hit (score 1.0); bbox → 54 stops; reverse-geocode → `provider: none, results: []` (honest).


### Phase 1.3+ — Owner decisions and D-3 research (2026-11-20)

- **Decisions recorded:** D-1 keep pilot candidate unpublished; D-2 pilot corridor = **central Colombo** (default bbox ratified); D-4 (ODbL legal review), D-5 (mobile device launch), D-6 (GitHub/CI), D-7 (si/ta reviewers) — **deferred by owner** with recorded "needed by" dates.
- **D-3 research** delivered: `docs/research/field-verification-approach.md` — compared six approaches (ODK/KoboToolbox structured surveys, StreetComplete, OpenStop, ride-along GPS audits, Field Papers, official-feed import) with retrieved web sources.
- **Recommendation adopted for implementation planning:** three-tier approach — **Tier 1** ODK/KoboToolbox offline forms pre-loaded with *our* stop/transfer lists (GPS + photo evidence → `verification_records` → moderation → candidate version; nothing auto-publishes); **Tier 2** OSM-native apps (OpenStop, StreetComplete) to fix upstream OSM during the same walks; **Tier 3** ride-along GPS audits to validate `route_pattern_stops` order/variants. Sub-choices open: KoboToolbox hosting vs self-hosted ODK; who does the field walks (works for a single owner with a smartphone).

---

## 7. Issues and resolutions log (append-only)

| # | Date | Phase | Issue | Impact | Fix | Evidence |
|---|---|---|---|---|---|---|
| I-01 | 2026-11-19 | 0.1 | Host `python` is 3.11.9; docs require 3.12+ (GAP-007) | Env drift risk | ADR-0005: Docker-first dev with pinned `python:3.12-slim` | audit §10 |
| I-02 | 2026-11-19 | 0.2 | `Docs` vs `docs` case mismatch after moves on Windows | Index/working-tree inconsistency | Two-step case rename + `git add -A`; later index normalization commit `616f43a` | Phase-0.2 report |
| I-03 | 2026-11-19 | 0.2 | Supersession note duplicated a heading in `product/06` | Doc blemish | Removed duplicate (`c568729`) | diff |
| I-04 | 2026-11-19 | 0.4 | ESLint 10 incompatible with `eslint-config-expo`'s plugin stack | Lint crashed | Pinned `eslint@^9.39.5` (expo's own selection) | lint log |
| I-05 | 2026-11-19 | 0.4 | `jest-expo` peer missing `@react-native/jest-preset` | Jest wouldn't start | Installed `@react-native/jest-preset@0.88.1` | test log |
| I-06 | 2026-11-19 | 0.4 | Template hook violated `react-hooks/set-state-in-effect` | Lint error | Rewrote `use-color-scheme.web.ts` with `useSyncExternalStore` hydration snapshots | lint log |
| I-07 | 2026-11-19 | 0.4 | Jest couldn't require web-only `global.css`; missing jest types; stale `package.json` after trim (tooling landed under `dependencies`) | Typecheck/test failures | CSS stub via `moduleNameMapper`; `@types/jest` + `"types"`; package.json rewritten with clean devDependencies | test logs |
| I-08 | 2026-11-20 | 1.1 | Missing `Integer` import broke migration run | Alembic failure | Import added; re-ran | migration log |
| I-09 | 2026-11-20 | 1.2 | Alembic `version_num` is VARCHAR(32) — 33-char revision ID failed stamping | Migration rolled back | Renamed revision to `0003_source_record_link` (≤32 chars) | error log |
| I-10 | 2026-11-20 | 1.2 | Running backend container was stale (pre-1.1 image, no `geoalchemy2`) → app import error, HTTP hangs | Live smoke blocked | `docker compose up -d --force-recreate backend` after rebuilds (note: `--reload` swaps files, not images) | container logs |
| I-11 | 2026-11-20 | 1.2 | `run_sync` did not flush `SyncRun` status changes on exit paths | Raw-SQL readers (and tests) saw stale `started` | Flush on every exit path of `run_sync` | integration tests |
| I-12 | 2026-11-20 | 1.2 | Upserts recorded `updated` diffs for identical content | Diff noise | Change detection → `unchanged` op, no diff row | test `test_changed_source_records_updates` |
| I-13 | 2026-11-20 | 1.2 | Committed API-test rows poisoned later tests; per-test event loops vs process-global engine | 5–6 test failures | Autouse canonical-table cleanup fixture; engine disposed/reset per service test | conftest |
| I-14 | 2026-11-20 | 1.2 | Rollback rejected a superseded version as target | Rollback unusable for the intended flow | Allow targets with status `published` or `superseded` | service.py |
| I-15 | 2026-11-20 | 1.3 | Inline CHECK constraints in raw-SQL migration `0002` got PostgreSQL auto-names; model-declared names drifted from DB | Migration `0004` initial failure | `0004` drops auto-named and adds convention-named constraints (both directions) | pg_constraint query |
| I-16 | 2026-11-20 | 1.3 | mypy couldn't narrow link optionals through a "collect-missing-then-raise" pattern | 3 mypy errors | Immediate per-reference `raise ValueError` in `PatternStopUpsert` | mypy log |
| I-17 | 2026-11-20 | 1.3 | PowerShell `Set-Content -Encoding utf8` wrote a BOM → fixture JSON unparseable | Live smoke quarantined (correctly!) | Rewrote file without BOM (`UTF8Encoding $false`) — the quarantine path proved itself | sync_runs.error |
| I-18 | 2026-11-20 | 1.4 | Integration-test canonical-table cleanup wiped the dev pilot data (tests share the dev DB) | Pilot had to be re-ingested | Re-ingested identically (`osm-overpass-4e442b17`, 230/176/54 — adapter is deterministic). Tech-debt recorded: dedicated test database for integration tests | sync history |
| I-18-fix | 2026-11-20 | 2 | Dedicated test database implemented: tests create + migrate `journey_planner_test` (init script + session fixture); dev data never touched by tests again | Recurring wipe risk eliminated | `tests/conftest.py` URL redirect; `tests/integration/conftest.py` session fixture (sync wrapper; AUTOCOMMIT DB creation; alembic upgrade) | pytest run: dev stops stayed intact |
| I-19 | 2026-11-20 | 2 | Overpass public instance returned 502 (and mirror ReadTimeout) → sync turned into unhandled 500 | Live re-ingest blocked; poor API semantics | (a) `run_sync` catches fetch failures → run `failed`, previous data keeps serving, API stays 200 (plan §5.2 rule 3); (b) Overpass **mirror fallback** (`OSM_OVERPASS_FALLBACK`, kumi.systems) added to adapter | container logs; retry succeeded |

---

## 8. Verification log (how to reproduce the current green state)

All commands run from the repository root unless noted. Docker Desktop must be running.

```powershell
# 1. Environment + stack
copy .env.example .env
docker compose --env-file .env -f infra/docker/compose.yaml up -d --build
docker compose --env-file .env -f infra/docker/compose.yaml run --rm backend alembic upgrade head

# 2. Backend gates (in-container; = CI)
docker compose --env-file .env -f infra/docker/compose.yaml run --rm backend `
  sh -c "ruff format --check . && ruff check . && mypy && pytest"
#   → 46 passed, 1 warning (starlette TestClient deprecation; third-party)

# 3. Mobile gates (from apps/mobile/)
cd apps/mobile; npm ci
npm run lint        # → 0 problems
npm run typecheck   # → 0 errors
npm test            # → 7 passed
npm start           # dev server; 'a'/'i' launches on a simulator (owner tooling)
```

**Live endpoints (local):** `GET /api/v1/health` (liveness) · `GET /api/v1/ready` (readiness) · `/api/v1/docs` (OpenAPI) · `/api/v1/admin/*` (data ops; local/test only).

**Recent live verifications:**
- 2026-11-20: `/ready` 200 (database ok, redis ok) after Phase 1.3 rebuild.
- 2026-11-20: OSM pilot ingest run `d4d4a724` succeeded (230/176/54) — see §6 Phase 1.3.
- 2026-11-20: QA report `backend/data/validation_reports/osm-overpass-d4d4a724.md` generated and committed.
- 2026-11-20: Phase 1.4 live verification — re-ingest `osm-overpass-4e442b17` succeeded (230/176/54, deterministic); coverage scorecard **17 routes, average 23.0/100**; QA queue **35 items**; field-survey exports generated (**100 stops / 22 patterns / 0 transfers**); reports committed under `backend/data/validation_reports/`.
- 2026-11-20: Phase 2 live verification — pilot re-ingested as `osm-overpass-3cf065d7` (230/176/54, after an Overpass outage was survived via mirror fallback); `GET /places/search?q=pettah` → 1 stop; `?q=176&types=route` → 1 route; `GET /stops?bbox=79.84,6.90,79.87,6.94` → **54 stops**; reverse-geocode honestly returns `provider: none`.

---

## 9. Open questions and pending decisions

**Resolved (owner, 2026-11-20):**

| # | Decision | Resolution |
|---|---|---|
| D-1 | Publish pilot candidate? | **Keep as candidate** — no publish until field verification (facts remain `unverified`) |
| D-2 | Pilot corridor | **Central Colombo** (default bbox `PILOT_BBOX=6.88,79.83,6.96,79.90` ratified; configurable, never hard-coded) |
| D-3 | Field-verification approach | **ADOPTED (2026-11-20): three-tier ODK-centred approach** — `docs/research/field-verification-approach.md`. Defaults: KoboToolbox free hosting (Tier-1 tool), owner as field worker. Implementation = Phase 1.4 |
| D-4 | ODbL legal review | **Deferred** — before any public release |
| D-5 | Mobile device launch | **Deferred** — owner tooling, before Phase 2 UX work |
| D-6 | GitHub remote + CI | **Deferred** — low effort when owner is ready |
| D-7 | Native si/ta reviewers | **Deferred** — needed by Phase 5 |

**Still open within resolved items:**
- D-3 staffing: who performs the field walks (the recommended approach works for a single owner with a smartphone).
- D-3 tooling sub-choice: KoboToolbox free hosting (fast start) vs self-hosted ODK (we have Docker).

**Known technical limitations (recorded, acceptable):**
- Rollback = pointer flip + re-materialisation runbook (no automated data reversal) — ADR-0007.
- QA report gaps (15 patterns without calls / 54 failed records) stem from OSM member nodes without names/tags in the bbox — a **coverage-data finding**, not a bug; field verification or a supplementary source resolves them.
- `pytest` deprecation warning originates in starlette's TestClient (third-party).
- npm audit reports moderate transitive advisories in RN tooling; `audit fix --force` deliberately avoided.
- Admin API is unauthenticated by design until Phase 9 (production-gated in code).

---

## 10. Remaining path to completion (living checklist)

**Phase 1 (finish):**
- [x] Owner decisions D-1/D-2 resolved (2026-11-20); D-3 adopted (three-tier approach)
- [x] Phase 1.4 — coverage scorecard (17 routes, avg 23/100); QA review queue (35 items); ODK form kit + export/import scripts; verification recording API; field kit committed (`data/field-verification/`)
- [ ] **Owner field walks** (2–3 days, per `data/field-verification/README.md`) — the Phase 1 exit gate's field-check item; deploy Kobo form, walk, import
- [ ] Tech-debt: dedicated test database for integration tests (I-18)

**Phase 2 — Place search, local names, map:**
- [x] Place/alias search API (trigram; language-tagged); ambiguous-result handling (listed, never auto-selected)
- [x] Geocoder behind provider adapter (NoGeocoder default — provider choice still open, GAP-013/D-item)
- [x] Mobile search flow (results + disambiguation + manual-coordinate fallback)
- [ ] MapLibre map screen — **pending dev-client/device spike** (owner tooling; recorded like the Phase 0 device item)
- [ ] Destination entrances for curated pilot POIs (Phase 2.2 candidate)

**Phase 3 — Pedestrian routing and transfer graph:**
- [ ] Valhalla proof of concept on Sri Lankan OSM pedestrian data (vs GraphHopper) → ADR
- [ ] Walking-router adapter (snapping, bounded fallback, no-path honesty)
- [ ] Access/egress/transfer walks as explicit legs; verified transfer connector overrides
- [ ] Route shapes import from OSM ways (deferred from 1.3)

**Phase 4 — Deterministic multimodal planner:**
- [ ] Graph interfaces over route patterns + explicit transfers; direct/multi-leg candidate generation
- [ ] Constraints (walk cap, transfer cap, modes, confidence threshold); Pareto filtering; ranking profiles
- [ ] Curated routing regression suite; cache keyed by dataset version; no-route/low-coverage outcomes

**Phase 5 — Instructions and itinerary experience:**
- [ ] Deterministic instruction templates per step type (unknowns rendered as "not confirmed")
- [ ] Itinerary schema + results/overview UI; en/si/ta templates with **native review** (D-7)

**Phase 6 — Active journey mode; Phase 7 — Offline/recovery/reports; Phase 8 — Grounded AI; Phase 9 — Pilot hardening/release; Phase 10 — Expansion**
- [ ] As specified in §4 / implementation plan (sequential gates)

**Standing obligations on every task:** update this report (§1 protocol); run gates; never invent transport facts; ADRs for material architecture changes.

---

## 11. Transport-data honesty statement (current data state)

- The only ingested source is **OpenStreetMap via Overpass** (ODbL) for a small central Colombo bbox — **candidate version `osm-overpass-d4d4a724`, not published**.
- Every imported fact carries `verification_status = 'unverified'`. No timetable, live-availability, fare, or accessibility claims exist or may be made.
- Coverage figures (100 stops / 17 routes / 22 patterns / 37 ordered calls) describe **imported data within the bbox**, not service reality; OSM does not guarantee operational status or complete sequences.
- Known data gaps (recorded in the committed QA report): 15 patterns with no resolvable stop calls, 3 patterns with <2 calls, no agency attributions, no shapes, no transfer connectors, no verified anything — all awaiting field verification (D-3) and/or additional sources.

---

*End of report. Next update: at the completion of Phase 1.4.*
