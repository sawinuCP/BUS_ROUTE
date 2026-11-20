"""Unified multilingual place/stop/route search (canonical module: `places`).

Searches canonical names AND language-tagged aliases (en/si/ta) across stops,
places, localities and routes using PostgreSQL trigram similarity plus prefix
matching. Ambiguity is handled by **listing** candidates — the product never
auto-selects an ambiguous result (architecture rule; US-001/US-004).

Scoring (transparent, highest first):
  1.0  exact canonical-name match
  0.9  canonical-name prefix match
  0.8  canonical-name substring match
  trigram similarity of the matched alias (floored at 0.5)
Ties broken by shorter matched text.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.places.normalize import normalize_text

_MIN_QUERY = 1


@dataclass(frozen=True)
class SearchHit:
    entity_type: str  # stop | place | locality | route
    entity_id: str
    name: str
    matched_text: str
    language: str  # 'canonical' or an ISO code from the matched alias
    score: float
    lon: float | None
    lat: float | None
    verification_status: str | None
    locality: str | None
    mode: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "name": self.name,
            "matched_text": self.matched_text,
            "matched_language": self.language,
            "score": round(self.score, 3),
            "coordinates": {"lon": self.lon, "lat": self.lat}
            if self.lon is not None and self.lat is not None
            else None,
            "verification_status": self.verification_status,
            "locality": self.locality,
            "mode": self.mode,
        }


class SearchService:
    async def search(
        self,
        session: AsyncSession,
        query: str,
        limit: int = 20,
        entity_types: set[str] | None = None,
    ) -> list[SearchHit]:
        normalized = normalize_text(query)
        if len(normalized) < _MIN_QUERY:
            return []
        pattern = f"%{normalized}%"
        prefix = f"{normalized}%"

        rows = (
            await session.execute(
                text(_SEARCH_SQL),
                {
                    "exact": normalized,
                    "prefix": prefix,
                    "pattern": pattern,
                    "norm": normalized,
                    "limit": limit * 3,  # over-fetch; dedupe keeps best per entity
                },
            )
        ).all()

        best: dict[tuple[str, str], Any] = {}
        for row in rows:
            key = (row.entity_type, str(row.entity_id))
            if key in best and best[key]["score"] >= row.score:
                continue
            best[key] = row._mapping

        hits = [SearchHit(**_to_hit(item)) for item in best.values()]
        if entity_types:
            hits = [hit for hit in hits if hit.entity_type in entity_types]
        hits.sort(key=lambda hit: (-hit.score, len(hit.matched_text), hit.entity_type))
        return hits[:limit]


def _to_hit(item: Any) -> dict[str, Any]:
    return {
        "entity_type": item["entity_type"],
        "entity_id": str(item["entity_id"]),
        "name": item["canonical"],
        "matched_text": item["matched_text"],
        "language": item["language"],
        "score": float(item["score"]),
        "lon": item["lon"],
        "lat": item["lat"],
        "verification_status": item["verification_status"],
        "locality": item["locality"],
        "mode": item["mode"],
    }


_SEARCH_SQL = """
    WITH c AS (
        SELECT 'stop'::text AS entity_type, s.id AS entity_id,
               s.name AS canonical,
               ST_X(s.location::geometry) AS lon, ST_Y(s.location::geometry) AS lat,
               s.verification_status, NULL::varchar AS locality, s.mode
        FROM stops s
        UNION ALL
        SELECT 'place', p.id, p.name,
               ST_X(p.location::geometry), ST_Y(p.location::geometry),
               p.verification_status, l.name, NULL
        FROM places p
        LEFT JOIN localities l ON l.id = p.locality_id
        UNION ALL
        SELECT 'locality', l.id, l.name,
               ST_X(l.location::geometry), ST_Y(l.location::geometry),
               NULL, NULL, NULL
        FROM localities l
        UNION ALL
        SELECT 'route', r.id, r.route_code || coalesce(' ' || r.route_name, ''),
               NULL, NULL, r.status, NULL, r.mode
        FROM transport_routes r
    ),
    name_matches AS (
        SELECT c.*, c.canonical AS matched_text, 'canonical' AS language,
               CASE WHEN lower(c.canonical) = :exact THEN 1.0
                    WHEN lower(c.canonical) LIKE :prefix THEN 0.9
                    ELSE 0.8 END AS score
        FROM c WHERE c.canonical ILIKE :pattern
    ),
    alias_matches AS (
        SELECT c.*, a.alias AS matched_text, a.language AS language,
               GREATEST(similarity(a.alias, :norm), 0.5) AS score
        FROM entity_aliases a
        JOIN c ON c.entity_type = a.entity_type AND c.entity_id = a.entity_id
        WHERE a.alias % :norm OR a.alias ILIKE :pattern
    )
    SELECT entity_type, entity_id, canonical, lon, lat, verification_status,
           locality, mode, matched_text, language, score
    FROM (SELECT * FROM name_matches UNION ALL SELECT * FROM alias_matches) m
    ORDER BY score DESC, length(matched_text), entity_type, entity_id
    LIMIT :limit
"""
