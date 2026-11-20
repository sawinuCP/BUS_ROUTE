"""Generate candidate transfer connections (Phase 3, ADR-0008).

Proximity-proposed stop pairs (default 300 m interchange radius, both stops
already served, no shared route pattern) are routed through the walking engine
and stored as `unverified` `transfer_connections` rows with real walk distance,
duration and geometry. Nothing is published or marked verified — the moderation
flow and field walks do that (data model doc §3; D-1).

Requires: the walking engine running (compose `valhalla` service), a migrated
database with ingested stops/patterns/access points.

Run inside the backend container (or with DATABASE_URL + VALHALLA_BASE_URL set):

    python scripts/generate_transfer_candidates.py [--radius-m 300] [--max-pairs 500] [--dry-run]
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.modules.pedestrian import get_walking_router  # noqa: E402
from app.modules.transfers import generate_transfer_candidates  # noqa: E402
from app.platform.config import get_settings  # noqa: E402
from app.platform.db import get_session_factory  # noqa: E402


async def run(radius_m: float, max_pairs: int, dry_run: bool) -> int:
    session = get_session_factory()()
    added = already = no_path = 0
    try:
        outcomes = await generate_transfer_candidates(
            session,
            get_walking_router(),
            radius_m=radius_m,
            max_pairs=max_pairs,
        )
        for outcome in outcomes:
            if outcome.result == "walk_routed":
                added += 1
                print(
                    f"  candidate: {outcome.walk_distance_m} m /"
                    f" {outcome.walk_seconds} s"
                    f" (straight {outcome.pair.straight_line_m:.0f} m)"
                )
            elif outcome.result == "already_connected":
                already += 1
            else:
                no_path += 1
        if dry_run:
            await session.rollback()
            print("dry-run: rolled back, nothing written")
        else:
            await session.commit()
            print(f"committed {added} candidate connector(s)")
    finally:
        await session.close()
    print(
        f"summary: {added} routed, {already} already connected, {no_path} without a walkable path"
    )
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--radius-m", type=float, default=300.0)
    parser.add_argument("--max-pairs", type=int, default=500)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    settings = get_settings()
    print(
        f"generating transfer candidates (radius {args.radius_m} m,"
        f" engine {settings.valhalla_base_url})"
    )
    raise SystemExit(asyncio.run(run(args.radius_m, args.max_pairs, args.dry_run)))


if __name__ == "__main__":
    main()
