# ADR-0004 — Background job processing library

**Date:** 2026-11-19
**Status:** Accepted (confirmed by the product owner on 2026-11-19)
**Deciders:** Product owner
**Phase/task context:** Phase 0.2 (audit finding C2 / GAP-006); the ratified stack deferred this selection to an ADR

## 1. Context

`docs/product/11_IMPLEMENTATION_PLAN.md` §3.1 requires "a Python worker and Redis-backed queue (choose a maintained library in ADR)"; `docs/architecture/07_TECH_STACK.md` lists "Celery or Dramatiq — select one, do not use both initially". Nothing in the repository requires background jobs before Phase 1 (source ingestion/sync), but the selection shapes the Phase 0.3 backend skeleton's task-queue plumbing.

## 2. Decision (proposed)

Adopt **Dramatiq** (with Redis broker) as the background job library, wrapped behind a thin internal task-dispatch interface in the `platform` module so the library remains replaceable.

Rationale for Dramatiq over Celery:
- Smaller, simpler API surface for the moderate job volume this MVP needs (scheduled source syncs, extraction, validation, graph publication — not high-throughput task fan-out).
- Fewer configuration moving parts and a smaller dependency/upgrade footprint in a modular monolith.
- Native support for retries with bounded backoff, rate limiting, and middleware hooks, which map directly onto the ingestion pipeline's timeout/retry/rate-limit requirements (`docs/architecture/09` §3–§4).
- Avoids Celery's larger operational surface (beat scheduling model, result backends, broker quirks) that the MVP does not need yet.

Scheduling: use a simple cron/interval scheduler invoking task dispatch (or Dramatiq's built-in periodic-signal scheduling) rather than Celery Beat.

## 3. Options considered

| Option | Summary | Consequences |
|---|---|---|
| **Dramatiq** (proposed) | Lightweight Redis-backed task queue | Fewer features than Celery; smaller ecosystem; sufficient for MVP job profiles |
| Celery | Industry default, very large ecosystem | Heavier operational/config surface; more than the MVP needs now; still viable if team familiarity argues for it |
| Plain Python worker loop + Redis primitives | Zero framework dependency | We must hand-build retries, concurrency, observability — false economy once ingestion lands |
| RQ | Very simple | Lacks robust retry/middleware semantics needed by the ingestion validation pipeline |

## 4. Rationale

The MVP's job profile is scheduled, moderate-volume, retry-sensitive pipeline work. Dramatiq covers it with the least complexity. The dispatch-interface requirement keeps the choice reversible regardless.

## 5. Consequences

- Positive: simplest viable queue backing the documented ingestion pipeline; clear upgrade path to Celery behind the dispatch interface if scale demands it.
- Negative: smaller community than Celery; if the team has deep Celery experience, that argues for choosing Celery instead — which is precisely why this ADR remains **Proposed** until the owner confirms.
- Migration impact: contained to the platform task-dispatch adapter if ever changed.

## 6. Related documents

`docs/product/11_IMPLEMENTATION_PLAN.md` §3.1 (background jobs), `docs/architecture/07_TECH_STACK.md` (backend table), `docs/architecture/09_DATA_INGESTION_AND_REFRESH.md` §3–§4, `docs/audits/phase-0-repository-audit.md` (C2).

## 7. Reversal conditions

If measured ingestion workloads require Celery-specific ecosystem features, or the team mandates Celery familiarity, supersede this ADR before Phase 1 worker implementation; the dispatch interface must keep the change inside `platform`.
