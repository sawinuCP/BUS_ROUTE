# Planner performance baseline — 2026-11-22 (Phase 4 exit criterion)

- Network: `osm-overpass-1679d061` — 432 stops, 9 patterns with ordered stop calls (of the imported patterns; patterns without usable call sequences are QA diagnostics), 38 transfer connectors (both directions).
- Workload: 5 representative stop-to-stop pairs (ends of the longest patterns), 10 iterations each, warm engine, stop endpoints (no walking-engine calls), in-process planner (no HTTP layer).

## Observed baseline (cache miss = full deterministic computation)

| metric | ms |
|---|---|
| min | 0.1 |
| p50 | 0.1 |
| p95 | 3.0 |
| max | 3.8 |

## Observed baseline (cache hit through Redis)

| metric | ms |
|---|---|
| min | 0.6 |
| p50 | 0.6 |
| p95 | 0.7 |
| max | 0.7 |

## Targets set from this baseline

- Stop-to-stop plan (cache miss): alert if p95 doubles from the observed value above (regression signal).
- Cache hit: **p95 < 20 ms** (single Redis round-trip + JSON decode).
- Coordinate endpoints add walking-engine calls: budget Valhalla latency separately (52–260 ms per leg, `docs/evidence/valhalla-poc-2026-11-20.md`).
- Re-measure after any planner algorithm change or dataset growth (Western Province → island scale).

_Generated 2026-11-22T07:31:36.922558+00:00 by `backend/scripts/plan_benchmark.py`._
