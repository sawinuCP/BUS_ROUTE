"""Application entrypoint and factory.

Run locally (host or container):

    uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from app.api.routes.admin import router as admin_router
from app.api.routes.health import router as health_router
from app.api.routes.journeys import router as journeys_router
from app.api.routes.pedestrian import router as pedestrian_router
from app.api.routes.search import router as search_router
from app.platform.config import get_settings
from app.platform.db import dispose_engine
from app.platform.errors import register_exception_handlers
from app.platform.logging import configure_logging
from app.platform.redis_client import close_redis

logger = logging.getLogger(__name__)


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
    register_exception_handlers(app)
    app.include_router(health_router, prefix=settings.api_v1_prefix)
    app.include_router(search_router, prefix=settings.api_v1_prefix)
    app.include_router(pedestrian_router, prefix=settings.api_v1_prefix)
    app.include_router(journeys_router, prefix=settings.api_v1_prefix)

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
