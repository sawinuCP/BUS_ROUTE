# Valhalla PoC evidence — Phase 3, work item 1 (2026-11-20)

**Purpose:** evidence for the walking-engine decision (ADR-0008, routing engine
doc §9 evaluation criteria). All routes were run against our **real pilot
stops** from the Phase 2 WP pilot dataset, not synthetic points.

## Environment

| Item | Value |
| --- | --- |
| Engine | Valhalla `3.5.1` (pinned — `latest` segfaults on this host, issue I-22) |
| Input | Geofabrik Sri Lanka snapshot `data/osm/sri-lanka-261119.osm.pbf` (138 MB) |
| Build | `valhalla_build_tiles` → `valhalla_build_extract`, ~9 min total, exit 0 |
| Tile extract | `data/osm/valhalla/tiles.tar` — **125.9 MB** (141 tiles) |
| Service | `valhalla_service` (compose `valhalla` service, port 8002) |
| Costing | `pedestrian`, `directions_options.units = kilometers` |
| Host | Windows 11, Docker Desktop / WSL2, 15.7 GB RAM |

Reproduce with `python backend/scripts/build_valhalla_tiles.py`, then
`docker compose -f infra/docker/compose.yaml up -d valhalla`.

## Route tests (results exactly as observed)

| # | From → To (real pilot stops) | Distance | Time | Latency | Maneuvers |
| --- | --- | --- | --- | --- | --- |
| 1 | Fort Bus Stop → Bambalapitiya Junction | 5.42 km | 63.8 min | 486 ms (cold), 52 ms (warm) | 16 |
| 2 | Colombo Fort → Pasyala Bus Stop (cross-district) | 42.55 km | 501.0 min | 261 ms | 17 |
| 3 | Negombo 'Bus #187' stop → Pasyala Bus Stop (NW corridor) | 30.53 km | 359.3 min | 75 ms | 21 |
| 4 | Colombo Fort → same point (self route) | 0.00 km | 0.0 min | 11 ms | 2 |

All four returned HTTP 200 with a complete `trip` object; no failures observed
in this run. One full response is committed as a sample:
`valhalla-fort-bambalapitiya-route.json`.

## Evaluation against routing-engine doc §9

- **Pedestrian graph coverage:** entire country built in one pass; routes
  succeed between three districts (Colombo, Gampaha, Kegalle corridors).
- **Footpaths/crossings/access:** maneuvers include `walkway` legs and
  pedestrian ramps ("Stay straight to take the ramp") — OSM foot infrastructure
  is present and used.
- **Route quality around terminals:** test 1 follows Olcott Mawatha → Lotus
  Road → Galle Face → Galle Road, the real walking corridor between Fort and
  Bambalapitiya; speed ≈ 5.1 km/h, plausible for walking time.
- **Deployment cost/update process:** single pinned container + a 126 MB
  tar extract; rebuild is a scripted, ~9-minute, fully offline process
  (no network calls at build time).
- **Licence/data terms:** derived solely from OSM data (ODbL) — same source
  and licence as the rest of the pilot data; aggregate outputs committed as
  evidence only.
- **Latency/reliability:** warm responses 52–260 ms; service survived the
  whole PoC run. `latest` image reliability failure is tracked as I-22 and
  mitigated by pinning 3.5.1.

## Caveats (honest limits of this PoC)

- GraphHopper was **not** prototyped in this session — see ADR-0008 for how
  that affects the decision.
- Long pedestrian "routes" (tests 2–3, 30–43 km) are technically valid but not
  realistic walking legs; the planner (Phase 4) must bound walk-leg distance
  and treat these as coverage evidence only.
- No elevation data was included; Colombo is mostly flat but Kandy-region
  walks will need elevation for plausible time estimates (config already has
  an `additional_data.elevation` slot).
- Instructions are English Valhalla strings; Phase 5 must map them to
  deterministic localised templates — raw engine text must not be surfaced.

## API wiring (verified live)

`GET /api/v1/walking/route?lon_from=79.8489576&lat_from=6.9343064&lon_to=79.8555889&lat_to=6.893302`
returned `status=ok`, 5,418 m, 3,828.9 s, 16 steps through the backend adapter.
