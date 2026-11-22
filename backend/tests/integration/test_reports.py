"""Phase 7 items 4, 7 and 8 — traveller reports and the moderation queue.

Under test (plan §Phase 7 verification):
- submission is append-only and idempotent per `client_key` (an offline-queued
  retry never duplicates a report);
- explicit consent is required — nothing is stored without it;
- the moderation queue lists reports; acceptance creates a **candidate**
  dataset version (the active dataset is untouched); rejection and
  needs-info change nothing outside the report row; accepted/rejected are
  terminal.
"""

from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.main import app
from app.platform.config import get_settings
from app.platform.db import dispose_engine
from tests.integration.conftest import _CLEANUP_ORDER


def _report_payload(client_key: str) -> dict[str, Any]:
    return {
        "category": "wrong_stop",
        "description": "The 138 boards at the opposite side of the road at this stop.",
        "consent": True,
        "client_key": client_key,
        "subject_type": "stop",
        "subject_id": None,
        "dataset_version_label": "osm-overpass-1679d061",
    }


async def test_report_submission_and_moderation_flow() -> None:
    engine = create_async_engine(get_settings().database_url)
    try:
        with TestClient(app) as client:
            # Submission: append-only, consent recorded, honest status.
            first = client.post("/api/v1/reports", json=_report_payload("client-key-1"))
            assert first.status_code == 201
            body = first.json()
            assert body["status"] == "submitted"
            assert body["consent"] is True
            assert body["duplicate"] is False

            # The same client_key (offline-queued retry) returns the same
            # report — a retry can never duplicate a submission.
            retry = client.post("/api/v1/reports", json=_report_payload("client-key-1"))
            assert retry.status_code == 201
            assert retry.json()["id"] == body["id"]
            assert retry.json()["duplicate"] is True

            second = client.post("/api/v1/reports", json=_report_payload("client-key-2"))
            assert second.json()["id"] != body["id"]

            # Explicit consent is required — nothing is stored without it.
            without_consent = _report_payload("client-key-3") | {"consent": False}
            assert client.post("/api/v1/reports", json=without_consent).status_code == 400

            # Categories are validated against the plan item 7 list.
            bad_category = _report_payload("client-key-4") | {"category": "made_up"}
            assert client.post("/api/v1/reports", json=bad_category).status_code == 422

            # Moderation queue: oldest first, both reports present.
            queue = client.get("/api/v1/admin/reports")
            assert queue.status_code == 200
            ids = [row["id"] for row in queue.json()]
            assert ids == [body["id"], second.json()["id"]]

            # Reject: status changes, nothing else does.
            rejected = client.post(
                f"/api/v1/admin/reports/{body['id']}/review",
                json={"decision": "reject", "note": "Not actionable without evidence."},
            )
            assert rejected.status_code == 200
            assert rejected.json()["status"] == "rejected"
            assert rejected.json()["candidate_version"] is None

            # Accepted/rejected are terminal (a fresh report replaces them).
            again = client.post(
                f"/api/v1/admin/reports/{body['id']}/review",
                json={"decision": "accept"},
            )
            assert again.status_code == 409

            # needs_info can be reviewed again later — accept it now.
            needs_info = client.post(
                f"/api/v1/admin/reports/{second.json()['id']}/review",
                json={"decision": "needs_info", "note": "Which route number?"},
            )
            assert needs_info.json()["status"] == "needs_info"
            async with engine.connect() as conn:
                before_active = (
                    await conn.execute(text("SELECT count(*) FROM active_dataset"))
                ).scalar_one()

            accepted = client.post(
                f"/api/v1/admin/reports/{second.json()['id']}/review",
                json={"decision": "accept", "note": "Field-checked on the owner walk."},
            )
            assert accepted.status_code == 200
            candidate = accepted.json()["candidate_version"]
            assert candidate is not None
            assert candidate["status"] == "candidate"

            async with engine.connect() as conn:
                version = (
                    await conn.execute(
                        text("SELECT status, notes FROM dataset_versions WHERE id = :id"),
                        {"id": candidate["id"]},
                    )
                ).one()
                # The candidate version is created for the pipeline — never
                # published and the active dataset is untouched.
                assert version.status == "candidate"
                assert "transport report" in version.notes
                after_active = (
                    await conn.execute(text("SELECT count(*) FROM active_dataset"))
                ).scalar_one()
            assert after_active == before_active
    finally:
        async with engine.begin() as conn:
            for statement in _CLEANUP_ORDER:
                await conn.execute(text(statement))
        await engine.dispose()
        await dispose_engine()
