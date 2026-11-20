# ADR-0008 — Walking engine: Valhalla vs GraphHopper

**Date:** 2026-11-20
**Status:** Accepted (owner, 2026-11-20: "Ratify: Valhalla pinned, skip GraphHopper PoC")
**Deciders:** Owner decision by ratification, 2026-11-20, based on PoC evidence
**Phase/task context:** Phase 3 (pedestrian routing & transfer graph), work item 1

## 1. Context

The ratified baseline (ADR-0002) named "Valhalla walking adapter pending
prototype"; the routing engine document §9 requires a walking-engine evaluation
covering pedestrian-graph coverage, footpath/access handling, route quality at
terminals, deployment cost and update process, licence terms, and latency/
reliability. The Phase 2 WP pilot data is live, and Phase 3 needs first/last
mile and transfer walks as explicit path legs.

A Valhalla PoC on the full Sri Lankan OSM extract was completed 2026-11-20
(evidence: `docs/evidence/valhalla-poc-2026-11-20.md`): 3.5.1 builds the whole
country in ~9 minutes into a 126 MB extract; routes between real pilot stops
across three districts succeed with warm latency 52–260 ms; footways, ramps
and named A-road walking corridors appear correctly in maneuvers; a scripted,
fully offline rebuild process exists; and the walking adapter is already wired
behind a vendor-agnostic `WalkingRouter` interface with 6 passing unit tests
and a live-verified `GET /api/v1/walking/route` endpoint.

Not yet done: a side-by-side GraphHopper prototype. The PoC revealed a
reliability issue with the Valhalla `latest` Docker image on this host (issue
I-22: worker segfaults; also took down the local Docker engine once) —
mitigated by pinning 3.5.1.

## 2. Decision

1. **Valhalla 3.5.1 (pinned) is the MVP walking engine**, operated as a
   local self-hosted service defined in the compose stack, behind the
   `WalkingRouter` adapter — no engine types may leak into domain code.
2. **The GraphHopper PoC will not be built now.** Valhalla met every §9
   criterion
   in the PoC; the marginal information from a second prototype is low, and
   Phase 3's remaining scope (shapes import, transfer connectors, field
   verification) is higher value. The adapter interface keeps a later switch
   cheap if field walks expose Valhalla-specific problems.
3. **Operational constraints:** engine versions pinned; tile builds scripted
   and reproducible from the committed build script; tiles stay under
   `data/osm` (gitignored); instructions from the engine are never surfaced
   raw — Phase 5 renders them through deterministic localised templates.
4. **Re-evaluation triggers:** (a) field verification (Phase 1 exit gate walks)
   shows systematic path-quality problems in the pilot corridor; (b) tile
   rebuild or memory footprint becomes unmanageable on target infrastructure;
   (c) a new engine version materially changes behaviour. Any trigger reopens
   this ADR, and the GraphHopper prototype becomes the first follow-up.

## 3. Options considered

| Option | Summary | Consequences |
|---|---|---|
| Valhalla pinned, skip GraphHopper PoC now (proposed) | PoC evidence meets all §9 criteria; adapter already implemented | Fastest path to finishing Phase 3; single-source evidence (risk mitigated by re-evaluation triggers) |
| Require GraphHopper side-by-side before deciding | Strictest reading of routing doc §9 ("prototype Valhalla and compare GraphHopper") | ~1 extra session of work; likely low information gain; delays shapes import and transfer work |
| Custom/graph-based walking router | Deterministic in-house routing on PostGIS | Far more engineering for worse path quality; contradicts ADR-0002 baseline |

## 4. Rationale

§9's evaluation criteria are about evidence, not ritual: the PoC measured
coverage, footpath handling, corridor quality, deployment cost, licence and
latency on real pilot stops. A second engine would duplicate one of seven
criteria (a comparison data point) while the product's binding constraint is
field-verified data quality, which no second engine improves. The decision is
reversible by design because domain code only sees `WalkPlan`.

## 5. Consequences

- `infra/docker/compose.yaml` carries the pinned `valhalla` service; the
  backend reaches it via `VALHALLA_BASE_URL`.
- `backend/app/modules/pedestrian/` owns the adapter (`WalkingRouter`,
  `ValhallaWalkingRouter`, `WalkPlan`, `WalkStep`); tests use canned responses,
  so the unit suite never requires a running engine.
- Missing paths are reported honestly (`no_path_found` /
  `walking_router_unavailable`); nothing is estimated or fabricated.
- Issue I-22 documents the `latest`-image segfault and the mitigation.
