"""Performance baseline for the deterministic planner (Phase 4 exit criterion).

Runs representative stop-to-stop plans against the real dev database and
reports latency percentiles for (a) full planner computation and (b) a cache
hit through the Redis plan cache (when Redis is reachable). Targets are set
from the observed baseline and recorded in
`docs/evidence/plan-benchmark-2026-11-22.md`.

Usage (from backend/):
    python scripts/plan_benchmark.py [--pairs 5] [--iterations 10]
"""

from __future__ import annotations

import argparse
import asyncio
import statistics
import sys
import time
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text  # noqa: E402

from app.modules.pedestrian.router import get_walking_router  # noqa: E402
from app.modules.planner import (  # noqa: E402
    Endpoint,
    JourneyPlanner,
    PlanningConstraints,
    load_network,
    serialize_result,
)
from app.modules.planner.cache import normalized_request_key  # noqa: E402
from app.platform.db import get_session_factory  # noqa: E402
from app.platform.plan_cache import RedisPlanCache  # noqa: E402
from app.platform.redis_client import get_redis  # noqa: E402


@asynccontextmanager
async def _session() -> AsyncIterator[Any]:
    factory = get_session_factory()
    async with factory() as session:
        yield session


async def _representative_pairs(limit: int) -> list[tuple[uuid.UUID, uuid.UUID, str]]:
    """Origin/destination pairs: ends of the longest route patterns."""
    async with _session() as session:
        rows = (
            await session.execute(
                text(
                    "WITH spans AS ("
                    "  SELECT rp.id, tr.route_code, count(*) AS calls,"
                    "    (SELECT ps2.stop_id FROM route_pattern_stops ps2"
                    "      WHERE ps2.pattern_id = rp.id"
                    "      ORDER BY ps2.sequence ASC LIMIT 1) AS first_stop,"
                    "    (SELECT ps3.stop_id FROM route_pattern_stops ps3"
                    "      WHERE ps3.pattern_id = rp.id"
                    "      ORDER BY ps3.sequence DESC LIMIT 1) AS last_stop"
                    "  FROM route_patterns rp"
                    "  JOIN transport_routes tr ON tr.id = rp.route_id"
                    "  JOIN route_pattern_stops ps ON ps.pattern_id = rp.id"
                    "  GROUP BY rp.id, tr.route_code"
                    "  HAVING count(*) >= 2"
                    ") SELECT first_stop, last_stop, route_code || '/' || id::text"
                    "  FROM spans ORDER BY calls DESC LIMIT :limit"
                ),
                {"limit": limit},
            )
        ).all()
    return [(uuid.UUID(str(r[0])), uuid.UUID(str(r[1])), str(r[2])) for r in rows]


