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
