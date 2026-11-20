"""Geocoding provider adapter (canonical module: `places`).

Architecture rule: every external dependency sits behind an adapter interface.
**No geocoding provider is configured yet** (the provider choice — paid service
vs self-hosted OSM-based — is a pending owner decision; public Nominatim must
not be used as an unrestricted production service per the knowledge base).

Until a provider is ratified, `NoGeocoder` is the active adapter: it returns
no results and is honest about it. Manual map-pin selection remains the
product's geocoding fallback (US-002/US-005, plan Phase 2 item 9).
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any

logger = logging.getLogger(__name__)


class GeocoderAdapter(ABC):
    """Contract for a geocoding provider (forward + reverse)."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Identifier recorded in responses/logs (e.g. 'nominatim')."""

    @abstractmethod
    async def geocode(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        """Forward geocode a free-text query to candidate coordinates."""

    @abstractmethod
    async def reverse_geocode(self, lon: float, lat: float) -> list[dict[str, Any]]:
        """Reverse geocode coordinates to candidate place descriptions."""


class NoGeocoder(GeocoderAdapter):
    """Active default: no provider configured; returns no results, honestly."""

    def __init__(self) -> None:
        self._warned = False

    @property
    def provider_name(self) -> str:
        return "none"

    async def geocode(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        self._warn_once()
        return []

    async def reverse_geocode(self, lon: float, lat: float) -> list[dict[str, Any]]:
        self._warn_once()
        return []

    def _warn_once(self) -> None:
        if not self._warned:
            logger.info("no geocoding provider configured; manual selection is the fallback")
            self._warned = True


def get_geocoder() -> GeocoderAdapter:
    """Provider factory — extended when the owner ratifies a provider (ADR)."""
    return NoGeocoder()