def _percentiles(values_ms: list[float]) -> dict[str, float]:
    ordered = sorted(values_ms)
    return {
        "min": ordered[0],
        "p50": statistics.median(ordered),
        "p95": ordered[min(len(ordered) - 1, int(round(0.95 * (len(ordered) - 1))))],
        "max": ordered[-1],
    }


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pairs", type=int, default=5)
    parser.add_argument("--iterations", type=int, default=10)
    args = parser.parse_args()

    pairs = await _representative_pairs(args.pairs)
    if not pairs:
        print("no patterns with >= 2 calls in the database; nothing to benchmark")
        return 1

    constraints = PlanningConstraints(max_transfers=1)

    async with _session() as session:
        network = await load_network(session)
        walking_router = get_walking_router()
        print(f"network version: {network.version_label}")
        print(
            f"stops={len(network.stops)} patterns={len(network.patterns)}"
            f" transfers={len(network.transfers)}"
        )

        # Warm-up (imports, engine pool, first plan).
        warm_origin, warm_dest, _ = pairs[0]
        planner = JourneyPlanner(network, walking_router)
        await planner.plan(
            Endpoint(kind="stop", stop_id=warm_origin),
            Endpoint(kind="stop", stop_id=warm_dest),
            constraints,
        )

        miss_ms: list[float] = []
        labels: list[str] = []
        for origin, dest, label in pairs:
            planner = JourneyPlanner(network, walking_router)
            result = None
            for _ in range(args.iterations):
                start = time.perf_counter()
                result = await planner.plan(
                    Endpoint(kind="stop", stop_id=origin),
                    Endpoint(kind="stop", stop_id=dest),
                    constraints,
                )
                miss_ms.append((time.perf_counter() - start) * 1000.0)
            labels.append(f"{label}: {result.status if result else '?'}")

        # Cache-hit latency through the real Redis cache (skip when down).
        cache = RedisPlanCache(get_redis(), ttl_seconds=300)
        payload = serialize_result(
            await JourneyPlanner(network, walking_router).plan(
                Endpoint(kind="stop", stop_id=pairs[0][0]),
                Endpoint(kind="stop", stop_id=pairs[0][1]),
                constraints,
            )
        )
        key = normalized_request_key(
            network.version_label,
            {"type": "stop", "stop_id": str(pairs[0][0])},
            {"type": "stop", "stop_id": str(pairs[0][1])},
            {
                "priority": "fastest",
                "max_walking_m": 1500,
                "max_transfers": 1,
                "allowed_modes": ["bus"],
                "require_verified_transfers": False,
            },
        )
        await cache.set_json(key, payload, 300)
        hit_ms: list[float] = []
        redis_ok = True
        for _ in range(args.iterations):
            start = time.perf_counter()
            cached = await cache.get_json(key)
            hit_ms.append((time.perf_counter() - start) * 1000.0)
            if cached is None:
                redis_ok = False
                break

    miss_p = _percentiles(miss_ms)
    print("\nrepresentative pairs:")
    for label in labels:
        print(f"  {label}")
    print(f"\nplanner (cache miss), n={len(miss_ms)}:")
    for name, value in miss_p.items():
        print(f"  {name}: {value:.1f} ms")

    if redis_ok and hit_ms:
        hit_p = _percentiles(hit_ms)
        print(f"\ncache hit via Redis, n={len(hit_ms)}:")
        for name, value in hit_p.items():
            print(f"  {name}: {value:.1f} ms")
    else:
        print("\ncache hit: Redis unreachable — skipped (graceful degradation)")

    evidence = Path(__file__).resolve().parents[2] / "docs" / "evidence"
    evidence.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Planner performance baseline — 2026-11-22 (Phase 4 exit criterion)",
        "",
        f"- Network: `{network.version_label}` — {len(network.stops)} stops,"
        f" {len(network.patterns)} patterns with ordered stop calls (of the"
        " imported patterns; patterns without usable call sequences are QA"
        f" diagnostics), {len(network.transfers)} transfer connectors"
        " (both directions).",
        f"- Workload: {len(pairs)} representative stop-to-stop pairs (ends of the"
        f" longest patterns), {args.iterations} iterations each, warm engine,"
        " stop endpoints (no walking-engine calls), in-process planner (no HTTP"
        " layer).",
        "",
        "## Observed baseline (cache miss = full deterministic computation)",
        "",
        "| metric | ms |",
        "|---|---|",
        *(f"| {name} | {value:.1f} |" for name, value in miss_p.items()),
    ]
    if redis_ok and hit_ms:
        lines += [
            "",
            "## Observed baseline (cache hit through Redis)",
            "",
            "| metric | ms |",
            "|---|---|",
            *(f"| {name} | {value:.1f} |" for name, value in _percentiles(hit_ms).items()),
        ]
    lines += [
        "",
        "## Targets set from this baseline",
        "",
        "- Stop-to-stop plan (cache miss): alert if p95 doubles from the observed"
        " value above (regression signal).",
        "- Cache hit: **p95 < 20 ms** (single Redis round-trip + JSON decode).",
        "- Coordinate endpoints add walking-engine calls: budget Valhalla"
        " latency separately (52–260 ms per leg,"
        " `docs/evidence/valhalla-poc-2026-11-20.md`).",
        "- Re-measure after any planner algorithm change or dataset growth"
        " (Western Province → island scale).",
        "",
        f"_Generated {datetime.now(UTC).isoformat()} by `backend/scripts/plan_benchmark.py`._",
    ]
    path = evidence / "plan-benchmark-2026-11-22.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nevidence written: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
