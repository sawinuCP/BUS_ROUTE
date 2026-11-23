"""Optional crash/error reporting sink (Phase 9, plan item 5).

Provider-neutral: when `ERROR_WEBHOOK_URL` is configured, unhandled
exceptions post a minimal JSON payload (service, request id, path, error
type, timestamp) to that URL — works with any collector that accepts JSON
webhooks (Sentry-compatible endpoints, Opsgenie, n8n, a logging relay...).
No SDK dependency, and **failures are swallowed and logged** — error
reporting must never break or slow a response. No exception messages or
stack traces leave the process: they stay in the local log stream only
(they can contain user content).
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

import httpx

from app.platform.config import get_settings

logger = logging.getLogger(__name__)


async def report_error(
    request_id: str | None,
    path: str,
    error_type: str,
    transport: httpx.AsyncBaseTransport | None = None,
) -> bool:
    """Post one minimal error payload; return True iff delivered."""
    url = (get_settings().error_webhook_url or "").strip()
    if not url:
        return False
    payload: dict[str, Any] = {
        "service": "sljp-backend",
        "request_id": request_id,
        "path": path,
        "error_type": error_type,
        "timestamp": datetime.now(UTC).isoformat(),
        # A note rather than the exception text: the message/stack stay in
        # the local log stream (they may contain user content).
        "note": "Unhandled exception; see the backend log stream for details.",
    }
    try:
        async with httpx.AsyncClient(
            timeout=get_settings().error_webhook_timeout_seconds, transport=transport
        ) as client:
            response = await client.post(url, json=payload)
        if response.status_code // 100 != 2:
            logger.warning("error sink rejected payload", extra={"status": response.status_code})
            return False
        return True
    except Exception as exc:  # noqa: BLE001 - reporting must never break responses
        logger.warning("error sink unreachable", extra={"error_type": type(exc).__name__})
        return False
