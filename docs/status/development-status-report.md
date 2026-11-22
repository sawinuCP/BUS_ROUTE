# Development Status Report — Sri Lanka Journey Planner

**Report ID:** `docs/status/development-status-report.md`
**Last updated:** 2026-11-20 (Phase 3 work item 1: Valhalla PoC + ADR-0008 ratified)
**Maintained by:** coding agent + product owner
**Companion documents:** `docs/product/11_IMPLEMENTATION_PLAN.md` (control document), `docs/audits/phase-0-repository-audit.md`, `docs/adr/ADR-0001…0008`, `data/source-rights-register.md`

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

**Stack (ADR-0002, ratified):** React Native + TypeScript + Expo (Expo Router, TanStack Query + Zustand, SQLite, MapLibre React Native) · Python 3.12+ (Docker-pinned, ADR-0005) / FastAPI / Pydantic / SQLAlchemy 2.x / Alembic · PostgreSQL 16 + PostGIS 3.4 · Redis (scoped, ADR-0003) · Dramatiq (ADR-0004, accepted) · deterministic multimodal transit graph · **Valhalla 3.5.1 walking engine (ADR-0008, ratified 2026-11-20)** · REST + OpenAPI · modular monolith · pytest, Ruff + mypy, Jest + RNTL, Maestro. Prohibited in MVP: Kubernetes, Kafka, vector databases, microservices.

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
| 0008 | Walking engine: Valhalla 3.5.1 pinned (GraphHopper PoC skipped; triggers recorded) | Accepted (owner, 2026-11-20) |

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

> **▸ CURRENT POSITION: Phase 6 done in code + Phase 7 items 1–3 and 5–6 done in code (offline core; recovery from a confirmed stop; grounded no-route adjustment suggestions) · remaining Phase 7: queued reports (4), moderation (7–8), preferences (9–10) · owner device runtime check (D-5/D-9) and owner field walks (shared exit gate) still pending**
>
> **Owner decisions 2026-11-20:** pilot candidate stays **unpublished** (D-1=A); pilot corridor **central Colombo** ratified (D-2=A); D-4–D-7 deferred by owner.
> **D-3 resolved (2026-11-20):** three-tier field-verification approach **adopted** (`docs/research/field-verification-approach.md`); Tier-1 tooling default = **KoboToolbox free hosting**; field staffing = **owner with smartphone** (single-person workflow supported).
> **D-8 (2026-11-20):** pilot bbox widened to **Western Province** (`PILOT_BBOX=6.60,79.75,7.30,80.25`) — owner approved; live ingest delivered **432 stops / 38 routes** island-of-WP coverage (vs 100 stops in central Colombo). Overpass query timeout raised to 300 s for the larger area.
> **D-9 (2026-11-20):** MapLibre map screen **integrated in code** (`/map` screen, stop markers, "View on map" from search); runtime verification on a device **pending owner dev-client spike** (Android Studio — same tooling dependency as the Phase 0 device item).
> **D-10 (2026-11-20):** walking engine **ADR-0008 ratified — Valhalla 3.5.1 pinned**; GraphHopper PoC deliberately skipped (re-evaluation triggers recorded in the ADR).
> **Infra hardening:** Docker DB republished on **host port 5433** (I-20: a native Windows PostgreSQL service on 5432 hijacked loopback connections); integration tests now provably target `journey_planner_test` only (I-21: the I-18 fix was incomplete — Alembic/cleanup still resolved the dev URL; dev data was wiped and **restored from the archived OSM pipeline**).

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
| **3 — Pedestrian routing & transfer graph** | ✅ Done* | (this phase) | Valhalla PoC + **ADR-0008 ratified**; walking adapter (`/api/v1/walking/route`); **route shapes imported for 41/45 patterns** (101 Moratuwa→Fort = 21.1 km ✓); 432 stop access points; **19 candidate transfer connectors** routed through the walking engine (51–434 m, avg 234 m) | **75/75 backend** (9 new tests); live: real reparse + candidate generation; *exit gate needs field-checked pilot paths (owner walks)* |
| **4 — Deterministic multimodal planner** | ✅ Done* | (this phase) | Core planner (exact patterns + explicit connectors, board-before-alight, walk legs only from routed paths, constraints, rail verified-only, Pareto + labels, honest `no_route`); **plan cache** (Redis, request+version keyed, ADR-0003); **saved journeys** (`save`, `GET /journeys/{id}`, `/refresh` re-plans against active version); **performance baseline** (`docs/evidence/plan-benchmark-2026-11-22.md`: miss p95 3.5 ms, hit p95 2.0 ms on 5 representative pairs × 10 iters) | **101/101 backend** (26 new across both tasks); live: direct + 1-transfer journeys ✓, cache miss→hit ✓, save/get/refresh ✓, version-change invalidation ✓; *owner field walks + regression-suite extension remain* |
| **5 — Instructions + itinerary UX** | ✅ Done* | (this phase) | Backend core (see 2026-11-22 record) **+ mobile screens (items 9–10)**: `journey` screen rewritten from placeholder to plan flow (stop pickers with explicit selection, `no_route` honesty, results **cards with trade-offs** — duration band labelled "network estimate", walking, transfers, label chips, confidence phrasing) and new `journey-steps` screen (ordered instruction steps verbatim from the backend templates, warnings, dataset-version + not-live footer); typed plan payloads + `planJourney()` in `lib/api.ts`; in-memory plan hand-off store | **18/18 mobile** (7 new: cards + trade-offs + hand-off, honest no_route, planning-failure error, ordered steps verbatim, no-plan state); tsc + eslint clean; *runtime device check still pending owner spike (D-5/D-9); si/ta native review pending (D-7)* |
| **6 — Active journey mode** | ✅ Done* | (this phase) | **Backend core** (see the 2026-11-22 record) **+ mobile**: new `active-journey` "Do this now" screen (confirm/pause/resume/end/re-plan buttons, manual progress authoritative), step facts carry `target_lat/lon` from canonical data (never invented), session client in `lib/api.ts` (start/get/event/replan; `planJourney` now saves plans so guided mode always starts from a grounded server-generated plan), local session persistence via expo-sqlite (session id + last snapshot — **no location stored**), pure GPS-suggestion logic (`lib/geoSuggestions.ts`: accuracy ≤ 50 m gate, 200 m jump rejection, 3-sample dwell; **suggestions only, never auto-advances a step**; off by default), opt-in keep-awake, offline snapshot fallback, honesty footer | **121/121 backend** · **30/30 mobile** (12 new: 5 "Do this now" screen tests incl. no-auto-advance + restore/no-session states, 6 GPS-safeguard unit tests, template-fact + steps-screen tests); tsc + eslint clean; backend live smoke end-to-end ✓; *owner device runtime check (D-5/D-9 spike) and voice/read-aloud (P1, D-7) remain* |
| **7 — Offline core (plan items 1–3)** | 🔄 In progress (offline core done) | `9b05927` | Offline plan cache (`lib/planDb.ts`: last plan + dataset version + opened option in SQLite; steps verbatim); journey-steps screen restores from cache after restart with a "Saved on this device · <age>" banner and an explicit capabilities note; offline manual progress (`lib/progressQueue.ts`): events queue in SQLite on network failure, a device-local projection mirrors `state_machine.py` so the itinerary stays followable, replay is ordered on reconnect, network failure keeps events queued, a 409 lets the **server state win** (remaining events dropped, rule text surfaced); queued events flushed before every new online action (ordering guard); stale-dataset-version note when the session's version differs from the cached plan; `ApiStatusError` separates 409s from offline failures | **50/50 mobile** (20 new: 5 planDb incl. corrupted-cache honesty, 10 progressQueue incl. ordering/network-keep/409-server-wins, 3 steps-screen offline restore, 2 active-journey offline queue/replay; cache-write asserted in the journey screen test); tsc + eslint clean; no backend change (backend remains the only authority); *airplane-mode device test pending owner spike* |
| **7 — Recovery + no-route suggestions (plan items 5–6)** | 🔄 In progress (done) | `d5a68ce` | **Backend**: `no_route` plan responses carry structured, grounded `suggestions` — `nearby_stop` (nearest mapped alternatives, straight-line always labelled "as mapped"; for coordinate endpoints the nearest stop even beyond the cap), `larger_walk_cap` (grounded in the *routed* walking-only distance from the walking engine, or an honestly-caveated mapped estimate), `allow_mode` (only when rail patterns exist in the dataset and rail is excluded, with the verified-station-order rule restated); `ok` responses carry none; deterministic and cached with the plan. **Mobile**: suggestion cards on `no_route` ("Try instead — from mapped data, nothing is promised to work") with actions that re-plan through the same honest planner; **recovery flow** in "Do this now": "Missed it? Re-plan" opens a confirm-where-you-are panel (search + explicit stop confirmation — never auto-detected; covers missed-stop, wrong-route and missed-transfer recovery) → `replan` with origin override; honest no-replacement preserved; same-OD re-plan kept as a panel action | **128/128 backend** (7 new: nearby stops, routed walk-cap suggestion, beyond-cap coordinate suggestion, allow_mode gating, ok-carries-none, payload serialization), **53/53 mobile** (3 new: suggestion card + re-plan-through-suggestion, recovery from confirmed stop, honest no-replacement + cancel); ruff/format/mypy + tsc/eslint clean; API contract documented in `11_BACKEND_API_DESIGN.md` |
| 8 … 10 (rest of Phase 7 + 8/9/10) | ⬜ Not started | — | See §4 | — |

