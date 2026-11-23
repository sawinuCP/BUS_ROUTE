# Sri Lanka Journey Planner — Product & Technical Documentation

Pre-development foundation for a Sri Lankan multimodal public transport journey planner focused on actionable, step-by-step travel instructions.

## Quickstart (backend — Phase 0.3)

Prerequisites: Docker Desktop running.

```powershell
copy .env.example .env        # then adjust values if needed (never commit .env)
docker compose --env-file .env -f infra/docker/compose.yaml up -d --build
docker compose --env-file .env -f infra/docker/compose.yaml run --rm backend pytest
```

Then open <http://localhost:8000/api/v1/health> (liveness), `/api/v1/ready` (readiness) and `/api/v1/docs` (OpenAPI). Full details: [backend/README.md](backend/README.md).

## Quickstart (mobile — Phase 0.4)

Prerequisites: Node.js 22.

```powershell
cd apps/mobile
npm install
copy .env.example .env        # then adjust EXPO_PUBLIC_API_BASE_URL if needed
npm run typecheck             # tsc --noEmit (strict)
npm run lint                  # eslint-config-expo
npm test                      # jest + jest-expo + React Native Testing Library
npm start                     # Expo dev server (simulator/device launch needs Android Studio / Xcode)
```

Full details: [apps/mobile/README.md](apps/mobile/README.md).

## CI

`.github/workflows/ci.yml` runs on push/PR: a **backend** job (format/lint/type-check/tests plus the Alembic baseline up/down wiring in the compose stack) and a **mobile** job (`npm ci`, lint, type-check, tests).

## Documentation layout

All project documentation lives under `docs/` (consolidated per ADR-0001):

| Location | Contents |
|---|---|
| `docs/product/` | Product knowledge base, documents `00`–`09` plus the implementation plan (`11_IMPLEMENTATION_PLAN.md`), pilot-release checklist and support/data-correction process |
| `docs/architecture/` | Final architecture package, documents `00`–`17` plus `README.md` and `MANIFEST.json` |
| `docs/adr/` | Architecture Decision Records (template + ADR-0001 onward) |
| `docs/runbooks/` | Operator procedures (`RUNBOOK.md`: admin auth + rotation, version lifecycle, jobs/scheduler) |
| `docs/status/` | Living development status report (current phase, test results, issue log, remaining path) |
| `docs/evidence/` | Committed verification evidence (load tests, plan benchmarks, Valhalla PoC) |
| `docs/research/` | Research notes (field-verification approach) |
| `docs/audits/` | Phase audit reports (starting with `phase-0-repository-audit.md`) |

## Start here

0. **`docs/status/development-status-report.md`** — living status report: current phase, what is done/tested, issues & fixes, remaining path (**kept updated on every task**).
1. **`docs/architecture/00_EXECUTIVE_SUMMARY_AND_DECISIONS.md`** — product definition and the ratified baseline architecture decision table.
2. **`docs/product/00_DOCUMENTATION_INDEX_AND_PRODUCT_VISION.md`** — product vision (research draft).
3. **`docs/product/11_IMPLEMENTATION_PLAN.md`** — the execution plan and engineering control document (Phases 0–10, engineering standards, coding-agent protocol).

## Product knowledge base (`docs/product/`)

1. [00 — Documentation index & product vision](product/00_DOCUMENTATION_INDEX_AND_PRODUCT_VISION.md)
2. [01 — Traveller problems](product/01_TRAVELLER_PROBLEMS.md)
3. [02 — Problem-to-gap analysis](product/02_PROBLEM_GAP_ANALYSIS.md)
4. [03 — Product features & experience](product/03_PRODUCT_FEATURES_AND_EXPERIENCE.md)
5. [04 — Sri Lanka-specific features](product/04_SRI_LANKA_SPECIFIC_FEATURES.md)
6. [05 — User stories & end-to-end flows](product/05_USER_STORIES_AND_FLOWS.md)
7. [06 — Technical architecture](product/06_TECHNICAL_ARCHITECTURE.md) *(research draft — superseded technology choices noted at top of file)*
8. [07 — Data sources & acquisition](product/07_DATA_SOURCES_AND_ACQUISITION.md)
9. [08 — Scope, roadmap & risks](product/08_SCOPE_ROADMAP_AND_RISKS.md)
10. [09 — Research references & validation](product/09_RESEARCH_REFERENCES_AND_VALIDATION.md)
11. [11 — Implementation plan (engineering control document)](product/11_IMPLEMENTATION_PLAN.md)

## Architecture package (`docs/architecture/`)

See [architecture/README.md](architecture/README.md) for the full index (`00` Executive summary & decisions through `17` Open questions).

## Decision records (`docs/adr/`)

- [ADR template](adr/ADR-TEMPLATE.md)
- ADR-0001 — Documentation layout, canonical phase numbering and user-story register
- ADR-0002 — Ratified baseline technology stack
- ADR-0003 — Redis scope in the MVP
- ADR-0004 — Background job processing library
- ADR-0005 — Docker-first local development environment (pinned Python 3.12)
- ADR-0006 — Canonical schema, dataset-versioning strategy and PostGIS conventions
- ADR-0007 — Ingestion framework: adapters, archive, idempotency, publish/rollback

**Data:** source-rights register at [`data/source-rights-register.md`](data/source-rights-register.md); committed data-quality reports and the coverage scorecard under `backend/data/validation_reports/`; field-verification kit under [`data/field-verification/`](data/field-verification/README.md).

## How to use

- Read the product vision first, then the architecture decision table.
- Treat the `docs/product/00–09` set as research grounding and the `docs/architecture/` package as the operative technical baseline.
- Use research validation and data acquisition documents as checklists for next discovery work.
- Record product/architecture decisions as ADRs in `docs/adr/`; coding agents must follow `AGENTS.md` at the repository root.

## Research caveat

The documentation collection distinguishes published findings, official-source descriptions, competitor claims, illustrative scenarios and hypotheses. Exact nationwide coverage audits, hands-on competitor tests, field verification and stakeholder interviews remain outstanding.

