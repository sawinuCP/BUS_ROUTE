"""Operational endpoints (Phase 9, plan item 5: metrics + dashboard).

- `GET /metrics` — Prometheus text exposition of the in-process counters
  and latency histograms. Public by convention (scrapers pull it inside the
  network); a reverse proxy may restrict it per deployment.
- `GET /ops/dashboard` — minimal self-contained HTML page rendering the
  same snapshot for the operator; requires the admin bearer token (same
  fail-closed behaviour as the admin router).

Both expose only operational metadata: routes, statuses and outcomes —
never query strings, bodies or locations.
"""

from __future__ import annotations

from datetime import UTC, datetime
from html import escape
from typing import Any

from fastapi import APIRouter, Depends, Response
from fastapi.responses import HTMLResponse, PlainTextResponse

from app.platform.metrics import render_metrics, snapshot
from app.platform.security import require_admin

router = APIRouter(tags=["ops"])


@router.get("/metrics", response_class=PlainTextResponse)
async def metrics() -> Response:
    """Prometheus text exposition (counters + request-latency histograms)."""
    return PlainTextResponse(render_metrics(), media_type="text/plain; version=0.0.4")


def _empty_rows(columns: int) -> str:
    return f'<tr><td colspan="{columns}">no data yet</td></tr>'


def _render_dashboard(snapshot: dict[str, Any]) -> str:
    counter_rows = "".join(
        f"<tr><td>{escape(name)}</td><td>{value:g}</td></tr>"
        for name, value in snapshot["counters"].items()
    ) or _empty_rows(2)
    latency_rows = "".join(
        f"<tr><td>{escape(name)}</td><td>{data['count']}</td>"
        f"<td>{data['avg_ms']} ms</td><td>{data['sum_ms']} ms</td></tr>"
        for name, data in snapshot["latencies"].items()
    ) or _empty_rows(4)
    return f"""<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><title>SLJP Operations</title>
<style>
body {{ font-family: system-ui, sans-serif; margin: 2rem; }}
table {{ border-collapse: collapse; margin-bottom: 2rem; }}
td, th {{ border: 1px solid #bbb; padding: 4px 10px; text-align: left; }}
h1 {{ font-size: 1.3rem; }} small {{ color: #666; }}
</style></head>
<body>
<h1>Sri Lanka Journey Planner — operations</h1>
<p><small>Generated {escape(datetime.now(UTC).isoformat())} ·
machine-readable: <a href="/api/v1/metrics">/api/v1/metrics</a> ·
health: <a href="/api/v1/health">/api/v1/health</a> ·
docs: <a href="/api/v1/docs">/api/v1/docs</a></small></p>
<h2>Counters</h2>
<table><tr><th>Counter</th><th>Value</th></tr>{counter_rows}</table>
<h2>Request latency</h2>
<table><tr><th>Path</th><th>Count</th><th>Avg</th><th>Total</th></tr>{latency_rows}</table>
</body></html>"""


@router.get("/ops/dashboard", response_class=HTMLResponse)
async def ops_dashboard(_admin: None = Depends(require_admin)) -> HTMLResponse:
    """Operator dashboard (admin token required outside local/test)."""
    return HTMLResponse(_render_dashboard(snapshot()))
