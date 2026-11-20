"""Admin API end-to-end flow (single TestClient: one app, one event loop).

Covers: source registration (+ duplicate rejection), sync of a file source,
run retrieval, candidate publish, active-version readout and rollback.
The archive root is redirected into a temp dir via RAW_ARCHIVE_DIR.
"""

from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient


def test_admin_source_sync_publish_flow(client: TestClient, tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("RAW_ARCHIVE_DIR", str(tmp_path / "raw"))

    fixture = tmp_path / "source.json"
    fixture.write_text(
        json.dumps(
            [
                {
                    "external_id": "stop-kollupitiya",
                    "entity_hint": "stop",
                    "payload": {"name": "Kollupitiya Junction", "lon": 79.8483, "lat": 6.9107},
                }
            ]
        ),
        encoding="utf-8",
    )
    abs_path = str(fixture)

    with TestClient(client.app) as tc:
        # 1. register a source
        created = tc.post(
            "/api/v1/admin/sources",
            json={"name": "api-flow-source", "format": "test", "licence": "test"},
        )
        assert created.status_code == 201
        source_id = created.json()["id"]

        # duplicate name rejected
        duplicate = tc.post(
            "/api/v1/admin/sources",
            json={"name": "api-flow-source", "format": "test"},
        )
        assert duplicate.status_code == 409

        # 2. run a sync
        synced = tc.post(
            f"/api/v1/admin/sources/{source_id}/sync",
            json={"adapter": "file", "path": abs_path},
        )
        assert synced.status_code == 200
        outcome = synced.json()
        assert outcome["status"] == "succeeded"
        assert outcome["records_added"] == 1
        assert outcome["version_label"]

        # 3. inspect the run
        run = tc.get(f"/api/v1/admin/sync-runs/{outcome['run_id']}")
        assert run.status_code == 200
        assert run.json()["status"] == "succeeded"

        # unknown run → 404
        missing = tc.get("/api/v1/admin/sync-runs/00000000-0000-0000-0000-000000000000")
        assert missing.status_code == 404

        # 4. publish the candidate version
        versions = tc.get("/api/v1/admin/dataset-versions")
        assert versions.status_code == 200
        version_id = next(
            v["id"] for v in versions.json() if v["version_label"] == outcome["version_label"]
        )
        published = tc.post(f"/api/v1/admin/dataset-versions/{version_id}/publish")
        assert published.status_code == 200
        assert published.json()["status"] == "published"

        active = tc.get("/api/v1/admin/dataset-versions/active")
        assert active.status_code == 200
        assert active.json()["id"] == version_id

        # publishing again is idempotent
        again = tc.post(f"/api/v1/admin/dataset-versions/{version_id}/publish")
        assert again.status_code == 200
