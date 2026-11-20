"""Data-quality rules for ingested records (plan §5.1/§5.2, final 09 §6/§8).

Rules are pure functions over a normalised RawRecord. The sync runner applies
them before any canonical write: any failure **quarantines the whole run**
(suspicious changes are isolated, never published — final 09 §8 step 9).
Unknown/optional facts stay absent; rules never invent values.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from app.modules.data_ingestion.adapters.base import RawRecord

# Sri Lanka bounding box with a small margin (records are expected to be
# Sri Lankan transport facts; anything far outside is suspect data, not truth).
SRILANKA_MIN_LON = 79.2
SRILANKA_MAX_LON = 82.1
SRILANKA_MIN_LAT = 5.5
SRILANKA_MAX_LAT = 10.1

RuleFunction = Callable[[RawRecord], list[str]]


@dataclass(frozen=True)
class RuleReport:
    """Outcome of applying all registered rules to one record."""

    record: RawRecord
    errors: list[str]

    @property
    def passed(self) -> bool:
        return not self.errors


def _required_stop_fields(record: RawRecord) -> list[str]:
    if record.entity_hint != "stop":
        return []
    payload = record.payload
    missing = [key for key in ("name",) if not payload.get(key)]
    return [f"missing required field '{key}'" for key in missing]


def _required_route_fields(record: RawRecord) -> list[str]:
    if record.entity_hint != "route":
        return []
    payload = record.payload
    missing = [key for key in ("route_code", "mode") if not payload.get(key)]
    return [f"missing required field '{key}'" for key in missing]


def _required_place_fields(record: RawRecord) -> list[str]:
    if record.entity_hint != "place":
        return []
    missing = [key for key in ("name",) if not record.payload.get(key)]
    return [f"missing required field '{key}'" for key in missing]


def _required_shape_fields(record: RawRecord) -> list[str]:
    if record.entity_hint != "route_shape":
        return []
    payload = record.payload
    errors: list[str] = []
    missing = [key for key in ("pattern_external_ref", "coordinates") if not payload.get(key)]
    errors.extend(f"missing required field '{key}'" for key in missing)
    coordinates = payload.get("coordinates")
    if isinstance(coordinates, list) and len(coordinates) < 2:
        errors.append(f"shape has {len(coordinates)} point(s); at least 2 required")
    return errors


def _coordinate_bounds(record: RawRecord) -> list[str]:
    payload = record.payload
    lon = payload.get("lon")
    lat = payload.get("lat")
    if lon is None and lat is None:
        return []  # unknown coordinates are allowed; they must not be fabricated
    errors: list[str] = []
    if not isinstance(lon, int | float) or not SRILANKA_MIN_LON <= lon <= SRILANKA_MAX_LON:
        errors.append(f"lon {lon!r} outside Sri Lanka bounds")
    if not isinstance(lat, int | float) or not SRILANKA_MIN_LAT <= lat <= SRILANKA_MAX_LAT:
        errors.append(f"lat {lat!r} outside Sri Lanka bounds")
    return errors


def _shape_bounds(record: RawRecord) -> list[str]:
    """Every shape coordinate must fall inside Sri Lanka (with a margin)."""
    if record.entity_hint != "route_shape":
        return []
    coordinates = record.payload.get("coordinates")
    if not isinstance(coordinates, list):
        return []
    for lon, lat in coordinates:
        if (
            not isinstance(lon, int | float)
            or not SRILANKA_MIN_LON <= lon <= SRILANKA_MAX_LON
            or not isinstance(lat, int | float)
            or not SRILANKA_MIN_LAT <= lat <= SRILANKA_MAX_LAT
        ):
            return [f"shape coordinate ({lon!r}, {lat!r}) outside Sri Lanka bounds"]
    return []


def _mode_value(record: RawRecord) -> list[str]:
    mode = record.payload.get("mode")
    if mode is not None and mode not in ("bus", "rail"):
        return [f"unsupported mode {mode!r}"]
    return []


BUILTIN_RULES: tuple[RuleFunction, ...] = (
    _required_stop_fields,
    _required_route_fields,
    _required_place_fields,
    _required_shape_fields,
    _coordinate_bounds,
    _shape_bounds,
    _mode_value,
)


def validate_record(
    record: RawRecord, rules: tuple[RuleFunction, ...] = BUILTIN_RULES
) -> list[str]:
    """Apply every registered rule; return all error messages (empty = pass)."""
    errors: list[str] = []
    for rule in rules:
        errors.extend(rule(record))
    return errors


def validate_records(records: list[RawRecord]) -> list[RuleReport]:
    return [RuleReport(record=record, errors=validate_record(record)) for record in records]
