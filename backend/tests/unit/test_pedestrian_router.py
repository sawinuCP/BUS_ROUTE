"""Unit tests for the walking-router adapter (Phase 3, ADR-0008).

The adapter is tested against canned Valhalla responses via httpx
MockTransport — no running Valhalla service is required.
"""

from __future__ import annotations

from collections.abc import Callable

import httpx
import pytest
from fastapi.testclient import TestClient

from app.modules.pedestrian.router import ValhallaWalkingRouter

# A MockTransport handler: callable[[Request], Response]
TripHandler = Callable[[httpx.Request], httpx.Response]

_TRIP = {
    "trip": {
        "summary": {"length": 5.42, "time": 3828},
        "legs": [
            {
                "maneuvers": [
                    {
                        "type": 1,
                        "instruction": "Walk west on the walkway.",
                        "length": 0.05,
                        "time": 36,
                        "street_names": [],
                    },
                    {
                        "type": 2,
                        "instruction": "Turn right onto Olcott Mawatha.",
                        "length": 1.2,
                        "time": 900,
                        "street_names": ["Olcott Mawatha"],
                    },
                ]
            }
        ],
    }
}


def _router(handler: TripHandler) -> ValhallaWalkingRouter:
    return ValhallaWalkingRouter(
        base_url="http://valhalla-test",
        timeout_seconds=2.0,
        transport=httpx.MockTransport(handler),
    )


@pytest.mark.asyncio
async def test_parses_valhalla_trip_into_walk_plan() -> None:
    router = _router(lambda request: httpx.Response(200, json=_TRIP))

    plan = await router.route_walk(79.85, 6.93, 79.86, 6.89)

    assert plan is not None
    assert plan.provider == "valhalla"
    assert plan.distance_m == pytest.approx(5420.0)
    assert plan.duration_s == pytest.approx(3828.0)
    assert len(plan.steps) == 2
    assert plan.steps[0].distance_m == pytest.approx(50.0)
    assert plan.steps[0].street_name is None
    assert plan.steps[1].street_name == "Olcott Mawatha"
    assert plan.steps[1].instruction == "Turn right onto Olcott Mawatha."


@pytest.mark.asyncio
async def test_http_error_returns_none_without_fabricating() -> None:
    router = _router(lambda request: httpx.Response(400, json={"error_code": 204}))

    assert await router.route_walk(79.85, 6.93, 79.86, 6.89) is None


@pytest.mark.asyncio
async def test_connection_error_returns_none() -> None:
    def raise_connect_error(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("service down", request=request)

    router = _router(raise_connect_error)

    assert await router.route_walk(79.85, 6.93, 79.86, 6.89) is None


@pytest.mark.asyncio
async def test_unparsable_payload_returns_none() -> None:
    router = _router(lambda request: httpx.Response(200, json={"unexpected": {}}))

    assert await router.route_walk(79.85, 6.93, 79.86, 6.89) is None


def test_endpoint_reports_no_path_honestly(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.api.routes import pedestrian as pedestrian_route_module

    async def no_path(*args: object) -> None:
        return None

    monkeypatch.setattr(pedestrian_route_module, "route_walk_between", no_path)

    response = client.get(
        "/api/v1/walking/route",
        params={"lon_from": 79.85, "lat_from": 6.93, "lon_to": 79.86, "lat_to": 6.89},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "no_path_found"
    assert body["provider"] == "valhalla"
    assert body["steps"] is None


def test_endpoint_returns_walk_plan(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    from app.api.routes import pedestrian as pedestrian_route_module
    from app.modules.pedestrian.router import WalkPlan, WalkStep

    async def fake_walk(*args: object) -> WalkPlan:
        return WalkPlan(
            distance_m=1250.0,
            duration_s=900.0,
            steps=(WalkStep(50.0, 36.0, "Walk west on the walkway.", None, 1),),
            provider="valhalla",
        )

    monkeypatch.setattr(pedestrian_route_module, "route_walk_between", fake_walk)

    response = client.get(
        "/api/v1/walking/route",
        params={"lon_from": 79.85, "lat_from": 6.93, "lon_to": 79.86, "lat_to": 6.89},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["distance_m"] == pytest.approx(1250.0)
    assert body["duration_s"] == pytest.approx(900.0)
    assert body["steps"][0]["instruction"] == "Walk west on the walkway."
