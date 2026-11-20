# Data-quality report — osm-overpass-4e442b17

*Generated:* 2026-11-20T07:21:51.937930+00:00  
*Version status:* `candidate`

## Caveats
- All facts in this version are 'unverified' until field-checked.
- OSM data does not prove operational status of any service.
- direction_id is not derivable from OSM alone; boarding side is unknown.
- Network feasibility only: no timetable or live availability claims.

## Diff by entity type

| Entity type | Changes |
|---|---|
| route | 17 |
| route_pattern | 22 |
| route_pattern_stop | 37 |
| stop | 100 |

## Coverage

- Stops: 100 (100 with coordinates)
- Routes: 17; patterns: 22; ordered calls: 37
- Aliases by language: 
- Transfer connections: 0
- Places: 0

## Checks

| Check | Count | Severity | Note |
|---|---|---|---|
| patterns with fewer than 2 ordered calls | 3 | warning | variants with <2 calls cannot be planned against |
| patterns with no stop calls at all | 15 | warning | usually unresolved member references at ingestion |
| routes without an agency attribution | 17 | info | OSM relations rarely carry operator data; field-verify |
| stops without coordinates | 0 | pass | coordinates unknown until resolved/verified |
| patterns without geometry (shape) | 22 | info | shapes not imported in this phase |
