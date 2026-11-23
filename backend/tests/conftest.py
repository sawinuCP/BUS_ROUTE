"""Shared pytest fixtures.

Settings are forced into `test` mode for the whole test session so tests never
accidentally depend on, or mutate, local-development data. The lru_cache on
get_settings() is cleared around tests that override settings.
"""

from __future__ import annotations

import os
from collections.abc import Iterator

import pytest

os.environ["APP_ENV"] = "test"
os.environ["LOG_LEVEL"] = "WARNING"
# Phase 9: admin bearer auth is opt-in per test (monkeypatch.setenv). Force
# the token OFF here — an empty environment variable wins over the root
# .env file, so the suite runs in dev-mode (allowed in test env) by default.
os.environ["ADMIN_API_TOKEN"] = ""
# I-18: integration tests must never touch development data. Redirect the DB
# to the dedicated test database (created by the compose init script; the
# integration-conftest session fixture applies migrations to it automatically).
_dev_url = os.environ.get("DATABASE_URL", "")
if _dev_url and "/journey_planner_test" not in _dev_url:
    os.environ["DATABASE_URL"] = _dev_url.replace("/journey_planner", "/journey_planner_test")

from app.platform.config import get_settings  # noqa: E402


@pytest.fixture(autouse=True)
def _clear_settings_cache() -> Iterator[None]:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture(autouse=True)
def _reset_rate_limiters() -> Iterator[None]:
    """Phase 9: rate limiter state must not leak between tests."""
    from app.platform.rate_limit import reset_rate_limiters

    reset_rate_limiters()
    yield
    reset_rate_limiters()


@pytest.fixture(autouse=True)
def _reset_metrics() -> Iterator[None]:
    """Phase 9 item 5: metric state must not leak between tests."""
    from app.platform.metrics import reset_metrics

    reset_metrics()
    yield
    reset_metrics()


@pytest.fixture
def client():
    """Synchronous TestClient over the app factory (httpx under the hood)."""
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as test_client:
        yield test_client
