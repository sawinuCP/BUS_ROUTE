"""Application entrypoint and factory.

Run locally (host or container):

    uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
"""

from __future__ import annotations

import logging
import time
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from app.api.routes.admin import router as admin_router
from app.api.routes.ai import router as ai_router
from app.api.routes.health import router as health_router
from app.api.routes.journey_sessions import router as journey_sessions_router
from app.api.routes.journeys import router as journeys_router
from app.api.routes.ops import router as ops_router
from app.api.routes.pedestrian import router as pedestrian_router
from app.api.routes.reports import router as reports_router
from app.api.routes.search import router as search_router
from app.platform.config import get_settings
from app.platform.db import dispose_engine
from app.platform.errors import register_exception_handlers
from app.platform.logging import configure_logging
from app.platform.metrics import increment_counter, normalize_path, observe_duration_ms
from app.platform.redis_client import close_redis

logger = logging.getLogger(__name__)


class MetricsMiddleware(BaseHTTPMiddleware):
    """Request counters + latency histogram + Server-Timing (Phase 9, item 5).

    Labels are bounded: route template when resolved, otherwise the path
    with UUID/numeric segments replaced by `{id}`.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        started = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - started) * 1000.0
        # The real request path with UUID/numeric segments replaced by {id}:
        # bounded cardinality without depending on route-object internals.
        path_label = normalize_path(request.url.path)
        labels = {
            "method": request.method,
            "path": path_label,
            "status": str(response.status_code),
        }
        increment_counter("sljp_http_requests_total", labels)
        observe_duration_ms("sljp_http_request_duration_ms", {"path": path_label}, duration_ms)
        # Lightweight tracing: server-side processing time per request.
        response.headers["Server-Timing"] = f"app;dur={duration_ms:.1f}"
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Baseline hardening headers on every response (Phase 9, doc 14).

    Minimal and API-appropriate: no sniffing, no framing, no referrer leak.
    HTTPS/HSTS is the reverse-proxy's job in a real deployment.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Cache-Control"] = "no-store"
        return response


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Attach a request ID and return it in the `X-Request-ID` response header.

    Logs only the method and path — never the query string (search terms are
    treated as user content) and never headers or bodies.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get("x-request-id") or uuid.uuid4().hex
        request.state.request_id = request_id
        logger.info(
            "request",
            extra={"request_id": request_id, "method": request.method, "path": request.url.path},
        )
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    logger.info("startup", extra={"app_env": settings.app_env, "debug": settings.debug})
    yield
    await dispose_engine()
    await close_redis()
    logger.info("shutdown")


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(service="sljp-backend", level=settings.log_level)

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        lifespan=lifespan,
        docs_url=f"{settings.api_v1_prefix}/docs",
        openapi_url=f"{settings.api_v1_prefix}/openapi.json",
        redoc_url=None,
    )

    if settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_credentials=False,
            allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
            allow_headers=["*"],
        )

    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(MetricsMiddleware)
    register_exception_handlers(app)
    app.include_router(health_router, prefix=settings.api_v1_prefix)
    app.include_router(ops_router, prefix=settings.api_v1_prefix)
    app.include_router(search_router, prefix=settings.api_v1_prefix)
    app.include_router(pedestrian_router, prefix=settings.api_v1_prefix)
    app.include_router(journeys_router, prefix=settings.api_v1_prefix)
    app.include_router(journey_sessions_router, prefix=settings.api_v1_prefix)
    app.include_router(reports_router, prefix=settings.api_v1_prefix)
    # Grounded AI assistance (Phase 8): optional, always answers with a
    # validated AI explanation or the deterministic fallback.
    app.include_router(ai_router, prefix=settings.api_v1_prefix)

    # Admin/data-operations endpoints are mounted only outside production.
    # Production must expose them behind OAuth2/OIDC + RBAC (architecture doc 14).
    if settings.app_env in ("local", "test"):
        app.include_router(admin_router, prefix=settings.api_v1_prefix)

    @app.get("/", include_in_schema=False)
    async def root() -> JSONResponse:
        return JSONResponse(
            content={
                "service": settings.app_name,
                "docs": f"{settings.api_v1_prefix}/docs",
                "health": f"{settings.api_v1_prefix}/health",
            }
        )

    return app


app = create_app()
