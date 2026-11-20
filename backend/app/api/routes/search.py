"""Public search and map-data endpoints (Phase 2 — plan items 1–6, 9).

- `GET /places/search` — unified multilingual search over stops, places,
  localities and routes. Ambiguous candidates are **listed, never
  auto-selected**; every result carries its verification status so the UI can
  distinguish confirmed from unconfirmed facts.
- `GET /stops?bbox=` — stops with coordinates inside a bbox, for map overlays.
- `POST /places/reverse-geocode` — provider-adapter geocoding; **no provider is
  configured yet** (owner decision pending), so it honestly returns
  `{"provider": null, "results": []}` rather than pretending to geocode.

These are public endpoints: no account required (product rule); rate limiting
and abuse protection arrive with the Phase 9 security work.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text

from app.modules.places.geocoder import get_geocoder
from app.modules.places.search import SearchService
from app.platform.db import get_session

router = APIRouter(tags=["search"])

_search = SearchService()

SessionDep = Annotated[Any, Depends(get_session)]


@router.get("/places/search")
async def search_places(
    session: SessionDep,
    q: str = Query(min_length=1, max_length=200),
    types: str | None = Query(
        default=None,
        description="Comma-separated entity types to include (stop,place,locality,route)",
    ),
    limit: int = Query(default=20, ge=1, le=50),
) -> Any:
    entity_types = {part.strip() for part in types.split(",") if part.strip()} if types else None
    hits = await _search.search(session, q, limit=limit, entity_types=entity_types)
    return {
        "query": q,
        "count": len(hits),
        "results": [hit.to_dict() for hit in hits],
        "note": (
            "Candidates are listed for user selection; ambiguous results are"
            " never auto-selected. verification_status 'unverified' means the"
            " fact has not been field-checked."
        ),
    }


@router.get("/stops")
async def stops_in_bbox(
    session: SessionDep,
    bbox: str = Query(
        description="Comma-separated minLon,minLat,maxLon,maxLat (WGS84, lon/lat order)"
    ),
    limit: int = Query(default=500, ge=1, le=2000),
) -> Any:
    try:
        min_lon, min_lat, max_lon, max_lat = (float(part) for part in bbox.split(","))
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail="bbox must be four comma-separated numbers: minLon,minLat,maxLon,maxLat",
        ) from exc
    if not (min_lon <= max_lon and min_lat <= max_lat):
        raise HTTPException(status_code=400, detail="bbox min values must not exceed max values")
    if not (-180 <= min_lon <= 180 and -90 <= min_lat <= 90):
        raise HTTPException(status_code=400, detail="bbox outside WGS84 bounds")

    rows = (
        await session.execute(
            text(
                "SELECT id, name, ST_X(location::geometry) AS lon,"
                " ST_Y(location::geometry) AS lat, stop_type, mode, verification_status"
                " FROM stops"
                " WHERE location IS NOT NULL"
                " AND ST_X(location::geometry) BETWEEN :min_lon AND :max_lon"
                " AND ST_Y(location::geometry) BETWEEN :min_lat AND :max_lat"
                " ORDER BY name LIMIT :limit"
            ),
            {
                "min_lon": min_lon,
                "min_lat": min_lat,
                "max_lon": max_lon,
                "max_lat": max_lat,
                "limit": limit,
            },
        )
    ).all()
    return {
        "bbox": {"min_lon": min_lon, "min_lat": min_lat, "max_lon": max_lon, "max_lat": max_lat},
        "count": len(rows),
        "stops": [
            {
                "entity_type": "stop",
                "entity_id": str(row.id),
                "name": row.name,
                "coordinates": {"lon": row.lon, "lat": row.lat},
                "stop_type": row.stop_type,
                "mode": row.mode,
                "verification_status": row.verification_status,
            }
            for row in rows
        ],
    }


@router.post("/places/reverse-geocode")
async def reverse_geocode(
    session: SessionDep,
    lon: float = Query(ge=-180, le=180),
    lat: float = Query(ge=-90, le=90),
) -> Any:
    geocoder = get_geocoder()
    results = await geocoder.reverse_geocode(lon, lat)
    return {
        "provider": geocoder.provider_name,
        "coordinates": {"lon": lon, "lat": lat},
        "results": [result.__dict__ for result in results],
        "note": "No geocoding provider is configured yet — manual selection remains the fallback.",
    }
