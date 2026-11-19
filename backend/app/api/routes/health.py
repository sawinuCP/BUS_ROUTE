"""Health and readiness endpoints (implementation plan Phase 0 exit criteria).

- `GET /health` — liveness: the process is up; no external dependencies checked.
- `GET /ready`  — readiness: database and Redis reachability with component detail.

These endpoints expose no sensitive configuration and never leak connection
strings or error details.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Literal

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.platform.config import get_settings
from app.platform.db import check_database
from app.platform.redis_client import check_redis

logger = logging.getLogger(__name__)
router = APIRouter(tags=["health"])

_COMPONENT_TIMEOUT_SECONDS = 2.0


class HealthResponse(BaseModel):
    status: Literal["ok"]
    service: str
    version: str
    app_env: str


class ComponentStatus(BaseModel):
    ok: bool
    error: str | None = None


class ReadyResponse(BaseModel):
    status: Literal["ready", "degraded"]
    components: dict[str, ComponentStatus]


@router.get("/health", response_model=HealthResponse)
async def liveness() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(
        status="ok",
        service=settings.app_name,
        version="0.1.0",
        app_env=settings.app_env,
    )


@router.get("/ready", response_model=ReadyResponse)
async def readiness() -> JSONResponse:
    results: dict[str, dict[str, Any]] = {}

    async def _with_timeout(name: str, check: Any) -> None:
        try:
            results[name] = await asyncio.wait_for(check(), timeout=_COMPONENT_TIMEOUT_SECONDS)
        except TimeoutError:
            results[name] = {"ok": False, "error": "timeout"}

    await asyncio.gather(
        _with_timeout("database", check_database),
        _with_timeout("redis", check_redis),
    )

    components = {name: ComponentStatus(**value) for name, value in results.items()}
    all_ok = all(component.ok for component in components.values())
    body = ReadyResponse(
        status="ready" if all_ok else "degraded",
        components=components,
    )
    return JSONResponse(
        content=body.model_dump(),
        status_code=status.HTTP_200_OK if all_ok else status.HTTP_503_SERVICE_UNAVAILABLE,
    )
