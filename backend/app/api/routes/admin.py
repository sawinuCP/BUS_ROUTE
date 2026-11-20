"""Admin/data-operations endpoints (Phase 1.2).

These endpoints manage the source registry, sync runs and dataset versions.
They are mounted **only outside production** (see `app.main`) — admin
authentication/authorization (OAuth2/OIDC + RBAC, architecture doc 14) and
rate limiting are enforced in Phase 9; no production deployment may expose
this router unauthenticated.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.modules.data_ingestion.adapters.file import FileSourceAdapter
from app.modules.data_ingestion.adapters.overpass import OverpassAdapter
from app.modules.data_ingestion.archive import LocalFilesystemArchive
from app.modules.data_ingestion.report import QualityReportService
from app.modules.data_ingestion.service import (
    DatasetVersionService,
    IngestionService,
    SourceRegistry,
)
from app.modules.data_quality.queue import QAQueueService
from app.modules.data_quality.scorecard import CoverageScorecardService
from app.platform.config import get_settings
from app.platform.db import get_session

router = APIRouter(prefix="/admin", tags=["admin"])

_registry = SourceRegistry()
_versions = DatasetVersionService()


class SourceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    owner: str | None = None
    access_method: str | None = None
    endpoint: str | None = None
    format: str | None = None
    licence: str | None = None
    terms_note: str | None = None
    update_cadence: str | None = None


class SourceOut(SourceCreate):
    id: uuid.UUID
    enabled: bool

    model_config = {"from_attributes": True}


class SyncRequest(BaseModel):
    adapter: Literal["file", "overpass"] = "file"
    # Required for the `file` adapter (path inside the backend container); the
    # `overpass` adapter uses PILOT_BBOX / OSM_OVERPASS_ENDPOINT from settings.
    path: str | None = None


class SyncRunOut(BaseModel):
    id: uuid.UUID
    status: str
    started_at: datetime
    finished_at: datetime | None
    records_in: int
    records_added: int
    records_updated: int
    records_failed: int
    parser_version: str | None
    error: str | None

    model_config = {"from_attributes": True}


class DatasetVersionOut(BaseModel):
    id: uuid.UUID
    version_label: str
    status: str
    published_at: datetime | None
    notes: str | None

    model_config = {"from_attributes": True}


SessionDep = Annotated[Any, Depends(get_session)]


@router.post("/sources", response_model=SourceOut, status_code=status.HTTP_201_CREATED)
async def create_source(body: SourceCreate, session: SessionDep) -> Any:
    try:
        source = await _registry.create_source(session, **body.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    await session.commit()
    return source


@router.get("/sources", response_model=list[SourceOut])
async def list_sources(session: SessionDep) -> Any:
    return await _registry.list_sources(session)


@router.post("/sources/{source_id}/sync")
async def sync_source(source_id: uuid.UUID, body: SyncRequest, session: SessionDep) -> Any:
    source = await _registry.get_source(session, source_id)
    settings = get_settings()
    service = IngestionService(archive=LocalFilesystemArchive(settings.raw_archive_dir))
    try:
        if body.adapter == "file":
            if not body.path:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="path is required for the file adapter",
                )
            adapter: FileSourceAdapter | OverpassAdapter = FileSourceAdapter(body.path)
        else:
            adapter = OverpassAdapter(
                bbox=settings.pilot_bbox,
                endpoint=settings.osm_overpass_endpoint,
                fallback_endpoint=settings.osm_overpass_fallback,
            )
        outcome = await service.run_sync(session, source, adapter)
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="source file not found"
        ) from exc
    await session.commit()
    return outcome.__dict__ | {"run_id": str(outcome.run_id)}


@router.get("/sync-runs/{run_id}", response_model=SyncRunOut)
async def get_sync_run(run_id: uuid.UUID, session: SessionDep) -> Any:
    return await _registry.get_run(session, run_id)


@router.get("/dataset-versions", response_model=list[DatasetVersionOut])
async def list_dataset_versions(session: SessionDep) -> Any:
    from sqlalchemy import select

    from app.modules.data_ingestion.models import DatasetVersion

    result = await session.execute(select(DatasetVersion).order_by(DatasetVersion.created_at))
    return list(result.scalars())


@router.get("/dataset-versions/active", response_model=DatasetVersionOut | None)
async def get_active_version(session: SessionDep) -> Any:
    return await _versions.active_version(session)


@router.post("/dataset-versions/{version_id}/publish", response_model=DatasetVersionOut)
async def publish_version(version_id: uuid.UUID, session: SessionDep) -> Any:
    version = await _versions.publish(session, version_id)
    await session.commit()
    return version


@router.post("/dataset-versions/{version_id}/rollback", response_model=DatasetVersionOut)
async def rollback_version(version_id: uuid.UUID, session: SessionDep) -> Any:
    version = await _versions.rollback(session, version_id)
    await session.commit()
    return version


_reports = QualityReportService()


@router.get("/dataset-versions/{version_id}/quality-report")
async def get_quality_report(version_id: uuid.UUID, session: SessionDep) -> Any:
    return await _reports.build(session, version_id)


@router.post("/dataset-versions/{version_id}/quality-report/write")
async def write_quality_report(version_id: uuid.UUID, session: SessionDep) -> Any:
    paths = await _reports.write(session, version_id, get_settings().validation_reports_dir)
    await session.commit()
    return paths


# ---- Phase 1.4: coverage scorecard, QA queue, verifications ---------------


@router.get("/coverage-scorecard")
async def coverage_scorecard(session: SessionDep) -> Any:
    return await CoverageScorecardService().build(session)


@router.get("/qa-queue")
async def qa_queue(session: SessionDep) -> Any:
    return await QAQueueService().items(session)


class VerificationCreate(BaseModel):
    entity_type: Literal[
        "agency",
        "route",
        "route_pattern",
        "route_pattern_stop",
        "stop",
        "stop_access_point",
        "route_shape",
        "transfer_connection",
        "place",
        "place_access_point",
        "locality",
        "entity_alias",
        "fare_rule",
    ]
    entity_id: uuid.UUID
    method: Literal["field_check", "official_source", "source_crosscheck", "report_review", "other"]
    reviewer: str | None = None
    result: Literal["verified", "rejected", "uncertain"]
    evidence: str | None = None
    notes: str | None = None
    verified_at: datetime | None = None  # defaults to now (UTC)


@router.post("/verifications", status_code=status.HTTP_201_CREATED)
async def create_verification(body: VerificationCreate, session: SessionDep) -> Any:
    from datetime import UTC

    from sqlalchemy import text as _text

    from app.modules.data_quality.models import VerificationRecord

    # The entity must actually exist — no verifications of phantom entities.
    table = {
        "agency": "transport_agencies",
        "route": "transport_routes",
        "route_pattern": "route_patterns",
        "route_pattern_stop": "route_pattern_stops",
        "stop": "stops",
        "stop_access_point": "stop_access_points",
        "route_shape": "route_shapes",
        "transfer_connection": "transfer_connections",
        "place": "places",
        "place_access_point": "place_access_points",
        "locality": "localities",
        "entity_alias": "entity_aliases",
        "fare_rule": "fare_rules",
    }[body.entity_type]
    exists = await session.execute(
        _text(f"SELECT 1 FROM {table} WHERE id = :id"), {"id": body.entity_id}
    )
    if exists.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail=f"{body.entity_type} not found")

    record = VerificationRecord(
        entity_type=body.entity_type,
        entity_id=body.entity_id,
        method=body.method,
        reviewer=body.reviewer,
        verified_at=body.verified_at or datetime.now(UTC),
        result=body.result,
        evidence=body.evidence,
        notes=body.notes,
    )
    session.add(record)
    await session.commit()
    await session.refresh(record)
    return {
        "id": str(record.id),
        "entity_type": record.entity_type,
        "entity_id": str(record.entity_id),
        "method": record.method,
        "result": record.result,
        "verified_at": record.verified_at.isoformat(),
        "reviewer": record.reviewer,
    }


@router.get("/verifications")
async def list_verifications(
    session: SessionDep,
    entity_type: str | None = None,
    entity_id: uuid.UUID | None = None,
) -> Any:
    from sqlalchemy import select

    from app.modules.data_quality.models import VerificationRecord

    query = select(VerificationRecord).order_by(VerificationRecord.verified_at.desc())
    if entity_type:
        query = query.where(VerificationRecord.entity_type == entity_type)
    if entity_id:
        query = query.where(VerificationRecord.entity_id == entity_id)
    records = (await session.execute(query.limit(200))).scalars()
    return [
        {
            "id": str(record.id),
            "entity_type": record.entity_type,
            "entity_id": str(record.entity_id),
            "method": record.method,
            "reviewer": record.reviewer,
            "verified_at": record.verified_at.isoformat(),
            "result": record.result,
            "evidence": record.evidence,
            "notes": record.notes,
        }
        for record in records
    ]
