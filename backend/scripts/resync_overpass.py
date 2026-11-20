"""One-off helper: re-register (if needed) and re-sync the Overpass source."""

import json
import urllib.request

BASE = "http://localhost:8000/api/v1/admin"


def call(path: str, method: str = "GET", body: dict | None = None) -> dict:
    request = urllib.request.Request(
        BASE + path,
        method=method,
        data=json.dumps(body).encode() if body else None,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=660) as response:
        return json.loads(response.read().decode())


sources = call("/sources")
if sources:
    source_id = sources[0]["id"]
else:
    created = call(
        "/sources",
        "POST",
        {
            "name": "osm-overpass",
            "endpoint": "https://overpass-api.de/api/interpreter",
            "format": "overpass-json",
            "licence": "ODbL-1.0",
        },
    )
    source_id = created["id"]

result = call(f"/sources/{source_id}/sync", "POST", {"adapter": "overpass"})
print(
    "sync:",
    result["status"],
    "in:",
    result["records_in"],
    "added:",
    result["records_added"],
    "failed:",
    result["records_failed"],
    "version:",
    result.get("version_label", ""),
)
