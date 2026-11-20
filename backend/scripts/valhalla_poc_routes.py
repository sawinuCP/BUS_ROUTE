"""Valhalla PoC route tests (Phase 3 work item 1).

Routes walking legs between our actual pilot stops and reports distance,
time, latency and a manoeuvre summary — evidence for the walking-engine ADR.
"""

import json
import time
import urllib.request

VALHALLA = "http://localhost:8002/route"

TESTS = [
    (
        "Fort Bus Stop → Bambalapitiya Junction (city corridor)",
        6.9343064,
        79.8489576,
        6.893302,
        79.8555889,
    ),
    (
        "Colombo Fort → Pasyala Bus Stop (cross-district, ~27 km)",
        6.9332535,
        79.8566929,
        7.1690623,
        80.12411,
    ),
    (
        "Negombo 'Bus #187' stop → Pasyala Bus Stop (NW corridor)",
        7.1660547,
        79.8843734,
        7.1690623,
        80.12411,
    ),
    (
        "Colombo Fort → same point (no-path/self check)",
        6.9343064,
        79.8489576,
        6.9343064,
        79.8489576,
    ),
]


def route(name: str, lat1: float, lon1: float, lat2: float, lon2: float) -> None:
    body = json.dumps(
        {
            "locations": [
                {"lat": lat1, "lon": lon1},
                {"lat": lat2, "lon": lon2},
            ],
            "costing": "pedestrian",
            "directions_options": {"units": "kilometers"},
            "id": name,
        }
    ).encode()
    request = urllib.request.Request(
        VALHALLA, data=body, headers={"Content-Type": "application/json"}
    )
    start = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            payload = json.loads(response.read().decode())
            elapsed_ms = (time.perf_counter() - start) * 1000
    except Exception as exc:  # noqa: BLE001 - PoC: print the failure honestly
        print(f"\n== {name}\n   FAILED: {type(exc).__name__}: {exc}")
        return

    trip = payload["trip"]
    summary = trip["summary"]
    legs = trip["legs"]
    maneuvers = [m for leg in legs for m in leg["maneuvers"]]
    instruction_sample = " ; ".join(m["instruction"] for m in maneuvers[:3] if m.get("instruction"))
    print(f"\n== {name}")
    print(
        f"   distance: {summary['length']:.2f} km | time: {summary['time'] / 60:.1f} min"
        f" | latency: {elapsed_ms:.0f} ms | maneuvers: {len(maneuvers)} | legs: {len(legs)}"
    )
    print(f"   first instructions: {instruction_sample[:180]}")


if __name__ == "__main__":
    for test in TESTS:
        route(*test)
