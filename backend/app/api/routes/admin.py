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
from app.modules.data_ingestion.archive import LocalFilesystemArchive
from app.modules.data_ingestion.service import (
    DatasetVersionService,
    IngestionService,
    SourceRegistry,
)
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
    adapter: Literal["file"] = "file"
    path: str = Field(min_length=1)


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
    if body.adapter != "file":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="unknown adapter")
    settings = get_settings()
    service = IngestionService(archive=LocalFilesystemArchive(settings.raw_archive_dir))
    try:
        adapter = FileSourceAdapter(body.path)
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
