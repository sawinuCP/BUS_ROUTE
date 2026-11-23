"""Phase 9 item 5 — metrics, error sink, tracing and the ops dashboard.

Under test:
- `GET /metrics` renders Prometheus text (counters + latency histograms)
  with bounded labels; `Server-Timing` carries per-request duration;
- domain counters: reports (submitted/duplicate, rate-limited) and AI
  explanations (mode + source) show up in the exposition;
- the operator dashboard: open in local/test dev mode, **403 fail-closed**
  in production without a token, `/metrics` stays public;
- the optional error sink: posts a minimal payload (no messages/stacks),
  swallows its own failures, is disabled without a URL, and is invoked by
  the unhandled-exception handler (which also counts the error).
"""

from __future__ import annotations

import httpx
import pytest
from fastapi.testclient import TestClient
from starlette.requests import Request

from app.main import app
from app.platform import error_sink, errors
from app.platform.config import Settings, get_settings


class FakeAIProvider:
    """Scripted provider for the AI counter test."""

    name = "fake"
    model = "fake-model"

    async def complete(self, system: str, user: str) -> object:
        return type(
            "Completion",
            (),
            {
                "text": (
                    '{"explanation": "Board route 101 at Willium Junction as'
                    ' mapped; the wording on the step is authoritative.",'
                    ' "cites": ["f_step"]}'
                )
            },
        )()


def _ai_payload() -> dict[str, object]:
    return {
        "status": "ok",
        "dataset_version": "test-net-1",
        "language": "en",
        "notes": [],
        "options": [
            {
                "id": "opt-1",
                "labels": ["101"],
                "warnings": [],
                "summary": {
                    "estimated_duration_minutes": {"min": 10, "max": 20},
                    "walking_distance_m": 100,
                    "transfer_count": 0,
                    "confidence": "unverified",
                },
                "steps": [
                    {
                        "action": "BOARD_TRANSIT",
                        "text": "Board route 101 at Willium Junction.",
                        "facts": {"route_code": "101", "stop_name": "Willium Junction"},
                        "confidence": "unverified",
                    }
                ],
            }
        ],
    }


def test_metrics_exposition_and_server_timing() -> None:
    with TestClient(app) as client:
        health = client.get("/api/v1/health")
        assert health.status_code == 200
        assert "app;dur=" in health.headers["Server-Timing"]

        exposition = client.get("/api/v1/metrics")
        assert exposition.status_code == 200
        assert "text/plain" in exposition.headers["content-type"]
        text = exposition.text
        assert "# TYPE sljp_http_requests_total counter" in text
        assert 'sljp_http_requests_total{method="GET", path="/api/v1/health", status="200"}' in text
        assert "# TYPE sljp_http_request_duration_ms histogram" in text
        assert 'sljp_http_request_duration_ms_bucket{path="/api/v1/health", le="5"}' in text
        assert 'sljp_http_request_duration_ms_bucket{path="/api/v1/health", le="+Inf"}' in text
        assert 'sljp_http_request_duration_ms_sum{path="/api/v1/health"}' in text
        assert 'sljp_http_request_duration_ms_count{path="/api/v1/health"}' in text


def test_report_counters_in_exposition() -> None:
    with TestClient(app) as client:
        created = client.post(
            "/api/v1/reports",
            json={
                "category": "wrong_stop",
                "description": "The 138 boards at the opposite side of the road here.",
                "consent": True,
                "client_key": "metrics-key-1",
            },
        )
        assert created.status_code == 201
        text = client.get("/api/v1/metrics").text
        assert 'sljp_reports_submitted_total{duplicate="false"}' in text


