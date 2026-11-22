"""Unit: itinerary estimates, Pareto filtering, dedup and ranking labels.

These are pure-domain properties the routing-engine doc requires: dominated
candidates removed, meaningful trade-offs kept, labels that match their
metrics, and deterministic output.
"""

from __future__ import annotations

from app.modules.planner.itinerary import (
    ROAD_DETOUR_FACTOR,
    Itinerary,
    RideLeg,
    dedup_itineraries,
    haversine_m,
    pareto_filter,
    rank_labels,
    ride_estimate,
    sort_options,
)


def _ride(
    pattern: str,
    board: str = "A",
    alight: str = "B",
    minutes_min: float = 10.0,
    minutes_max: float = 15.0,
    intermediate_stops: int | None = 0,
) -> RideLeg:
    return RideLeg(
        pattern_id=f"pattern-{pattern}",
        route_id=f"route-{pattern}",
        route_code=pattern,
        mode="bus",
        direction_id=0,
        pattern_code=None,
        origin_label=None,
        destination_label=None,
        verification_status="unverified",
        board_stop_id=board,
        board_stop_name=board,
        board_sequence=1,
        alight_stop_id=alight,
        alight_stop_name=alight,
        alight_sequence=2,
        intermediate_stops=intermediate_stops,
        estimated_distance_m=1000.0,
        duration_min_s=minutes_min * 60.0,
        duration_max_s=minutes_max * 60.0,
    )


def _itinerary(
    ride: RideLeg,
    *,
    transfers: int = 0,
    walk: float = 0.0,
    walk_seconds: float = 0.0,
) -> Itinerary:
    return Itinerary(
        legs=(ride,),
        transfer_count=transfers,
        walk_distance_m=walk,
        duration_min_s=ride.duration_min_s + walk_seconds,
        duration_max_s=ride.duration_max_s + walk_seconds,
        warnings=(),
        confidence="verified",
    )


def test_dominated_candidate_is_removed_trade_off_kept() -> None:
    fast = _itinerary(_ride("138", minutes_min=10, minutes_max=12), walk=300.0)
    slow_same = _itinerary(_ride("100", minutes_min=15, minutes_max=18), walk=300.0)
    slow_short_walk = _itinerary(_ride("101", minutes_min=15, minutes_max=18), walk=50.0)

    kept = pareto_filter([fast, slow_same, slow_short_walk])

    assert fast in kept
    assert slow_short_walk in kept  # trade-off: longer but much less walking
    assert slow_same not in kept  # dominated: worse duration, same walking


def test_equal_metric_candidates_are_both_kept() -> None:
    a = _itinerary(_ride("138", minutes_min=10, minutes_max=12))
    b = _itinerary(_ride("145", minutes_min=10, minutes_max=12))

    kept = pareto_filter([a, b])

    # Neither is strictly better in any dimension: both are real alternatives.
    assert set(map(id, kept)) == {id(a), id(b)}


def test_labels_match_their_metrics() -> None:
    fast = _itinerary(_ride("138", minutes_min=10, minutes_max=12))
    walker = _itinerary(_ride("100", minutes_min=20, minutes_max=25), walk=100.0)
    simple = _itinerary(_ride("101", minutes_min=25, minutes_max=30))
    options = [fast, walker, simple]

    labels = rank_labels(options)

    assert labels["fastest"] == options.index(fast)
    assert labels["least_walking"] == options.index(fast)  # fast also walks least
    assert labels["fewest_transfers"] == options.index(fast)
    assert labels["simplest"] == options.index(fast)


def test_labels_tie_break_deterministically() -> None:
    a = _itinerary(_ride("138", minutes_min=10, minutes_max=12), walk=100.0)
    b = _itinerary(_ride("145", minutes_min=10, minutes_max=12), walk=100.0)

    labels = rank_labels([a, b])

    assert labels["fastest"] == 0  # first of the tied pair (deterministic)


def test_sort_options_orders_by_priority() -> None:
    fast = _itinerary(_ride("138", minutes_min=10, minutes_max=12), walk=300.0)
    walker = _itinerary(_ride("100", minutes_min=20, minutes_max=25), walk=50.0)

    by_fastest = sort_options([fast, walker], "fastest")
    by_walking = sort_options([fast, walker], "least_walking")

    assert by_fastest[0] is fast
    assert by_walking[0] is walker


def test_dedup_keeps_first_signature() -> None:
    a = _itinerary(_ride("138"))
    b = _itinerary(_ride("138"))
    other = _itinerary(_ride("145"))

    kept = dedup_itineraries([a, b, other])

    assert kept == [a, other]


def test_ride_estimate_uses_detour_and_speed_band() -> None:
    distance, seconds_min, seconds_max = ride_estimate(1000.0)

    assert distance == 1000.0 * ROAD_DETOUR_FACTOR
    # 18 km/h ≈ 0.05 m/s ... 12 km/h ≈ 0.3 m/s: min time < max time, both > 0.
    assert 0 < seconds_min < seconds_max
    assert abs(seconds_min - distance / (18.0 / 3.6)) < 1e-6
    assert abs(seconds_max - distance / (12.0 / 3.6)) < 1e-6


def test_haversine_matches_known_distance() -> None:
    # One degree of latitude ≈ 111.2 km.
    metres = haversine_m(79.85, 6.90, 79.85, 7.90)

    assert 110_000 < metres < 112_500
