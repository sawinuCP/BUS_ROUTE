# Phase 0 — Task 0.1: Repository and Documentation Audit

**Audit date:** 2026-11-19
**Auditor:** Coding agent (Phase 0.1 — repository and documentation audit)
**Report status:** First issue; no prior audit report existed at this path.

## 0. Scope and limitations

- This is an inspection and reporting task. No source files, documentation, manifests, or infrastructure were modified. The only file created is this report (`docs/audits/phase-0-repository-audit.md`).
- All 32 text files in the repository were read: 10 product documents, 20 files in the final architecture package (18 numbered documents plus `README.md` and `MANIFEST.json`), and 2 root files (`README.md`, `IMPLEMENTATION_PLAN.md`).
- **No application code, tests, migrations, CI configuration, or infrastructure files exist in the repository.** The repository is documentation-only. Consequently, sections describing code, tests, and implementation inventory report the absence of evidence rather than evaluations of code.
- **This directory is not a Git repository.** `git status`, `git log`, and `git branch` all fail with `fatal: not a git repository (or any of the parent directories): .git`. There is no commit history, branch state, or working-tree delta to audit. This is a critical finding (GAP-001).
- No Git state means "repository state at the time of inspection" is captured only by this audit: 32 files as listed in Section 2.2, untracked by any VCS.
- Secrets scan: no environment files, credentials, or secret-bearing files exist anywhere in the tree; there is nothing to redact. No `.env`, `.env.example`, or config file is present.
- No external services, databases, or networks were contacted. No commands with side effects were executed; only version-check commands and file reads.
- Findings distinguish: **confirmed** (directly observed), **inferred** (stated in documentation but not verified), and **unknown** (no evidence either way).

---

## 1. Executive summary

The repository is a **pre-implementation, documentation-only project**: a complete, high-quality written knowledge base for a Sri Lankan multimodal journey planner, with **zero code, zero version control, and zero engineering scaffolding**. This is consistent with the repository's own framing — `IMPLEMENTATION_PLAN.md` (Document ID 11) describes itself as a "Proposed execution baseline — approval required before Phase 0 implementation", and its Section 13 names "Phase 0 / Task 0.1: repository and documentation audit" as the first coding-agent task.

**Key findings:**

1. **The written baseline is coherent and unusually strong.** Two documentation sets exist and are largely aligned: the research-draft product set (`Docs/Product docs/00–09`) and a "final architecture" package (`Docs/sri_lanka_journey_planner_final_architecture/00–17`) that operationalizes the earlier drafts. The agreed technology baseline supplied for this audit (React Native + TypeScript + Expo, FastAPI + Pydantic, SQLAlchemy + Alembic, PostgreSQL + PostGIS, Redis, MapLibre, Valhalla-candidate walking router, deterministic transit graph, modular monolith) matches what the documents prescribe. No document introduces a divergent technology that must be rejected.
2. **The critical blocker is not architectural — it is project hygiene.** There is no Git repository, so nothing is versioned, attributable, or recoverable, and the audit-trail discipline the implementation plan itself demands ("Never claim a test passed unless it was run", final reports must record "Repository commit/branch inspected") cannot function. Initializing version control must happen before any further phase.
3. **The knowledge base is split across three locations** (`Docs/Product docs/`, `Docs/sri_lanka_journey_planner_final_architecture/`, and root `IMPLEMENTATION_PLAN.md`), while `IMPLEMENTATION_PLAN.md` §0.1 states companion documents "should remain together in the repository's `docs/product/` or equivalent". The root `README.md` indexes only the 10 product documents and does not mention the architecture package or the implementation plan at all.
4. **Three different phase-numbering schemes coexist** (implementation plan Phases 0–10; `16_ROADMAP_AND_ACCEPTANCE_GATES.md` Phases 0–6; `08_SCOPE_ROADMAP_AND_RISKS.md` Phases 0–5). They describe the same underlying sequence at different granularity, but they will cause task-assignment ambiguity unless reconciled or explicitly mapped (GAP-003).
5. **A small number of technology decisions are recorded as undecided and need ADRs**: Redis scope (optional vs. baseline component), background-job library (Celery vs. Dramatiq vs. plain worker), mobile navigation (Expo Router vs. React Navigation), E2E tooling (Maestro vs. Detox), and walking router (Valhalla vs. GraphHopper, pending a Sri Lankan pedestrian-coverage prototype). None blocks starting Phase 0.2.
6. **The documented data model is capable of satisfying every transport-data requirement in the audit brief** — route variants as first-class entities (`route_patterns` with `direction_id`), ordered stop sequences (`route_pattern_stops`, unique `(pattern_id, sequence)`), explicit transfer connections with geometry (`transfer_connections`), multilingual aliases (`entity_aliases` with language tags), and provenance/versioning/verification (`data_sources`, `source_snapshots`, `source_records`, `sync_runs`, `dataset_versions`, `active_dataset`, `verification_records`). But this is **design only**; no schema, migration, or model exists.
7. **Environment readiness is good but imperfect:** Docker 29.5.3 + Compose v5.1.4, Node 22.16.0 / npm 9.8.1, Git 2.40.0, PostgreSQL client 15.4 are installed; the default `python` is 3.11.9 while the architecture package specifies Python 3.12+ (a second interpreter, 3.14.2, is available via the `py` launcher); Redis is not installed natively (acceptable — it will run in Docker per plan).

**Readiness classification: READY WITH CONDITIONS.** The knowledge base is sufficient to begin Phase 0 foundation work (ADRs, conventions, skeletons), but version control must be established first, and a short list of documented-but-undecided items must be recorded as ADRs before dependent phases.

---

## 2. Repository overview

### 2.1 Top-level structure (complete; nothing excluded)

```text
c:\MIHA\BUS_ROUTE\
├── Docs\
│   ├── Product docs\                       (10 markdown documents, numbered 00–09)
│   └── sri_lanka_journey_planner_final_architecture\   (18 numbered documents + README.md + MANIFEST.json)
├── IMPLEMENTATION_PLAN.md                  (root; Document ID 11, v1.0, 2026-11-19)
└── README.md                               (root; indexes the 10 product documents)
```

