# Data-quality report — osm-overpass-1e98b698

*Generated:* 2026-11-20T09:34:01.535236+00:00  
*Version status:* `candidate`

## Caveats
- All facts in this version are 'unverified' until field-checked.
- OSM data does not prove operational status of any service.
- direction_id is not derivable from OSM alone; boarding side is unknown.
- Network feasibility only: no timetable or live availability claims.

## Diff by entity type

| Entity type | Changes |
|---|---|
| route | 21 |
| route_pattern | 23 |
| route_pattern_stop | 21 |
| stop | 337 |

## Coverage

- Stops: 437 (437 with coordinates)
- Routes: 38; patterns: 45; ordered calls: 58
- Aliases by language: si: 2
- Transfer connections: 0
- Places: 0

## Checks

| Check | Count | Severity | Note |
|---|---|---|---|
| patterns with fewer than 2 ordered calls | 4 | warning | variants with <2 calls cannot be planned against |
| patterns with no stop calls at all | 36 | warning | usually unresolved member references at ingestion |
| routes without an agency attribution | 38 | info | OSM relations rarely carry operator data; field-verify |
| stops without coordinates | 0 | pass | coordinates unknown until resolved/verified |
| patterns without geometry (shape) | 45 | info | shapes not imported in this phase |
