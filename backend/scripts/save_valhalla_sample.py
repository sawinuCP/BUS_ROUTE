"""Save one full Valhalla /route response as PoC evidence (aggregate only).

Run from repository root:  python backend/scripts/save_valhalla_sample.py
Writes docs/evidence/valhalla-fort-bambalapitiya-route.json.
"""

from __future__ import annotations

import json
import time
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "docs" / "evidence" / "valhalla-fort-bambalapitiya-route.json"

# Colombo Fort Bus Stop → Bambalapitiya Junction (both are real pilot stops,
# verified in the Phase 2 pilot dataset).
LOCATIONS = [{"lat": 6.9343064, "lon": 79.8489576}, {"lat": 6.893302, "lon": 79.8555889}]


def main() -> None:
    body = json.dumps(
        {
            "locations": LOCATIONS,
            "costing": "pedestrian",
            "directions_options": {"units": "kilometers"},
            "id": "poc-fort-bambalapitiya",
        }
    ).encode()
    request = urllib.request.Request(
        "http://localhost:8002/route", data=body, headers={"Content-Type": "application/json"}
    )
    started = time.perf_counter()
    with urllib.request.urlopen(request, timeout=60) as response:
        payload = json.load(response)
    elapsed_ms = (time.perf_counter() - started) * 1000
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    summary = payload["trip"]["summary"]
    print(
        f"saved {OUT.relative_to(REPO)} "
        f"({summary['length']:.2f} km, {summary['time']:.0f} s, {elapsed_ms:.0f} ms)"
    )


if __name__ == "__main__":
    main()
