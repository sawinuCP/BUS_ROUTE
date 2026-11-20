# ADR-0006 — Canonical schema, dataset-versioning strategy and PostGIS conventions

**Date:** 2026-11-19
**Status:** Accepted
**Deciders:** Coding agent, under the Phase 1.1 task approved by the product owner
**Phase/task context:** Phase 1.1 (canonical transport data foundation — schema and migrations); resolves the versioning fork flagged in the Phase 0.1 audit (Section 7, item 6)

## 1. Context

Phase 1.1 requires the canonical transport schema. Two decisions had to be made that the knowledge base deliberately left open:

1. **Dataset-versioning strategy** — `docs/architecture/08_DATA_MODEL.md` §4 says: "Choose either immutable versioned network tables or a robust snapshot/blue-green schema approach. Do not mix ad hoc in-place edits with version pointers."
2. **Physical conventions** for PostGIS columns, UUIDs, enums, and constraint naming (the logical model does not fix them).

## 2. Decision

### Versioning: canonical working tables + versioned entity membership + atomic pointer

- **Canonical tables are the single source of truth** for the working network (mutable, with provenance and verification status on every row).
- **`dataset_versions`** records candidate/published/rejected/superseded versions with validation summaries; **`dataset_version_entities`** records per-version diffs (`added`/`updated`/`removed` per entity); **`active_dataset`** is a singleton pointer (CHECK `id = 1`) to the published version used by routing.
- Publication applies validated changes to canonical tables and atomically switches the `active_dataset` pointer inside one transaction. `data_change_audit` captures before/after for every material edit.
- **Rollback semantics:** rollback replays the reverse diff recorded in `dataset_version_entities` + `data_change_audit` (an operational procedure implemented in Phase 1.2/1.3 tooling), because canonical tables are mutable. Immutable per-version network tables (full blue-green duplication) are **deferred** until measured need — the audit trail plus reverse-diff replay satisfies the requirement that "a rollback restores the previous dataset/graph pointer" (implementation plan §5.2 rule 7) without doubling the schema.
- Prohibited: ad-hoc in-place edits that bypass the audit and version records.

### Physical conventions

- **Primary keys:** UUID with `gen_random_uuid()` server default (stable internal IDs; never route numbers or stop names).
- **Timestamps:** `timestamptz`, UTC in storage, `Asia/Colombo` only at display boundaries.
- **Geometry:** PostGIS `geography` columns (SRID 4326) — `POINT` for stops/access points/places/localities, `MULTILINESTRING` for shapes and transfer paths; **GiST index on every geography column**; coordinates may be NULL until verified (unknown facts are represented, not fabricated).
- **Enumerations:** `VARCHAR` + named `CHECK` constraints (`ck_<table>_<name>`) rather than PostgreSQL enums, so values evolve without enum-alter migrations. Verification state everywhere: `unverified` / `reported` / `verified`.
- **Constraint naming:** the convention in `backend/app/platform/db.py` (`fk_…`, `uq_…`, `ix_…`, `ck_…`, `pk_…`) so Alembic diffs are deterministic and reversible.
- **Core invariant:** `UNIQUE (pattern_id, sequence)` on `route_pattern_stops` — the ordered-stop-sequence guarantee routing depends on; plus `CHECK (sequence >= 1)`, `from <> to` transfer endpoints, positive walk distance, validity-range checks, fare-scope requirement, and the `active_dataset` singleton check.
- **Models live in their canonical modules** (`app/modules/{transport,places,data_ingestion,data_quality}/models.py`); `app/platform/db.py` holds the declarative `Base`/mixins only. The registry (`app/platform/model_registry.py`) is the single import point for Alembic.
- **Cross-module FKs** (transport → `data_sources`/`source_records`) are intentional: provenance is infrastructure shared by all content modules.

## 3. Options considered

| Option | Summary | Consequence |
|---|---|---|
| Canonical tables + membership + pointer (chosen) | One copy of data; audited diffs | Rollback is a replay procedure, not a pointer flip alone |
| Immutable versioned network tables (blue-green) | Pointer-flip rollback | Doubles schema size and write complexity now; no measured need yet |
| PostgreSQL enums | DB-enforced values | Every value change needs `ALTER TYPE`; CHECK constraints avoid that |
| `geometry` columns | Flat-space operations | `geography` gives spheroidal metre semantics the planner needs |

## 4. Rationale

The MVP requires auditable, reviewable, reversible data releases without premature complexity. Membership+pointer satisfies every documented gate (idempotent ingestion, atomic publish, audit trail) while keeping one copy of the network. `geography` matches routing semantics (metres on the spheroid).

## 5. Consequences

- Positive: Phase 1.2/1.3 ingestion records diffs and publishes versions without schema changes; routing resolves the active version from `active_dataset`.
- Negative: rollback correctness depends on writing `dataset_version_entities`/`data_change_audit` rows — enforced by convention and Phase 1.2 tooling, not by the database alone.
- Deferred with re-evaluation triggers: full immutable table versioning (if reverse-diff replay proves unreliable), trigram/full-text alias indexes (Phase 2), report/moderation tables (Phase 7).

## 6. Related documents

`docs/architecture/08_DATA_MODEL.md`, `docs/architecture/09_DATA_INGESTION_AND_REFRESH.md`, `docs/product/11_IMPLEMENTATION_PLAN.md` §5.1–§5.2, `docs/audits/phase-0-repository-audit.md` §7, `docs/adr/ADR-0002`.

## 7. Reversal conditions

If review tooling shows reverse-diff replay is unreliable, or concurrent multi-candidate publishing is required, move to immutable versioned network tables via a superseding ADR and a data-migration plan.
