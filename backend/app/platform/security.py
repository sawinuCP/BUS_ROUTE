"""Admin authentication (Phase 9 — pilot hardening).

The admin/data-operations router must never be exposed unauthenticated in a
real deployment. Mechanism here:

- `ADMIN_API_TOKEN` set in the environment → every admin request must carry
  `Authorization: Bearer <token>` (compared with `secrets.compare_digest`,
  timing-safe). Wrong/missing → 401 with the stable error envelope; the
  attempt is audit-logged without the presented credential.
- `ADMIN_API_TOKEN` unset → fail-open **only** in `local`/`test` (developer
  convenience; the router is only mounted there anyway) and **fail-closed**
  (403) in `staging`/`production` — an unconfigured production deployment
  can never serve admin endpoints.

OAuth2/OIDC + RBAC (architecture doc 14) replace this single-operator token
when accounts/identity exist; the dependency is the single seam for that.
"""

from __future__ import annotations

import logging
import secrets
from typing import Any

from fastapi import HTTPException, Request, status

from app.platform.config import get_settings
from app.platform.metrics import increment_counter

logger = logging.getLogger(__name__)

_OPEN_ENVS = frozenset({"local", "test"})


def require_admin(request: Request) -> None:
    """FastAPI dependency guarding every admin endpoint."""
    settings = get_settings()
    expected = settings.admin_api_token.strip()
    client = request.client.host if request.client else "unknown"

    if not expected:
        if settings.app_env in _OPEN_ENVS:
            # Dev convenience only; documented in the operations runbook.
            logger.warning(
                "admin access without a configured token (dev mode)",
                extra={"client": client, "path": request.url.path},
            )
            return
        logger.error(
            "admin access refused: ADMIN_API_TOKEN is not configured",
            extra={"client": client, "path": request.url.path},
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Admin endpoints are locked: ADMIN_API_TOKEN is not configured for this deployment."
            ),
        )

    header = request.headers.get("authorization") or ""
    scheme, _, presented = header.partition(" ")
    if scheme.lower() != "bearer" or not presented:
        logger.warning(
            "admin request without a bearer token",
            extra={"client": client, "path": request.url.path},
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin endpoints require: Authorization: Bearer <ADMIN_API_TOKEN>.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not secrets.compare_digest(presented.strip(), expected):
        logger.warning(
            "admin request with an invalid token",
            extra={"client": client, "path": request.url.path},
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin token.",
            headers={"WWW-Authenticate": "Bearer"},
        )


def audit_admin_action(
    request: Request,
    action: str,
    *,
    entity: str,
    outcome: str,
    details: dict[str, Any] | None = None,
) -> None:
    """Structured audit line for data-changing admin operations (doc 14).

    Logged with the request id so the JSON log stream can be filtered; never
    contains tokens, bodies or credentials.
    """
    payload: dict[str, Any] = {
        "request_id": getattr(request.state, "request_id", None),
        "client": request.client.host if request.client else "unknown",
        "action": action,
        "entity": entity,
        "outcome": outcome,
    }
    if details:
        payload["details"] = details
    logger.info("admin_audit", extra=payload)
    increment_counter("sljp_admin_actions_total", {"action": action, "outcome": outcome})
