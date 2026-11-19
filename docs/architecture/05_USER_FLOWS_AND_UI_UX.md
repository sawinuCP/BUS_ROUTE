# 05 — User Flows and UI/UX Design

## Flow A — Plan a journey
1. User chooses current location or searches for an origin.
2. User searches for a destination.
3. App presents ambiguous place candidates for confirmation.
4. User optionally selects preferences: less walking, fewer transfers, simplest or fastest estimated.
5. Client calls `POST /api/v1/journeys/plan`.
6. Backend resolves canonical entities and active dataset version.
7. Routing engine generates feasible candidates and removes dominated options.
8. API returns legs, geometry, instructions, estimates, warnings and freshness.
9. User compares options and opens a detailed itinerary.
10. User may start or save the selected itinerary.

Failure states: no path in coverage; ambiguous origin; unsupported mode; walking engine unavailable; incomplete transfer; stale source; API timeout. Never silently turn a failed leg into a straight-line instruction.

## Flow B — Follow an itinerary
1. User starts selected plan.
2. App stores a local journey snapshot and dataset version.
3. Active screen shows one current action.
4. User walks to the named boarding point.
5. App may use GPS to suggest arrival, but user can confirm manually.
6. App shows route/direction/boarding location.
7. User confirms boarding.
8. App shows destination alighting point and optional progress.
9. User confirms alighting.
10. App presents transfer walk and next boarding instruction.
11. Final walk guides to destination access point.
12. User completes or reports an issue.

## Flow C — Re-plan after deviation
1. App detects likely deviation only after accuracy and persistence checks.
2. User sees a non-alarming prompt.
3. User confirms current location or selects a point manually.
4. Planner generates new supported options.
5. User selects a new plan.
6. Original plan remains available for reference.

## Flow D — Report incorrect data
1. User taps “Report a problem” on a stop/leg.
2. App preselects entity ID and active dataset version.
3. User chooses category: wrong stop, route, direction, transfer, name, access point, other.
4. Optional note/location/photo is collected with consent.
5. Report is stored as pending.
6. Reviewer checks report against sources/field evidence.
7. Approved changes enter the staging pipeline.
8. Validated candidate is published and report is resolved.

## Flow E — Source refresh
1. Scheduler selects due source.
2. Adapter checks ETag, last-modified, feed version or content hash where supported.
3. Fetch raw payload and archive it.
4. Parse and normalise into staging tables.
5. Compare with current source snapshot.
6. Validate schema, IDs, geometry, stop order, referential integrity and anomaly thresholds.
7. Quarantine suspicious changes.
8. Build candidate dataset version.
9. Reviewer or automated policy approves.
10. Atomically publish active-version pointer.
11. Run smoke tests and monitor.
12. Roll back if critical post-publish checks fail.

## UI structure
- **Home/search:** origin, destination, recent searches, map selection.
- **Results:** route cards with estimated duration, walk distance, transfer count and quality.
- **Itinerary detail:** ordered legs, map, stop names, directions and data caveats.
- **Active journey:** current action, progress, confirm/pause/re-plan/report controls.
- **Saved journeys:** saved intents and refreshed plans.
- **Settings:** language, privacy, permissions and accessibility preferences.
- **Admin console:** sources, sync history, candidate changes, reports, validation and releases.

## UX rules
- Always show the next action prominently in active mode.
- Pair map directions with text.
- Use plain local terminology and explain unfamiliar terms.
- Distinguish verified, estimated, reported and unknown.
- Never rely on colour alone.
- Avoid excessive GPS prompts.
- Make manual controls available.
- Keep text readable outdoors and support screen readers.