**Current quality gate totals:** backend `pytest` **128 passed** · `ruff format --check`/`check` clean · `mypy` clean (59 files) · mobile `jest` **53 passed** · mobile `tsc --noEmit` + `eslint` clean · Docker stack healthy (postgres/redis/backend/valhalla).

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


### Phase 2.1 — Coverage widening, map prep, infra hardening (2026-11-20)

- **D-8 coverage widening**: `PILOT_BBOX` → Western Province `6.60,79.75,7.30,80.25`; Overpass query timeout → 300 s (`OSM_OVERPASS_TIMEOUT_SECONDS`); WP ingest `osm-overpass-1679d061` → **432 stops / 38 routes / 573 records added** (live verification: `?q=pasyala` → 2 stops at lat 7.169 (Gampaha); `?q=negombo` → 2 hits; bbox `79.95,7.05,80.05,7.20` → stops). QA report regenerated. Note: OSM route relations are bbox-selected but recursion pulls their full member geometry island-wide — WP-edge/long-distance members surface as the 37 unresolved records (honest, reported).
- **D-9 MapLibre integration (code-complete, device verification pending)**: `@maplibre/maplibre-react-native@11.5.1` + Expo config plugin in `app.json`; new `/map` screen (`Map`/`Camera`/`Marker`, `EXPO_PUBLIC_MAP_STYLE` — MapLibre demo style for dev only, production basemap = separate owner decision); "View on map" link from a selected search hit or manual coordinates; 2 new RNTL tests with the native module mocked. Gates: typecheck 0 errors, lint 0 problems, **13/13 tests**.
- **I-20 (infra)**: host port conflict with a native Windows PostgreSQL service → Docker DB republished **5433:5432**; settings default + `.env` updated.
- **I-21 (test isolation, critical)**: I-18's test-DB fix was incomplete — Alembic `env.py` and the cleanup fixture still resolved the dev URL, so this session's first full pytest run **wiped the dev pilot**. Fixed by pinning `DATABASE_URL` to `journey_planner_test` at conftest-import time. Dev data restored via the ingestion pipeline (idempotent upserts, archived source unchanged). Proven: 60/60 pytest **then** dev stops still 432, `data_sources` intact.


### Field-kit refresh for the Western Province scale (2026-11-20, pre-Phase-3)

- **Walking tiers added to the export** (`backend/scripts/export_field_surveys.py`): each stop now carries a `tier` — **A = called at by ≥1 route pattern** (routing-relevant) — and an `area` corridor label (6 zones) so the owner can plan walk days. Current export: **Tier A = 57 stops** (52 in the Colombo city core alone), Tier B = 375 (optional sweeps); QA queue now 78 items.
- **Kobo-ready XLSForm**: `backend/scripts/build_kobo_form.py` (openpyxl added to requirements) builds `data/field-verification/forms/stop_verification.xlsx` directly from the versioned CSV sheets — the owner uploads one file, no manual Excel conversion. Form retitled "Western Province pilot", version bumped to 1.1.
- **README rewritten as an owner walk plan** (`data/field-verification/README.md`): exact KoboToolbox account → upload → deploy → ODK Collect device steps; 3-day plan (Day 1: Colombo city core, 52 tier-A stops; Day 2: north/south-suburb remainder; Day 3: ride-along); **ride-along candidates identified from the data**: route **101** Moratuwa→Fort (23 resolved calls), route **154** Kiribathgoda→Angulana (20), then 141/138; import round-trip unchanged (`import_field_verifications.py`, dry-run first).
- Exports regenerated against the WP dataset (432 stops / 45 patterns / 0 transfers). Nothing about the verification flow changed: submissions → `verification_records` → review → candidate version; nothing auto-publishes.

### Phase 3 — work item 1: Valhalla PoC and walking adapter (2026-11-20)

- **Tiles built from the Geofabrik Sri Lanka snapshot** (`data/osm/sri-lanka-261119.osm.pbf`, 138 MB; the `/latest` URL was stuck in a CDN redirect loop, so a dated snapshot was used — ODbL provenance recorded in the source register): `valhalla_build_tiles` → `valhalla_build_extract`, **~9 min, exit 0**, extract `data/osm/valhalla/tiles.tar` **125.9 MB / 141 tiles**. A WP clip was made with osmium (`wp-261119.osm.pbf`) but proved unnecessary — the whole country builds fast, which also serves Phase 10 expansion later.
- **PoC route tests between real pilot stops** (`backend/scripts/valhalla_poc_routes.py`): Fort Bus Stop → Bambalapitiya Junction **5.42 km / 63.8 min / 16 maneuvers** (correct corridor: Olcott Mawatha → Lotus Road → Galle Face → Galle Road); Fort → Pasyala 42.55 km; Negombo → Pasyala 30.53 km (cross-district coverage); self-route 0 km clean. Warm latency **52–260 ms**. Evidence: `docs/evidence/valhalla-poc-2026-11-20.md` + committed sample response JSON.
- **Walking adapter implemented** (`backend/app/modules/pedestrian/`): vendor-agnostic `WalkingRouter` contract → `ValhallaWalkingRouter` (httpx, configurable base URL/timeout), `WalkPlan`/`WalkStep` in metres/seconds; failures return `None` — **no-path honesty, nothing estimated**. Endpoint `GET /api/v1/walking/route` reports `ok` / `no_path_found` / `walking_router_unavailable`. **6 new unit tests** (canned-response parsing via httpx MockTransport, HTTP/connection-error honesty, endpoint states) — **backend 66/66**.
- **ADR-0008 ratified by owner** (D-10): Valhalla **3.5.1 pinned** as the MVP walking engine; GraphHopper PoC deliberately skipped; re-evaluation triggers recorded (field-walk quality findings, footprint, engine drift).
- **Compose**: `valhalla` service added (pinned image, port 8002, tile data under gitignored `data/osm`); backend gets `VALHALLA_BASE_URL=http://valhalla:8002`. Reproducible build script: `backend/scripts/build_valhalla_tiles.py`.

### Phase 3 — items 2–3: route shapes, access points, candidate transfers (2026-11-20)

- **Route shapes imported** (adapter 0.2.0): the Overpass query already recursed into member ways/nodes, so the adapter now assembles each pattern's geometry from its member ways in order (consecutive duplicates removed; missing nodes counted, **never interpolated**). `ShapeUpsert` stores `route_shapes` MULTILINESTRING rows and links `route_patterns.shape_id`; re-runs are idempotent (normalised-WKT change detection). Live result: **41/45 patterns have shapes** — 101 Moratuwa→Fort = **21,098 m** and 154 Kiribathgoda→Angulana = **18,794 m** (both match reality); the 112 km outlier is a truncated island-wide relation, flagged in QA (4 patterns without shape = info).
- **Stop access points imported**: one per named stop at its mapped node (`unverified`, no invented type/name — the physical roadside position is unknown until field-checked). 432 rows. These anchor access/egress walking and the transfer graph.
- **Candidate transfer connectors generated** (`backend/app/modules/transfers/service.py` + script): proximity *proposals* (≤300 m, both stops served by ≥1 pattern, **no shared pattern**) routed through the walking engine into `transfer_connections` with real distance/duration/geometry — **19 candidates committed (51–434 m, avg 234 m), all `unverified`**, provenance recorded on a derived data source `walking-engine-derived` (ODbL-derived). Rule honored: proximity proposes; a *routed pedestrian path* is the explicit connector; only the moderation/field flow can verify or promote anything (data model doc §3).
- **Overpass was down** during the live import (both primary and mirror; I-23): the honest fallback was `reparse_latest_snapshot.py` — the **archived checksum-verified snapshot** re-parsed with adapter 0.2.0 into candidate version `osm-overpass-1679d061` (1083 records: 473 added / 573 unchanged / 37 failed — same unresolved records as always), recorded as a dedicated SyncRun with `parser_version='0.2.0-reparse'` and a validation-summary reparse note. Provenance exact: every new fact links to the same archived bytes it was parsed from.

