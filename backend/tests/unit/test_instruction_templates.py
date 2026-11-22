"""Unit: deterministic instruction templates (Phase 5).

Snapshot tests for the exact English template strings, plus the
no-fabrication rules: an absent headsign never appears in the text, and an
unreliable stop sequence withholds the intermediate-stop count.
"""

from __future__ import annotations

import uuid

from app.modules.itineraries import (
    ALIGHT_TRANSIT,
    BOARD_TRANSIT,
    RIDE_TRANSIT,
    WALK_TO_DESTINATION,
    WALK_TO_STOP,
    WALK_TRANSFER,
    build_steps,
)
from app.modules.planner import RideLeg, WalkLeg
from app.modules.planner.network import StopSpec, TransitNetwork

_STOP_A = uuid.uuid4()
_STOP_B = uuid.uuid4()

_NETWORK = TransitNetwork(
    version_label="test",
    stops={
        _STOP_A: StopSpec(
            id=_STOP_A, name="Kollupitiya Junction halt", mode="bus", lon=79.8483, lat=6.9107
        ),
        _STOP_B: StopSpec(id=_STOP_B, name="Colombo Fort", mode="bus", lon=79.8583, lat=6.9350),
    },
)


def _ride(
    *,
    destination_label: str | None = "Colombo Fort",
    intermediate_stops: int | None = 0,
) -> RideLeg:
    return RideLeg(
        pattern_id="p1",
        route_id="r1",
        route_code="101",
        mode="bus",
        direction_id=0,
        pattern_code="r15449974",
        origin_label="Moratuwa",
        destination_label=destination_label,
        verification_status="unverified",
        board_stop_id=str(_STOP_A),
        board_stop_name="Kollupitiya Junction halt",
        board_sequence=4,
        alight_stop_id=str(_STOP_B),
        alight_stop_name="Colombo Fort",
        alight_sequence=8,
        intermediate_stops=intermediate_stops,
        estimated_distance_m=4600.0,
        duration_min_s=900.0,
        duration_max_s=1380.0,
    )


def test_board_template_includes_verified_headsign() -> None:
    step = build_steps(_NETWORK, (_ride(),))[0]

    assert step.action == BOARD_TRANSIT
    assert step.text == (
        "Board route 101 at Kollupitiya Junction halt heading towards Colombo Fort."
    )
    assert step.facts["headsign"] == "Colombo Fort"
    assert step.facts["variant"] == "r15449974"
    assert step.confidence == "unverified"


def test_board_template_omits_absent_headsign() -> None:
    step = build_steps(
        _NETWORK,
        (
            _ride(
                destination_label=None,
            ),
        ),
    )[0]

    assert step.text == "Board route 101 at Kollupitiya Junction halt."
    assert "towards" not in step.text
    assert step.facts["headsign"] == "not confirmed"  # stated, not invented


def test_ride_template_counts_stops_when_sequence_is_reliable() -> None:
    step = build_steps(_NETWORK, (_ride(intermediate_stops=2),))[1]

    assert step.action == RIDE_TRANSIT
    assert step.text == "Ride 3 stops to Colombo Fort."
    assert step.facts["intermediate_stops"] == 2


def test_ride_template_singular_stop() -> None:
    step = build_steps(_NETWORK, (_ride(intermediate_stops=0),))[1]

    assert step.text == "Ride 1 stop to Colombo Fort."


def test_ride_template_withholds_count_when_sequence_has_gaps() -> None:
    step = build_steps(_NETWORK, (_ride(intermediate_stops=None),))[1]

    assert step.text == "Stay on route 101 and alight at Colombo Fort."
    assert step.facts["intermediate_stops"] == "not confirmed"


def test_alight_template() -> None:
    step = build_steps(_NETWORK, (_ride(),))[2]

    assert step.action == ALIGHT_TRANSIT
    assert step.text == "Alight at Colombo Fort."
    assert step.facts["alight_sequence"] == 8


