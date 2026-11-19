"""Structured JSON logging format (implementation plan Phase 0 item 10)."""

from __future__ import annotations

import json
import logging

from app.platform.logging import JsonFormatter, configure_logging


def test_json_formatter_emits_single_line_json() -> None:
    formatter = JsonFormatter(service="test-service")
    record = logging.LogRecord(
        name="app.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="hello %s",
        args=("world",),
        exc_info=None,
    )
    rendered = formatter.format(record)
    assert rendered.count("\n") == 0
    payload = json.loads(rendered)
    assert payload["message"] == "hello world"
    assert payload["level"] == "INFO"
    assert payload["service"] == "test-service"
    assert payload["logger"] == "app.test"
    assert "ts" in payload


def test_json_formatter_includes_extra_fields() -> None:
    formatter = JsonFormatter(service="test-service")
    record = logging.LogRecord(
        name="app.test",
        level=logging.WARNING,
        pathname=__file__,
        lineno=1,
        msg="db check failed",
        args=(),
        exc_info=None,
    )
    record.request_id = "abc123"  # type: ignore[attr-defined]
    payload = json.loads(formatter.format(record))
    assert payload["request_id"] == "abc123"


def test_configure_logging_sets_json_handler_on_root() -> None:
    configure_logging(service="test-service", level="WARNING")
    root = logging.getLogger()
    assert root.level == logging.WARNING
    assert root.handlers
    assert any(isinstance(handler.formatter, JsonFormatter) for handler in root.handlers)
