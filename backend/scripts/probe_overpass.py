"""One-off helper: probe Overpass endpoints with a tiny query."""

import time
import urllib.parse
import urllib.request

QUERY = '[out:json][timeout:50];node["highway"="bus_stop"](6.93,79.84,6.94,79.86);out skel qt;'
ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]
DATA = urllib.parse.urlencode({"data": QUERY}).encode()

for endpoint in ENDPOINTS:
    started = time.time()
    try:
        request = urllib.request.Request(
            endpoint,
            data=DATA,
            headers={"User-Agent": "sljp-probe/0.1"},
        )
        with urllib.request.urlopen(request, timeout=90) as response:
            body = response.read()
        print(f"{endpoint}: HTTP 200, {len(body)} bytes in {time.time() - started:.0f}s")
    except Exception as exc:  # noqa: BLE001 - probe reports, does not raise
        print(f"{endpoint}: {type(exc).__name__} after {time.time() - started:.0f}s")