def test_walk_templates_by_purpose() -> None:
    transfer = WalkLeg(
        purpose="transfer",
        distance_m=142.4,
        duration_s=100.0,
        from_ref={"kind": "stop", "id": str(_STOP_A), "name": "Kollupitiya Junction halt"},
        to_ref={"kind": "stop_access_point", "id": "ap-1", "stop_id": str(_STOP_B)},
        provider="stored_connector",
    )
    access_to_stop = WalkLeg(
        purpose="access",
        distance_m=240.0,
        duration_s=180.0,
        from_ref={"kind": "coordinates", "lon": 79.85, "lat": 6.91},
        to_ref={"kind": "stop", "id": str(_STOP_A), "name": "Kollupitiya Junction halt"},
    )
    access_to_ap = WalkLeg(
        purpose="access",
        distance_m=240.0,
        duration_s=180.0,
        from_ref={"kind": "coordinates", "lon": 79.85, "lat": 6.91},
        to_ref={"kind": "stop_access_point", "id": "ap-2", "stop_id": str(_STOP_A)},
    )
    egress = WalkLeg(
        purpose="egress",
        distance_m=310.5,
        duration_s=220.0,
        from_ref={"kind": "stop", "id": str(_STOP_B), "name": "Colombo Fort"},
        to_ref={"kind": "coordinates", "lon": 79.86, "lat": 6.93},
    )

    transfer_step = build_steps(_NETWORK, (transfer,))[0]
    access_stop_step = build_steps(_NETWORK, (access_to_stop,))[0]
    access_ap_step = build_steps(_NETWORK, (access_to_ap,))[0]
    egress_step = build_steps(_NETWORK, (egress,))[0]

    assert transfer_step.action == WALK_TRANSFER
    assert transfer_step.text == "Walk 142 m to Colombo Fort to change buses."
    assert transfer_step.facts["next_boarding_point"] == "Colombo Fort"
    assert access_stop_step.action == WALK_TO_STOP
    assert access_stop_step.text == "Walk 240 m to Kollupitiya Junction halt."
    assert access_ap_step.text == "Walk 240 m to the boarding point."
    assert access_ap_step.facts["to_access_point_id"] == "ap-2"
    assert egress_step.action == WALK_TO_DESTINATION
    assert egress_step.text == "Walk 310 m to your destination."


def test_walk_facts_carry_target_coordinates_from_canonical_data() -> None:
    """GPS assist facts come from the network only — never invented."""
    transfer = WalkLeg(
        purpose="transfer",
        distance_m=142.4,
        duration_s=100.0,
        from_ref={"kind": "stop", "id": str(_STOP_A), "name": "Kollupitiya Junction halt"},
        to_ref={"kind": "stop_access_point", "id": "ap-1", "stop_id": str(_STOP_B)},
        provider="stored_connector",
    )
    access = WalkLeg(
        purpose="access",
        distance_m=240.0,
        duration_s=180.0,
        from_ref={"kind": "coordinates", "lon": 79.85, "lat": 6.91},
        to_ref={"kind": "stop", "id": str(_STOP_A), "name": "Kollupitiya Junction halt"},
    )
    unmapped = WalkLeg(
        purpose="egress",
        distance_m=100.0,
        duration_s=80.0,
        from_ref={"kind": "stop", "id": str(_STOP_B), "name": "Colombo Fort"},
        to_ref={"kind": "coordinates", "lon": 79.86, "lat": 6.93},
    )

    transfer_step = build_steps(_NETWORK, (transfer,))[0]
    access_step = build_steps(_NETWORK, (access,))[0]
    unmapped_step = build_steps(_NETWORK, (unmapped,))[0]

    # Stop B's canonical mapped position (no access point with that id exists,
    # so the stop's own position is the honest fallback).
    assert transfer_step.facts["target_lat"] == _NETWORK.stops[_STOP_B].lat
    assert transfer_step.facts["target_lon"] == _NETWORK.stops[_STOP_B].lon
    assert access_step.facts["target_lat"] == _NETWORK.stops[_STOP_A].lat
    # A pure coordinate reference has no stop to resolve → no invented target.
    assert "target_lat" not in unmapped_step.facts
    assert "target_lon" not in unmapped_step.facts


def test_step_order_is_executable() -> None:
    access = WalkLeg(
        purpose="access",
        distance_m=240.0,
        duration_s=180.0,
        from_ref={"kind": "coordinates", "lon": 79.85, "lat": 6.91},
        to_ref={"kind": "stop", "id": str(_STOP_A), "name": "Kollupitiya Junction halt"},
    )
    egress = WalkLeg(
        purpose="egress",
        distance_m=100.0,
        duration_s=80.0,
        from_ref={"kind": "stop", "id": str(_STOP_B), "name": "Colombo Fort"},
        to_ref={"kind": "coordinates", "lon": 79.86, "lat": 6.93},
    )

    steps = build_steps(_NETWORK, (access, _ride(), egress))

    assert [s.action for s in steps] == [
        WALK_TO_STOP,
        BOARD_TRANSIT,
        RIDE_TRANSIT,
        ALIGHT_TRANSIT,
        WALK_TO_DESTINATION,
    ]
