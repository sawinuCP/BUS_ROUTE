# ADR-0003 — Redis scope in the MVP

**Date:** 2026-11-19
**Status:** Accepted
**Deciders:** Coding agent recommendation ratified by the product owner's baseline approval ("Architecture baseline: yes"); recorded per audit finding C1 / GAP-006
**Phase/task context:** Phase 0.2/0.3 (shapes the local Docker stack)

## 1. Context

The audit found a scope divergence: the ratified baseline and `docs/product/11_IMPLEMENTATION_PLAN.md` §3.1 include Redis as a stack component, while `docs/architecture/00` says "Redis when measured need exists" and `docs/architecture/06` shows it as "(optional cache/queue)". All documents agree Redis must never be the source of truth. Phase 0.3 provisions a local Docker stack, so the question must be settled now.

## 2. Decision

1. **Redis is provisioned from Phase 0.3** in the local Docker Compose stack (alongside PostgreSQL/PostGIS) and is expected in staging, so no component needs to be retrofitted when caching or rate limiting becomes real.
2. **Permitted uses in the MVP:** route/search response caching keyed by normalized request + network dataset version; API rate limiting; transient/session state (e.g., ingestion-run locks). It backs the background-job queue selected in ADR-0004.
3. **Prohibited uses:** a data source, a session store of record, a transport-data cache that can serve routes without the canonical database, or any place where losing Redis data changes a routing result. Cache invalidation must be tied to `network_dataset_version` changes.
4. **Measured-need discipline:** features must not be built *on* Redis before there is a measured need (architecture-package framing), but the infrastructure may exist from day one so no later migration is required. Public endpoints get rate limiting from the start (architecture `11` API rules), which is a concrete day-one use.
5. If Redis is unavailable, the API must degrade gracefully: serve from PostgreSQL, refuse or throttle rather than serve stale route data as fresh.

## 3. Options considered

| Option | Summary | Consequences |
|---|---|---|
| Provision Redis from Phase 0.3 with a scoped role (chosen) | Matches the ratified baseline; no retrofit | One extra local service; discipline required to keep it non-authoritative |
| Defer Redis until a measured need | Matches architecture `00` phrasing literally | Retrofit risk (rate limiting/caching added late touches many call sites); contradicts the ratified baseline stack table |

## 4. Rationale

The ratified baseline lists Redis as a component; the architecture package's caution is about *usage*, not existence. This ADR reconciles both: infrastructure present, authority absent, adoption measured.

## 5. Consequences

- Positive: rate limiting and version-keyed caching are available when Phase 4/2 need them; no rework.
- Negative: the backend skeleton must handle Redis-unavailable fallback (tested in Phase 0.3 readiness checks).
- Migration impact: none if scopes above are respected.

## 6. Related documents

`docs/architecture/06_SYSTEM_ARCHITECTURE.md`, `docs/architecture/11_BACKEND_API_DESIGN.md` (rate limits), `docs/product/11_IMPLEMENTATION_PLAN.md` §3.1 (cache), `docs/audits/phase-0-repository-audit.md` (C1).

## 7. Reversal conditions

If measured metrics show no cache hit rate or rate-limit abuse after pilot launch, Redis may be dropped from staging — removal must not require code-path changes beyond configuration (adapter/toggle), which is the design goal here.
