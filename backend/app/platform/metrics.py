"""Lightweight in-process metrics (Phase 9, plan item 5).

Zero-dependency counters and latency histograms rendered in the Prometheus
text exposition format at `GET /api/v1/metrics`, plus a dict snapshot for
the operator dashboard (`GET /api/v1/ops/dashboard`).

Scope notes (recorded honestly):
- In-process and single-node: a multi-node deployment must aggregate (e.g.
  pull from each replica, or move these counters to Redis/StatsD) — that is
  a release-checklist item.
- Only operational metadata is measured (routes, statuses, outcomes); no
  query strings, bodies or locations.
- Tests reset via `reset_metrics()`.
"""

from __future__ import annotations

import re
import time
from typing import Any

BUCKETS_MS: tuple[float, ...] = (5, 10, 25, 50, 100, 250, 500, 1000, 2500, 5000, 10000)

_UUID_SEGMENT = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)


def normalize_path(path: str) -> str:
    """Bound label cardinality: UUID/numeric path segments become `{id}`."""
    parts = [
        "{id}" if (_UUID_SEGMENT.match(seg) or seg.isdigit()) else seg for seg in path.split("/")
    ]
    return "/".join(parts)


# Full Prometheus series key (name + labels) -> value.
_counters: dict[str, float] = {}
# Base key (name + labels) -> histogram state.
_histograms: dict[str, dict[str, Any]] = {}


def _escape_label(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def _series(name: str, labels: dict[str, str] | None = None) -> str:
    """Prometheus series identifier: `name{label="value",...}` (sorted)."""
    if not labels:
        return name
    joined = ", ".join(
        f'{key}="{_escape_label(str(value))}"' for key, value in sorted(labels.items())
    )
    return f"{name}{{{joined}}}"


def increment_counter(name: str, labels: dict[str, str] | None = None, value: float = 1.0) -> None:
    """Add `value` to one labeled counter series."""
    _counters[_series(name, labels)] = _counters.get(_series(name, labels), 0.0) + value


def observe_duration_ms(name: str, labels: dict[str, str] | None, duration_ms: float) -> None:
    """Record one latency observation (histogram buckets + sum + count)."""
    key = _series(name, labels)
    state = _histograms.setdefault(key, {"buckets": [0] * len(BUCKETS_MS), "sum": 0.0, "count": 0})
    for index, bound in enumerate(BUCKETS_MS):
        if duration_ms <= bound:
            state["buckets"][index] += 1
    state["sum"] += duration_ms
    state["count"] += 1


def render_metrics() -> str:
    """Render the full exposition (Prometheus text format, version 0.0.4)."""
    lines: list[str] = []
    for key in sorted(_counters):
        base = key.split("{", 1)[0]
        lines.append(f"# TYPE {base} counter")
        lines.append(f"{key} {_counters[key]:g}")
    for key in sorted(_histograms):
        base = key.split("{", 1)[0]
        state = _histograms[key]
        labels_part = key[key.index("{") :] if "{" in key else ""
        labels_with_le = (labels_part[1:-1] + ", ") if labels_part else ""
        lines.append(f"# TYPE {base} histogram")
        cumulative = 0
        for index, bound in enumerate(BUCKETS_MS):
            cumulative += state["buckets"][index]
            lines.append(f'{base}_bucket{{{labels_with_le}le="{bound:g}"}} {cumulative}')
        lines.append(f'{base}_bucket{{{labels_with_le}le="+Inf"}} {state["count"]:g}')
        lines.append(f"{base}_sum{labels_part} {state['sum']:g}")
        lines.append(f"{base}_count{labels_part} {state['count']:g}")
    return "\n".join(lines) + "\n"


def _bucket_labels(key: str) -> str:
    """`labels,` prefix for histogram sub-series ("" when no labels)."""
    if "{" not in key:
        return ""
    return key[key.index("{") + 1 : -1] + ", "


def snapshot() -> dict[str, Any]:
    """Dashboard-friendly snapshot: counters + latency summaries."""
    latencies = {
        key: {
            "count": state["count"],
            "sum_ms": round(state["sum"], 1),
            "avg_ms": round(state["sum"] / state["count"], 1) if state["count"] else 0.0,
            "max_bucket_ms": max(
                (bound for index, bound in enumerate(BUCKETS_MS) if state["buckets"][index]),
                default=0,
            ),
        }
        for key, state in _histograms.items()
    }
    return {
        "counters": dict(sorted(_counters.items())),
        "latencies": dict(sorted(latencies.items())),
    }


def reset_metrics() -> None:
    """Drop all metric state (tests)."""
    _counters.clear()
    _histograms.clear()


def monotonic_ms() -> float:
    """Current monotonic clock in ms (for middleware timing)."""
    return time.perf_counter() * 1000.0