### Phase 4 — core: deterministic multimodal planner (2026-11-20)

- **New canonical module `app/modules/planner/`** (no FastAPI/SQLAlchemy/Valhalla imports in domain code): `network.py` loads an immutable snapshot — patterns with ordered calls, stops with access points, **explicit** `transfer_connections` only (normalised both directions), version label from `active_dataset` (ADR-0006; falls back to newest dataset version so the unpublished candidate can be planned against in the pilot, honestly labelled).
- **Candidate generation** (`service.py`): bounded breadth-first expansion — ride edges only on exact patterns with **board-before-alight enforced** against the ordered calls and boarding/alighting flags honoured; moves between patterns only via stored connectors (never proximity) or a same-stop re-board (zero walk — you change buses where you stand; not a connector claim); anti-loop rules (no same-stop re-board of the bus just left; visited (stop, depth) pruning). **Walk legs exist only when the walking engine routed them** (`None` → candidate dropped with an honest note — never straight-line).
- **Constraints (plan items 8, 7, 12)**: allowed modes, max total walking (sum of all walk legs), max transfers (0–3), `require_verified_transfers` (excludes unverified connectors); **rail rides require `verification_status='verified'`** (station order) — unverified rail is excluded with an explanatory note, never ridden. `no_route` returns the reasons (no stops within walk cap, walking-only exceeds cap, rail excluded, etc.).
- **Alternatives (plan items 9–10)**: dedup by route/stop-chain signature; **Pareto filter** on (duration_max, walk_distance, transfers) removing only strictly dominated candidates; ranking labels `fastest / least_walking / fewest_transfers / simplest` computed from the final set (label always matches its metric).
- **Estimates (routing doc §5)**: walking time/distance from the routed engine or stored connectors; **in-vehicle time = network distance (straight-line × 1.4 detour allowance) ÷ explicit speed band 12–18 km/h**, returned as a `{min, max}` band and labelled "not timetable data; waiting times unknown". No fabricated waiting/arrival claims.
- **API**: `POST /api/v1/journeys/plan` (API design doc §example): origin/destination as `stop` or `coordinates`, preferences (priority, caps, modes, verified-transfer rule); response carries `dataset_version`, `availability_scope: network_feasible_not_live_confirmed`, per-option warnings/confidence and instruction codes. `no_route` is a 200 with reasons.
- **Tests (17 new)**: 8 unit (Pareto dominance/trade-offs, label-vs-metric, deterministic tie-break, dedup, estimate band, haversine) + 9 integration on a seeded network (direct with board<alight, explicit-connector transfer + verified-transfer exclusion, same-stop re-board, walk cap, honest no-route, walking-only fallback, verified-rail rule, determinism, endpoint contract).
- **Deliberately deferred to a follow-up bounded task** (Phase 4 remains in progress): plan cache keyed by normalised request + network version (item 13, ADR-0003 scope), saved journeys/refresh endpoints, fare ranking (item 11, no fare evidence), and extension of the curated OD regression suite to the full enumerated case list.

### Phase 4 — completion: plan cache, saved journeys, performance baseline (2026-11-22)

- **Plan cache (item 13, ADR-0003 scope honored)**: `app/modules/planner/cache.py` defines the structural `PlanCache` port + `NullPlanCache` + the normalized-request key builder (canonical sorted JSON + **network version label** — a version change produces a new key, so invalidation is immediate and old entries can only age out, never serve a new network); `app/platform/plan_cache.py` is the Redis adapter (best-effort reads/writes, **every failure degrades to a miss** — losing Redis never changes a routing result). TTL default 3600 s (`PLAN_CACHE_TTL_SECONDS`). Route handler returns `cache: hit|miss`.
- **Saved journeys** (`journey_sessions` module; migration `0006_saved_journeys`): `POST /journeys/plan` with `"save": true` persists the exact request + response snapshot (anonymous — no account required, per product rule; user association is Phase 6); `GET /journeys/{journey_id}` returns the stored snapshot with `saved_at_dataset_version` (never re-derives); `POST /journeys/{journey_id}/refresh` **re-plans against the current active dataset version** (cache bypassed) and returns `refreshed: true` with `previous_dataset_version` so callers see what changed; unknown IDs → 404 error envelope. Save works on both cache miss and cache hit (snapshot identical either way).
- **Performance baseline (exit criterion)**: `backend/scripts/plan_benchmark.py` measures representative stop-to-stop pairs (ends of the longest patterns) in-process. Observed on `osm-overpass-1679d061` (432 stops, 9 patterns with ordered calls, 38 connectors): **cache-miss p95 3.5 ms / p50 0.2 ms; Redis hit p95 2.0 ms / p50 0.9 ms**. Targets recorded in `docs/evidence/plan-benchmark-2026-11-22.md` (miss-p95 doubling = regression alert; hit p95 < 20 ms; coordinate endpoints budget Valhalla separately). Honest caveat recorded: the network is small because most imported patterns have incomplete ordered-call sequences (QA-diagnosed OSM gap) — re-measure at island scale.
- **Regression additions**: multi-transfer chain test (2 transfers across 3 patterns with the cap enforced — 1-transfer cap returns `no_route` for the same OD), cache hit/version-change invalidation, save/get/refresh flow incl. 404.
- **Live verification**: cache `miss → hit` on identical requests; saved journey created on a cache hit (snapshot identical), `GET` snapshot matches, `refresh` re-plans and reports versions; unknown ID → 404.

### Phase 5 — backend core: deterministic instructions (2026-11-22)

- **New canonical module `itineraries`** (`instructions.py`; the boundary stub from ADR-0001 now implemented): converts planner legs into ordered typed `InstructionStep`s with the API design doc's stable action codes. Walk legs → one step each; ride legs → **board → ride → alight**. Transfer steps carry `next_boarding_point` (work item 6); board steps show route number + **headsign only when the pattern's destination label exists**, otherwise the fact is recorded as "not confirmed" (work item 3, no-fabrication rule).
- **Reliability-gated stop counts (work item 5)**: `RideLeg.intermediate_stops` is computed only when the stored sequence numbers are contiguous across the ride span; a gap (incomplete OSM member sequence) renders "Stay on route X and alight at Y." and records the count as "not confirmed". Live proof: Kollupitiya→Fort on route 101 honestly withholds the count because the OSM relation's stop sequence has gaps.
- **Language**: `POST /journeys/plan` accepts `language: en|si|ta`; non-English requests render English with an explicit note that native review is pending (D-7) — never machine-translated and presented as reviewed. Language is part of the normalized **cache key** and of the saved-journey preferences (refresh renders in the stored language).
- **Tests (9 new)**: 8 template snapshot tests (exact strings; absent-headsign omission; gap-withheld count; walk-purpose variants; executable step ordering) + endpoint assertions (ordered actions, exact texts, si fallback note). Two real defects were found and fixed during verification: the cache key initially omitted `language` (an si request would have been served the cached en payload), and endpoint tests touching the real Redis client corrupted later tests' event loops (fake cache injected; global engine disposed after TestClient tests, I-13 pattern).
- **Deliberately deferred within Phase 5**: si/ta template authoring + native review (D-7, owner-blocked), and the mobile results/instructions screens (plan items 9–10) as a separate bounded task.

### Phase 5 — mobile screens: results cards + step-by-step instructions (2026-11-22)

- **`lib/api.ts`**: typed plan payloads mirroring the backend contract exactly (`PlanEndpoint`, `PlanOption`/`PlanStep`/legs incl. `intermediate_stops: number | null`) + `planJourney()` (POST `/journeys/plan`, 30 s timeout — planning may route walking legs).
- **`lib/planStore.ts`**: in-memory hand-off of the last plan (Expo Router params must be strings; a full plan is too large for a URL). Losing it on app restart is acceptable — plans are regenerated on demand and can be saved server-side.
- **`app/journey.tsx` rewritten** (was the Phase 0.4 placeholder): two stop pickers (search → explicit user selection, ambiguous results never auto-selected), "Find journeys" → results **cards with explicit trade-offs**: duration band labelled "network estimate", walking distance, transfer count, ranking-label chips, honest confidence phrasing ("Includes route data/transfer path not yet field-checked"), warnings, and a footer with the dataset version + "service frequency is not confirmed". `no_route` renders the backend's own notes in an honest block — the app never invents a journey; planning failures show a connection error.
- **`app/journey-steps.tsx` (new)**: renders the selected option's ordered `steps` **verbatim from the backend's deterministic templates** (never rewritten client-side), with the option summary, warnings, and the honesty footer (dataset version; "network feasible, not live confirmed — waiting times are unknown; board the next bus on the shown route"). Opened without a plan → an explanatory "No plan in progress" state.
- **Wiring**: `journey-steps` registered in `_layout.tsx`; home link renamed "Plan a journey".
- **Tests (7 new → 18/18)**: cards render trade-offs/labels/confidence and hand the plan to the store; `no_route` shows the backend notes and no cards; planning-failure error (only the POST fails — searches keep working); ordered steps rendered verbatim with warnings + honesty footer; no-plan state. One real bug found and fixed during testing (a duplicated leftover stylesheet broke the suite parse).
- **Deliberately deferred**: runtime on-device verification (D-5/D-9 owner spike) and si/ta native review (D-7).

