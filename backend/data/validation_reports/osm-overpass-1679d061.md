# Data-quality report — osm-overpass-1679d061

*Generated:* 2026-11-20T15:04:50.814550+00:00  
*Version status:* `candidate`

## Caveats
- All facts in this version are 'unverified' until field-checked.
- OSM data does not prove operational status of any service.
- direction_id is not derivable from OSM alone; boarding side is unknown.
- Network feasibility only: no timetable or live availability claims.

## Diff by entity type

| Entity type | Changes |
|---|---|
| route | 38 |
| route_pattern | 45 |
| route_pattern_stop | 58 |
| route_shape | 41 |
| stop | 432 |
| stop_access_point | 432 |

## Coverage

- Stops: 432 (432 with coordinates); stop access points: 432
- Routes: 38; patterns: 45; ordered calls: 58; patterns with a shape: 41 (41 shape geometries)
- Aliases by language: si: 2
- Transfer connections: 19
- Places: 0

## Checks

| Check | Count | Severity | Note |
|---|---|---|---|
| patterns with fewer than 2 ordered calls | 4 | warning | variants with <2 calls cannot be planned against |
| patterns with no stop calls at all | 36 | warning | usually unresolved member references at ingestion |
| routes without an agency attribution | 38 | info | OSM relations rarely carry operator data; field-verify |
| stops without coordinates | 0 | pass | coordinates unknown until resolved/verified |
| patterns without geometry (shape) | 4 | info | truncated relations or members without way geometry; field-verify |
