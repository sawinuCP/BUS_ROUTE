"""Liveness/readiness endpoint behaviour (Phase 0 exit: health/readiness endpoints)."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_root_returns_service_metadata(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == 200
    body = response.json()
    assert body["service"]
    assert body["health"].endswith("/health")


def test_health_returns_ok_without_dependencies(client: TestClient) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"]
    assert body["version"] == "0.1.0"
    assert body["app_env"] == "test"


def test_health_response_includes_request_id_header(client: TestClient) -> None:
    response = client.get("/api/v1/health")
    assert response.headers.get("X-Request-ID")


def test_ready_reports_components_when_dependencies_down(client: TestClient) -> None:
    # In the unit-test environment no database/Redis is guaranteed to be up.
    # The endpoint must answer honestly (503 degraded) and never crash.
    response = client.get("/api/v1/ready")
    assert response.status_code in (200, 503)
    body = response.json()
    assert body["status"] in ("ready", "degraded")
    assert set(body["components"]) == {"database", "redis"}
    for component in body["components"].values():
        assert isinstance(component["ok"], bool)


def test_openapi_schema_is_generated(client: TestClient) -> None:
    response = client.get("/api/v1/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    assert schema["info"]["title"]
    assert "/api/v1/health" in schema["paths"]
    assert "/api/v1/ready" in schema["paths"]
