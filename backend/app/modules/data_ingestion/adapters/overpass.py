"""Overpass (OpenStreetMap) source adapter (Phase 1.3).

Fetches named bus stops and `route=bus` relations for a configurable pilot
bbox from the public Overpass API and parses them into normalised records:

- stop records from tagged nodes (named only; unnamed nodes are counted as
  diagnostics, never fabricated);
- one `route` record per **route ref** (the public route identity) — relations
  sharing a ref are variants, not separate routes;
- one `route_pattern` record per relation (the ordered variant/direction);
- ordered `route_pattern_stop` records with boarding/alighting eligibility
  derived from OSM member roles (stop / stop_entry_only / stop_exit_only).

Licence: ODbL 1.0 (see `data/source-rights-register.md` and
`docs/product/07_DATA_SOURCES_AND_ACQUISITION.md`). Attribution obligations
apply to any published derived data. OSM does not guarantee operational
status, complete stop sequences or boarding positions — all facts imported
here stay `unverified` until field-checked.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx

from app.modules.data_ingestion.adapters.base import FetchResult, RawRecord, SourceAdapter

logger = logging.getLogger(__name__)


def build_overpass_query(bbox: str, timeout_seconds: int = 90) -> str:
    """Read-only Overpass QL for named stops + bus route relations in a bbox."""
    return (
        f"[out:json][timeout:{timeout_seconds}];"
        "("
        'node["highway"="bus_stop"](' + bbox + ");"
        'node["public_transport"="platform"](' + bbox + ");"
        'relation["route"="bus"](' + bbox + ");"
        ");"
        "out body;"
        ">;"
        "out skel qt;"
    )


class OverpassAdapter(SourceAdapter):
    """Reads one snapshot from an Overpass API endpoint for a fixed bbox.

    Tries the primary endpoint, then an optional mirror (public instances are
    frequently overloaded — 502s are transient, not a data problem).
    """

    def __init__(
        self,
        bbox: str,
        endpoint: str = "https://overpass-api.de/api/interpreter",
        fallback_endpoint: str | None = None,
        timeout_seconds: int = 90,
        adapter_version: str = "0.1.0",
    ) -> None:
        self._bbox = bbox
        self._endpoint = endpoint
        self._fallback_endpoint = fallback_endpoint
        self._timeout = timeout_seconds
        self._adapter_version = adapter_version

    @property
    def adapter_version(self) -> str:
        return self._adapter_version

    def fetch(self) -> FetchResult:
        endpoints = [self._endpoint]
        if self._fallback_endpoint and self._fallback_endpoint != self._endpoint:
            endpoints.append(self._fallback_endpoint)
        last_error: Exception | None = None
        for endpoint in endpoints:
            try:
                return self._fetch_from(endpoint)
            except httpx.HTTPError as exc:
                last_error = exc
                logger.warning(
                    "overpass endpoint failed",
                    extra={"endpoint": endpoint, "error_type": type(exc).__name__},
                )
        assert last_error is not None
        raise last_error

    def _fetch_from(self, endpoint: str) -> FetchResult:
        query = build_overpass_query(self._bbox, self._timeout)
        response = httpx.post(
            endpoint,
            data={"data": query},
            timeout=self._timeout,
            headers={"User-Agent": "sljp-ingestion/0.1 (journey planner pilot; ODbL)"},
        )
        response.raise_for_status()
        return FetchResult(
            content=response.content,
            content_type=response.headers.get("content-type", "application/json"),
            metadata={"endpoint": endpoint, "bbox": self._bbox},
        )

    def parse(self, content: bytes, metadata: dict[str, Any]) -> list[RawRecord]:
        document = json.loads(content.decode("utf-8"))
        elements: list[dict[str, Any]] = document.get("elements", [])

        stop_records: list[RawRecord] = []
        skipped_unnamed = 0
        relations: list[dict[str, Any]] = []

        for element in elements:
            if element.get("type") == "node":
                tags = element.get("tags") or {}
                is_stop = tags.get("highway") == "bus_stop"
                is_platform = tags.get("public_transport") == "platform"
                if not (is_stop or is_platform):
                    continue
                name = tags.get("name")
                if not name:
                    skipped_unnamed += 1
                    continue
                aliases = [
                    {"language": language, "alias": tags[tag]}
                    for language, tag in (("si", "name:si"), ("ta", "name:ta"))
                    if tags.get(tag)
                ]
                stop_records.append(
                    RawRecord(
                        external_id=f"osm-node/{element['id']}",
                        entity_hint="stop",
                        payload={
                            "name": name,
                            "lon": element["lon"],
                            "lat": element["lat"],
                            "aliases": aliases,
                        },
                    )
                )
            elif element.get("type") == "relation":
                tags = element.get("tags") or {}
                if tags.get("type") == "route" and tags.get("route") == "bus" and tags.get("ref"):
                    relations.append(element)

        # Deterministic ordering for stable diff recording.
        stop_records.sort(key=lambda record: record.external_id)
        relations.sort(key=lambda element: element["id"])

        route_records: list[RawRecord] = []
        pattern_records: list[RawRecord] = []
        pattern_stop_records: list[RawRecord] = []

        seen_refs: set[str] = set()
        for relation in relations:
            tags = relation.get("tags") or {}
            ref = str(tags["ref"])
            relation_external_id = f"osm-relation/{relation['id']}"

            if ref not in seen_refs:
                seen_refs.add(ref)
                route_records.append(
                    RawRecord(
                        external_id=f"osm-route-ref/{ref}",
                        entity_hint="route",
                        payload={"route_code": ref, "mode": tags.get("route", "bus")},
                    )
                )

            pattern_records.append(
                RawRecord(
                    external_id=relation_external_id,
                    entity_hint="route_pattern",
                    payload={
                        "route_external_ref": f"osm-route-ref/{ref}",
                        "pattern_code": f"r{relation['id']}",
                        "direction_id": 0,  # not derivable from OSM alone; field-verify
                        "origin_label": tags.get("from"),
                        "destination_label": tags.get("to"),
                        "variant_description": tags.get("name"),
                    },
                )
            )

            node_members = (m for m in relation.get("members", []) if m.get("type") == "node")
            for sequence, member in enumerate(node_members, start=1):
                role = member.get("role", "")
                pattern_stop_records.append(
                    RawRecord(
                        external_id=f"{relation_external_id}/{sequence}",
                        entity_hint="route_pattern_stop",
                        payload={
                            "pattern_external_ref": relation_external_id,
                            "stop_external_ref": f"osm-node/{member['ref']}",
                            "sequence": sequence,
                            "boarding_allowed": role != "stop_exit_only",
                            "alighting_allowed": role != "stop_entry_only",
                        },
                    )
                )

        records = stop_records + route_records + pattern_records + pattern_stop_records
        if skipped_unnamed:
            # Diagnostics surface in QA review; unnamed stops are excluded rather
            # than given invented names.
            metadata.setdefault("osm", {})["skipped_unnamed_stop_nodes"] = skipped_unnamed
        return records
