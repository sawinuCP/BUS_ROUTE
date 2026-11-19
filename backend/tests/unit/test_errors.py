"""Stable error-envelope behaviour (implementation plan §4.2)."""

from __future__ import annotations

import json

from fastapi.testclient import TestClient


def test_unknown_route_returns_not_found_envelope(client: TestClient) -> None:
    response = client.get("/api/v1/does-not-exist")
    assert response.status_code == 404
    error = response.json()["error"]
    assert error["code"] == "NOT_FOUND"
    assert error["request_id"]


def test_validation_error_envelope_is_stable() -> None:
    # The handler is exercised directly: Phase 0.3 has no body-model endpoint yet.
    import asyncio

    from fastapi.exceptions import RequestValidationError
    from starlette.requests import Request as StarletteRequest

    from app.platform.errors import validation_exception_handler

    scope = {
        "type": "http",
        "method": "POST",
        "path": "/api/v1/ready",
        "headers": [],
        "query_string": b"",
    }
    request = StarletteRequest(scope)
    request.state.request_id = "test-req-id"
    exc = RequestValidationError(
        errors=[{"loc": ("body", "origin"), "msg": "Field required", "type": "missing"}]
    )

    response = asyncio.run(validation_exception_handler(request, exc))
    assert response.status_code == 422
    payload = json.loads(bytes(response.body))
    error = payload["error"]
    assert error["code"] == "VALIDATION_ERROR"
    assert error["request_id"] == "test-req-id"
    assert error["details"] == [{"field": "origin", "message": "Field required"}]


def test_request_id_header_is_echoed(client: TestClient) -> None:
    response = client.get("/", headers={"X-Request-ID": "test-request-id-123"})
    assert response.headers["X-Request-ID"] == "test-request-id-123"


def test_no_stack_trace_leaks_in_error_response(client: TestClient) -> None:
    response = client.get("/api/v1/does-not-exist")
    raw = response.text
    assert "Traceback" not in raw
    assert 'File "' not in raw
