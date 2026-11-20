# ADR-0007 — Ingestion framework: adapters, snapshot archive, idempotency and publish/rollback semantics

**Date:** 2026-11-20
**Status:** Accepted
**Deciders:** Coding agent, under the Phase 1.2 task approved by the product owner
**Phase/task context:** Phase 1.2 (source registry and ingestion framework). Refines the rollback semantics of ADR-0006 §2 based on implementation experience.

## 1. Context

Phase 1.2 implements the ingestion framework between the Phase 1.1 schema and the first real source adapter (Phase 1.3). ADR-0006 left rollback as "reverse-diff replay"; implementing it showed the replay procedure cannot be safely specified before real adapters exercise the diff recording. The plan's own rollback semantics (§5.2 rule 7) is "restores the previous dataset/graph pointer and invalidates affected caches" — pointer-based, not data-reconstruction-based.

## 2. Decision

1. **Adapter contract** (`app/modules/data_ingestion/adapters/base.py`): each source implements `SourceAdapter` (`adapter_version`, `fetch() -> FetchResult`, `parse(content, metadata) -> list[RawRecord]`). `RawRecord` = `(external_id, entity_hint, payload)`. The framework is source-agnostic; adding a source means adding an adapter, never editing the framework. The generic local `FileSourceAdapter` is a development/fixture source; real sources (OSM/NSDI/NTC/GTFS) arrive in Phase 1.3.
2. **Snapshot archiving**: `SnapshotArchive` interface; dev implementation `LocalFilesystemArchive` stores content-addressed payloads (`data/raw/<source>/<sha256>.<ext>`) via `RAW_ARCHIVE_DIR`. Object storage (S3-compatible) is a drop-in adapter for staging/production — no ingestion-logic change.
3. **Idempotency** (plan §5.2 rule 2): 
   - unchanged payload (same sha256 for the source) short-circuits the run (`unchanged=true`, no new snapshot, no canonical writes);
   - every parsed record links to exactly one canonical entity via `source_records.canonical_entity_type/canonical_entity_id` (migration `0003_source_record_link`);
   - upsert handlers diff before writing: no-op updates are reported as `unchanged` and produce **no** `dataset_version_entities` diff row; material changes record `added`/`updated`.
4. **Quality gate** (`quality.py`): builtin rules (required fields per entity, Sri Lanka coordinate bounds, supported mode) run before any canonical write; **any failure quarantines the entire run** — run status `quarantined`, canonical tables untouched (verified live: a malformed payload was isolated with `parse failed: JSONDecodeError`).
5. **Publish/rollback semantics** (supersedes ADR-0006 §2 "Rollback semantics" paragraph):
   - `publish(version)`: candidate (or rejected→re-approved) version becomes the single `published` version; the previous active version becomes `superseded`; the `active_dataset` pointer is switched in the same transaction.
   - `rollback(target)`: pointer-flip to any **previously published** (currently `published` or `superseded`) version. Data re-materialisation for the target is an operational runbook step: re-run the target version's sources (their raw snapshots are archived), which regenerates the canonical rows idempotently. Automated reverse-diff replay is **not** implemented in the MVP and remains a documented limitation with the reversal trigger recorded in ADR-0006 §7.
6. **Admin endpoints** (`/api/v1/admin/*`): source registry CRUD-lite, sync trigger, run inspection, version list/publish/rollback. **Mounted only when `app_env` is `local` or `test`**; production exposure requires the Phase 9 OAuth2/OIDC + RBAC work.

## 3. Options considered

| Option | Summary | Consequence |
|---|---|---|
| Adapter-per-source with generic framework (chosen) | New sources are additive | Framework must stay stable; covered by integration tests |
| Reverse-diff replay rollback | Pointer + data reversal in one step | Cannot be proven safe before real adapters; deferred with trigger |
| Per-record quarantine | Isolate only bad records | Mixed-quality publication risk; whole-run quarantine matches "suspicious changes are isolated" (final 09 §8) |

## 4. Rationale

The framework can be fully verified today (checksum dedupe, link bookkeeping, quarantine, publish/rollback pointer semantics) while keeping all source-specific risk behind one interface. This matches the architecture's adapter rule ("Every external dependency must be behind an adapter interface").

## 5. Consequences

- Positive: Phase 1.3's first real adapter is a single class plus a rights review; publication/rollback semantics are test-verified end to end.
- Negative: rollback does not auto-revert canonical data (runbook required); diff quality depends on the upsert handlers' change detection (scalar fields + location WKT comparison in Phase 1.2).
- Deferred: pattern/stop-sequence and transfer upsert handlers (require cross-record matching → Phase 1.3); object-storage archive; moderation.

## 6. Related documents

`docs/adr/ADR-0006`, `docs/product/11_IMPLEMENTATION_PLAN.md` §5.2, `docs/architecture/09_DATA_INGESTION_AND_REFRESH.md`, `docs/architecture/06_SYSTEM_ARCHITECTURE.md` §6.

## 7. Reversal conditions

If real adapters prove reverse-diff replay necessary (e.g., re-running a retired source is impossible), implement replay of `dataset_version_entities` + `data_change_audit` rows via a superseding ADR; the interface seams (upsert handlers recording before/after) are already in place.
