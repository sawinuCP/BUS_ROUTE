"""Generic local-file source adapter (framework/dev source).

Reads a JSON document from a local path and parses it into RawRecords. This is
a *framework* adapter for development, fixtures and tests — real Sri Lankan
transport sources (OSM/NSDI/NTC/GTFS) arrive in Phase 1.3 with their own
adapters, rights checks and parsers.

Expected JSON shape (list of records):
    [
      {"external_id": "stop-001", "entity_hint": "stop",
       "payload": {"name": "Homagama Junction", "lon": 79.9777, "lat": 6.8440}},
      ...
    ]
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.modules.data_ingestion.adapters.base import FetchResult, RawRecord, SourceAdapter


class FileSourceAdapter(SourceAdapter):
    """Reads one local JSON file; parse is a pure function over its bytes."""

    def __init__(self, path: str | Path, adapter_version: str = "1.0.0") -> None:
        self._path = Path(path)
        self._adapter_version = adapter_version

    @property
    def adapter_version(self) -> str:
        return self._adapter_version

    def fetch(self) -> FetchResult:
        content = self._path.read_bytes()
        return FetchResult(content=content, content_type="application/json")

    def parse(self, content: bytes, metadata: dict[str, Any]) -> list[RawRecord]:
        document = json.loads(content.decode("utf-8"))
        if not isinstance(document, list):
            raise ValueError("file source must contain a JSON array of records")
        records: list[RawRecord] = []
        for index, item in enumerate(document):
            if not isinstance(item, dict):
                raise ValueError(f"record {index} is not an object")
            external_id = item.get("external_id")
            entity_hint = item.get("entity_hint")
            payload = item.get("payload")
            if not external_id or not entity_hint or not isinstance(payload, dict):
                raise ValueError(
                    f"record {index} requires external_id, entity_hint and payload object"
                )
            records.append(
                RawRecord(
                    external_id=str(external_id), entity_hint=str(entity_hint), payload=payload
                )
            )
        return records
