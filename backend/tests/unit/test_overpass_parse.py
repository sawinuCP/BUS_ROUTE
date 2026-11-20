"""Overpass adapter parsing (synthetic fixture; no real-world claims)."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.modules.data_ingestion.adapters.overpass import OverpassAdapter, build_overpass_query

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "overpass_sample.json"


@pytest.fixture
def parsed() -> list:
    content = FIXTURE.read_bytes()
    return OverpassAdapter("6.88,79.83,6.96,79.90").parse(content, {})


def test_query_contains_bbox_and_filters() -> None:
    query = build_overpass_query("6.88,79.83,6.96,79.90")
    assert "(6.88,79.83,6.96,79.90)" in query
    assert 'node["highway"="bus_stop"]' in query
    assert 'relation["route"="bus"]' in query
    assert query.strip().endswith("out skel qt;")


def test_named_stops_become_stop_records_with_aliases(parsed: list) -> None:
    stops = [record for record in parsed if record.entity_hint == "stop"]
    assert {record.external_id for record in stops} == {
        "osm-node/100001",
        "osm-node/100002",
    }
    homagama_like = next(r for r in stops if r.external_id == "osm-node/100001")
    assert homagama_like.payload["name"] == "Pettah Terminal"
    assert {"language": "si", "alias": "පෙට්ටා ස්ථානය"} in homagama_like.payload["aliases"]
    tamil = next(r for r in stops if r.external_id == "osm-node/100002")
    assert tamil.payload["aliases"][0]["language"] == "ta"


def test_unnamed_tagged_node_is_skipped_not_invented(parsed: list) -> None:
    stops = [record for record in parsed if record.entity_hint == "stop"]
    assert all(record.external_id != "osm-node/100003" for record in stops)


def test_relations_sharing_ref_yield_one_route_and_multiple_variants(parsed: list) -> None:
    routes = [record for record in parsed if record.entity_hint == "route"]
    assert [record.external_id for record in routes] == ["osm-route-ref/100", "osm-route-ref/101"]

    patterns = [record for record in parsed if record.entity_hint == "route_pattern"]
    assert {record.external_id for record in patterns} == {
        "osm-relation/200001",
        "osm-relation/200002",
        "osm-relation/200003",
    }
    by_id = {record.external_id: record for record in patterns}
    # Relations 200001/200002 share ref 100 → both variants reference one route.
    assert by_id["osm-relation/200001"].payload["route_external_ref"] == "osm-route-ref/100"
    assert by_id["osm-relation/200002"].payload["route_external_ref"] == "osm-route-ref/100"
    assert by_id["osm-relation/200001"].payload["origin_label"] == "Pettah"
    assert by_id["osm-relation/200001"].payload["destination_label"] == "Kollupitiya"


def test_ordered_calls_and_role_derived_eligibility(parsed: list) -> None:
    calls = [record for record in parsed if record.entity_hint == "route_pattern_stop"]
    calls_by_pattern: dict[str, list] = {}
    for record in calls:
        calls_by_pattern.setdefault(record.payload["pattern_external_ref"], []).append(record)

    relation_1 = calls_by_pattern["osm-relation/200001"]
    assert [
        (call.payload["sequence"], call.payload["stop_external_ref"]) for call in relation_1
    ] == [
        (1, "osm-node/100001"),
        (2, "osm-node/100002"),
    ]
    assert all(
        call.payload["boarding_allowed"] and call.payload["alighting_allowed"]
        for call in relation_1
    )

    relation_3 = calls_by_pattern["osm-relation/200003"]
    assert (
        relation_3[0].payload["boarding_allowed"],
        relation_3[0].payload["alighting_allowed"],
    ) == (
        True,
        False,
    )  # stop_entry_only
    assert (
        relation_3[1].payload["boarding_allowed"],
        relation_3[1].payload["alighting_allowed"],
    ) == (
        False,
        True,
    )  # stop_exit_only
