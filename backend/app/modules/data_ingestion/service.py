"""Ingestion framework services (canonical module: `data_ingestion`).

Implements the plan §5.2 lifecycle for one source sync:

    fetch → checksum → archive (dedupe) → parse → validate → upsert →
    record diffs (dataset_version_entities) → candidate dataset version

Publication (`DatasetVersionService.publish`) is a separate, explicit step:
candidate versions never affect the active network until reviewed. Rollback is
the pointer-flip semantics of implementation plan §5.2 rule 7 (see ADR-0007).

Idempotency: an unchanged source payload (same sha256) short-circuits the run;
each external record links to exactly one canonical entity via
`source_records.canonical_entity_*`, so re-runs update rather than duplicate.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.data_ingestion.adapters.base import RawRecord, SourceAdapter
from app.modules.data_ingestion.archive import SnapshotArchive, sha256_hex
from app.modules.data_ingestion.models import (
    ActiveDataset,
    DatasetVersion,
    DatasetVersionEntity,
    DataSource,
    SourceRecord,
    SourceSnapshot,
    SyncRun,
)
from app.modules.data_ingestion.quality import validate_records
from app.modules.places.models import EntityAlias, Place
from app.modules.transport.models import (
    RoutePattern,
    RoutePatternStop,
    RouteShape,
    Stop,
    StopAccessPoint,
    TransportAgency,
    TransportRoute,
)

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(UTC)


# ---------------------------------------------------------------------------
# entity upsert handlers
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class UpsertResult:
    entity_type: str
    entity_id: uuid.UUID
    operation: str  # added | updated | unchanged


async def _stored_point_wkt(session: AsyncSession, table: str, entity_id: uuid.UUID) -> str | None:
    """Canonical stored location as WKT, for precise change detection."""
    row = await session.execute(
        text(f"SELECT ST_AsText(location::geometry) FROM {table} WHERE id = :i"), {"i": entity_id}
    )
    value = row.scalar_one_or_none()
    return str(value) if value is not None else None


class EntityUpsert:
    """Upserts one normalised record into its canonical table, idempotently."""

    entity_type: str

    async def upsert(
        self,
        session: AsyncSession,
        source: DataSource,
        snapshot_id: uuid.UUID,
        record: RawRecord,
    ) -> UpsertResult:
        raise NotImplementedError


async def _find_canonical_link(
    session: AsyncSession, source_id: uuid.UUID, external_id: str, entity_type: str
) -> SourceRecord | None:
    result = await session.execute(
        select(SourceRecord).where(
            SourceRecord.data_source_id == source_id,
            SourceRecord.external_id == external_id,
            SourceRecord.canonical_entity_type == entity_type,
        )
    )
    return result.scalar_one_or_none()


async def _upsert_aliases(
    session: AsyncSession, entity_type: str, entity_id: uuid.UUID, payload: dict
) -> int:
    """Insert missing aliases for an entity; returns the count added."""
    added = 0
    for alias_item in payload.get("aliases", []) or []:
        language = alias_item.get("language")
        alias_text = alias_item.get("alias")
        if not language or not alias_text:
            raise ValueError("alias entries require 'language' and 'alias'")
        existing = await session.execute(
            select(EntityAlias).where(
                EntityAlias.entity_type == entity_type,
                EntityAlias.entity_id == entity_id,
                EntityAlias.language == language,
                EntityAlias.alias == alias_text,
            )
        )
        if existing.scalar_one_or_none() is None:
            session.add(
                EntityAlias(
                    entity_type=entity_type,
                    entity_id=entity_id,
                    language=language,
                    alias=alias_text,
                    transliteration=alias_item.get("transliteration"),
                )
            )
            added += 1
    return added


class StopUpsert(EntityUpsert):
    entity_type = "stop"

    async def upsert(
        self, session: AsyncSession, source: DataSource, snapshot_id: uuid.UUID, record: RawRecord
    ) -> UpsertResult:
        payload = record.payload
        location = None
        lon, lat = payload.get("lon"), payload.get("lat")
        if lon is not None and lat is not None:
            location = f"POINT({lon} {lat})"

        link = await _find_canonical_link(session, source.id, record.external_id, self.entity_type)
        if link is not None and link.canonical_entity_id is not None:
            stop = await session.get(Stop, link.canonical_entity_id)
            if stop is None:
                raise ValueError(f"linked stop {link.canonical_entity_id} no longer exists")
            new_name = payload["name"]
            new_type = payload.get("stop_type")
            new_mode = payload.get("mode", "bus")
            changed = stop.name != new_name or stop.stop_type != new_type or stop.mode != new_mode
            if location is not None and location != await _stored_point_wkt(
                session, "stops", stop.id
            ):
                stop.location = location
                changed = True
            stop.name = new_name
            stop.stop_type = new_type
            stop.mode = new_mode
            aliases_added = await _upsert_aliases(session, "stop", stop.id, payload)
            changed = changed or aliases_added > 0
            await session.flush()
            return UpsertResult(self.entity_type, stop.id, "updated" if changed else "unchanged")

        stop = Stop(
            name=payload["name"],
            mode=payload.get("mode", "bus"),
            location=location,
            stop_type=payload.get("stop_type"),
        )
        session.add(stop)
        await session.flush()
        await _upsert_aliases(session, "stop", stop.id, payload)
        session.add(
            SourceRecord(
                data_source_id=source.id,
                snapshot_id=snapshot_id,
                external_id=record.external_id,
                entity_hint=record.entity_hint,
                canonical_entity_type=self.entity_type,
                canonical_entity_id=stop.id,
                raw_payload=record.payload,
            )
        )
        return UpsertResult(self.entity_type, stop.id, "added")


class RouteUpsert(EntityUpsert):
    entity_type = "route"

    async def upsert(
        self, session: AsyncSession, source: DataSource, snapshot_id: uuid.UUID, record: RawRecord
    ) -> UpsertResult:
        payload = record.payload
        agency_id = None
        agency_name = payload.get("agency_name")
        if agency_name:
            result = await session.execute(
                select(TransportAgency).where(TransportAgency.name == agency_name)
            )
            agency = result.scalar_one_or_none()
            if agency is None:
                agency = TransportAgency(name=agency_name)
                session.add(agency)
                await session.flush()
            agency_id = agency.id

        link = await _find_canonical_link(session, source.id, record.external_id, self.entity_type)
        if link is not None and link.canonical_entity_id is not None:
            route = await session.get(TransportRoute, link.canonical_entity_id)
            if route is None:
                raise ValueError(f"linked route {link.canonical_entity_id} no longer exists")
            new_code = payload["route_code"]
            new_name = payload.get("route_name")
            new_mode = payload.get("mode", "bus")
            changed = (
                route.route_code != new_code
                or route.route_name != new_name
                or route.mode != new_mode
                or route.agency_id != agency_id
            )
            route.route_code = new_code
            route.route_name = new_name
            route.mode = new_mode
            route.agency_id = agency_id
            await session.flush()
            return UpsertResult(self.entity_type, route.id, "updated" if changed else "unchanged")

        route = TransportRoute(
            agency_id=agency_id,
            route_code=payload["route_code"],
            route_name=payload.get("route_name"),
            mode=payload.get("mode", "bus"),
        )
        session.add(route)
        await session.flush()
        session.add(
            SourceRecord(
                data_source_id=source.id,
                snapshot_id=snapshot_id,
                external_id=record.external_id,
                entity_hint=record.entity_hint,
                canonical_entity_type=self.entity_type,
                canonical_entity_id=route.id,
                raw_payload=record.payload,
            )
        )
        return UpsertResult(self.entity_type, route.id, "added")


class PlaceUpsert(EntityUpsert):
    entity_type = "place"

    async def upsert(
        self, session: AsyncSession, source: DataSource, snapshot_id: uuid.UUID, record: RawRecord
    ) -> UpsertResult:
        payload = record.payload
        location = None
        lon, lat = payload.get("lon"), payload.get("lat")
        if lon is not None and lat is not None:
            location = f"POINT({lon} {lat})"

        link = await _find_canonical_link(session, source.id, record.external_id, self.entity_type)
        if link is not None and link.canonical_entity_id is not None:
            place = await session.get(Place, link.canonical_entity_id)
            if place is None:
                raise ValueError(f"linked place {link.canonical_entity_id} no longer exists")
            new_name = payload["name"]
            new_category = payload.get("category")
            changed = place.name != new_name or place.category != new_category
            if location is not None and location != await _stored_point_wkt(
                session, "places", place.id
            ):
                place.location = location
                changed = True
            place.name = new_name
            place.category = new_category
            aliases_added = await _upsert_aliases(session, "place", place.id, payload)
            changed = changed or aliases_added > 0
            await session.flush()
            return UpsertResult(self.entity_type, place.id, "updated" if changed else "unchanged")

        place = Place(name=payload["name"], category=payload.get("category"), location=location)
        session.add(place)
        await session.flush()
        await _upsert_aliases(session, "place", place.id, payload)
        session.add(
            SourceRecord(
                data_source_id=source.id,
                snapshot_id=snapshot_id,
                external_id=record.external_id,
                entity_hint=record.entity_hint,
                canonical_entity_type=self.entity_type,
                canonical_entity_id=place.id,
                raw_payload=record.payload,
            )
        )
        return UpsertResult(self.entity_type, place.id, "added")


class PatternUpsert(EntityUpsert):
    """A route variant/direction; references its route via a source-record link."""

    entity_type = "route_pattern"

    async def upsert(
        self, session: AsyncSession, source: DataSource, snapshot_id: uuid.UUID, record: RawRecord
    ) -> UpsertResult:
        payload = record.payload
        route_link = await _find_canonical_link(
            session, source.id, payload["route_external_ref"], "route"
        )
        if route_link is None or route_link.canonical_entity_id is None:
            raise ValueError(
                f"pattern {record.external_id} references route"
                f" '{payload['route_external_ref']}' which has no canonical link yet"
            )

        link = await _find_canonical_link(session, source.id, record.external_id, self.entity_type)
        fields = (
            payload.get("pattern_code"),
            int(payload.get("direction_id", 0)),
            payload.get("origin_label"),
            payload.get("destination_label"),
            payload.get("variant_description"),
        )
        if link is not None and link.canonical_entity_id is not None:
            pattern = await session.get(RoutePattern, link.canonical_entity_id)
            if pattern is None:
                raise ValueError(f"linked pattern {link.canonical_entity_id} no longer exists")
            changed = (
                pattern.route_id != route_link.canonical_entity_id
                or pattern.pattern_code != fields[0]
                or pattern.direction_id != fields[1]
                or pattern.origin_label != fields[2]
                or pattern.destination_label != fields[3]
                or pattern.variant_description != fields[4]
            )
            pattern.route_id = route_link.canonical_entity_id
            pattern.pattern_code = fields[0]
            pattern.direction_id = fields[1]
            pattern.origin_label = fields[2]
            pattern.destination_label = fields[3]
            pattern.variant_description = fields[4]
            await session.flush()
            return UpsertResult(self.entity_type, pattern.id, "updated" if changed else "unchanged")

        pattern = RoutePattern(
            route_id=route_link.canonical_entity_id,
            pattern_code=fields[0],
            direction_id=fields[1],
            origin_label=fields[2],
            destination_label=fields[3],
            variant_description=fields[4],
        )
        session.add(pattern)
        await session.flush()
        session.add(
            SourceRecord(
                data_source_id=source.id,
                snapshot_id=snapshot_id,
                external_id=record.external_id,
                entity_hint=record.entity_hint,
                canonical_entity_type=self.entity_type,
                canonical_entity_id=pattern.id,
                raw_payload=record.payload,
            )
        )
        return UpsertResult(self.entity_type, pattern.id, "added")


class PatternStopUpsert(EntityUpsert):
    """An ordered stop call; references pattern + stop via source-record links."""

    entity_type = "route_pattern_stop"

    async def upsert(
        self, session: AsyncSession, source: DataSource, snapshot_id: uuid.UUID, record: RawRecord
    ) -> UpsertResult:
        payload = record.payload
        pattern_link = await _find_canonical_link(
            session, source.id, payload["pattern_external_ref"], "route_pattern"
        )
        if pattern_link is None or pattern_link.canonical_entity_id is None:
            # Unresolvable references are recorded as failed records and surface
            # in the quality report — never guessed.
            raise ValueError(f"unresolved reference: pattern '{payload['pattern_external_ref']}'")
        stop_link = await _find_canonical_link(
            session, source.id, payload["stop_external_ref"], "stop"
        )
        if stop_link is None or stop_link.canonical_entity_id is None:
            raise ValueError(f"unresolved reference: stop '{payload['stop_external_ref']}'")

        pattern_id = pattern_link.canonical_entity_id
        stop_id = stop_link.canonical_entity_id
        sequence = int(payload["sequence"])
        boarding = bool(payload.get("boarding_allowed", True))
        alighting = bool(payload.get("alighting_allowed", True))

        result = await session.execute(
            select(RoutePatternStop).where(
                RoutePatternStop.pattern_id == pattern_id,
                RoutePatternStop.sequence == sequence,
            )
        )
        existing = result.scalar_one_or_none()
        if existing is not None:
            changed = (
                existing.stop_id != stop_id
                or existing.boarding_allowed != boarding
                or existing.alighting_allowed != alighting
            )
            existing.stop_id = stop_id
            existing.boarding_allowed = boarding
            existing.alighting_allowed = alighting
            await session.flush()
            return UpsertResult(
                self.entity_type, existing.id, "updated" if changed else "unchanged"
            )

        call = RoutePatternStop(
            pattern_id=pattern_id,
            stop_id=stop_id,
            sequence=sequence,
            boarding_allowed=boarding,
            alighting_allowed=alighting,
        )
        session.add(call)
        await session.flush()
        return UpsertResult(self.entity_type, call.id, "added")


class ShapeUpsert(EntityUpsert):
    """A route pattern's geometry from OSM member ways; links pattern → shape.

    The shape itself is a new canonical row (its identity is the SourceRecord
    link `osm-relation/<id>/shape`); the pattern's `shape_id` points at it.
    Gaps are preserved honestly: coordinates missing from the snapshot are not
    interpolated, and the pattern keeps whatever geometry was recoverable.
    """

    entity_type = "route_shape"

    async def upsert(
        self, session: AsyncSession, source: DataSource, snapshot_id: uuid.UUID, record: RawRecord
    ) -> UpsertResult:
        payload = record.payload
        pattern_link = await _find_canonical_link(
            session, source.id, payload["pattern_external_ref"], "route_pattern"
        )
        if pattern_link is None or pattern_link.canonical_entity_id is None:
            # Unresolvable references are recorded as failed records and surface
            # in the quality report — never guessed.
            raise ValueError(f"unresolved reference: pattern '{payload['pattern_external_ref']}'")

        coordinates = payload["coordinates"]
        line = ", ".join(f"{lon} {lat}" for lon, lat in coordinates)
        wkt = f"MULTILINESTRING(({line}))"
        pattern_id = pattern_link.canonical_entity_id

        link = await _find_canonical_link(session, source.id, record.external_id, self.entity_type)
        if link is not None and link.canonical_entity_id is not None:
            shape = await session.get(RouteShape, link.canonical_entity_id)
            if shape is None:
                raise ValueError(f"linked shape {link.canonical_entity_id} no longer exists")
            stored_wkt = await _stored_shape_wkt(session, shape.id)
            # Both sides normalised the same way (whitespace stripped) so an
            # unchanged coordinate list reports `unchanged`, not `updated`.
            changed = stored_wkt != wkt.replace(" ", "")
            if changed:
                shape.geometry = wkt
            await session.flush()
            await _link_pattern_shape(session, pattern_id, shape.id)
            return UpsertResult(self.entity_type, shape.id, "updated" if changed else "unchanged")

        shape = RouteShape(data_source_id=source.id, geometry=wkt)
        session.add(shape)
        await session.flush()
        session.add(
            SourceRecord(
                data_source_id=source.id,
                snapshot_id=snapshot_id,
                external_id=record.external_id,
                entity_hint=record.entity_hint,
                canonical_entity_type=self.entity_type,
                canonical_entity_id=shape.id,
                raw_payload=record.payload,
            )
        )
        await _link_pattern_shape(session, pattern_id, shape.id)
        return UpsertResult(self.entity_type, shape.id, "added")


async def _stored_shape_wkt(session: AsyncSession, shape_id: uuid.UUID) -> str | None:
    """Canonical stored shape geometry as normalised WKT, for change detection."""
    row = await session.execute(
        text("SELECT ST_AsText(geometry::geometry) FROM route_shapes WHERE id = :i"),
        {"i": shape_id},
    )
    value = row.scalar_one_or_none()
    if value is None:
        return None
    # ST_AsText normalises floats; compare with whitespace stripped so our
    # generated WKT and the stored text agree on identical coordinates.
    return str(value).replace(" ", "")


async def _link_pattern_shape(
    session: AsyncSession, pattern_id: uuid.UUID, shape_id: uuid.UUID
) -> None:
    pattern = await session.get(RoutePattern, pattern_id)
    if pattern is None:
        raise ValueError(f"pattern {pattern_id} no longer exists")
    if pattern.shape_id != shape_id:
        pattern.shape_id = shape_id
        await session.flush()


class AccessPointUpsert(EntityUpsert):
    """A stop's default boarding/alighting access point at the mapped node.

    The physical roadside position/type is unknown until field-checked, so the
    row carries only the mapped coordinate and honest nulls elsewhere. It gives
    access/egress walking and the transfer graph their canonical endpoints.
    """

    entity_type = "stop_access_point"

    async def upsert(
        self, session: AsyncSession, source: DataSource, snapshot_id: uuid.UUID, record: RawRecord
    ) -> UpsertResult:
        payload = record.payload
        stop_link = await _find_canonical_link(
            session, source.id, payload["stop_external_ref"], "stop"
        )
        if stop_link is None or stop_link.canonical_entity_id is None:
            # Unresolvable references are recorded as failed records and surface
            # in the quality report — never guessed.
            raise ValueError(f"unresolved reference: stop '{payload['stop_external_ref']}'")
        stop_id = stop_link.canonical_entity_id
        location = f"POINT({payload['lon']} {payload['lat']})"

        link = await _find_canonical_link(session, source.id, record.external_id, self.entity_type)
        if link is not None and link.canonical_entity_id is not None:
            access_point = await session.get(StopAccessPoint, link.canonical_entity_id)
            if access_point is None:
                raise ValueError(f"linked access point {link.canonical_entity_id} no longer exists")
            stored = await _stored_point_wkt(session, "stop_access_points", access_point.id)
            changed = access_point.stop_id != stop_id or stored != location
            access_point.stop_id = stop_id
            if stored != location:
                access_point.location = location
            await session.flush()
            return UpsertResult(
                self.entity_type, access_point.id, "updated" if changed else "unchanged"
            )

        access_point = StopAccessPoint(stop_id=stop_id, location=location)
        session.add(access_point)
        await session.flush()
        session.add(
            SourceRecord(
                data_source_id=source.id,
                snapshot_id=snapshot_id,
                external_id=record.external_id,
                entity_hint=record.entity_hint,
                canonical_entity_type=self.entity_type,
                canonical_entity_id=access_point.id,
                raw_payload=record.payload,
            )
        )
        return UpsertResult(self.entity_type, access_point.id, "added")


UPSERTERS: dict[str, EntityUpsert] = {
    StopUpsert.entity_type: StopUpsert(),
    RouteUpsert.entity_type: RouteUpsert(),
    PlaceUpsert.entity_type: PlaceUpsert(),
    PatternUpsert.entity_type: PatternUpsert(),
    PatternStopUpsert.entity_type: PatternStopUpsert(),
    ShapeUpsert.entity_type: ShapeUpsert(),
    AccessPointUpsert.entity_type: AccessPointUpsert(),
}


@dataclass
class SyncOutcome:
    """Result summary of one sync run (returned before commit; caller commits)."""

    run_id: uuid.UUID
    status: str
    records_in: int = 0
    records_added: int = 0
    records_updated: int = 0
    records_unchanged: int = 0
    records_failed: int = 0
    version_label: str | None = None
    unchanged: bool = False
    quarantine_errors: list[str] = field(default_factory=list)


class IngestionService:
    """Orchestrates one idempotent source sync (plan §5.2)."""

    def __init__(self, archive: SnapshotArchive) -> None:
        self._archive = archive

    async def run_sync(
        self, session: AsyncSession, source: DataSource, adapter: SourceAdapter
    ) -> SyncOutcome:
        run = SyncRun(data_source_id=source.id, started_at=_utcnow(), status="started")
        session.add(run)
        await session.flush()

        try:
            fetched = adapter.fetch()
        except Exception as exc:  # noqa: BLE001 - provider failures must not 500 the API
            # Plan §5.2 rule 3: a failed source sync leaves the previous
            # version serving. Canonical data untouched.
            run.status = "failed"
            run.finished_at = _utcnow()
            run.error = f"fetch failed: {type(exc).__name__}"
            await session.flush()
            logger.warning(
                "sync fetch failed",
                extra={"source": source.name, "error_type": type(exc).__name__},
            )
            return SyncOutcome(run_id=run.id, status="failed", quarantine_errors=[run.error or ""])
        checksum = sha256_hex(fetched.content)

        # Idempotency short-circuit: this exact payload is already archived.
        existing_snapshot = await session.execute(
            select(SourceSnapshot).where(
                SourceSnapshot.data_source_id == source.id,
                SourceSnapshot.checksum_sha256 == checksum,
            )
        )
        existing = existing_snapshot.scalar_one_or_none()
        if existing is not None:
            run.snapshot_id = existing.id
            run.status = "succeeded"
            run.finished_at = _utcnow()
            await session.flush()
            logger.info(
                "sync unchanged",
                extra={"source": source.name, "checksum": checksum, "run_id": str(run.id)},
            )
            return SyncOutcome(run_id=run.id, status="succeeded", unchanged=True)

        storage_uri = self._archive.store(source.name, checksum, fetched)
        snapshot = SourceSnapshot(
            data_source_id=source.id,
            fetched_at=_utcnow(),
            storage_uri=storage_uri,
            checksum_sha256=checksum,
            content_type=fetched.content_type,
            extra_metadata=fetched.metadata,
        )
        session.add(snapshot)
        await session.flush()
        run.snapshot_id = snapshot.id

        try:
            records = adapter.parse(fetched.content, fetched.metadata)
        except Exception as exc:  # noqa: BLE001 - parse failure quarantines the run
            run.status = "quarantined"
            run.records_failed = 1
            run.finished_at = _utcnow()
            run.error = f"parse failed: {type(exc).__name__}"
            await session.flush()
            return SyncOutcome(
                run_id=run.id, status="quarantined", quarantine_errors=[run.error or ""]
            )

        reports = validate_records(records)
        failures = [report for report in reports if not report.passed]
        if failures:
            error_lines = [
                f"{report.record.external_id} ({report.record.entity_hint}): {msg}"
                for report in failures
                for msg in report.errors
            ][:50]
            run.status = "quarantined"
            run.records_in = len(records)
            run.records_failed = len(failures)
            run.finished_at = _utcnow()
            run.error = "; ".join(error_lines)
            await session.flush()
            logger.warning(
                "sync quarantined",
                extra={"source": source.name, "run_id": str(run.id), "failures": len(failures)},
            )
            return SyncOutcome(
                run_id=run.id,
                status="quarantined",
                records_in=len(records),
                records_failed=len(failures),
                quarantine_errors=error_lines,
            )

        version = DatasetVersion(
            version_label=f"{source.name}-{run.id.hex[:8]}",
            status="candidate",
            validation_summary={
                "records": len(records),
                "quality_rules": "builtin",
                "adapter_version": adapter.adapter_version,
            },
        )
        session.add(version)
        await session.flush()

        added = updated = failed = unchanged = 0
        for record in records:
            upserter = UPSERTERS.get(record.entity_hint)
            if upserter is None:
                failed += 1
                continue
            try:
                async with session.begin_nested():
                    result = await upserter.upsert(session, source, snapshot.id, record)
                    if result.operation != "unchanged":
                        session.add(
                            DatasetVersionEntity(
                                dataset_version_id=version.id,
                                entity_type=result.entity_type,
                                entity_id=result.entity_id,
                                operation=result.operation,
                                changed_at=_utcnow(),
                            )
                        )
            except Exception as exc:  # noqa: BLE001 - record-level failure, run continues
                failed += 1
                logger.warning(
                    "record upsert failed",
                    extra={
                        "source": source.name,
                        "external_id": record.external_id,
                        "error_type": type(exc).__name__,
                    },
                )
                continue
            if result.operation == "added":
                added += 1
            elif result.operation == "updated":
                updated += 1
            else:
                unchanged += 1

        run.status = "succeeded"
        run.records_in = len(records)
        run.records_added = added
        run.records_updated = updated
        run.records_failed = failed
        run.finished_at = _utcnow()
        run.parser_version = adapter.adapter_version
        await session.flush()

        return SyncOutcome(
            run_id=run.id,
            status="succeeded",
            records_in=len(records),
            records_added=added,
            records_updated=updated,
            records_failed=failed,
            records_unchanged=unchanged,
            version_label=version.version_label,
        )


class DatasetVersionService:
    """Candidate/publish/rollback lifecycle for dataset versions (ADR-0006/0007)."""

    async def create_candidate(
        self, session: AsyncSession, label: str | None = None, notes: str | None = None
    ) -> DatasetVersion:
        version = DatasetVersion(
            version_label=label or f"candidate-{uuid.uuid4().hex[:8]}",
            status="candidate",
            notes=notes,
        )
        session.add(version)
        await session.flush()
        return version

    async def get(self, session: AsyncSession, version_id: uuid.UUID) -> DatasetVersion:
        version = await session.get(DatasetVersion, version_id)
        if version is None:
            from fastapi import HTTPException

            raise HTTPException(status_code=404, detail="dataset version not found")
        return version

    async def active_version(self, session: AsyncSession) -> DatasetVersion | None:
        result = await session.execute(select(ActiveDataset).where(ActiveDataset.id == 1))
        active = result.scalar_one_or_none()
        if active is None:
            return None
        return await session.get(DatasetVersion, active.dataset_version_id)

    async def publish(self, session: AsyncSession, version_id: uuid.UUID) -> DatasetVersion:
        version = await self.get(session, version_id)
        if version.status == "published":
            active = await self.active_version(session)
            if active is not None and active.id == version.id:
                return version  # idempotent
        if version.status not in ("candidate", "rejected"):
            from fastapi import HTTPException

            raise HTTPException(
                status_code=409, detail=f"cannot publish version in status '{version.status}'"
            )

        # Supersede the currently active published version (at most one exists).
        current = await self.active_version(session)
        if current is not None and current.status == "published":
            current.status = "superseded"

        version.status = "published"
        version.published_at = _utcnow()

        result = await session.execute(select(ActiveDataset).where(ActiveDataset.id == 1))
        active_row = result.scalar_one_or_none()
        if active_row is None:
            session.add(ActiveDataset(id=1, dataset_version_id=version.id, activated_at=_utcnow()))
        else:
            active_row.dataset_version_id = version.id
            active_row.activated_at = _utcnow()

        logger.info("dataset version published", extra={"version": version.version_label})
        return version

    async def rollback(self, session: AsyncSession, target_version_id: uuid.UUID) -> DatasetVersion:
        """Pointer-flip rollback (plan §5.2 rule 7): active → target.

        Note (ADR-0007): with mutable canonical tables this restores the
        *active version pointer*; re-materialising the target's entity data is
        done by re-running the target version's sources (snapshots are
        archived), which is the documented operational runbook.
        """
        target = await self.get(session, target_version_id)
        if target.status not in ("published", "superseded"):
            from fastapi import HTTPException

            raise HTTPException(
                status_code=409,
                detail="rollback target must be a previously published version",
            )
        current = await self.active_version(session)
        if current is not None and current.id == target.id:
            return target  # already active
        if current is not None and current.status == "published":
            current.status = "superseded"
        result = await session.execute(select(ActiveDataset).where(ActiveDataset.id == 1))
        active_row = result.scalar_one_or_none()
        if active_row is None:
            session.add(ActiveDataset(id=1, dataset_version_id=target.id, activated_at=_utcnow()))
        else:
            active_row.dataset_version_id = target.id
            active_row.activated_at = _utcnow()
        logger.info("dataset rollback", extra={"target": target.version_label})
        return target


class SourceRegistry:
    """Registry CRUD for data sources (plan Phase 1 item 1)."""

    async def create_source(self, session: AsyncSession, **fields: Any) -> DataSource:
        source = DataSource(**fields)
        session.add(source)
        try:
            await session.flush()
        except Exception as exc:  # noqa: BLE001 - surface duplicates as user error
            if "uq" in str(exc).lower() or "unique" in str(exc).lower():
                raise ValueError(f"source name '{fields.get('name')}' already registered") from exc
            raise
        return source

    async def list_sources(self, session: AsyncSession) -> list[DataSource]:
        result = await session.execute(select(DataSource).order_by(DataSource.name))
        return list(result.scalars())

    async def get_source(self, session: AsyncSession, source_id: uuid.UUID) -> DataSource:
        source = await session.get(DataSource, source_id)
        if source is None:
            from fastapi import HTTPException

            raise HTTPException(status_code=404, detail="source not found")
        return source

    async def get_run(self, session: AsyncSession, run_id: uuid.UUID) -> SyncRun:
        run = await session.get(SyncRun, run_id)
        if run is None:
            from fastapi import HTTPException

            raise HTTPException(status_code=404, detail="sync run not found")
        return run
