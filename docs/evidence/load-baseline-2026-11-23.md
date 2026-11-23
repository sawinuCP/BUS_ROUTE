# Load baseline — 2026-11-23 (Phase 9 plan item 4)

- Target: `http://localhost:8000` (Docker stack: FastAPI + Postgres + Redis, single node, localhost, no TLS).
- Workload: 10 concurrent users for 20s — mix 50% stop-to-stop plans (representative pattern-end pairs, cache-served after the first), 30% stop search, 20% health; 50–200 ms think time.
- Requests: **799** · wall 19.3s · throughput **41.3 req/s**.
- Transport errors: 0

## Status distribution

| scenario:status | count |
|---|---|
| health:200 | 156 |
| plan:200 | 402 |
| search:200 | 241 |

## Latency per scenario (ms)

| scenario | p50 | p90 | p99 | max |
|---|---|---|---|---|
| health | 22 | 94 | 256 | 296 |
| plan | 116 | 364 | 932 | 936 |
| search | 41 | 193 | 574 | 856 |

## Targets (from this baseline + the plan benchmark)

- Zero 5xx under this workload (any 500 is a regression).
- Plan p50 at or below the cache-hit baseline in `docs/evidence/plan-benchmark-2026-11-22.md`; alert when p95 doubles.
- Re-run this script after dataset growth or planner changes and diff against this report.

_Generated 2026-11-23T08:38:12.750378+00:00 by `backend/scripts/load_test.py`._
