# ADR-0001 — Documentation layout, canonical phase numbering and user-story register

**Date:** 2026-11-19
**Status:** Accepted (product-owner decision: "consolidate")
**Deciders:** Product owner
**Phase/task context:** Phase 0.2 (resolving audit findings GAP-002, GAP-003, GAP-005 from `docs/audits/phase-0-repository-audit.md`)

## 1. Context

The Phase 0.1 audit found the knowledge base split across `Docs/Product docs/`, `Docs/sri_lanka_journey_planner_final_architecture/` and root `IMPLEMENTATION_PLAN.md`; the root README indexed only the ten research documents. Three different phase-numbering schemes and two user-story registers coexist. Coding agents are scoped by phase/task IDs (implementation plan §12.1) and must locate companion documents (§0.1), so ambiguity causes wrong-scope or wrong-document work.

## 2. Decision

1. **Documentation layout (owner chose "consolidate"):** all documentation moves under `docs/`:
   - `docs/product/` — research product set `00`–`09` **plus** the implementation plan as `docs/product/11_IMPLEMENTATION_PLAN.md` (was root `IMPLEMENTATION_PLAN.md`);
   - `docs/architecture/` — final architecture package `00`–`17`, `README.md`, `MANIFEST.json`;
   - `docs/adr/` — decision records; `docs/audits/` — phase audit reports.
   This matches the layout suggested by implementation plan §4.1; §0.1's "docs/product/ or equivalent" is hereby satisfied literally.
2. **Canonical phase numbering:** the implementation plan's Phases 0–10 (`docs/product/11_IMPLEMENTATION_PLAN.md` §7) are the single canonical scheme for task scoping and status reporting. Mapping to the other schemes: architecture package `16_ROADMAP_AND_ACCEPTANCE_GATES.md` Phases 0–6 are a compressed view (its Phase 0 "product/data validation" ≈ plan Phase 1 pilot/data work and Phase 2 spikes; its Phase 1 "platform foundation" ≈ plan Phase 0.3–0.4; its Phases 2–5 ≈ plan Phases 1, 3–7/8; its Phase 6 ≈ plan Phases 8–10); product `08_SCOPE_ROADMAP_AND_RISKS.md` Phases 0–5 likewise map onto plan Phases 1–9. The implementation plan governs.
3. **Canonical backend module map:** implementation plan §3.3 module names (`places`, `transport`, `pedestrian`, `transfers`, `routing`, `itineraries`, `journey_sessions`, `data_ingestion`, `data_quality`, `reports`, `ai_assistance`, `platform`) are canonical for the backend skeleton. Architecture-package `06` §3 names (`transport_network`, `journeys`, `data_sources`, `fares`, `identity`, `assistant`) are conceptual aliases; `transport_network` → `transport`, `data_sources` → `data_ingestion`, `journeys` → `journey_sessions` + `itineraries`, `fares` → part of `transport` until fares become a standalone module, `identity` → part of `platform` until accounts are implemented, `assistant` → `ai_assistance`.
4. **Canonical user-story register:** `docs/architecture/04_USER_STORIES.md` (US-001–US-039, with Given/When/Then acceptance criteria) is the authoritative register for development and testing. `docs/product/05_USER_STORIES_AND_FLOWS.md` (US-01–US-35) remains valuable research/context and is not deleted. The delivery-phase mapping in implementation plan §10 (which references the old IDs) applies as follows: US-01→US-001–005, US-02→US-005/US-038, US-03→US-003, US-04→US-001/004, US-05→US-002/US-038, US-06–07→US-006/US-007 area, US-08–12→US-006–US-010/US-012, US-13–17→US-013–US-017, US-18–20→US-018–US-020, US-21–26→US-021–US-026, US-27–31→US-027–US-031/US-037–039, US-32–35→US-032–US-035. Where numbers diverge, the authoritative register's content governs.

## 3. Options considered

| Option | Summary | Consequences |
|---|---|---|
| Consolidate under `docs/` (chosen) | Matches plan §4.1; single tree, clean indices | Requires one-time move; all internal cross-references audited once |
| Keep split locations and amend plan §0.1 | No file moves | Three roots persist; README/agent lookups remain error-prone |

## 4. Rationale

The plan itself specifies the `docs/product/` layout; the owner approved consolidation. A single canonical phase scheme and story register restore the traceability the plan's governance rules require ("Every public feature has a user story, acceptance criteria and tests").

## 5. Consequences

- Positive: agents resolve documents and phase IDs deterministically; README indexes everything; story traceability has one source of truth.
- Negative: historical references to old paths (e.g., audit report references to `Docs\...`) remain accurate only as of the audit date; Git history preserves the mapping.
- No content of the moved documents was altered except the supersession note on `docs/product/06_TECHNICAL_ARCHITECTURE.md` (see that note and GAP-004).

## 6. Related documents

`docs/audits/phase-0-repository-audit.md` (GAP-002/003/005), `docs/product/11_IMPLEMENTATION_PLAN.md` §0.1, §4.1, §7, §10, §12.1, `docs/architecture/04_USER_STORIES.md`, `docs/product/05_USER_STORIES_AND_FLOWS.md`.

## 7. Reversal conditions

If a future tooling choice (e.g., a monorepo generator or separate backend/mobile repositories) requires a different docs topology, supersede this ADR rather than moving documents ad hoc.
