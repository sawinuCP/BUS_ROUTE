"""Shared rate-limiting infrastructure (Phase 9 — pilot hardening).

One tiny per-key sliding-window limiter, process-wide, with named
namespaces so different endpoints have independent budgets:

- `ai` — grounded AI assistance calls (cost control, Phase 8 item 8);
- `reports` — traveller report submissions (abuse protection, doc 14).

Single-node only: a multi-node deployment must back this with the shared
store (Redis per ADR-0003) or an edge proxy; that is recorded as a Phase 9
release-checklist item. Tests reset the state via `reset_rate_limiters()`.
"""

from __future__ import annotations

import threading
import time
from collections import deque
from typing import Any


class SlidingWindowLimiter:
    """Tiny per-key sliding-window limiter (60-second window).

    Thread-safe: concurrent requests (async task or worker thread) share the
    process-wide limiter, so the check-then-record step is atomic.
    """

    def __init__(self, max_per_minute: int) -> None:
        self._max = max_per_minute
        self._events: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def allow(self, key: str, now: float | None = None) -> bool:
        current = time.monotonic() if now is None else now
        with self._lock:
            window = self._events.setdefault(key, deque())
            while window and current - window[0] > 60.0:
                window.popleft()
            if len(window) >= self._max:
                return False
            window.append(current)
            return True


_limiters: dict[str, SlidingWindowLimiter] = {}


def get_rate_limiter(namespace: str, settings: Any) -> SlidingWindowLimiter:
    """Return the namespace's limiter, sized from settings on first use."""
    limiter = _limiters.get(namespace)
    if limiter is None:
        if namespace == "ai":
            limit = settings.ai_requests_per_minute
        elif namespace == "reports":
            limit = settings.report_rate_limit_per_minute
        else:  # pragma: no cover - defensive; new namespaces must be added here
            raise ValueError(f"unknown rate-limit namespace: {namespace}")
        limiter = SlidingWindowLimiter(limit)
        _limiters[namespace] = limiter
    return limiter


def reset_rate_limiters() -> None:
    """Drop all limiter state (tests)."""
    _limiters.clear()
