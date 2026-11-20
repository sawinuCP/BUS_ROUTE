"""One-off helper: write the quality report for the latest dataset version."""

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
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.loads(response.read().decode())


versions = call("/dataset-versions")
latest = versions[0]["id"]
result = call(f"/dataset-versions/{latest}/quality-report/write", "POST")
print("report:", result.get("markdown") or result.get("path") or result)
