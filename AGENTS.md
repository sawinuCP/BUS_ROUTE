# AGENTS.md — Coding-Agent Instructions

This file governs how AI coding agents work in this repository. It complements (and never overrides) the documents listed below.

## 1. Project

The Sri Lanka Journey Planner: a multimodal public-transport journey planner that produces step-by-step, executable travel instructions grounded in validated transport data. Core principle: a route suggestion is not a successful journey plan unless the traveller can understand and carry out every leg.

## 2. Required reading before any change

Read, in this order, the parts relevant to your task:

1. `docs/status/development-status-report.md` — **current phase, status, issue log and remaining path; keep it updated (see §5)**
2. `docs/product/11_IMPLEMENTATION_PLAN.md` — engineering control document (Phases 0–10, standards, agent protocol §12).
3. `docs/architecture/00_EXECUTIVE_SUMMARY_AND_DECISIONS.md` — ratified baseline decisions.
4. `docs/architecture/07_TECH_STACK.md`, `docs/architecture/08_DATA_MODEL.md`, `docs/architecture/10_ROUTING_ENGINE.md`, `docs/architecture/11_BACKEND_API_DESIGN.md` — stack, data model, routing and API contracts.
5. Relevant product documents in `docs/product/00–09` for the feature area.
6. `docs/adr/` — all accepted ADRs; check whether your task conflicts with a recorded decision.

Document precedence when documents conflict (per `11_IMPLEMENTATION_PLAN.md` §0.2): ADR-recorded latest owner decision > approved technical architecture > the implementation plan > product feature/user-story documents > earlier research drafts. Flag conflicts; never resolve them silently.

## 3. Approved baseline (ADR-0002)

React Native + TypeScript + Expo (Expo Router, TanStack Query + Zustand, SQLite, MapLibre React Native); Python 3.12+ / FastAPI / Pydantic / SQLAlchemy 2.x / Alembic; PostgreSQL + PostGIS; Redis (scoped per ADR-0003); deterministic multimodal transit graph; Valhalla walking adapter pending prototype; REST + OpenAPI; modular monolith; pytest, Ruff + mypy/pyright, Jest + React Native Testing Library, Maestro. No Kubernetes, Kafka, vector databases, RAG-as-routing-dependency, or microservices in the MVP.

## 4. Critical product rules

- Every itinerary must be grounded in canonical, versioned transport data; never invent a stop, route, direction, fare, timetable, landmark or service-availability claim.
- Keep route variants and directions distinct; a route number alone is not a service identity.
- Every transfer needs an explicit pedestrian connector; proximity alone never creates one.
- No schedule-aware or live claims in the static MVP.
- Critical instructions are deterministic templates; AI may only explain/translate supplied facts and must have a deterministic fallback.
- Preserve provenance, licence, freshness and fact-level confidence.
- Basic planning must not require an account; location permission must have a manual fallback.
- Do not auto-publish user reports or unverified source updates.

## 5. Working protocol

1. Work in one bounded phase/task at a time, using the canonical phase numbering in ADR-0001 (implementation plan Phases 0–10).
2. Before changing code: inspect the repository, current branch, working tree, existing tests. Never assume a planned component already exists or that the repository is empty.
3. Produce a short implementation plan, then implement only the approved scope.
4. Add/execute the required tests. **Never claim a test passed unless it was run and passed.** Do not weaken or delete tests to make a task pass.
5. Provide a truthful final report: task/phase, branch/commit inspected, files changed, data/schema/API changes, commands executed with exact results, acceptance criteria PASS/FAIL/BLOCKED with evidence, limitations, ADR/documentation updates, and a recommended next bounded task.
5b. **Update `docs/status/development-status-report.md`** — the status dashboard (§5), phase record (§6), issue log (§7, append-only) and remaining path (§10) — so the report always reflects the true current position, test results, and any issues and their fixes.
6. Stop and ask when a decision materially affects data rights, route correctness, privacy, architecture or user safety.

## 6. Repository conventions

- Layout per ADR-0001: backend in `backend/`, mobile in `apps/mobile/`, infrastructure in `infra/`, sample data in `data/`, docs in `docs/`.
- No business rules in route handlers or UI components. Domain code must not depend on FastAPI, SQLAlchemy, Redis, a map vendor or an LLM SDK.
- Stable internal IDs; never use route numbers or stop names as primary keys.
- WGS84 longitude/latitude order at API boundaries; metres and seconds internally; `Asia/Colombo` for local display; UTC in storage.
- Secrets only via environment/secret manager; `.env.example` contains placeholders only; never commit secrets, licensed source extracts, or large raw datasets.
- Do not mark work complete because code was generated; complete only after verification.