def test_rate_limit_counter_in_exposition(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("REPORT_RATE_LIMIT_PER_MINUTE", "1")
    get_settings.cache_clear()
    try:
        with TestClient(app) as client:
            body = {
                "category": "wrong_stop",
                "description": "The 138 boards at the opposite side of the road here.",
                "consent": True,
            }
            assert (
                client.post("/api/v1/reports", json=body | {"client_key": "rlc-000001"}).status_code
                == 201
            )
            assert (
                client.post("/api/v1/reports", json=body | {"client_key": "rlc-000002"}).status_code
                == 429
            )
            text = client.get("/api/v1/metrics").text
            assert 'sljp_rate_limited_total{scope="reports"}' in text
    finally:
        get_settings.cache_clear()


def test_ai_explanation_counter(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = Settings(
        _env_file=None,
        ai_provider="none",
        ai_explanations_enabled=True,
        ai_requests_per_minute=100,
    )
    monkeypatch.setattr("app.api.routes.ai.get_settings", lambda: settings)
    monkeypatch.setattr(
        "app.modules.ai_assistance.service.create_provider", lambda s: FakeAIProvider()
    )
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/ai/explain-step",
            json={"mode": "explain_step", "journey": _ai_payload(), "step_index": 0},
        )
        assert response.status_code == 200
        text = client.get("/api/v1/metrics").text
        assert 'sljp_ai_explanations_total{mode="explain_step", source="ai"}' in text


def test_dashboard_open_in_test_env_and_metrics_public() -> None:
    with TestClient(app) as client:
        # A request first, so the dashboard snapshot has data to show (the
        # dashboard's own request is counted only after it renders).
        assert client.get("/api/v1/metrics").status_code == 200
        dashboard = client.get("/api/v1/ops/dashboard")
        assert dashboard.status_code == 200
        assert "text/html" in dashboard.headers["content-type"]
        assert "operations" in dashboard.text
        assert "sljp_http_requests_total" in dashboard.text

        # /metrics stays public (scrapers pull it inside the network).
        assert client.get("/api/v1/metrics").status_code == 200


def test_dashboard_fail_closed_in_production(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("ADMIN_API_TOKEN", "")
    get_settings.cache_clear()
    try:
        with TestClient(app) as client:
            assert client.get("/api/v1/ops/dashboard").status_code == 403
            # The machine-readable metrics stay public.
            assert client.get("/api/v1/metrics").status_code == 200
    finally:
        get_settings.cache_clear()


async def test_error_sink_disabled_without_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ERROR_WEBHOOK_URL", "")
    get_settings.cache_clear()
    try:
        assert await error_sink.report_error("rid", "/x", "ValueError") is False
    finally:
        get_settings.cache_clear()


async def test_error_sink_posts_minimal_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    import json

    monkeypatch.setenv("ERROR_WEBHOOK_URL", "https://collector.example/hook")
    get_settings.cache_clear()
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["body"] = request.read()
        return httpx.Response(200, request=request)

    try:
        ok = await error_sink.report_error(
            "rid-1", "/api/v1/x", "ValueError", transport=httpx.MockTransport(handler)
        )
        assert ok is True
        assert str(captured["url"]).startswith("https://collector.example/")
        raw_body = captured["body"]
        assert isinstance(raw_body, bytes)
        payload = json.loads(raw_body)
        assert payload["service"] == "sljp-backend"
        assert payload["request_id"] == "rid-1"
        assert payload["error_type"] == "ValueError"
        # The exception text itself never leaves the process.
        assert "traceback" not in raw_body.decode().lower()
    finally:
        get_settings.cache_clear()


async def test_error_sink_swallows_failures(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ERROR_WEBHOOK_URL", "https://collector.example/hook")
    get_settings.cache_clear()

    def failing(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("boom")

    try:
        assert (
            await error_sink.report_error(
                "rid", "/x", "ValueError", transport=httpx.MockTransport(failing)
            )
            is False
        )
    finally:
        get_settings.cache_clear()


async def test_unhandled_exception_handler_counts_and_reports(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict[str, object]] = []

    async def spy(request_id: str | None, path: str, error_type: str, **kwargs: object) -> bool:
        calls.append({"request_id": request_id, "path": path, "error_type": error_type})
        return True

    monkeypatch.setattr(errors.error_sink, "report_error", spy)
    request = Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/api/v1/boom/123",
            "headers": [],
            "query_string": b"",
            "client": ("testclient", 0),
        }
    )
    request.state.request_id = "rid-42"
    response = await errors.unhandled_exception_handler(request, ValueError("x"))
    assert response.status_code == 500
    assert calls == [
        {"request_id": "rid-42", "path": "/api/v1/boom/123", "error_type": "ValueError"}
    ]
    from app.platform.metrics import render_metrics

    assert 'sljp_unhandled_errors_total{path="/api/v1/boom/{id}"} 1' in render_metrics()
