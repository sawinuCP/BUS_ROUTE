"""Phase 9 — pilot hardening: admin auth, rate limiting, security headers.

Under test:
- **Admin authentication** (`ADMIN_API_TOKEN`): a configured token is
  required on every admin request (401 without/with a wrong token, 200 with
  the right one); unset fails open only in local/test and **fails closed**
  (403) in staging/production — an unconfigured production deployment can
  never serve admin endpoints;
- **Audit logging**: data-changing admin actions emit `admin_audit` records
  (action/entity/outcome, request id) — doc 14 requirement;
- **Rate limiting**: report submissions are throttled per client with the
  stable 429 RATE_LIMITED envelope;
- **Security headers** on every response.
"""

from __future__ import annotations

import logging

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.platform.config import get_settings
from tests.integration.test_reports import _report_payload


@pytest.fixture
def admin_token(monkeypatch: pytest.MonkeyPatch) -> str:
    """Enable admin bearer auth with a known token for this test."""
    monkeypatch.setenv("ADMIN_API_TOKEN", "op-secret-token-1")
    get_settings.cache_clear()  # env overrides must be visible to the app
    yield "op-secret-token-1"  # type: ignore[misc]
    get_settings.cache_clear()


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_admin_requires_bearer_token_when_configured(admin_token: str) -> None:
    with TestClient(app) as client:
        no_header = client.get("/api/v1/admin/sources")
        assert no_header.status_code == 401
        assert no_header.json()["error"]["code"] == "UNAUTHORIZED"

        wrong = client.get("/api/v1/admin/sources", headers=_auth("not-the-token"))
        assert wrong.status_code == 401

        wrong_scheme = client.get(
            "/api/v1/admin/sources", headers={"Authorization": "Basic op-secret-token-1"}
        )
        assert wrong_scheme.status_code == 401

        ok = client.get("/api/v1/admin/sources", headers=_auth(admin_token))
        assert ok.status_code == 200


def test_admin_fail_closed_in_production_without_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ADMIN_API_TOKEN", "")
    monkeypatch.setenv("APP_ENV", "production")
    get_settings.cache_clear()  # env overrides must be visible to the app
    with TestClient(app) as client:
        response = client.get("/api/v1/admin/sources")
    assert response.status_code == 403
    assert "ADMIN_API_TOKEN is not configured" in response.json()["error"]["message"]


def test_admin_works_in_production_with_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ADMIN_API_TOKEN", "prod-secret-1")
    monkeypatch.setenv("APP_ENV", "production")
    get_settings.cache_clear()  # env overrides must be visible to the app
    with TestClient(app) as client:
        ok = client.get("/api/v1/admin/sources", headers=_auth("prod-secret-1"))
        assert ok.status_code == 200
        rejected = client.get("/api/v1/admin/sources")
        assert rejected.status_code == 401


def test_admin_open_in_local_test_without_token() -> None:
    # The suite forces ADMIN_API_TOKEN off (dev-mode); the token unset +
    # test-env combination must keep working for local development.
    assert get_settings().admin_api_token == ""
    with TestClient(app) as client:
        response = client.get("/api/v1/admin/sources")
    assert response.status_code == 200


def test_admin_audit_log_for_report_review(admin_token: str) -> None:
    # caplog is not usable here: importing app.main runs configure_logging,
    # which clears the root handlers pytest attached. Attach a dedicated
    # handler to the audit logger instead, and set its level explicitly so
    # the root logger's WARNING level never filters the INFO audit record.
    audit_logger = logging.getLogger("app.platform.security")
    captured: list[logging.LogRecord] = []

    class _Capture(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            captured.append(record)

    handler = _Capture(level=logging.INFO)
    original_level = audit_logger.level
    audit_logger.addHandler(handler)
    audit_logger.setLevel(logging.INFO)
    try:
        with TestClient(app) as client:
            created = client.post("/api/v1/reports", json=_report_payload("audit-key-1"))
            assert created.status_code == 201
            reviewed = client.post(
                f"/api/v1/admin/reports/{created.json()['id']}/review",
                json={"decision": "accept", "note": "Field-checked."},
                headers=_auth(admin_token),
            )
            assert reviewed.status_code == 200
    finally:
        audit_logger.removeHandler(handler)
        audit_logger.setLevel(original_level)

    audit_records = [r for r in captured if r.getMessage() == "admin_audit"]
    assert audit_records, "expected an admin_audit record"
    record = audit_records[-1]
    assert record.action == "report.accept"  # type: ignore[attr-defined]
    assert str(record.entity).startswith("transport_report:")  # type: ignore[attr-defined]
    assert record.outcome == "accept"  # type: ignore[attr-defined]
    assert record.request_id  # type: ignore[attr-defined]
    # No credential material in the audit line.
    assert all("op-secret-token-1" not in str(r.__dict__) for r in captured)


def test_reports_rate_limited_per_client(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("REPORT_RATE_LIMIT_PER_MINUTE", "2")
    get_settings.cache_clear()  # env overrides must be visible to the app
    with TestClient(app) as client:
        first = client.post("/api/v1/reports", json=_report_payload("rl-key-1"))
        assert first.status_code == 201
        second = client.post("/api/v1/reports", json=_report_payload("rl-key-2"))
        assert second.status_code == 201
        third = client.post("/api/v1/reports", json=_report_payload("rl-key-3"))
        assert third.status_code == 429
        body = third.json()
        assert body["error"]["code"] == "RATE_LIMITED"


def test_security_headers_on_responses() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["X-Frame-Options"] == "DENY"
        assert response.headers["Referrer-Policy"] == "no-referrer"
        assert response.headers["Cache-Control"] == "no-store"
