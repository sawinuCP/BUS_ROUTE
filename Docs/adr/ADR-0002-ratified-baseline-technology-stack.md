# ADR-0002 — Ratified baseline technology stack

**Date:** 2026-11-19
**Status:** Accepted (product-owner decision: "Architecture baseline: yes")
**Deciders:** Product owner
**Phase/task context:** Phase 0.2 (resolving audit GAP-006/008 and Section 15.A4: the "proposed baseline" documents required ratification before skeleton code)

## 1. Context

The Phase 0.1 audit confirmed that the repository contains no code and that all technology positions exist only as written proposals. Two documents carried "proposed / approval required" status (`docs/architecture/` package and `docs/product/11_IMPLEMENTATION_PLAN.md`). Per the plan's own precedence rules (§0.2) an approved decision must exist before implementation. The audit also flagged small undecided selections inside the stack (navigation library, E2E tool, Python version).

## 2. Decision

The product owner ratified the architecture baseline on 2026-11-19. The stack is accepted as follows:

| Layer | Decision |
|---|---|
| Mobile | React Native + TypeScript, **Expo development builds** (not Expo Go), **Expo Router** for navigation |
| Mobile state/data | **TanStack Query** (server state) + **Zustand** (transient UI/active-session state) |
| Forms/validation | **React Hook Form + Zod** |
| Maps | **MapLibre React Native**; tile provider selected later under a provider abstraction (no community tile servers in production) |
| Location | **Expo Location** |
| Offline store | **SQLite** (Expo-compatible); **SecureStore** for tokens/secrets |
| Localisation | **i18next** or equivalent |
| Backend | **Python 3.12+ (pinned), FastAPI, Pydantic, SQLAlchemy 2.x, Alembic** |
| Database | **PostgreSQL + PostGIS** (source of truth) |
| Cache/queue backing | **Redis** — scope defined in ADR-0003 |
| Walking router | **Valhalla** baseline candidate behind an adapter interface; adopt only after a prototype on a Sri Lankan OSM extract (final `10` §9); GraphHopper is the comparison candidate |
| Transit planning | **Custom deterministic multimodal graph** (no LLM, no RAG, no vector database in the routing path) |
| API | REST + FastAPI-generated OpenAPI, base path `/api/v1` |
| Architecture | Modular monolith with clean domain boundaries; module map per ADR-0001 item 3 |
| Backend quality | **pytest; Ruff + mypy/pyright; structured JSON logging; OpenTelemetry** when observability lands |
| Mobile testing | **Jest + React Native Testing Library; Maestro** for E2E |
| Delivery | Docker + Docker Compose; environment-based config; CI pipeline |

Ratification of the two "proposed baseline" documents is likewise recorded: `docs/architecture/` package v1.0 and `docs/product/11_IMPLEMENTATION_PLAN.md` v1.0 are accepted as the operative technical baseline, subject to ADR precedence.

## 3. Options considered

Not re-litigated here; the evaluation history is in `docs/architecture/07_TECH_STACK.md`, `docs/product/06_TECHNICAL_ARCHITECTURE.md` (superseded draft), and the Phase 0.1 audit (Sections 5–6). The audit found no repository evidence contradicting any baseline choice.

## 4. Rationale

The baseline matches every ratified decision table in the knowledge base, resolves the remaining "choose in ADR" items with the defaults those documents themselves proposed (Expo Router, Maestro), and keeps all provider-dependent choices behind adapter interfaces so later decisions do not rework domain code.

## 5. Consequences

- Positive: implementation can proceed without reopening stack debates; the Phase 0 exit tests have a defined target.
- Negative: Python 3.12+ must be pinned in project tooling (local default `python` is 3.11.9; a 3.14.2 interpreter exists via the `py` launcher) — a Phase 0.3 task.
- Open sub-decisions intentionally deferred, each behind an adapter: tile/geocoding providers, walking-router adoption, hosting/cloud.

## 6. Related documents

`docs/architecture/07_TECH_STACK.md`, `docs/architecture/00_EXECUTIVE_SUMMARY_AND_DECISIONS.md` §3, `docs/product/11_IMPLEMENTATION_PLAN.md` §3, `docs/audits/phase-0-repository-audit.md` §5, §10.

## 7. Reversal conditions

A provider-prototype failure (e.g., Valhalla path quality on Sri Lankan pedestrian data), a blocking library incompatibility (e.g., MapLibre ↔ Expo build tooling), or an ecosystem EOL would trigger a superseding ADR — not an ad-hoc switch.
