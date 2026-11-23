"""Unit tests for the background-job interface (ADR-0004 / Phase 9 item).

The API app must stay Dramatiq-free (dispatch via `app.platform.jobs`);
the actors/runner/scheduler are tested against the stub broker and the
test database.
"""

from __future__ import annotations

import pytest

from app.jobs.scheduling import parse_cadence
from app.platform import jobs as jobs_module


def test_parse_cadence_accepts_compact_machine_values() -> None:
    assert parse_cadence("30m") == 1800
    assert parse_cadence("12h") == 43_200
    assert parse_cadence("7d") == 604_800
    assert parse_cadence("7D") == 604_800  # case-insensitive
    assert parse_cadence(" 90m ") == 5400  # whitespace tolerated


def test_parse_cadence_rejects_prose_and_garbage() -> None:
    # Doc 09 §5: cadences are configured per source; prose ("weekly",
    # "on publication") is human policy — never auto-synced.
    for value in (None, "", "weekly", "on publication", "1-2h", "m"):
        assert parse_cadence(value) is None, value


def test_dispatch_disabled_is_an_honest_no_op(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(jobs_module, "jobs_available", lambda: False)
    assert jobs_module.jobs_available() is False
    assert jobs_module.dispatch_sync_source("0000", reason="test") is False
    assert jobs_module.jobs_status()["library"] == "dramatiq"