**Confirmed absences** (verified by recursive listing with hidden files): no `.git\`, no `.gitignore`, no `LICENSE`, no backend or mobile directories (`backend/`, `apps/`, `infra/`, `tests/`, `data/`), no Docker or Compose files, no `.github/workflows/`, no environment templates, no dependency manifests or lockfiles, no lowercase `docs/` directory, no `AGENTS.md`, no ADR directory, no scripts. There are no generated directories to exclude (`node_modules`, virtual environments, build output, caches) because nothing has ever been installed or built.

### 2.2 File inventory (all 32 files)

Root:
- `README.md` (29 lines) — indexes the ten `00–09` product documents; states documents are "proposed design, not immutable requirements".
- `IMPLEMENTATION_PLAN.md` (1,015 lines) — Document ID 11; "execution plan and engineering control document"; version 1.0 dated 2026-11-19; status "Proposed execution baseline — approval required before Phase 0 implementation".

`Docs/Product docs/` (research-draft product set; `00` marked "Version: 0.1 — research draft"):
`00_DOCUMENTATION_INDEX_AND_PRODUCT_VISION.md`, `01_TRAVELLER_PROBLEMS.md`, `02_PROBLEM_GAP_ANALYSIS.md`, `03_PRODUCT_FEATURES_AND_EXPERIENCE.md`, `04_SRI_LANKA_SPECIFIC_FEATURES.md`, `05_USER_STORIES_AND_FLOWS.md`, `06_TECHNICAL_ARCHITECTURE.md`, `07_DATA_SOURCES_AND_ACQUISITION.md`, `08_SCOPE_ROADMAP_AND_RISKS.md`, `09_RESEARCH_REFERENCES_AND_VALIDATION.md`.

`Docs/sri_lanka_journey_planner_final_architecture/` (v1.0 package, "Proposed baseline for review before implementation", prepared 2026-11-19; contents declared in `MANIFEST.json`):
`00_EXECUTIVE_SUMMARY_AND_DECISIONS.md`, `01_PRODUCT_VISION_AND_USERS.md`, `02_TRAVELLER_PROBLEMS_AND_GAPS.md`, `03_FEATURES_AND_SCOPE.md`, `04_USER_STORIES.md`, `05_USER_FLOWS_AND_UI_UX.md`, `06_SYSTEM_ARCHITECTURE.md`, `07_TECH_STACK.md`, `08_DATA_MODEL.md`, `09_DATA_INGESTION_AND_REFRESH.md`, `10_ROUTING_ENGINE.md`, `11_BACKEND_API_DESIGN.md`, `12_AI_AND_LANGUAGE_DESIGN.md`, `13_MOBILE_APP_DESIGN.md`, `14_SECURITY_PRIVACY_ACCESSIBILITY.md`, `15_TESTING_DEPLOYMENT_OPERATIONS.md`, `16_ROADMAP_AND_ACCEPTANCE_GATES.md`, `17_OPEN_QUESTIONS_PRE_IMPLEMENTATION.md`, plus `README.md` and `MANIFEST.json`.

### 2.3 Project-type assessment

**Conclusion (confirmed):** This is a **new project at the pre-implementation stage** — pure written specification. Evidence: zero code, manifests, or tooling anywhere in the tree; `IMPLEMENTATION_PLAN.md` status requires approval before implementation; the final-architecture README states it is "a technical/product design, not a claim that Sri Lanka has a complete public transport API". The absence of any Git history means it is impossible that code was deleted within this directory; there is **no evidence of abandoned work**. It is not an existing prototype, an actively developed application, or a mixture of experimental and production code.

---

## 3. Documentation inventory and review

All 11 documents named in the audit brief were located. None is missing. `11_IMPLEMENTATION_PLAN.md` exists as root-level `IMPLEMENTATION_PLAN.md` (the file self-identifies as "Document ID: 11"); documents `00–09` are in `Docs/Product docs/`. There is intentionally no `10_*` document — the numbering jumps from 09 to the implementation plan (ID 11). One additional documentation set (the final architecture package) exists beyond the named list and is included in this review.

### 3.1 `IMPLEMENTATION_PLAN.md` (root — Document ID 11)

- **Purpose:** Execution plan and engineering control document; defines Phases 0–10, engineering standards, repository layout, data governance, routing/instruction contracts, coding-agent protocol, and open questions.
- **Key requirements/decisions to preserve:** document precedence order (§0.2: ADR-recorded owner decision > approved technical architecture > this plan > product/user-story docs > earlier research drafts); MVP feature list P0 (§2.2, 14 items) and deferred list (§2.3, 9 items); "all possible routes" = all practical non-dominated alternatives within configured limits (§2.4); stack table (§3.1); backend module boundaries (`places`, `transport`, `pedestrian`, `transfers`, `routing`, `itineraries`, `journey_sessions`, `data_ingestion`, `data_quality`, `reports`, `ai_assistance`, `platform`) with the rule "Domain code must not depend on FastAPI, SQLAlchemy, Redis, a map vendor or an LLM SDK" (§3.3); code-quality rules (§4.2 — WGS84 lon/lat order at API boundaries, metres/seconds internally, `Asia/Colombo` timezone, stable internal IDs never route number/stop name as key); ingestion lifecycle rules (§5.2 — idempotent adapters, never overwrite live dataset in place, rollback restores prior version); Phase 0–10 work items with tests and exit criteria; feature-to-test traceability matrix (§8); release gates A–F (§11); coding-agent master instruction (§12.2).
- **Dependencies:** declares the ten `00–09` documents as required companions; references story IDs from `05_USER_STORIES_AND_FLOWS.md`.
- **Issues:** none found internally; it is internally consistent and dated today. Its suggested repository layout (`docs/product/`, `docs/adr/`) does not match the actual current layout (GAP-002).

### 3.2 `Docs/Product docs/` set (research drafts, v0.1)

| Document | Purpose | Notable content / constraints to preserve | Issues |
|---|---|---|---|
| `00_DOCUMENTATION_INDEX_AND_PRODUCT_VISION.md` | Vision, positioning, goals, non-goals, users, principles, success measures | "A route suggestion is not a successful journey plan unless the traveller can understand and carry out every leg"; non-goals exclude live tracking, ticketing, invented facts, exhaustive enumeration | None material; evidence correctly qualified as partly illustrative |
| `01_TRAVELLER_PROBLEMS.md` | 16 problem themes (P1–P16) with evidence status | Every theme marked "research-backed themes + hypotheses to validate"; examples declared illustrative, not interviews | Self-limits evidence correctly; validation interviews outstanding (stated) |
| `02_PROBLEM_GAP_ANALYSIS.md` | 20 gaps (G01–G20) with proposed solutions and priorities | P0 gaps: unified itinerary, stop clarity, variants, transfer connectors, first/last mile, static-service caveat, uncertainty, alternatives, provenance, instruction-first UX, multilingual search | None material |
| `03_PRODUCT_FEATURES_AND_EXPERIENCE.md` | Feature inventory A–N (P0/P1/P2); result-card and active-trip screen designs | "Avoid forcing login for core planning"; active step derived from itinerary state and confirmed user/GPS signals | None material |
| `04_SRI_LANKA_SPECIFIC_FEATURES.md` | Local grounding: multilingual identity, variants, stop/stand/side context, landmarks, transfers, tourist support, fares, mode scope, validation strategy | Names competitors (Beep, LMT-GO) with caution that differentiation "cannot honestly be 'we have journey planning'" | None material; competitor claims correctly flagged unverified |
| `05_USER_STORIES_AND_FLOWS.md` | 35 user stories (US-01–US-35) + 14 flows (A–N) | Every flow must have normal/no-data/low-confidence/permission-denied/network-failure/recovery paths | Story IDs referenced by implementation plan §10 — must be preserved |
| `06_TECHNICAL_ARCHITECTURE.md` | Suggested architecture and domain model | Stack marked "evaluate, not final"; client listed as "Flutter or React Native"; routing options include OTP, GraphHopper, Valhalla, custom | **Superseded by the final architecture package** but carries no supersession marker; read alone it conflicts with the agreed baseline (GAP-004, P2) |
| `07_DATA_SOURCES_AND_ACQUISITION.md` | Minimum data needs; source inventory (OSM, NSDI, NTC, GTFS, Sri Lanka Railways, third-party sites) with URLs; canonical table list; confidence model; QA checklist; rights rules | "Public accessibility does not equal permission to redistribute"; confidence levels Verified/High/Medium/Low/Unverified; fact-level confidence | URLs are recorded candidates — availability/licence remain unknown (doc states this itself) |
| `08_SCOPE_ROADMAP_AND_RISKS.md` | Scope boundaries, 6-phase roadmap, pilot selection criteria, 14 risks (R1–R14), 11 product decisions, open decisions, MVP-done definition | Risk register and "Definition of MVP done" checklist valuable to preserve verbatim | Phase numbering differs from the implementation plan (GAP-003) |
| `09_RESEARCH_REFERENCES_AND_VALIDATION.md` | Source register (CoMTrans, UoM studies, IPS, R4TLI), competitor benchmark protocol, evaluation metrics, research gaps | States quantitative coverage counts "have **not yet been measured**" | None material |

**Preservation verdict:** the `Docs/Product docs/` set remains valuable as problem/evidence/research grounding and the user-story source of truth. It should not be rewritten, but superseded technical content in `06` needs a supersession note (GAP-004).

### 3.3 `Docs/sri_lanka_journey_planner_final_architecture/` set (v1.0, 2026-11-19)

This is the operationalization of the research drafts. All 18 numbered documents plus README and `MANIFEST.json` were read in full.

| Document | Purpose | Key decisions / content |
|---|---|---|
| `00_EXECUTIVE_SUMMARY_AND_DECISIONS.md` | Product definition + baseline decision table | Decision table matches the agreed baseline; "RAG: Not required for core journey planning"; "Redis when measured need exists"; "Initial live data: No assumption of live vehicle positions"; 8 critical product rules (never invent facts; proximity match ≠ valid transfer; variants separate; guest planning allowed) |
| `01_PRODUCT_VISION_AND_USERS.md` | Vision, 7 user groups, principles, success measures | Principles include "Evidence over confidence theatre", "Human confirmation: GPS assists; it does not automatically prove boarding or alighting" |
| `02_TRAVELLER_PROBLEMS_AND_GAPS.md` | 18 problem/gap rows (P01–P18) | Reframes the research-draft problem set into response-oriented table; adds "Service availability may be unknown" (P18) |
| `03_FEATURES_AND_SCOPE.md` | Feature catalogue F01–F38 with priorities | Explicit "out of first release" list (8 items) including AI-generated route/fare facts |
| `04_USER_STORIES.md` | US-001–US-039 with Given/When/Then acceptance criteria | More testable than the research-draft stories; includes admin stories US-034–US-036 and account/data-deletion story US-039. **Note:** story IDs here (US-001…) differ from `Docs/Product docs/05` (US-01…); the implementation plan §10 maps phases to the *older* ID set — reconciliation needed (GAP-005) |
| `05_USER_FLOWS_AND_UI_UX.md` | Flows A–E + UI structure + UX rules | Flow E is the full 12-step source-refresh pipeline with rollback |
| `06_SYSTEM_ARCHITECTURE.md` | Modular monolith; backend modules; request path; refresh path; adapter rule | "Every external dependency must be behind an adapter interface"; Redis shown as "(optional cache/queue)" |
| `07_TECH_STACK.md` | Concrete stack with rationale | Expo Router; TanStack Query + Zustand; React Hook Form + Zod; i18next; Jest + RNTL; Maestro; Python 3.12+; SQLAlchemy 2.x; Shapely/GeoAlchemy; Ruff + mypy/pyright; OpenTelemetry; "Celery or Dramatiq — select one"; rules: pin versions, no Kubernetes/Kafka/vector DB/microservices in MVP |
| `08_DATA_MODEL.md` | Logical PostGIS schema | See Section 7 of this audit — the core data-model evidence |
| `09_DATA_INGESTION_AND_REFRESH.md` | 15-step refresh pipeline; source registry fields; per-source freshness policy; validation examples; versioning/rollback; outage handling | "Never assume an open website means unrestricted commercial reuse"; published versions immutable; journey session retains plan snapshot |
| `10_ROUTING_ENGINE.md` | Graph model, algorithms, costs, instructions, confidence/suppression, walking-engine evaluation | Dijkstra baseline, A* later, multi-criteria label-setting, Pareto dominance; step types `WALK_TO_STOP`, `BOARD_TRANSIT`, `RIDE_TRANSIT`, `ALIGHT_TRANSIT`, `WALK_TRANSFER`, `WALK_TO_DESTINATION`; "Transit edge is tied to a specific route pattern and direction. Do not connect every geographically close stop." |
| `11_BACKEND_API_DESIGN.md` | `/api/v1` endpoint catalogue; plan request/response examples; API rules | Stable internal IDs; request ID + dataset version + warnings; separate network feasibility from live availability; consistent error shape; idempotency keys; rate limits |
| `12_AI_AND_LANGUAGE_DESIGN.md` | Grounded AI design; tool boundary; hallucination controls; RAG decision; language handling | "RAG is not needed for route computation"; PostgreSQL full-text + trigram before any embeddings; narrow tool list; no arbitrary SQL access to LLM |
| `13_MOBILE_APP_DESIGN.md` | Screens, state management, offline model, location, active-journey state machine, accessibility | State machine `PLANNED → STARTED → WALKING_TO_STOP → … → COMPLETED` + `PAUSED/DEVIATED/REPLANNING/MANUAL_ASSISTANCE`; "Do not duplicate the full transport network on the phone in the first release" |
| `14_SECURITY_PRIVACY_ACCESSIBILITY.md` | Security/privacy/accessibility requirements | OAuth2/OIDC + RBAC for admin; guest planning without account; retention periods; Sri Lankan data-protection review with counsel |
| `15_TESTING_DEPLOYMENT_OPERATIONS.md` | Test strategy; environments; 8 CI/CD gates; observability; backup; 9 runbooks | Environments: local (Docker Compose + seeded synthetic data), CI (ephemeral DB), staging, production |
| `16_ROADMAP_AND_ACCEPTANCE_GATES.md` | Phases 0–6 with deliverables and exit gates | Phase numbering and content differ from the implementation plan (GAP-003) |
| `17_OPEN_QUESTIONS_PRE_IMPLEMENTATION.md` | 25 open questions in 5 groups + suggested defaults + approval checklist | Suggested defaults: small Colombo-area corridor pilot; Android+iOS React Native; guest planning; fares omitted unless verified; AI after deterministic planner |

### 3.4 Cross-document consistency analysis

**Consistent across both sets (confirmed by direct comparison):**
- Product promise, non-goals, and privacy-first/no-account principles are identical in substance across `Docs/Product docs/00` and the final package `00/01/03`.
- The "route number is not enough" principle (variants, direction, headsign) appears in all problem/feature/data-model documents without contradiction.
- Static-network MVP framing (no timetable/live claims; network feasibility ≠ live availability) is uniform.
- AI boundary (explain/translate only; never route authority; deterministic fallback; RAG not required) is stated consistently in `06_TECHNICAL_ARCHITECTURE.md` §12, final `00` §3, and final `12`.
- Data-rights stance (public availability ≠ redistribution permission; per-source licence tracking) is uniform in `07_DATA_SOURCES_AND_ACQUISITION.md` §7, final `00` §8, and final `09` §3.
- The final package's decision table matches the agreed technical baseline supplied for this audit on every layer: mobile (React Native + TS + Expo), backend (FastAPI + Pydantic + SQLAlchemy), DB (PostgreSQL + PostGIS), maps (MapLibre), SQLite offline, deterministic transit graph, modular monolith, admin console as a separate protected web client.

**Tensions and discrepancies found (none fatal; all resolvable by ADR or an editorial note):**

| # | Tension | Documents involved | Assessment |
|---|---|---|---|
| C1 | **Redis status**: audit brief and `IMPLEMENTATION_PLAN.md` §3.1 list Redis as a baseline stack component; final `00` says "Redis when measured need exists" and final `06` shows Redis as "(optional cache/queue)" | IMPLEMENTATION_PLAN vs. final 00/06 | Substantive scope divergence. Recommendation: ADR should define Redis's MVP role (rate limiting + route/search cache only; never source of truth — consistent in all docs) and whether it is provisioned at Phase 0.3 |
| C2 | **Background-job library**: "choose a maintained library in ADR" (IMPLEMENTATION_PLAN §3.1) vs. "Celery or Dramatiq — select one" (final `07`) | Same decision, undecided | Needs ADR before the backend skeleton (Phase 0.3); not blocking 0.2 |
| C3 | **Mobile navigation**: "React Navigation or Expo Router (choose one and record ADR)" (IMPLEMENTATION_PLAN §3.1) vs. "Expo Router" decided in final `07` | Minor conflict; final package more specific | Recommend confirming Expo Router in ADR-001 unless the product owner prefers React Navigation |
| C4 | **E2E tooling**: "Maestro or Detox (select one)" (IMPLEMENTATION_PLAN §3.1) vs. "Maestro" decided (final `07`) | Same pattern as C3 | Confirm Maestro in ADR-001 |
| C5 | **Walking router**: final `00` "Evaluate Valhalla first; compare GraphHopper"; final `10` §9 and IMPLEMENTATION_PLAN §1.3 require a prototype comparison on Sri Lankan OSM data before adoption | Internally consistent; decision open | Keep open, gated on the Phase 1/2 proof of concept (as docs prescribe) |
| C6 | **Phase numbering**: three schemes — IMPLEMENTATION_PLAN Phases 0–10 (engineering-sequenced); final `16` Phases 0–6 (compressed); `08_SCOPE_ROADMAP_AND_RISKS.md` Phases 0–5 (discovery-sequenced). E.g., "Phase 1" = canonical data foundation (plan), "platform foundation" (final `16`), "data foundation" (`08`) | IMPLEMENTATION_PLAN vs. final 16 vs. 08 | Same underlying sequence, different granularity; but task prompts will carry a "Phase/task ID" — ambiguity will cause wrong-scope work (GAP-003) |
| C7 | **User-story ID collision**: `Docs/Product docs/05` uses US-01–US-35; final `04_USER_STORIES.md` uses US-001–US-039 with different grouping/content | IMPLEMENTATION_PLAN §10 references the old IDs | Must declare one authoritative story register (GAP-005) |
| C8 | **Client framework in the older draft**: `Docs/Product docs/06` §2 offers "Flutter or React Native", stack "evaluate, not final" | Older draft vs. everything else | Historical draft; needs a supersession note, not a rewrite (GAP-004) |
| C9 | **Data strategy phrasing**: final `00` "API-first hybrid: live/request APIs where suitable, canonical local data for relationships" vs. IMPLEMENTATION_PLAN §5 / final `09` canonical-versioned ingestion-first | Final 00 vs. 09 | Resolved by final `09` §1 (relationship joins are not guaranteed by any single stable API). Note precedence; no further action |

**Verification of brief-specific consistency checks:**
- Product vision vs. MVP scope: aligned (MVP = static network + instructions; live/timetable/ticketing deferred everywhere).
- User stories vs. product features: aligned (every P0 feature in final `03` maps to stories in final `04`; the P0 backend sync pipeline F26 is covered by admin stories US-034–036).
- Technical architecture vs. implementation roadmap: aligned in content; phase-numbering mismatch only (C6).
- Data-source assumptions vs. actual data availability: documents consistently refuse to assert availability; final `17` §C and `09_RESEARCH_REFERENCES_AND_VALIDATION.md` §9 explicitly leave coverage counts and rights as unmeasured. **Confirmed unknown — no dataset, API key, feed sample, or rights document exists in the repository.**
- Sri Lankan transport requirements vs. proposed data structures: supported — see Section 7.
- Security/privacy/licensing/operational requirements vs. implementation plans: security/privacy requirements (final `14`) map to plan Phase 9 review gates and the CI gates in final `15` §3; licensing is embedded in the ingestion pipeline (registry + rights check before import). One gap: no document assigns a named owner for moderation/field verification (flagged in final `17` and IMPLEMENTATION_PLAN §14.5/§14.8) — consistent, but unresolved.

---

## 4. Current implementation inventory

**Confirmed: there is no implementation.** Every capability category listed in the audit brief classifies as **Not implemented**:

| Capability | Classification | Evidence |
|---|---|---|
| Backend entry points / app configuration | Not implemented | No Python files exist anywhere in the tree |
| API routers / endpoints | Not implemented | No code; endpoint catalogue exists only as design (`final 11`) |
| Database models / relationships | Not implemented | No models; logical schema exists only as design (`final 08`, `07_DATA_SOURCES` §4) |
| Migrations | Not implemented | No Alembic directory or migration files |
| Authentication / authorization | Not implemented | Design-only (OAuth2/OIDC, RBAC — final `14`) |
| Service / repository layers | Not implemented | Module boundaries are design-only (IMPLEMENTATION_PLAN §3.3, final `06` §3) |
| Routing / graph algorithms | Not implemented | Algorithm choices are design-only (final `10`) |
| Transport data structures | Not implemented | No data files of any kind in the tree |
| Place search / geocoding integrations | Not implemented | Design-only (provider abstraction, final `07_TECH_STACK` §"Routing and maps") |
| Map integration | Not implemented | Design-only (MapLibre React Native) |
| Mobile navigation / screens | Not implemented | No React Native project |
| API client / state management | Not implemented | Design-only (TanStack Query + Zustand) |
| Offline capabilities | Not implemented | Design-only (SQLite caching model, final `13`) |
| Error handling / logging | Not implemented | Design-only (structured JSON logging) |
| Background jobs / scheduled tasks | Not implemented | Design-only (worker/scheduler, final `06` §5) |
| External API integrations | Not implemented | No HTTP clients, keys, or adapters exist |

"Cannot determine" applies to nothing — absence is complete and directly observable. No code-quality findings are possible; Section 3's documentation review stands in for the architectural review at this stage.

---

## 5. Technology stack assessment

**Confirmed:** the repository imposes **no** existing technology — there are no manifests, lockfiles, or source files to conflict with the agreed baseline. Nothing needs to be "changed"; everything in the baseline will be a green-field introduction, which removes the usual migration-risk category entirely.

Alignment of the agreed baseline against the documentation (all confirmed by reading):

| Layer | Agreed baseline | Documentation position | Match |
|---|---|---|---|
| Mobile | React Native + TypeScript + Expo | Final `00` §3, `07_TECH_STACK` §"Mobile application" (Expo development builds, Expo Router, Expo Location, SecureStore, i18next) | ✅ (nav library undecided — C3) |
| Backend API | Python + FastAPI | Final `00` §3, `07` §Backend | ✅ |
| Validation | Pydantic | Same | ✅ |
| ORM | SQLAlchemy | "SQLAlchemy 2.x" (final `07`) | ✅ |
| Migrations | Alembic | Same | ✅ |
| Database | PostgreSQL + PostGIS | Same (final `08` §"Use PostgreSQL + PostGIS") | ✅ |
| Caching | Redis | Final `00`: "Redis when measured need exists"; final `06`: "(optional)" | ⚠️ scope divergence (C1) |
| Maps | MapLibre | "MapLibre React Native; provider/tiles selected after licensing and compatibility review" | ✅ (tile provider open) |
| Walking routing | Valhalla (subject to validation) | "Evaluate Valhalla first; compare GraphHopper" + prototype requirement | ✅ (open decision by design) |
| Journey planning | Custom deterministic multimodal graph | Final `10`; "Do not connect every geographically close stop" | ✅ |
| API communication | REST + OpenAPI | FastAPI-generated OpenAPI, `/api/v1` (final `11`) | ✅ |
| Offline storage | SQLite | "SQLite for selected journeys and offline instructions" | ✅ |
| Architecture | Modular monolith | Final `06` §1; IMPLEMENTATION_PLAN §3 | ✅ |
| Vector DB / RAG | Not to be introduced | Final `00`: "RAG: Not required for core journey planning"; final `12` §5: full-text + trigram first | ✅ explicitly ruled out in writing |

Additional stack elements documented beyond the brief (to be respected during implementation, all from final `07`/`15`): Shapely/GeoAlchemy for geometry, httpx for async HTTP, Ruff + mypy/pyright, pytest, Jest + React Native Testing Library, OpenTelemetry, structured JSON logging, object storage for raw source archives, and the prohibitions: no Kubernetes, Kafka, vector databases, or microservices in the MVP; do not rely on public community tile servers for production traffic.

---

## 6. Architecture assessment

**Confirmed:** architecture exists as a complete written specification and nowhere else. The prescribed architecture is adequate for the product requirements:

- **Modular monolith with clean boundaries:** IMPLEMENTATION_PLAN §3.3 defines 12 backend modules with an explicit dependency direction (API → application use cases → domain; domain code must not depend on framework/infra libraries). Final `06` §3 lists the same boundaries with slightly different module names (`transport_network` vs `transport`, `journeys` vs `journey_sessions`+`itineraries`). The two module lists must be reconciled into one canonical module map when the backend skeleton is created (minor; fold into GAP-003 resolution).
- **Adapter discipline:** "Every external dependency must be behind an adapter interface" (final `06` §6) — geocoding, walking router, tiles, transport sources. This directly supports the open provider decisions (map tiles, geocoder, Valhalla) without blocking development.
- **Versioned data publication path:** the request path never touches ingestion; publishing is atomic with rollback (final `06` §5–§7, final `09` §7). This is the correct shape for the "must not invent / must be auditable" requirement.
- **Scaling path** is defined and modest (single API + worker + managed Postgres first; extraction only on measured need) — consistent with MVP discipline.
- **Gaps in the written architecture:** none structural. Two operational aspects are named but unassigned: admin/ops ownership (publishing authority) and background-job library (C2). Both are recorded as open decisions in final `17` and IMPLEMENTATION_PLAN §14.

---

## 7. Database and transport-data readiness

**Status: design-ready; zero implementation.** The authoritative logical schema is `Docs/sri_lanka_journey_planner_final_architecture/08_DATA_MODEL.md`, reinforced by IMPLEMENTATION_PLAN §5.1 and `07_DATA_SOURCES_AND_ACQUISITION.md` §4. Evaluating the eight specific readiness questions from the audit brief against that documented schema:

| # | Requirement | Documented support | Verdict |
|---|---|---|---|
| 1 | Two variants of the same bus route representable separately | `route_patterns` is a separate table keyed to `transport_routes` with `pattern_code`, `direction_id`, `origin_label`, `destination_label`, `variant_description`, `shape_id`, `verification_status`, `valid_from/valid_to`. "Represents a specific ordered route variant and direction." | ✅ Supported by design |
| 2 | Route direction and ordered stops correct | `route_pattern_stops` with `pattern_id`, `stop_id`, `sequence`, `boarding_allowed`, `alighting_allowed`, `source_record_id`, **unique constraint `(pattern_id, sequence)`**; direction carried by `route_patterns.direction_id` | ✅ Supported by design |
| 3 | Transfer as a real, explicit walking connection | `transfer_connections` with `from_access_point_id`, `to_access_point_id`, `walk_distance_m`, `walk_geometry`, `estimated_walk_seconds`, accessibility attributes, verification status, validity dates. Explicit rule: "Do not auto-create a transfer solely because two stops are close." | ✅ Supported by design (transfer granularity is access-point level, which is stronger than stop level) |
| 4 | Sinhala/Tamil/English names or aliases on a stop | `entity_aliases` (entity type/id, language, alias text, transliteration, source, confidence); final `12` §6: language tags `en`/`si`/`ta`, canonical name stored separately from aliases, transliteration kept as search alias | ✅ Supported by design |
| 5 | Source and verification history retained | `data_sources` (licence, terms, adapter, enabled), `source_snapshots` (checksum, fetch time, storage URI), `source_records` (external ID → snapshot mapping), `verification_records` (reviewer, method, evidence, date, status), `data_change_audit` (before/after, actor, reason, release) | ✅ Supported by design |
| 6 | Versions of the transport network managed safely | `dataset_versions` (candidate/published/rejected + validation summary), `dataset_version_entities`, `active_dataset` singleton pointer; final `09` §7: published versions immutable, atomic pointer switch, audited rollback, sessions retain plan snapshot. IMPLEMENTATION_PLAN §5.2: "Never overwrite the live dataset in place" | ✅ Supported by design; one implementation fork to decide: immutable versioned tables vs. snapshot/blue-green — final `08` §4 says "Do not mix ad hoc in-place edits with version pointers" but leaves the choice open (candidate for a Phase 1 ADR) |
| 7 | Incomplete/uncertain info without pretending verified | `verification_status` columns throughout; fact-level confidence doctrine ("A route can have verified stop coordinates but unverified operating pattern" — `07_DATA_SOURCES` §5; five confidence levels); nullable fields with reason in API contract (IMPLEMENTATION_PLAN §6.5: "Unknown information must be represented as unknown/null with a reason") | ✅ Supported by design |
| 8 | Journey reconstructible with enough detail for instructions | Ordered `route_pattern_stops` + `stop_access_points` (side/platform/bay) + `transfer_connections` geometry + `place_access_points` (destination entrances) + `route_shapes` + instruction step types (final `10` §7) | ✅ Supported by design |

**Requirements from the audit brief with no explicit home in the documented schema (small gaps to close during Phase 1 schema design):**
- `fare_records`/`fare_rules` exist as optional entities (`final 08` §5, IMPLEMENTATION_PLAN §5.1) but no applicability-validation model yet; docs correctly defer this.
- Agencies/operators exist (`transport_agencies`); route ownership by agency is represented.
- Platforms/boarding points exist via `stop_access_points.access_type` + `side_or_platform` — the design deliberately models access points finer than stops.
- **Pedestrian network representation is left as an interface decision:** IMPLEMENTATION_PLAN §5.1 offers "`pedestrian_nodes`, `pedestrian_edges` or a Valhalla graph reference/version" — an explicit either/or that must be settled (it determines whether transfer/access walking is computed live by Valhalla or served from stored geometry, and how provenance is recorded for computed paths). Candidate for a Phase 1 ADR.
- **Licensing:** source availability and licence status are **unknown** (no evidence in the repository). The documents only assert candidates and the need for rights checks. This audit records no dataset as available.

---

## 8. Routing-engine readiness

**Status: design-ready; zero implementation.** Final `10_ROUTING_ENGINE.md` plus IMPLEMENTATION_PLAN §6 fully specify the intended workflow. Evaluating the brief's routing-readiness questions:

| Question | Documented answer | Assessment |
|---|---|---|
| Can the architecture support the 10-step workflow (resolve → access points → candidate stops → variants → candidates → transfer walks → evaluate → prune → rank → instructions)? | Yes, by design: request path (final `06` §4), candidate generation (IMPLEMENTATION_PLAN §6.2), algorithms (final `10` §3), instruction step types (final `10` §7) | ✅ The specified pipeline matches the brief's workflow almost step-for-step |
| Transport and pedestrian networks separated appropriately? | Yes: transit edges tied to specific route pattern + direction; walk edges on pedestrian graph; explicit transfer edges; "Do not connect every geographically close stop" | ✅ |
| Can routing distinguish directions and variants? | Yes: transit edge carries pattern ID and ordered sequence span (final `10` §2); board/alight validated against the exact variant (IMPLEMENTATION_PLAN §6.2 step 4); regression rule "No route may board after its alighting stop in sequence" | ✅ |
| Can transfer constraints be enforced? | Yes: "No transfer may exist without an explicit valid connector" (IMPLEMENTATION_PLAN regression suite); connector-based multi-leg generation; configurable transfer cap | ✅ |
| Can route generation operate without an LLM? | Yes: "Use a deterministic, explainable routing engine. AI does not decide which route exists." (final `10` §1); AI is a downstream explainer with a deterministic fallback (final `12`) | ✅ |
| Can explanations be generated from structured itinerary data? | Yes: deterministic template examples with unknown-fact honesty rules (IMPLEMENTATION_PLAN §6.6); step types with structured facts (final `10` §7) | ✅ |
| Can route regression testing be supported? | Yes: curated OD-pair regression suite with expected variants and board/alight sequences (IMPLEMENTATION_PLAN Phase 4); dataset-version change produces a new plan/cache key (IMPLEMENTATION_PLAN §6.5) | ✅ by design |
| Alternatives quality | Pareto dominance removal; "Do not return four options that are the same route with trivial stop differences" (final `10` §6); ranking labels computed from the returned candidate set (IMPLEMENTATION_PLAN §6.3) | ✅ |
| Confidence/suppression | Rule-based exclusion/downgrade rules enumerated (final `10` §8); "Confidence should be rule-based and explainable, not a made-up LLM score" | ✅ |

**Open items affecting routing order (recorded, not blocking):**
- Walking-engine choice (Valhalla vs. GraphHopper) must be prototyped on a Sri Lankan OSM extract before walking integration (final `10` §9; IMPLEMENTATION_PLAN §1.3) — the brief's caution matches the documentation's own gate.
- Time estimation without timetables: network-feasible paths + configured/validated corridor estimates presented as ranges; no fabricated waiting times (final `10` §5).
- Algorithm depth is deliberately staged (Dijkstra → A* → multi-criteria label-setting; RAPTOR only when real stop times exist) — appropriate restraint for the static MVP.

---

## 9. Mobile application readiness

**Status: design-only.** No React Native/Expo project exists. The design is nonetheless detailed enough to build from directly:

- Screens: final `13` §1 (Home/search, results/map picker, alternatives, detail, active journey, saved, reports, settings; admin console as a separate protected web client).
- State/data: TanStack Query (server state) + Zustand (transient UI/active session) + SQLite (offline itinerary) + SecureStore (tokens) — final `13` §2, with the boundary "Do not duplicate the full transport network on the phone in the first release".
- Offline model: cache plan + dataset version + ordered legs/instructions/aliases/geometry/warnings; offline banner with cache age; no live claims offline; manual confirmations continue (final `13` §3; research-draft Flow H).
- Location: contextual permission, mandatory manual fallback, persistent tracking indicator, stop on journey end (final `13` §4) — matches US-038 and the brief's privacy stance.
- Active journey state machine: 11 primary states + 4 auxiliary states (`PAUSED`, `DEVIATED`, `REPLANNING`, `MANUAL_ASSISTANCE`), event-driven and auditable; GPS suggests, user confirms boarding/alighting (final `13` §5).
- Accessibility: dynamic text, screen readers, contrast, no colour-only cues, no unverified accessibility claims (final `13` §6).
- Open items affecting mobile: navigation library (C3 — recommendation: Expo Router), E2E tooling (C4 — recommendation: Maestro), and a MapLibre-React-Native compatibility spike (final `07` warns "Use Expo development builds rather than assuming Expo Go supports every native map/location requirement").

---

## 10. Infrastructure and development-environment readiness

**Repository-provided infrastructure: none.** No Docker/Compose files, environment templates, CI workflows, migration tooling, or lint configs exist. Below is host-environment evidence from read-only version checks:

| Component | Observed | Assessment |
|---|---|---|
| Python (`python`) | 3.11.9 | ⚠️ Final `07` specifies Python 3.12+. A 3.14.2 interpreter exists via the `py` launcher; a pinned 3.12+ venv (or uv/pyenv) must be established at Phase 0.3 |
| Node.js / npm | 22.16.0 / 9.8.1 | ✅ Adequate (confirm the exact Expo SDK target at skeleton creation) |
| Git | 2.40.0.windows.1 installed | ✅ Binary available — but **not initialized in this directory** (GAP-001) |
| Docker / Compose | 29.5.3 / v5.1.4 | ✅ Sufficient for the local PostGIS + Redis (+ later Valhalla) stack |
| PostgreSQL client | psql 15.4 | ✅ Server not required locally (runs in Docker); PostGIS comes from the Docker image |
| PostGIS / Redis native installs | Not installed | Acceptable — both provided by Docker per plan (Redis scope also subject to C1) |
| Mobile tooling (Xcode/Android Studio/simulators) | Not verified in this audit | Unknown — required before the Phase 0.4 mobile skeleton can be *run*; creating the skeleton does not require them |
| Env templates / secrets handling | Absent | Phase 0.3 work item (IMPLEMENTATION_PLAN Phase 0 item 5: `.env.example` with placeholders only) |
| CI workflows / test & lint configs | Absent | Phase 0 items 8–9 (install/lint/type-check/unit tests/build checks) |
| Object storage / secret manager / monitoring | Absent | Deferred by design to staging deployment (final `07` §Infrastructure); no cloud vendor may be hard-coded (IMPLEMENTATION_PLAN §1.3) |

Missing prerequisites before the Phase 0 exit gate (per IMPLEMENTATION_PLAN Phase 0 tests): a working Docker Compose stack with PostGIS enabled and Redis responding; a pinned Python ≥3.12; reachable mobile simulators/devices.

---

## 11. Git and project-history assessment

**Confirmed: there is no Git repository.** `git status`, `git log`, and `git branch` fail with `fatal: not a git repository (or any of the parent directories): .git`.

- Current branch / latest commit / recent history / uncommitted modifications / untracked files: **none exist** — no VCS is tracking this directory.
- Incomplete or abandoned implementation work: none detectable; the tree contains only documentation, and nothing suggests deleted code.
- Project classification: **a new project, pre-version-control**. The knowledge base itself anticipates this: root `README.md` §"How to use" says "Keep future changes in version control and record product/architecture decisions as they are made" — version control has not yet been started.
- User-owned changes: the entire tree is user-owned content; nothing in this audit touches it.

**Consequences (why GAP-001 is P0):**
1. Every subsequent phase-report field demanded by IMPLEMENTATION_PLAN §12.3 ("Repository commit/branch inspected") is impossible to fill truthfully until a repo exists.
2. No rollback safety exists for the code and documentation the project will produce, contradicting the project's own data-versioning philosophy.
3. There is no branch protection or review mechanism, which the architecture package assumes for admin/data publishing workflows.

---

## 12. Security and privacy assessment

**Implemented provisions: none** (nothing is implemented). Assessment is therefore of *documented* provisions and their completeness relative to the brief:

| Area | Documented provision | Gap |
|---|---|---|
| Location permission | Contextual request, manual fallback mandatory, no background tracking in MVP, persistent tracking indicator, stop-on-end (research `03`/`06` §10; final `13` §4; US-038) | None — exceeds the brief's minimum |
| Personal data collection | Guest planning without account (US-037); accounts only for saved/sync; minimize retention; no default journey-history retention (final `14`; IMPLEMENTATION_PLAN §9.5) | None |
| Data retention | Retention periods for reports/sessions/logs required; account export/deletion workflow (US-039); deletion/retention verified in Phase 7 tests | Policy values (durations) not yet defined — correctly deferred, but should be set before pilot |
| API authentication | OAuth2/OIDC for accounts; guest access within rate limits; RBAC for admin (final `14`) | None; consistent with brief's "no unnecessary auth" |
| Authorization | Admin endpoints "require strong authorisation and audit logging" (final `11`); publishing/moderation roles referenced (US-034–036) | Named human owners unresolved (open question in final `17`) |
| Input validation | Pydantic schemas; bounded coordinate/radius inputs; parameterized queries; no raw SQL from user input (final `11`; IMPLEMENTATION_PLAN §4.2) | None |
| Rate limiting | "Rate-limit public endpoints and protect admin endpoints" (final `11`); Redis noted as rate-limit backing | Implementation-level; covered in skeleton phase |
| Logging / sensitive data exposure | "Do not log precise coordinates, search terms or trip details unless required"; log "operational metadata, not raw precise journeys" (final `06` §10; IMPLEMENTATION_PLAN §4.2/§9.5) | None documented |
| Secure API configuration | HTTPS everywhere; secrets in secret manager, never in source or mobile bundle; separate env credentials (final `14`) | None |
| User-submitted reports | Categories defined; reports stored pending; moderation queue; "Reports cannot directly mutate production data" (final `16` Phase 5 gate); idempotent submission; privacy notes for photos/location (research `05` Flow I) | None |
| Moderation & verification | Reviewer validates against sources/field evidence; no auto-publish (final `09` §9); consent + attribution terms for contributors (research `07` §7) | Owner/staffing unresolved (IMPLEMENTATION_PLAN §1.3) |
| Administrative data publishing | Atomic publish, validation gates, post-publish smoke tests, audited rollback (final `09` §7; US-036) | None |
| Backup & recovery | Automated DB backups + PITR, restore drills, immutable raw snapshots, 9 operational runbooks (final `15` §5–§6) | RTO/RPO deferred until pilot requirements known (stated) |
| Monitoring & rollback | Observability metric list (final `15` §4); rollback pointer + cache invalidation (IMPLEMENTATION_PLAN §5.2 rule 7) | None |
| Legal | "Review applicable Sri Lankan data protection requirements… with qualified counsel" (final `14`) | Counsel review not yet performed — flagged, not blocking Phase 0 |

**Brief-specific check — "MVP should not require an account":** confirmed as an explicit, repeated product decision (IMPLEMENTATION_PLAN §2.2 item 13, §9.5; final `00` §8; US-030/US-037; research `03` "Avoid forcing login for core planning"). No contradiction found anywhere in the knowledge base.

**Observed security posture of the repository itself:** no secrets, no credentials, no environment files exist; nothing to remediate.

---

## 13. Testing and quality-assurance assessment

**Existing tests: none.** No test files, fixtures, CI configuration, lint/type-check configs, or coverage measurement exist anywhere in the repository. **Coverage has never been measured and cannot be stated; this audit does not fabricate a figure.**

**Documented QA strategy (assessed against the brief's future test categories):**

- Test pyramid: unit → integration → contract → data-quality → routing regression → mobile component → E2E (IMPLEMENTATION_PLAN §9.1; final `15` §1 enumerates matching concrete targets).
- CI/CD gates: 8 steps — format/lint/type, unit, integration, migration checks, dependency scan, mobile build, staging smoke, human approval (final `15` §3).
- Transport-data tests: docs already cover duplicate IDs/stops ("No duplicate canonical IDs; alias collisions surfaced rather than silently merged"), coordinate bounds/SRID, ordered non-duplicated variant sequences, distinct partial services, stops-vs-shape plausibility, transfer connector validity, licence/attribution presence, ingestion idempotency, failed-ingestion safety, publish/rollback integrity (IMPLEMENTATION_PLAN Phase 1; final `15` "Data tests"). Provenance/version checks are named generically; fixtures and sample datasets do not exist yet — Phase 1 must create the curated corridor fixtures both doc sets assume.
- Routing tests: the Phase 4 regression suite enumerates direct/one-transfer/multi-transfer/bus-rail/rail-bus/walking-only/no-route/low-coverage/ambiguous cases, the board-after-alight invariant, the explicit-connector invariant, constraint enforcement, label-vs-metric consistency, Pareto behaviour, and versioned cache keys (IMPLEMENTATION_PLAN Phase 4). Deterministic repeatability is implied by the deterministic-planner and cache-key design but is not an explicitly named test; recommend adding it to the Phase 4 suite definition.
- Instruction tests: schema/snapshot tests per step type; "No template emits route/direction/landmark values absent from structured facts"; no-live-availability honesty; localization fixtures with native review (IMPLEMENTATION_PLAN Phase 5).
- Tooling selected in design: pytest, Jest + React Native Testing Library, Maestro, OpenAPI contract tests.

**Foundation assessment:** the QA strategy is well-specified on paper, but zero test infrastructure exists; every category starts from nothing. This is expected at Phase 0 and is addressed by Phase 0 items 8–9 (test commands, CI) and Phase 1 (data fixtures).

---

## 14. Prioritized gap analysis

Priorities per the brief's definitions. No rewrite is recommended anywhere — the repository contains only valuable documentation.

### P0 — Critical (must be addressed before dependent implementation proceeds safely)

| ID | Description | Evidence | Why it matters | Affected layer | Recommended resolution | Decision needed? |
|---|---|---|---|---|---|---|
| GAP-001 | No version control: the directory is not a Git repository | `git status` → `fatal: not a git repository`; Git 2.40 binary is installed | All subsequent audit/reporting/rollback discipline (IMPLEMENTATION_PLAN §12.3) is unachievable; no change is recoverable | All | Initialize Git with a `.gitignore` prepared for Python/Node/Expo/Docker; commit the existing 32 files + this audit as the baseline commit. Owner action or explicitly delegated agent task | Yes — trivial but must be approved/owned |
| GAP-002 | Knowledge-base location/index mismatch: `IMPLEMENTATION_PLAN.md` sits at root while §0.1 says companions belong in `docs/product/` "or equivalent"; root `README.md` indexes only the 10 research docs and omits the final architecture package and the implementation plan | Root listing; README "Documents"; IMPLEMENTATION_PLAN §0.1 | Coding agents following the companion-doc rule will look in `docs/product/` and find nothing; the newer architecture package can be missed entirely | Documentation/tooling | Phase 0.2: adopt a documented docs layout (consolidate into `docs/` per IMPLEMENTATION_PLAN §4.1, or amend §0.1 to declare the current layout the "equivalent"); extend the root README index to cover all three locations | Yes — layout preference |
| GAP-003 | Three inconsistent phase-numbering schemes (and two backend module lists) across control documents | IMPLEMENTATION_PLAN Phases 0–10 vs. final `16` Phases 0–6 vs. `08_SCOPE_ROADMAP_AND_RISKS.md` Phases 0–5; module lists IMPLEMENTATION_PLAN §3.3 vs. final `06` §3 | Phase/task IDs are the unit of agent scoping (§12.1); ambiguity risks wrong-scope implementation | Governance | Phase 0.2: declare the implementation plan's Phase 0–10 canonical, publish an explicit mapping table to the other two schemes, and reconcile the backend module list into one canonical module map | Yes — product-owner ratification |

### P1 — High (address during early foundation work)

| ID | Description | Evidence | Why it matters | Recommended resolution | Decision needed? |
|---|---|---|---|---|---|
| GAP-004 | `Docs/Product docs/06_TECHNICAL_ARCHITECTURE.md` carries superseded undecided-technology content ("Flutter or React Native"; stack "evaluate, not final") with no supersession marker | That document §2 vs. final `00` §3 / `07_TECH_STACK` | A reader of the older set alone could treat Flutter/OTP as live options | Add a supersession note at the top of `06` pointing to the final architecture package (editorial note only) | No |
| GAP-005 | Competing user-story registers: `Docs/Product docs/05` (US-01–35) vs. final `04_USER_STORIES.md` (US-001–039, with acceptance criteria); IMPLEMENTATION_PLAN §10 maps phases to the old IDs | Both story documents; IMPLEMENTATION_PLAN §10 | Traceability ("Every public feature has a user story") breaks if two registers drift | Phase 0.2: declare the final package's `04_USER_STORIES.md` authoritative, record the old→new ID mapping in the decision log | Yes — owner confirmation |
| GAP-006 | Undecided technology selections flagged "choose in ADR": Redis scope (C1), background-job library (C2), navigation (C3), E2E tool (C4), pedestrian-network storage model (§7), dataset-versioning strategy (§7 item 6) | IMPLEMENTATION_PLAN §3.1; final `07`; final `08` §4 | First dependent implementation tasks need these answers; the Redis decision shapes the Phase 0.3 Docker stack | Phase 0.2/0.3: write ADRs; the docs' own suggested defaults (Expo Router, Maestro, "Celery or Dramatiq — select one") are sound starting points | Yes — ADRs required |
| GAP-007 | Python version drift: environment default is 3.11.9 while final `07` specifies 3.12+ | §10 version checks | Library compatibility and reproducible environments; the Phase 0 exit test requires a fresh-clone setup | Phase 0.3: pin ≥3.12 (py launcher / uv / pyenv or Docker-based Python); record in ADR-001 | No |
| GAP-008 | No ADRs, ADR template, or decision log exist, although three documents mandate ADR-based governance | No `adr/` directory; IMPLEMENTATION_PLAN §0.2, §11; final `17` approval checklist | Future decisions (providers, corridors, licensing) need a recorded precedent format | Phase 0.2: create the ADR template; record ADR-001 (baseline stack) plus GAP-006 decisions | No |

### P2 — Medium (address during the relevant feature phase)

| ID | Description | Evidence | Why it matters | Recommended resolution | Timing |
|---|---|---|---|---|---|
| GAP-009 | Pilot corridor, destination set, and benchmark journeys undecided | final `17` §A1; IMPLEMENTATION_PLAN §14.1; `08` §3 | Data ingestion (Phase 1) and routing regression fixtures need it; the engineering foundation does not | Resolve via the documented coverage scorecard + owner decision | Before Phase 1 ingestion; decision required |
| GAP-010 | Transport-source rights/availability entirely unevidenced: no datasets, API keys, licences, or rights register exist | Nothing in tree; docs assert unknown themselves (`09_RESEARCH` §9; final `17` §C) | Nothing can be imported or published without it; planning logic is unaffected | Source-by-source rights audit before any ingestion; keep sources private until registered | Before Phase 1.3; legal/owner decision |
| GAP-011 | Named owners unresolved for field verification, moderation, data publishing, support response times | final `17` §C17/D23; IMPLEMENTATION_PLAN §1.3, §14.5/§14.8 | Multiple gates (field checks, moderation, publish approval) block on humans, not code | Collect owner names during Phase 0/1; record in decision log | Before public pilot |
| GAP-012 | Retention-period values, legal counsel review, app-store privacy disclosures not yet produced | final `14` §Privacy; IMPLEMENTATION_PLAN Phase 9 item 7 | Required before pilot release, not before foundation | Schedule in Phase 9 as documented; do not pull forward | Phase 9 |

### P3 — Low (optimization / future)

| ID | Description | Evidence | Recommended resolution | Timing |
|---|---|---|---|---|
| GAP-013 | Map tile/geocoding providers, hosting vendor, and budget undecided | final `17` §D20–21; IMPLEMENTATION_PLAN §14.2–3 | Decide during Phase 2 spikes; ADR each | Phase 2 |
| GAP-014 | Timetables, live tracking, fare calculation, accounts/social features deliberately deferred | IMPLEMENTATION_PLAN §2.3; final `03` §H; final `16` Phase 6 | Revisit only via documented scope-change decision | Post-MVP |

---

## 15. Open questions and required decisions

### A. Must resolve before Phase 0 foundation proceeds

| # | Question | Why it matters | Latest safe point |
|---|---|---|---|
| A1 | **Is this directory the intended main project repository, and may version control be initialized here?** | Everything else builds on a versioned baseline (GAP-001) | Before Phase 0.2 begins |
| A2 | **Which documentation layout is canonical** — consolidate into `docs/` per IMPLEMENTATION_PLAN §4.1, or keep the current split and amend §0.1? | Agent companion-doc lookups and index integrity (GAP-002) | Phase 0.2 |
| A3 | **Confirm the canonical phase/task numbering** (recommend IMPLEMENTATION_PLAN Phase 0–10) and canonical story register (recommend final `04`) | Prevents wrong-scope tasks and broken traceability (GAP-003/005) | Phase 0.2 |
| A4 | **Ratify the "proposed baseline" status of the final architecture package and IMPLEMENTATION_PLAN** — both are dated today and marked "approval required" | The plan's own precedence rules require an approved decision before implementation; proceeding unapproved violates §0.2 | Before Phase 0.3 skeleton code |

### B. Can resolve during later implementation phases (docs already assign them)

- Pilot corridor and benchmark journeys (GAP-009) — before Phase 1 ingestion; needs the coverage scorecard and a product decision.
- Source-by-source rights/licensing determinations (GAP-010) — before each source's first import.
- Map tile provider, style/attribution terms (Phase 2, per IMPLEMENTATION_PLAN §1.3).
- Geocoding provider and caching policy (Phase 2).
- Valhalla vs. GraphHopper on a real Sri Lankan OSM extract (Phase 1/2 proof of concept, before walking integration).
- Background-job library (Phase 0.3 backend skeleton, ADR).
- Android-first vs. equal iOS support (before Phase 0.4 mobile skeleton target devices — IMPLEMENTATION_PLAN §14.4).
- Named field-verification/moderation/publishing owners (GAP-011) — before public pilot.
- Dataset-versioning strategy and pedestrian-graph storage model (GAP-006) — Phase 1 ADRs.

### C. Future product decisions (not blockers)

- Exact timetable integration, live tracking, fare calculation, crowd data (Phase 10 / post-MVP; each requires its own source contract and rights review).
- Accounts, saved-journey sync, social/sharing features (only if a product case emerges; MVP explicitly excludes them).
- Voice guidance maturity and automatic alighting notifications (Phase 5+/6 items already staged behind native review).
- Coverage expansion beyond the pilot (gated on measured pilot outcomes — final `16` Phase 6, IMPLEMENTATION_PLAN Phase 10).

---

## 16. Recommended Phase 0 implementation sequence

Adjusted from IMPLEMENTATION_PLAN §13 to reflect the audit findings (the plan's own sequence is preserved; only a prerequisite is inserted and Phase 0.2 content is enriched):

1. **Phase 0.1 (this task)** — complete. Deliverable: this report.
2. **Phase 0.1b (prerequisite)** — Initialize Git (GAP-001): create `.gitignore`, `git init`, commit the existing documentation + this audit as the baseline commit. Requires owner approval per Section 15.A1; nothing existing is modified.
3. **Phase 0.2 — ADRs and project conventions** (IMPLEMENTATION_PLAN Phase 0 items 2–4): ADR template + ADR-001 (baseline stack incl. Python ≥3.12 pin, Expo Router, Maestro); resolve GAP-002 (docs layout + README index), GAP-003 (canonical phase numbering + module map), GAP-005 (story register); add supersession note to `Docs/Product docs/06` (GAP-004); add `AGENTS.md` coding-agent instructions.
4. **Phase 0.3 — Local infrastructure and backend skeleton** (Phase 0 items 5–7, 10): Docker Compose for PostgreSQL/PostGIS + Redis (scope per Redis ADR); FastAPI skeleton with health/readiness + OpenAPI; Alembic initialized; `.env.example` with placeholders only; structured logging; background-job library ADR.
5. **Phase 0.4 — Mobile skeleton and CI** (Phase 0 items 7, 9): Expo + TypeScript skeleton with navigation and env config; CI gates (install, lint, type-check, unit tests, build checks); verify the Phase 0 exit tests (fresh-clone setup, PostGIS enabled, Redis responds, app launches on at least one device path, CI green, no secrets committed).

---

## 17. Final readiness assessment

### Classification: **READY WITH CONDITIONS**

**Evidence supporting readiness:**
- The complete knowledge base exists, is internally coherent on product scope, data governance, AI boundaries, security/privacy, and testing strategy, and matches the agreed technology baseline on every layer (Sections 3, 5, 6).
- The documented data model satisfies all eight transport-data readiness requirements and the documented routing architecture satisfies all eight routing-readiness requirements (Sections 7, 8) — no architectural rework is required before foundation work.
- The implementation plan explicitly anticipates this audit as the first task and provides the sequencing, exit criteria, and agent protocol for everything that follows.
- Nothing exists that must be untangled: there is no legacy code, no conflicting implementation, and no repository-imposed technology.

**Conditions (must be resolved before or during the immediately following work):**
1. Version control must be initialized (GAP-001) — P0, before Phase 0.2 outputs are considered durable.
2. Documentation layout, phase numbering, and story register must be declared canonical (GAP-002/003/005) — Phase 0.2.
3. The "proposed baseline" documents require product-owner ratification before skeleton code is written (Section 15.A4).
4. Five undecided technology selections need ADRs (GAP-006) — Phase 0.2/0.3.

### Direct answers to the brief's closing questions

**1. Can we safely begin Phase 0.2?**
Yes — after the Git baseline commit (Phase 0.1b) is made. Phase 0.2 (ADRs, conventions, docs reconciliation) touches no runtime systems and is exactly what the remaining P0/P1 documentation gaps require. If version control cannot be initialized immediately, Phase 0.2 may still proceed, but its outputs should not be considered durable until committed.

**2. What should be the next three implementation tasks?**
1. Phase 0.1b — Git initialization + `.gitignore` + baseline commit (GAP-001).
2. Phase 0.2 — ADR template; ADR-001 (baseline stack incl. Python ≥3.12, Expo Router, Maestro); docs-layout/README index fix; canonical phase-map + story-register declaration; `AGENTS.md` (GAP-002/003/004/005/008).
3. Phase 0.3 — Docker Compose (PostGIS + Redis per Redis ADR); FastAPI skeleton with health/readiness and OpenAPI; Alembic init; `.env.example`; structured logging (GAP-007; background-job ADR).

**3. What must not be implemented yet?**
Per the knowledge base's own deferrals and this audit: no routing engine, no data ingestion, no pilot-corridor data import (pilot undecided — GAP-009), no map screen, no AI features, no timetables/live tracking/fares/accounts, no vector database or RAG, no microservices/Kubernetes, and no technology migrations. Also: no source scraping or dataset downloads until the rights register exists (GAP-010).

**4. Which existing components should be preserved?**
All of them — the entire tree is documentation and all of it carries decision value:
- `IMPLEMENTATION_PLAN.md` — engineering control document; preserve verbatim (including §0.2 precedence and §12 agent protocol).
- `Docs/Product docs/00–09` — problem evidence, gap matrix, story register, source register, risk register; preserve (add only a supersession note to `06`, GAP-004).
- `Docs/sri_lanka_journey_planner_final_architecture/00–17` + `MANIFEST.json` — the operative technical baseline; preserve verbatim.
- Root `README.md` — extend its index (GAP-002), do not rewrite its content.
- No component should be deleted; nothing requires replacement.

**5. Which architectural decisions need formal ADRs?**
- ADR-001: Baseline stack ratification (including Python ≥3.12 pin, Expo Router over React Navigation, Maestro over Detox, TanStack Query + Zustand, i18next, Ruff + mypy/pyright).
- ADR-002: Redis scope in MVP (baseline component for cache/rate-limit vs. deferred entirely; affects the Phase 0.3 Docker stack).
- ADR-003: Background-job library (Celery vs. Dramatiq vs. plain Python worker + Redis queue).
- ADR-004 (Phase 1): Dataset-versioning strategy — immutable versioned tables vs. snapshot/blue-green publication.
- ADR-005 (Phase 1): Pedestrian network representation — stored `pedestrian_nodes/edges` vs. external Valhalla graph reference/version, and provenance of computed walk paths.
- Later, per docs: walking router (Valhalla vs. GraphHopper after the OSM prototype), tile provider, geocoding provider, hosting/cloud, authentication scope when saved-journey sync is considered.

**6. What information is needed from the product owner before proceeding?**
1. Approval to initialize Git in `c:\MIHA\BUS_ROUTE` (A1/GAP-001) and confirmation that this directory is the main project repository.
2. Choice of documentation layout (A2/GAP-002): consolidate under `docs/` or amend the plan's §0.1 to bless the current layout.
3. Ratification of the canonical phase-numbering scheme and authoritative story register (A3/GAP-003/005).
4. Formal approval of the "proposed baseline" documents as the execution baseline (A4), including the Redis-scope answer for ADR-002.
5. ADR choices for the five undecided items in GAP-006 (the defaults proposed in the docs are sound if the owner prefers).
6. Target platform emphasis (Android-first vs. iOS-equal) before Phase 0.4 device targets are chosen.
7. Pilot corridor preference (may stay open until the Phase 1 coverage scorecard, but early input shortens it).
8. Availability of mobile development tooling (Android Studio/Xcode) for the Phase 0 exit test.

---

## Appendix A — Commands executed during this audit

All commands were read-only or produced this report only:

- `Get-ChildItem -Force` (root listing) and a recursive filtered listing (structure inventory).
- `git status --porcelain=v1 -b`, `git log --oneline -15`, `git branch -a` → all failed with `fatal: not a git repository` (finding GAP-001).
- Code-search queries for `00_DOCUMENTATION_INDEX` and `11_IMPLEMENTATION_PLAN` (document-location confirmation).
- File reads across all 32 repository files (documentation audit).
- Version checks: `python --version` (3.11.9), `py --version` (3.14.2), `node --version` (22.16.0), `npm --version` (9.8.1), `git --version` (2.40.0), `docker --version` (29.5.3), `docker compose version` (v5.1.4), `psql --version` (15.4), `redis-server --version` / `redis-cli --version` → not installed (expected; runs in Docker per plan).
- Creation of `docs/audits/phase-0-repository-audit.md` (this file).

No migrations, dependency installs, Docker state changes, file deletions, or Git operations were performed.

## Appendix B — Glossary of document references used in this report

- "IMPLEMENTATION_PLAN" = root `IMPLEMENTATION_PLAN.md` (Document ID 11).
- "research `NN`" = `Docs/Product docs/NN_*.md`.
- "final `NN`" = `Docs/sri_lanka_journey_planner_final_architecture/NN_*.md`.

*End of report.*
