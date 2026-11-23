"""Report submission endpoint (Phase 7, plan items 4 and 7).

Append-only and idempotent: a submission carries a client-generated
`client_key` (stable across offline-queued retries), so a retry can never
duplicate a report. **Explicit consent is required** — the request must set
`consent: true`, and the consent is recorded on the stored row. Reports
store no location data and never affect canonical data directly; only the
moderation queue (admin) can act on them.
"""

from __future__ import annotations

import uuid
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from app.modules.reports import create_report, serialize_report
from app.platform.config import get_settings
from app.platform.db import get_session
from app.platform.metrics import increment_counter
from app.platform.rate_limit import get_rate_limiter

router = APIRouter(tags=["reports"])

SessionDep = Annotated[Any, Depends(get_session)]


class ReportCreate(BaseModel):
    category: Literal[
        "wrong_stop",
        "route_variant",
        "direction",
        "transfer_path",
        "landmark_name",
        "fare",
        "access_attribute",
        "outdated_data",
        "other",
    ]
    description: str = Field(min_length=5, max_length=2000)
    consent: bool = Field(
        description=(
            "Must be true: the traveller explicitly agrees that this report is"
            " stored and reviewed by a moderator before any data change."
        )
    )
    client_key: str = Field(
        min_length=8,
        max_length=64,
        description="Client-generated idempotency key, stable across offline retries.",
    )
    subject_type: Literal["stop", "route", "pattern", "transfer", "journey"] | None = None
    subject_id: uuid.UUID | None = None
    dataset_version_label: str | None = Field(default=None, max_length=100)


@router.post("/reports", status_code=201)
async def submit_report(request: Request, session: SessionDep, body: ReportCreate) -> Any:
    """Store one traveller report (idempotent per `client_key`)."""
    settings = get_settings()
    client_key_addr = request.client.host if request.client else "unknown"
    if not get_rate_limiter("reports", settings).allow(client_key_addr):
        increment_counter("sljp_rate_limited_total", {"scope": "reports"})
        raise HTTPException(
            status_code=429,
            detail="Too many reports from this client right now — please try again later.",
        )
    if not body.consent:
        raise HTTPException(
            status_code=400,
            detail=(
                "Explicit consent is required: set consent=true so the report"
                " can be stored and reviewed. Nothing is stored without it."
            ),
        )
    report, created = await create_report(
        session,
        category=body.category,
        description=body.description,
        consent=body.consent,
        client_key=body.client_key,
        subject_type=body.subject_type,
        subject_id=body.subject_id,
        dataset_version_label=body.dataset_version_label,
    )
    await session.commit()
    increment_counter("sljp_reports_submitted_total", {"duplicate": str(not created).lower()})
    payload = serialize_report(report)
    payload["duplicate"] = not created
    return payload