### Phase 6 — backend core: active journey sessions (2026-11-22)

- **Migration `0007_journey_sessions`** (applied to test + dev DBs): `journey_sessions` (journey FK → `saved_journeys` CASCADE, option id, dataset version, origin/destination/preferences for replan, `plan_snapshot` JSONB = the exact option payload, status + `current_step_index`) and append-only `journey_events` (typed, optional step index + note). **No coordinates anywhere** (data model §6: minimise location storage; sessions are anonymous until accounts exist).
- **Pure state machine** (`state_machine.py`, one transition table): execution states are **derived from the current step's action** (WALK_TO_STOP → active_walk; BOARD/RIDE/ALIGHT → active_ride; WALK_TRANSFER → transfer_walk; WALK_TO_DESTINATION → final_walk), with explicit `paused` / `needs_confirmation` / `completed` / `cancelled`. Rules: **terminal states accept nothing**; progress cannot advance while paused (resume first); completion is always an explicit traveller event, never an implicit side effect of stepping past the last instruction. GPS has **no backend pathway** — manual progress is authoritative (plan §Phase 6: GPS assistive, not authoritative).
- **Grounded sessions only**: `POST /journey-sessions` requires `journey_id` + `option_id` of a **saved** plan and snapshots that exact server-generated option — nothing client-crafted is executed. The response is the "Do this now" payload (plan item 2): `current_step` (action + template text), `next_step`, `progress`.
- **Manual progress (plan items 3–4, 8)**: `POST .../events` applies `step_advanced` (arrived/boarded/alighted are step advances), `paused`, `resumed`, `completed`, `cancelled` — invalid transitions are **409 with the rule text**. `GET /journey-sessions/{id}` restores state after background/restart (exit criterion: no unexpected state loss).
- **Replan entry points (plan item 8)**: `POST .../replan` re-plans against the **current active dataset** (cache bypassed), optionally with an `origin` override for missed-stop recovery. On success: progress honestly resets to step 0, `previous_dataset_version` recorded, `replanned` event appended. When nothing connects: `replanned: false` with the no_route reasons and the **session untouched** (dataset version and progress preserved) — never a fabricated replacement. Replanning a completed/cancelled session is 409.
- **Tests (12 new)**: 6 state-machine unit tests (derived states, pause/resume roundtrip, terminal-state rejection, no-advance-while-paused, unknown state) + 6 integration tests over the real endpoints (full manual lifecycle to completion, 409s, restore, grounded-start 404s, replan version change with progress reset, origin override, honest no-replacement, completed-session 409).
- **Deliberately deferred within Phase 6**: mobile "Do this now" screen (follow-up bounded task); GPS proximity suggestions with accuracy/dwell safeguards (plan item 5 — client-side only, and only ever as *suggestions* requiring manual confirmation, `needs_confirmation` state reserved); screen-awake option and voice/read-aloud (plan items 6–7, voice blocked on D-7 native review).

### Phase 6 — mobile: "Do this now" screen, GPS suggestions, session persistence (2026-11-22)

- **Grounded hand-off into guided mode**: `lib/api.ts` gained the session client (`startJourneySession`, `getJourneySession`, `postSessionEvent`, `replanJourneySession` — typed `JourneySessionState`/`SessionStep` payloads) and `planJourney` now **saves the plan server-side**; the steps screen's "Start guided journey" requires a saved plan. Guided mode therefore always executes a server-generated option — nothing client-crafted.
- **Step facts now carry `target_lat`/`target_lon`** (backend `itineraries/instructions.py` template facts, from canonical stop data — coordinates are never invented client-side); unit-test updated; 9/9 template tests pass.
- **`active-journey` screen (plan items 2–6, 8)**: shows the current action verbatim from the backend template + next step + progress; buttons confirm/pause/resume/end/re-plan; re-plan failures surface the backend's honest no-replacement note; dataset-version + not-live + no-location honesty footer; restore after restart from the persisted session; offline fallback shows the last known snapshot with an explicit "could not refresh" note.
- **Local session persistence (`lib/sessionDb.ts`, expo-sqlite)**: stores only `session_id` + the last state snapshot (no location); cleared on completed/cancelled.
- **GPS suggestions (`lib/geoSuggestions.ts` — pure, unit-tested)**: accuracy gate (samples worse than 50 m reset the run), jump rejection (> 200 m resets), 3-sample dwell inside a 40 m radius before a suggestion fires. The screen's GPS toggle is **off by default**; a suggestion only surfaces a card ("confirm above when you are sure") — **GPS never advances a step** (asserted by test: no `/events` call). Stale watchers after re-toggles are guarded (cancelled check) so an old watch can never evaluate samples.
- **Keep-awake is opt-in** (`expo-keep-awake` activate/deactivate tied to the toggle, deactivated on unmount).
- **Tests (12 new)**: 5 screen tests (do-this-now render + manual advance, pause/resume, GPS dwell suggestion + never-auto-advance + weak-signal clears, terminal state, no-session state) + 6 pure-suggestion tests (single-fix rejection, dwell, accuracy reset, jump glitch, outside-radius, distance scale) + 1 steps-screen expectation. **30/30 mobile**; tsc + eslint clean.
- **Notable fixes during the work (see I-25)**: RNTL's `act()` always returns a thenable that must be awaited — a non-awaited `act()` left the act scope open and silently swallowed every later state update (in that test *and* subsequent tests in the file); the GPS watcher setup was restructured into a `useEffect` with a purely synchronous switch handler, and the switch interaction uses `fireEvent(..., 'valueChange', ...)`.

### Phase 7 — offline core: cached plans and offline manual progress (2026-11-22)

Scope: implementation-plan Phase 7 **work items 1–3** (cache + banner + offline progress). Items 4–10 (queued reports, recovery flows, adjustment suggestions, moderation, preferences, account sync) remain open. Mobile-only bounded task; the backend is unchanged and stays the **only authority** for session state.

