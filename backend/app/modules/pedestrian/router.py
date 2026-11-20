"""Walking-router adapter (canonical module: `pedestrian`, ADR-0001).

Architecture rule: every external dependency sits behind an adapter interface.
The routing engine (ADR-0002 baseline: "Valhalla walking adapter pending
prototype") is reached only through `WalkingRouter`; the deterministic planner
(Phase 4) consumes `WalkPlan` objects and never Valhalla's response format.

Domain rules encoded here:
- WGS84 lon/lat order at the API boundary; metres/seconds internally.
- Failure is honest: connection errors, unsupported paths and HTTP errors
  return `None` — the planner must never invent a walking leg.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)

# Valhalla /route maneuver types we care about at this stage are kept opaque;
# Phase 5 will map them to deterministic instruction templates.
_WALKING_COSTING = "pedestrian"


@dataclass(frozen=True)
class WalkStep:
    """One walking maneuver, in metres/seconds (internal units)."""

    distance_m: float
    duration_s: float
    instruction: str | None
    street_name: str | None
    maneuver_type: int | None


@dataclass(frozen=True)
class WalkPlan:
    """A pedestrian path between two points, ready for itinerary assembly."""

    distance_m: float
    duration_s: float
    steps: tuple[WalkStep, ...]
    provider: str

    @property
    def summary(self) -> str:
        """Human summary of the walk (en; localisation is Phase 5)."""
        steps_desc = f"{len(self.steps)} steps" if self.steps else "no steps"
        return f"{self.distance_m:.0f} m, {self.duration_s / 60:.0f} min ({steps_desc})"


class WalkingRouter(ABC):
    """Contract for a pedestrian routing provider."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Identifier recorded in responses/logs (e.g. 'valhalla')."""

    @abstractmethod
    async def route_walk(
        self,
        lon_from: float,
        lat_from: float,
        lon_to: float,
        lat_to: float,
    ) -> WalkPlan | None:
        """Route a walking leg between two WGS84 points.

        Returns `None` when no path can be produced (unreachable, outside
        covered area, service unavailable) — callers must treat `None` as
        "no walking leg", never substitute an estimate.
        """


class ValhallaWalkingRouter(WalkingRouter):
    """Walking router backed by a local Valhalla /route HTTP service.

    Requires a pre-built tile extract (see `backend/scripts/
    build_valhalla_tiles.py`); the service container is defined in
    `infra/docker/compose.yaml` (pinned image, I-22).
    """

    def __init__(
        self,
        base_url: str,
        timeout_seconds: float = 10.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds
        self._transport = transport

    @property
    def provider_name(self) -> str:
        return "valhalla"

    async def route_walk(
        self,
        lon_from: float,
        lat_from: float,
        lon_to: float,
        lat_to: float,
    ) -> WalkPlan | None:
        payload = {
            "locations": [
                {"lat": lat_from, "lon": lon_from},
                {"lat": lat_to, "lon": lon_to},
            ],
            "costing": _WALKING_COSTING,
            "directions_options": {"units": "kilometers"},
            "id": "walking-adapter",
        }
        try:
            async with httpx.AsyncClient(
                base_url=self._base_url,
                timeout=self._timeout_seconds,
                transport=self._transport,
            ) as client:
                response = await client.post("/route", json=payload)
        except httpx.HTTPError as exc:
            logger.warning("valhalla request failed: %s", type(exc).__name__)
            return None

        if response.status_code != 200:
            logger.warning(
                "valhalla returned HTTP %s (no walking leg will be fabricated)",
                response.status_code,
            )
            return None

        try:
            trip = response.json()["trip"]
            return _parse_trip(trip, self.provider_name)
        except (KeyError, TypeError, ValueError) as exc:
            logger.warning("unparsable valhalla response: %s", type(exc).__name__)
            return None


def get_walking_router() -> WalkingRouter:
    """Factory — extended when a second engine is ratified (ADR-0008)."""
    from app.platform.config import get_settings

    settings = get_settings()
    return ValhallaWalkingRouter(
        base_url=settings.valhalla_base_url,
        timeout_seconds=settings.valhalla_timeout_seconds,
    )


async def route_walk_between(
    lon_from: float,
    lat_from: float,
    lon_to: float,
    lat_to: float,
) -> WalkPlan | None:
    """Module-level convenience: route a walk via the configured adapter."""
    router = get_walking_router()
    return await router.route_walk(lon_from, lat_from, lon_to, lat_to)


def _parse_trip(trip: dict, provider: str) -> WalkPlan:
    """Convert a Valhalla `trip` object into a `WalkPlan`.

    Valhalla reports lengths in kilometres and times in seconds; convert to
    internal units (metres/seconds) here, at the adapter boundary.
    """
    summary = trip["summary"]
    steps: list[WalkStep] = []
    for leg in trip.get("legs", []):
        for maneuver in leg.get("maneuvers", []):
            street_names = maneuver.get("street_names") or []
            steps.append(
                WalkStep(
                    distance_m=float(maneuver.get("length", 0.0)) * 1000.0,
                    duration_s=float(maneuver.get("time", 0.0)),
                    instruction=maneuver.get("instruction"),
                    street_name=street_names[0] if street_names else None,
                    maneuver_type=maneuver.get("type"),
                )
            )
    return WalkPlan(
        distance_m=float(summary["length"]) * 1000.0,
        duration_s=float(summary["time"]),
        steps=tuple(steps),
        provider=provider,
    )
