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


@pytest.fixture
def client():
    """Synchronous TestClient over the app factory (httpx under the hood)."""
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as test_client:
        yield test_client
