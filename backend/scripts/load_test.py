"""Concurrency load test against a running backend (Phase 9, plan item 4).

Drives the API with realistic pilot traffic — representative stop-to-stop
plans (ends of the longest patterns, as in `plan_benchmark.py`), stop
search and health checks — at the configured concurrency for a fixed
duration, then reports throughput, latency percentiles and the status
distribution, and writes the evidence report to `docs/evidence/`.

Usage (from backend/, with the Docker stack running):

    python scripts/load_test.py [--base-url http://localhost:8000]
        [--users 10] [--seconds 20]

Honest scope: localhost, no TLS, single node, local Postgres — this
measures the application's concurrency behaviour and establishes a
relative baseline (compare against re-runs), not internet-scale numbers.
"""

from __future__ import annotations

import argparse
import asyncio
import random
import statistics
import sys
import time
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text  # noqa: E402

from app.platform.db import get_session_factory  # noqa: E402


async def _representative_pairs(limit: int) -> list[tuple[str, str]]:
    """Stop ids for the ends of the longest route patterns (direct rides)."""
    factory = get_session_factory()
    async with factory() as session:
        rows = (
            await session.execute(
                text(
                    "WITH spans AS ("
                    "  SELECT rp.id,"
                    "    (SELECT ps2.stop_id FROM route_pattern_stops ps2"
                    "      WHERE ps2.pattern_id = rp.id"
                    "      ORDER BY ps2.sequence ASC LIMIT 1) AS first_stop,"
                    "    (SELECT ps3.stop_id FROM route_pattern_stops ps3"
                    "      WHERE ps3.pattern_id = rp.id"
                    "      ORDER BY ps3.sequence DESC LIMIT 1) AS last_stop"
                    "  FROM route_patterns rp"
                    "  JOIN route_pattern_stops ps ON ps.pattern_id = rp.id"
                    "  GROUP BY rp.id"
                    "  HAVING count(*) >= 2"
                    ") SELECT first_stop::text, last_stop::text"
                    "  FROM spans ORDER BY random() LIMIT :limit"
                ),
                {"limit": limit},
            )
        ).all()
    return [(str(r[0]), str(r[1])) for r in rows]


def _percentiles(values_ms: list[float]) -> dict[str, float]:
    ordered = sorted(values_ms)
    if not ordered:
        return {}
    return {
        "p50": statistics.median(ordered),
        "p90": ordered[min(len(ordered) - 1, int(round(0.9 * (len(ordered) - 1))))],
        "p99": ordered[min(len(ordered) - 1, int(round(0.99 * (len(ordered) - 1))))],
        "max": ordered[-1],
    }


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--users", type=int, default=10)
    parser.add_argument("--seconds", type=int, default=20)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    rng = random.Random(args.seed)

    pairs = await _representative_pairs(min(20, max(4, args.users)))
    if not pairs:
        print("no patterns with >= 2 calls in the database; nothing to load")
        return 1
    print(f"loaded {len(pairs)} representative stop pairs")

    latencies: dict[str, list[float]] = {}
    statuses: Counter[str] = Counter()
    errors: list[str] = []
    deadline = time.monotonic() + args.seconds
    lock = asyncio.Lock()

    async def user(worker: int, client: httpx.AsyncClient) -> None:
        """One concurrent user: mixed plan/search/health with think time."""
        nonlocal latencies, statuses, errors
        plan_pair = pairs[worker % len(pairs)]
        rng = random.Random(args.seed + worker)
        while time.monotonic() < deadline:
            scenario = rng.random()
            start = time.perf_counter()
            try:
                if scenario < 0.5:
                    response = await client.post(
                        "/api/v1/journeys/plan",
                        json={
                            "origin": {"type": "stop", "stop_id": plan_pair[0]},
                            "destination": {"type": "stop", "stop_id": plan_pair[1]},
                            "preferences": {"max_transfers": 1},
                            "save": False,
                        },
                        timeout=30.0,
                    )
                    label = "plan"
                elif scenario < 0.8:
                    response = await client.get("/api/v1/places/search?q=CO", timeout=15.0)
                    label = "search"
                else:
                    response = await client.get("/api/v1/health", timeout=10.0)
                    label = "health"
            except Exception as exc:  # noqa: BLE001 - load failures are data
                async with lock:
                    errors.append(type(exc).__name__)
                continue
            elapsed_ms = (time.perf_counter() - start) * 1000.0
            async with lock:
                statuses[f"{label}:{response.status_code}"] += 1
                latencies.setdefault(label, []).append(elapsed_ms)
            # Small randomized think time, like a real traveller browsing.
            await asyncio.sleep(rng.uniform(0.05, 0.2))

    async with httpx.AsyncClient(base_url=args.base_url) as client:
        warm = await client.get("/api/v1/health", timeout=10.0)
        print(f"warm-up health: {warm.status_code}")
        started = time.perf_counter()
        await asyncio.gather(*(user(i, client) for i in range(args.users)))
        wall = time.perf_counter() - started
    total = sum(len(v) for v in latencies.values())
    rps = total / wall if wall else 0.0
    print(f"\nrequests: {total} · wall {wall:.1f}s · {rps:.1f} req/s · users {args.users}")
    print("status distribution:")
    for key, count in sorted(statuses.items()):
        print(f"  {key}: {count}")
    if errors:
        print("transport errors:", dict(Counter(errors)))
    print("\nlatency per scenario (ms):")
    for label in sorted(latencies):
        percentiles = _percentiles(latencies[label])
        formatted = " · ".join(f"{name} {value:.0f}" for name, value in percentiles.items())
        print(f"  {label}: {formatted}")

    evidence = Path(__file__).resolve().parents[2] / "docs" / "evidence"
    evidence.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y-%m-%d")
    lines = [
        f"# Load baseline — {stamp} (Phase 9 plan item 4)",
        "",
        f"- Target: `{args.base_url}` (Docker stack: FastAPI + Postgres +"
        " Redis, single node, localhost, no TLS).",
        f"- Workload: {args.users} concurrent users for {args.seconds}s — mix"
        " 50% stop-to-stop plans (representative pattern-end pairs,"
        " cache-served after the first), 30% stop search, 20% health;"
        " 50–200 ms think time.",
        f"- Requests: **{total}** · wall {wall:.1f}s · throughput **{rps:.1f} req/s**.",
        f"- Transport errors: {len(errors)}"
        + (f" ({dict(Counter(errors))})" if errors else ""),
        "",
        "## Status distribution",
        "",
        "| scenario:status | count |",
        "|---|---|",
        *(f"| {key} | {count} |" for key, count in sorted(statuses.items())),
        "",
        "## Latency per scenario (ms)",
        "",
        "| scenario | p50 | p90 | p99 | max |",
        "|---|---|---|---|---|",
        *(
            f"| {label} | "
            + " | ".join(f"{value:.0f}" for value in _percentiles(latencies[label]).values())
            + " |"
            for label in sorted(latencies)
        ),
        "",
        "## Targets (from this baseline + the plan benchmark)",
        "",
        "- Zero 5xx under this workload (any 500 is a regression).",
        "- Plan p50 at or below the cache-hit baseline in"
        " `docs/evidence/plan-benchmark-2026-11-22.md`; alert when p95 doubles.",
        "- Re-run this script after dataset growth or planner changes and"
        " diff against this report.",
        "",
        f"_Generated {datetime.now(UTC).isoformat()} by `backend/scripts/load_test.py`._",
    ]
    path = evidence / f"load-baseline-{stamp}.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nevidence written: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

