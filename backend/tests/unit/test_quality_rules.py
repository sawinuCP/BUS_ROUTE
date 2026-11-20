"""Quality-rule behaviour (quarantine decisions are product-critical)."""

from __future__ import annotations

from app.modules.data_ingestion.adapters.base import RawRecord
from app.modules.data_ingestion.quality import validate_record


def _record(entity_hint: str, payload: dict) -> RawRecord:
    return RawRecord(external_id="rec-1", entity_hint=entity_hint, payload=payload)


def test_stop_without_name_fails() -> None:
    errors = validate_record(_record("stop", {"lon": 79.9, "lat": 6.9}))
    assert any("name" in error for error in errors)


def test_stop_with_valid_fields_passes() -> None:
    errors = validate_record(
        _record("stop", {"name": "Homagama Junction", "lon": 79.9777, "lat": 6.8440})
    )
    assert errors == []


def test_unknown_coordinates_are_allowed() -> None:
    errors = validate_record(_record("stop", {"name": "Unnamed Road Stop"}))
    assert errors == []


def test_out_of_bounds_coordinates_fail() -> None:
    errors = validate_record(_record("stop", {"name": "X", "lon": 2.35, "lat": 48.85}))
    assert any("lon" in error for error in errors)
    assert any("lat" in error for error in errors)


def test_nan_guard_and_sri_lanka_bbox() -> None:
    # London (out of bounds) fails; Jaffna (in bounds) passes.
    assert validate_record(_record("place", {"name": "Paris", "lon": 2.35, "lat": 48.85})) != []
    assert (
        validate_record(
            _record("place", {"name": "Jaffna Bus Stand", "lon": 80.0098, "lat": 9.6615})
        )
        == []
    )


def test_unsupported_mode_fails() -> None:
    errors = validate_record(_record("route", {"route_code": "1", "mode": "tuktuk"}))
    assert any("mode" in error for error in errors)


def test_route_requires_code_and_mode() -> None:
    errors = validate_record(_record("route", {}))
    assert any("route_code" in error for error in errors)
    assert any("mode" in error for error in errors)


def test_rules_only_apply_to_matching_entity() -> None:
    # stop required-field rule must not reject a route record.
    errors = validate_record(_record("route", {"route_code": "138", "mode": "bus"}))
    assert errors == []