- **Offline plan cache (`lib/planDb.ts`, expo-sqlite `cached_plan`)**: the last successful plan response (itinerary, ordered steps, dataset version) plus the option the traveller opened. Written on every successful `planJourney` (journey screen) and pointed at the opened option when a card is tapped. The journey-steps screen restores from the cache when the in-memory hand-off is empty (app restart), so a downloaded itinerary remains readable after a process restart. A corrupted cache row returns `null` — the app never fabricates a plan from broken data.
- **"Saved on this device" banner (plan item 2)**: cached views show the cache age ("Saved on this device · 4 min ago") and an explicit capabilities note ("If you are offline, planning, search and live checks are unavailable — the steps below remain followable as written."). The app never presents cached content as fresh and never claims offline state it cannot know (no false "offline" label without a failed request).
- **Offline manual progress (`lib/progressQueue.ts`, `pending_session_events`)**: when a progress event cannot reach the backend (network failure — `ApiStatusError` distinguishes this from a 409), the event is queued in SQLite and its effect is projected locally: the "Do this now" card advances to the next step from the cached plan's steps, with the status derived by a table that mirrors `backend/app/modules/journey_sessions/state_machine.py` exactly. The projection **refuses exactly what the backend refuses** (terminal states, advance while paused, unknown/beyond-last steps, steps unknown locally) and the screen says so honestly instead of inventing progress. No location data is queued — events are the same typed payloads the API accepts.
- **Ordered replay on reconnect**: queued events replay in insertion order (the backend's transition table stays valid). Network failure keeps the remaining events queued for a later retry. A 409 means the server state wins: remaining queued events are dropped (a terminal session makes them invalid by definition), the server's rule text is surfaced, and the server state is adopted. Queued events are flushed **before** any new online action so the backend always receives them in the order the traveller performed them. Projected terminal states keep the local session cached until the backend confirms completion.
- **Stale-data honesty**: after a successful restore, if the session's `dataset_version` differs from the cached plan's, the screen shows an explicit "planned on dataset X; the network now serves Y" note (plan item 2's stale-version warning).
- **Tests (20 new → 50/50 mobile)**: 5 planDb unit tests (round-trip with verbatim steps, option recording, per-journey step lookup, corrupted-row honesty, clear), 10 progressQueue unit tests (queue order/isolation; projection: advance+derive, pause/resume, terminal events, refusal matrix; replay: ordered success, network-failure retention, 409-server-wins, conflict-with-unreachable-refresh, empty queue), 3 journey-steps screen tests (cache restore + banner, honest no-plan for an uncached option, no banner for the live flow), 2 active-journey screen tests (offline queue + local projection + banner; replay after restore with "Synced 1 offline progress change."), plus a cache-write assertion in the journey screen test. tsc + eslint clean.

### Phase 7 — recovery flows and no-route adjustment suggestions (2026-11-22)

Scope: implementation-plan Phase 7 **work items 5–6**. Bounded across backend + mobile; the API contract change is documented in `docs/architecture/11_BACKEND_API_DESIGN.md` (plan response `suggestions` field + recovery phrasing on the replan endpoint).

- **No-route adjustment suggestions (backend, item 6)**: `PlanningResult.suggestions` (deterministic; serialized into the plan payload and cached with it; `ok` responses carry none). Three grounded kinds:
  - `nearby_stop` — for a stop-kind endpoint, the nearest other mapped stops within a fixed 800 m browse radius (max 2, deterministic order); for a coordinate endpoint whose nearest mapped stop lies beyond the walking cap, that stop is named explicitly ("outside the 1500 m walking cap"). Distances are **straight-line and always labelled "as mapped; walking distance not checked"** — a suggestion is never a walk leg.
  - `larger_walk_cap` — when the walk-only fallback was attempted, the suggested cap is derived from the **routed** distance the walking engine actually produced ("the routed walking-only distance is 4219 m"); for beyond-cap coordinate endpoints the cap comes from the mapped straight-line distance with an explicit caveat ("the actual walking distance may be longer — checked only when you re-plan").
  - `allow_mode` — only when rail patterns exist in the dataset and rail is excluded by the mode preference; the verified-station-order rule is restated (a suggestion can never bypass a grounding rule). Allowing rail removes the suggestion; the refusal reason (unverified station order) is then stated on its own.
  - No suggestion claims a service, timetable or fare, and none asserts the alternative *works* — the client re-plans through the same endpoint and the planner answers honestly again.
- **Recovery from a confirmed stop (mobile, item 5)**: "Missed it? Re-plan" in "Do this now" opens a **"Where are you now?" panel**: search + explicit stop confirmation → `replan` with the origin override (Phase 6 backend). This single honest mechanism covers missed-stop, wrong-route and missed-transfer recovery (you alight, confirm where you are, continue from there). **Nothing is auto-detected** — GPS stays assistive-only. The backend's honest no-replacement behaviour is preserved verbatim (the reason is surfaced, the plan is kept); a same-OD re-plan remains available as a panel action; the manual controls stay usable while the panel is open.
- **Suggestion cards (mobile, item 6)**: on `no_route`, the journey screen renders the backend's suggestion texts verbatim under "Try instead (from mapped data — nothing is promised to work)"; nearby-stop and walk-cap suggestions have action buttons that re-plan through the same planner (swapping the suggested stop in, or raising the cap). `allow_mode` stays text-only until preferences plumbing (plan item 9).
- **Tests (7 backend → 128/128; 3 mobile → 53/53)**: nearby-stop suggestions (both ends, deterministic nearest, honest wording), routed walk-cap suggestion, beyond-cap coordinate suggestion + caveated cap, allow_mode gating (present without rail allowed, absent with), ok-carries-none, payload serialization via the API contract test; mobile: suggestion card rendering + re-plan-through-suggestion with the suggested stop as origin, recovery from a confirmed stop (search → confirm → origin override in the replan body → state adopted), honest no-replacement + cancel back to the journey. ruff/format/mypy + tsc/eslint clean.




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
| I-20 | 2026-11-20 | 2.1 | A native Windows PostgreSQL 15 service (auto-start) shares host port 5432 with the Docker DB → loopback connections nondeterministically hit the wrong server; host-side pytest auth failed | Host gates unreliable; would break again at every reboot | Docker `db` republished as **5433:5432**; settings default `DATABASE_URL` → `localhost:5433` (compose in-container override unchanged); `.env`/docs updated | netstat (two 5432 listeners); asyncpg auth error; pytest 60/60 after fix |
| I-21 | 2026-11-20 | 2.1 | **I-18's fix was incomplete**: the session fixture *created* `journey_planner_test`, but Alembic's `env.py` and the cleanup fixture still resolved `get_settings().database_url` = **dev DB** → the Phase-2.1 pytest run wiped the dev pilot (0 stops) | Dev data destroyed; test isolation claim was false | conftest now sets `DATABASE_URL=…journey_planner_test` at **conftest-import time** (before any app/alembic code resolves settings) so migration + cleanup + app-under-test all target the test DB; dev data re-ingested from the pipeline (`osm-overpass-1679d061`, 610/573/37) | pytest 60/60 **and dev stops still 432 after the run** (decisive check) |
| I-22 | 2026-11-20 | 3 | Valhalla Docker image `latest` (3.6.x) crashed during the walking-engine PoC: worker threads threw C++ exceptions (`terminate called recursively`), the service segfaulted (exit 139) on route requests, and the failed engine coincided with the local Docker engine returning API 500s (Docker Desktop restart needed) | PoC blocked; dev stack briefly down | Engine **pinned to `3.5.1`** (compose + build script); config regenerated with the *same* version's `valhalla_build_config` (a 3.6.x-generated config is missing keys 3.5.1 expects, e.g. `service_limits.tile.max_matrix_distance`); PowerShell `>` redirection writes UTF-16 — script writes config bytes directly (UTF-8, cf. I-17) | `valhalla_build_tiles`/`build_extract` exit 0; `/status` 200; 4/4 PoC routes; Docker Desktop restarted; core stack (db/redis/backend) auto-recovered healthy |
| I-23 | 2026-11-20 | 3 | Overpass fully unavailable during the Phase 3 live import (primary URLError after 43 s, kumi mirror timeout after 111 s; three sync attempts failed) — shapes/access points could not be fetched live | New entities missing from dev DB until resolved | `backend/scripts/reparse_latest_snapshot.py`: the **latest archived checksum-verified snapshot** was re-parsed with adapter 0.2.0 into the existing candidate version (`osm-overpass-1679d061`), recorded as its own SyncRun (`parser_version='0.2.0-reparse'`) + validation-summary reparse note; failed live syncs left the previous data serving (plan §5.2 rule 3 held) | `reparse: in=1083 added=473 unchanged=573 failed=37`; 41 shapes / 432 access points present; 101 = 21.1 km reality-check |
| I-24 | 2026-11-22 | 5 | **Recurrence of the I-17 class**: rewriting a source file via PowerShell (`Get-Content -Raw` → `-replace` → `Set-Content -Encoding utf8`) double-encoded its non-ASCII characters (em-dash → `â€”`) — twice in one session, and the initial damage also introduced a BOM. Separately, endpoint tests using the process-global Redis client corrupted later tests' event loops (aioredis pools bind to one loop; `RuntimeError: Event loop is closed` / pre-ping failures, intermittent in the full suite) | Source-file corruption (caught by inspection); full-suite flakiness | Rule adopted: **never rewrite source files with PowerShell text cmdlets — use the editor tool**; corruption repaired via editor and verified byte-wise (no unexpected non-ASCII); endpoint tests inject a fake plan cache instead of the real Redis client and dispose the global engine after TestClient tests (I-13 pattern) | `python` byte-check over all lines: only intended `—`/`→` remain; 109/109 twice consecutively |
| I-25 | 2026-11-22 | 6 | Mobile: three "Do this now" tests failed — (a) an **RNTL `act()` was not awaited**; RNTL's `act()` always wraps the callback in an async function and returns a thenable, so a bare `act(() => …)` leaves the act scope open and silently swallows every later state update in that test **and in the following tests of the file** (GPS suggestion never rendered; terminal/no-session tests cascaded); (b) the GPS toggle's async permission/watch chain ran across act boundaries inside the Switch event; (c) `jest.restoreAllMocks()` strips factory-created `jest.fn` implementations needed by later tests; a dwell test also pushed only 2 of the 3 required samples | 3 failing tests looked like app bugs; cost significant debugging time | `await act(async () => …)` for position callbacks; GPS watcher setup moved into a `useEffect` (switch handler purely synchronous; cancelled-flag guard so a stale watcher can never evaluate samples); `jest.clearAllMocks()` instead of `restoreAllMocks`; sample count fixed; `fireEvent(switch, 'valueChange', …)` kept for Switch (userEvent.press does not drive `onValueChange`) | 30/30 mobile jest pass; tsc + eslint clean; commit `f3b15af` |

---

## 8. Verification log (how to reproduce the current green state)

All commands run from the repository root unless noted. Docker Desktop must be running.

```powershell
# 1. Environment + stack
copy .env.example .env
docker compose --env-file .env -f infra/docker/compose.yaml up -d --build
docker compose --env-file .env -f infra/docker/compose.yaml run --rm backend alembic upgrade head

# 2. Backend gates
docker compose --env-file .env -f infra/docker/compose.yaml run --rm backend `
  sh -c "ruff format --check . && ruff check . && mypy && pytest"
#   → 66 passed, 2 warnings (starlette TestClient deprecations; third-party)
#   Host-side equivalents (after I-20/I-21): ruff format --check . && ruff check .
#   && mypy && pytest  → 66 passed; dev DB (journey_planner, host port 5433)
#   retains 432 stops / 38 routes after the run (I-21 proof).

# 2b. Walking engine (Phase 3, ADR-0008)
python backend/scripts/build_valhalla_tiles.py
#   → config + tiles + tiles.tar (~126 MB) built in ~9 min (needs the pbf in data/osm)
docker compose --env-file .env -f infra/docker/compose.yaml up -d valhalla
curl http://localhost:8002/status                          # → {"version":"3.5.1", ...}
curl "http://localhost:8000/api/v1/walking/route?lon_from=79.8489576&lat_from=6.9343064&lon_to=79.8555889&lat_to=6.893302"
#   → {"status":"ok","distance_m":5418.0,"duration_s":3828.9,"steps":[16 steps]}

# 2c. Shapes + access points + transfer candidates (Phase 3)
python scripts/resync_overpass.py        # live fetch (fails honestly when Overpass is down, I-23)
python scripts/reparse_latest_snapshot.py # fallback: reparse the archived checksum-verified snapshot
python scripts/write_qa_report.py        # regenerate the committed QA report
python scripts/generate_transfer_candidates.py [--dry-run] [--radius-m 300]
#   → proposal-only transfer connectors (unverified) via the walking engine

# 2d. Journey planning (Phase 4)
curl -X POST http://localhost:8000/api/v1/journeys/plan \
  -H 'Content-Type: application/json' \
  -d '{"origin":{"type":"stop","stop_id":"<uuid>"},"destination":{"type":"stop","stop_id":"<uuid>"},"preferences":{"priority":"fastest","max_walking_m":1500,"max_transfers":1}}'
#   → {"status":"ok","dataset_version":"...","options":[...],"cache":"miss|hit"} or {"status":"no_route","notes":[reasons]}
# Add "save": true → response includes journey_id; then:
#   GET  /api/v1/journeys/{journey_id}           → stored snapshot + saved_at_dataset_version
#   POST /api/v1/journeys/{journey_id}/refresh   → re-plan vs active version (refreshed, previous_dataset_version)
python scripts/plan_benchmark.py [--pairs 5] [--iterations 10]   # performance baseline → docs/evidence/

# 2e. Active journey sessions (Phase 6)
# Save a plan first ("save": true on /journeys/plan → journey_id), then:
curl -X POST http://localhost:8000/api/v1/journey-sessions \
  -H 'Content-Type: application/json' \
  -d '{"journey_id":"<uuid>","option_id":"option-1"}'
#   → {"status":"active_ride|active_walk|...","progress":{...},"current_step":{...},"next_step":{...}}
curl -X POST http://localhost:8000/api/v1/journey-sessions/{id}/events \
  -H 'Content-Type: application/json' \
  -d '{"event_type":"step_advanced","step_index":1}'
#   → updated state; invalid transitions → 409 with the rule; paused/completed/cancelled also via events
curl http://localhost:8000/api/v1/journey-sessions/{id}            # restore after restart
curl -X POST http://localhost:8000/api/v1/journey-sessions/{id}/replan \
  -H 'Content-Type: application/json' -d '{"origin":{"type":"stop","stop_id":"<uuid>"}}'
#   → {"replanned":true,...} (progress reset) or {"replanned":false,"status":"no_route","notes":[...]}

# 3. Mobile gates (from apps/mobile/)
cd apps/mobile; npm ci
npm run lint        # → 0 problems
npm run typecheck   # → 0 errors
npm test            # → 50 passed (11 suites; native modules mocked incl. expo-sqlite/expo-location)
npm start           # dev server; 'a'/'i' launches on a simulator (owner tooling)
```

**Live endpoints (local):** `GET /api/v1/health` (liveness) · `GET /api/v1/ready` (readiness) · `/api/v1/docs` (OpenAPI) · `/api/v1/admin/*` (data ops; local/test only).

**Recent live verifications:**
- 2026-11-20: `/ready` 200 (database ok, redis ok) after Phase 1.3 rebuild.
- 2026-11-20: OSM pilot ingest run `d4d4a724` succeeded (230/176/54) — see §6 Phase 1.3.
- 2026-11-20: QA report `backend/data/validation_reports/osm-overpass-d4d4a724.md` generated and committed.
- 2026-11-20: Phase 1.4 live verification — re-ingest `osm-overpass-4e442b17` succeeded (230/176/54, deterministic); coverage scorecard **17 routes, average 23.0/100**; QA queue **35 items**; field-survey exports generated (**100 stops / 22 patterns / 0 transfers**); reports committed under `backend/data/validation_reports/`.
- 2026-11-20: Phase 2 live verification — pilot re-ingested as `osm-overpass-3cf065d7` (230/176/54, after an Overpass outage was survived via mirror fallback); `GET /places/search?q=pettah` → 1 stop; `?q=176&types=route` → 1 route; `GET /stops?bbox=79.84,6.90,79.87,6.94` → **54 stops**; reverse-geocode honestly returns `provider: none`.
- 2026-11-20: Phase 2.1 live verification — WP ingest `osm-overpass-1679d061` (610/573/37, primary 504 → retry OK); `?q=pasyala` → 2 stops (lat 7.169, Gampaha); `?q=negombo` → 2 hits; `GET /stops?bbox=79.95,7.05,80.05,7.20` → 3 stops; QA report `backend/data/validation_reports/osm-overpass-1679d061.md`. I-21 proof: full pytest (60/60) → dev DB still 432 stops / 1 source.
- 2026-11-20: Field-kit refresh — exports regenerated for WP (`data/field-verification/exports/`: 432 stops → 57 tier-A / 375 tier-B; 45 patterns; 0 transfers); XLSForm built (`forms/stop_verification.xlsx`, openpyxl read-back verified: survey 17 rows, choices 12 rows); backend gates 60/60, dev DB intact after run.
- 2026-11-20: Phase 3 work item 1 — Valhalla tiles built from the SL snapshot (~9 min, exit 0; 125.9 MB extract); 4/4 PoC routes between real pilot stops succeeded (Fort→Bambalapitiya 5.42 km/16 maneuvers; warm latency 52–260 ms); `GET /api/v1/walking/route` live through the backend adapter (status ok, 5,418 m, 16 steps); backend gates **66/66**, mypy/ruff/format clean; evidence in `docs/evidence/valhalla-poc-2026-11-20.md` (+ committed sample JSON); ADR-0008 ratified (D-10).
- 2026-11-20: Phase 3 items 2–3 — three live Overpass fetch attempts failed (I-23); **archived snapshot reparse** imported adapter 0.2.0 output into `osm-overpass-1679d061`: **41 route shapes** (101 = 21,098 m, 154 = 18,794 m — reality-checked), **432 stop access points**, 473 added / 573 unchanged / 37 failed (unchanged failure set). `generate_transfer_candidates.py` routed **19 candidate connectors** through the real Valhalla service (51–434 m, avg 234 m, all unverified, none straight-line). QA report regenerated (committed); backend gates **75/75**, mypy/ruff/format clean; dev DB still 432 stops / 1 OSM source + 1 derived source.
- 2026-11-20: Phase 4 core — `POST /api/v1/journeys/plan` live against the real dev network: **Kollupitiya→Colombo Fort** direct on route 101 (0 transfers, 0 walking, 12.5–18.7 min band, confidence `unverified_pattern`) and **Willium Junction→Narahenpita** one-transfer (101 → stored 142 m connector walk → 141, 20.7–30.2 min, confidence `unverified_transfer`); Fort→Kollupitiya correctly returns `no_route` (the OSM relation only captured the Moratuwa→Fort direction — riding backwards is refused, board-before-alight held). Backend gates **92/92** (17 new), ruff/format/mypy clean; dev DB intact (432 stops).
- 2026-11-22: Phase 4 completion — migration `0006_saved_journeys` applied to the dev DB; live smoke: plan cache `miss → hit` on identical requests, `save: true` on a cache hit persists an identical snapshot (`journey_id` returned), `GET /journeys/{id}` returns the snapshot with `saved_at_dataset_version`, `/refresh` re-plans (`refreshed: true`, previous/current version labels), unknown ID → 404; performance baseline measured (`plan_benchmark.py`): **miss p95 3.5 ms / p50 0.2 ms, Redis hit p95 2.0 ms / p50 0.9 ms** → targets in `docs/evidence/plan-benchmark-2026-11-22.md`; backend gates **101/101** (9 new), ruff/format/mypy clean; dev DB intact (432 stops).
- 2026-11-22: Phase 5 backend core — live: Kollupitiya→Colombo Fort renders ordered steps — "Board route 101 at Kollupitiya Junction halt heading towards Colombo Fort." → "Stay on route 101 and alight at Colombo Fort." (intermediate-stop count **honestly withheld**: the OSM relation's sequence has gaps, `facts.intermediate_stops = "not confirmed"`) → "Alight at Colombo Fort."; `language: si` falls back to English with the D-7 native-review note; cache keys include language (en/si never cross-served). Backend gates **109/109** (9 new), ruff/format/mypy clean, run twice consecutively; dev DB intact (432 stops).
- 2026-11-22: Phase 5 mobile — `npm test` **18/18** (7 new), `tsc --noEmit` clean, `expo lint` clean; screens: journey (plan + results cards with trade-offs and honest `no_route`) and journey-steps (verbatim ordered instructions + honesty footer). Device runtime check remains pending the owner's dev-client spike (D-5/D-9).
- 2026-11-22: Phase 6 backend core — migration `0007_journey_sessions` applied to the dev DB; live smoke against the real network: plan saved (3 steps) → session started ("Do this now": "Board route 101 at Kollupitiya Junction halt heading towards Colombo Fort." + next step) → step advance → pause (advance attempt → **409** "event 'step_advanced' is not allowed from 'paused'") → resume → complete → GET restores `completed`. Backend gates **121/121** (12 new), ruff/format/mypy clean; dev DB intact (432 stops; session/event rows from the smoke remain as dev data).
- 2026-11-22: Phase 6 mobile — new `active-journey` "Do this now" screen over the session endpoints (manual confirm/pause/resume/end/re-plan; restore after restart via expo-sqlite persistence — session id + snapshot only, no location; offline snapshot fallback; honesty footer); pure GPS-suggestion module with accuracy (≤ 50 m) / jump (> 200 m) / dwell (3 samples) safeguards — **suggestions only, never auto-advances a step** (asserted: no `/events` call from GPS), off by default; opt-in keep-awake; `planJourney` saves plans so guided mode starts only from server-generated plans. Mobile gates **30/30** (12 new), tsc + eslint clean; debugging found and fixed the RNTL non-awaited-`act()` trap (I-25). Commit `f3b15af`.
- 2026-11-22: Phase 7 offline core — mobile-only bounded task (plan items 1–3): offline plan cache (`lib/planDb.ts`, steps verbatim + dataset version), "Saved on this device" banner with capabilities note on the restored steps screen, offline manual progress (`lib/progressQueue.ts`: SQLite event queue, device-local projection mirroring `state_machine.py`, ordered replay on reconnect, 409 → server state wins with the rule text surfaced, flush-before-post ordering guard, stale-dataset-version note after restore). No backend change; the backend stays the only authority. Mobile gates **50/50** (20 new), tsc + eslint clean. Commit `9b05927`. Airplane-mode device check pending the owner spike.
- 2026-11-22: Phase 7 recovery + suggestions — plan items 5–6: backend `no_route` responses carry grounded `suggestions` (nearby_stop as-mapped; larger_walk_cap from the routed walk-only distance or a caveated mapped estimate; allow_mode only when rail data exists and is excluded, with the verified-station-order rule restated; `ok` carries none; deterministic + cached). Mobile: "Try instead" suggestion cards that re-plan through the same planner, and a "Where are you now?" recovery panel (search + explicit stop confirmation → replan origin override; honest no-replacement preserved; same-OD re-plan in the panel). Backend gates **128/128** (7 new), ruff/format/mypy clean; mobile gates **53/53** (3 new), tsc + eslint clean. API contract documented in `11_BACKEND_API_DESIGN.md`. Commit `d5a68ce`.



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
| D-10 | Walking engine (ADR-0008) | **ADOPTED (2026-11-20): Valhalla 3.5.1 pinned**; GraphHopper PoC skipped per owner ratification; re-evaluation triggers recorded in the ADR |

**Still open within resolved items:**
- D-3 staffing: who performs the field walks (the recommended approach works for a single owner with a smartphone).
- D-3 tooling sub-choice: KoboToolbox free hosting (fast start) vs self-hosted ODK (we have Docker).

**Known technical limitations (recorded, acceptable):**
- Rollback = pointer flip + re-materialisation runbook (no automated data reversal) — ADR-0007.
- QA report gaps (15 patterns without calls / 37 failed records at WP scale) stem from OSM member nodes without names/tags or outside the bbox — a **coverage-data finding**, not a bug; field verification or a supplementary source resolves them.
- `pytest` deprecation warnings originate in starlette's TestClient (third-party).
- npm audit reports moderate transitive advisories in RN tooling; `audit fix --force` deliberately avoided.
- Admin API is unauthenticated by design until Phase 9 (production-gated in code).
- The Docker DB publishes host port **5433** because a native Windows PostgreSQL service occupies 5432 (I-20). If the owner disables that service, the port can return to 5432.
- MapLibre basemap: dev-only MapLibre demo style; production basemap/tiles provider = owner decision (licensing + hosting).

---

## 10. Remaining path to completion (living checklist)

**Phase 1 (finish):**
- [x] Owner decisions D-1/D-2 resolved (2026-11-20); D-3 adopted (three-tier approach)
- [x] Phase 1.4 — coverage scorecard (17 routes, avg 23/100); QA review queue (35 items); ODK form kit + export/import scripts; verification recording API; field kit committed (`data/field-verification/`)
- [x] Dedicated test database for integration tests (I-18, completed properly under I-21)
- [x] Field kit refreshed for the WP scale: tiered walk plan (57 tier-A stops), Kobo-ready XLSForm, owner walk-plan README (2026-11-20)
- [ ] **Owner: create KoboToolbox account, upload `forms/stop_verification.xlsx`, deploy** (~30 min)
- [ ] **Owner field walks** (Day 1: Colombo core 52 tier-A stops; Day 2: remainder; Day 3: ride-along on route 101/154) — then import submissions

**Phase 2 — Place search, local names, map:**
- [x] Place/alias search API (trigram; language-tagged); ambiguous-result handling (listed, never auto-selected)
- [x] Geocoder behind provider adapter (NoGeocoder default — provider choice still open, GAP-013/D-item)
- [x] Mobile search flow (results + disambiguation + manual-coordinate fallback)
- [x] Coverage widened to Western Province (D-8) — 432 stops / 38 routes live
- [x] MapLibre `/map` screen integrated in code (D-9) — stop markers + "View on map"; **runtime verification pending owner dev-client/device spike** (D-5)
- [ ] Destination entrances for curated pilot POIs (Phase 2.2 candidate)

**Phase 3 — Pedestrian routing and transfer graph:**
- [x] Valhalla proof of concept on Sri Lankan OSM pedestrian data → **ADR-0008 ratified** (D-10; GraphHopper comparison deliberately skipped, triggers recorded)
- [x] Walking-router adapter (vendor-agnostic contract, no-path honesty, bounded failure) + `GET /api/v1/walking/route` live-verified
- [x] Route shapes import from OSM ways — 41/45 patterns have geometry (4 truncated relations flagged; shapes stay `unverified`)
- [x] Access/egress/transfer walks as explicit legs — 432 default access points + **19 candidate transfer connectors** routed through the walking engine (`unverified`; proximity proposes, a routed path is the connector, only field walks verify)
- [ ] **Owner field walks** verifying pilot transfer paths and access points (shared with the Phase 1 exit gate) — this is the remaining Phase 3 exit criterion

**Phase 4 — Deterministic multimodal planner:**
- [x] Graph interfaces over route patterns + explicit transfers; direct/multi-leg candidate generation (deterministic, bounded; board-before-alight enforced)
- [x] Constraints (walk cap, transfer cap, modes, verified-transfer rule; rail only with verified station order); Pareto filtering; ranking profiles (labels computed from the returned set)
- [x] `POST /api/v1/journeys/plan` — honest `no_route` reasons, walking-only fallback, walking legs only from routed paths
- [x] Plan cache keyed by normalized request + network version (ADR-0003; Redis adapter degrades to recompute; version change invalidates) — item 13
- [x] Saved journeys: save/get snapshot + `/refresh` re-plan against the active version (migration `0006`; anonymous pending Phase 6 accounts)
- [x] Performance baseline vs representative pilot queries (`docs/evidence/plan-benchmark-2026-11-22.md`, targets set from observed numbers)
- [ ] Fare ranking (needs fare evidence — plan item 11)
- [ ] Curated routing regression suite extended to the full enumerated case list (bus-rail, rail-bus, ambiguous-stop cases — blocked on verified rail data and place resolution)
- [ ] Owner field walks (Phase 3 gate) — connector candidates feed the planner only as `unverified_transfer` until verified

**Phase 5 — Instructions and itinerary experience:**
- [x] Typed itinerary response schema + stable step/action types (`itineraries` module; API-design-doc action codes; per-step structured facts + confidence)
- [x] Deterministic instruction templates for walk-to-stop, board, ride, alight, transfer walk and final walk — facts only; unknown facts rendered as "not confirmed"; transfer steps show the next boarding point
- [x] Route number + direction/headsign shown only when the pattern's destination label exists; route variant carried in facts
- [x] Intermediate-stop count only when the ordered stop sequence is reliable (contiguous sequences; gaps withheld)
- [x] `language` parameter with honest si/ta→English fallback note (D-7); language included in cache keys and saved-journey refresh
- [ ] si/ta template authoring + **native review** (D-7 — owner-blocked)
- [x] Time/distance breakdown, confidence, dataset version and static-service caveat per option (delivered with the Phase 4 planner response)
- [x] Mobile: results cards with trade-offs + map preview path ("View on map" from search; step screens consume backend `steps` verbatim) + step-by-step instructions screen (plan items 9–10)
- [ ] Owner device runtime check of the journey flow (D-5/D-9 spike) and si/ta native review (D-7)
- [ ] Owner field walks (shared exit gate) — verified facts will upgrade instruction details (access-point names, landmarks, entrances)

**Phase 6 — Active journey mode and progress management:**
- [x] Journey state machine (pure, single transition table): execution states derived from step actions; paused / needs_confirmation / completed / cancelled; terminal states final; invalid transitions rejected
- [x] "Do this now" payload: current action + next action + progress, from a **server-saved** plan snapshot (grounded sessions only)
- [x] Progress by step via manual events (arrived/boarded/alighted/advanced, pause, complete, cancel); GET restores state after background/restart
- [x] Replan entry points: same-OD replan against the active dataset + origin override for missed-stop recovery; honest no-replacement behaviour
- [x] Session data minimised: no location history stored (data model §6); anonymous sessions pending accounts
- [x] Mobile "Do this now" screen: start (from saved plan)/pause/resume/complete/end UI over the session endpoints; restore after restart; offline snapshot fallback; honesty footer
- [x] GPS proximity suggestions with accuracy + dwell safeguards (client-side only; **never auto-advances a step**; off by default; `needs_confirmation` state reserved)
- [x] Screen-awake option under user control (opt-in toggle, deactivated on unmount/toggle-off)
- [ ] Voice/read-aloud (P1 — blocked on D-7 native review)
- [ ] Owner device runtime check of the full guided flow (plan → guided journey → manual progress — D-5/D-9 spike)
- [ ] Owner field walks (shared exit gate)

**Phase 7 — Offline support, recovery, reports and user preferences:**
- [x] Cache selected itinerary, instructions and dataset version in SQLite (`lib/planDb.ts`; steps verbatim; corrupted rows never fabricate a plan) — plan item 1
- [x] Cache-age + saved-on-device banner with capabilities note; stale-dataset-version warning after restore — plan item 2 (banner currently on the steps/active screens; a global banner can follow)
- [x] Manual progress while offline: SQLite event queue, device-local projection mirroring the backend state machine, ordered replay on reconnect, 409 → server state wins, flush-before-post ordering guard — plan item 3
- [ ] Optional queued reports with explicit consent and later sync (idempotent retries) — plan item 4
- [x] Missed-stop, wrong-route and missed-transfer recovery from confirmed location (schedule-honest; explicit stop confirmation, never auto-detected) — plan item 5
- [x] No-route adjustment suggestions (nearby stop, larger walk cap, extra mode) without inventing a service — plan item 6 (grounded in mapped data / routed distances; client re-plans through the same honest planner)
- [ ] Report categories (wrong stop, route/variant, direction, transfer path, landmark/name, fare, access attribute, outdated data, other) — plan item 7
- [ ] Moderation/triage queue; approval creates a dataset candidate/version, rejection changes nothing — plan item 8
- [ ] User preferences: language, maximum walk, allowed modes, transfers, text size, voice — plan item 9
- [ ] Saved-journeys local-first/privacy policy statement; account sync optional/deferred — plan item 10
- [ ] Airplane-mode device test after itinerary download (owner device spike)
- [ ] Owner field walks (shared exit gate)

**Standing obligations on every task:** update this report (§1 protocol); run gates; never invent transport facts; ADRs for material architecture changes.

---

## 11. Transport-data honesty statement (current data state)

- The only ingested source is **OpenStreetMap via Overpass** (ODbL), bbox = **Western Province** (`6.60,79.75,7.30,80.25`, D-8) — **candidate version `osm-overpass-1679d061`, not published**.
- Every imported fact carries `verification_status = 'unverified'`. No timetable, live-availability, fare, or accessibility claims exist or may be made.
- Coverage figures (**432 stops / 38 routes / 45 patterns**) describe **imported data within the bbox**, not service reality; OSM does not guarantee operational status or complete sequences.
- Phase 3 additions (all `unverified`): **41 route shapes** from OSM member ways (4 patterns lack geometry — truncated island-wide relations; one shape spans 112 km for that reason and must not be trusted as a service path until checked), **432 default stop access points** located at the mapped stop nodes (the real roadside position is unknown), and **19 candidate transfer connectors** with routed walking paths (never straight-line estimates; never auto-verified).
- Phase 4 planner honesty: journeys are **network-feasible, not live-confirmed** (`availability_scope` says so); in-vehicle times are a labelled conservative band (12–18 km/h over a 1.4× detour-allowed network distance), **not timetable data**; every option carries the pattern's/connector's verification state (`unverified_pattern` / `unverified_transfer`) and the static-service caveat; planner rides only in the captured direction of each pattern (a one-directional OSM relation cannot serve the reverse journey — it returns an explained `no_route`, not a fabricated reverse ride); walking legs are never estimated from straight-line distance. Plan caching (ADR-0003) never changes a result: keys embed the dataset version, Redis loss degrades to recompute, and saved journeys are retrieval-only snapshots with explicit re-plan via `/refresh`.
- Phase 5 instruction honesty: templates emit **only values present in the structured facts** — a missing headsign is never replaced by an invented destination, and intermediate-stop counts appear only when the ordered sequence numbers are contiguous (live example: route 101 Kollupitiya→Fort withholds the count because the OSM relation's member sequence has gaps). si/ta requests currently receive English text with an explicit "native review pending" note — no machine translation is presented as reviewed. No step text contains live-availability, waiting-time or fare language.
- Phase 6 session honesty: active journeys are **manual-first** — the backend has no GPS pathway at all, so no server state can change from a location signal; sessions execute only **server-generated** plan snapshots (nothing client-crafted is executed); completion is an explicit traveller action, never implicit; replanning honestly resets progress only when a replacement plan actually exists and otherwise preserves the session untouched with the reasons; **no location data is stored** on sessions or events, and sessions are anonymous until accounts exist.
- Phase 7 offline honesty (current code): the offline cache stores only the plan response (itinerary, steps, dataset version) and progress **event payloads** — never location data. Cached views are always labelled "Saved on this device" with the cache age, and the offline progress projection is **display-only**: it mirrors the backend's transition rules, refuses exactly what the backend refuses, and is always reconciled against the server on reconnect (ordered replay; on a 409 the server state wins and the remaining events are dropped with the rule text shown). No queued report, moderation change or preference sync exists yet — nothing auto-publishes and nothing affects canonical data from a device.
- Phase 7 recovery/suggestion honesty (current code): no-route **suggestions** are grounded only in mapped stops (straight-line distances always labelled "as mapped; walking distance not checked") or in distances the walking engine actually routed; a suggestion never claims a service, timetable or fare and never promises the alternative works — the traveller re-plans through the same honest planner. **Recovery always requires an explicit stop confirmation** (search + tap); nothing about the traveller's position is auto-detected or stored, and a recovery re-plan that finds nothing returns the backend's reasons and keeps the journey untouched.
- Known data gaps (recorded in the committed QA report `backend/data/validation_reports/osm-overpass-1679d061.md`): patterns with unresolvable stop calls, no agency attributions, no shapes, no transfer connectors, no verified anything — all awaiting field verification (D-3) and/or additional sources. 37 unresolved records include WP-edge members and long-distance relations whose member geometry extends island-wide.

---

*End of report. Next update: Phase 7 reports/moderation/preferences in code, or after the owner device check / field walks.*
