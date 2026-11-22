"""Report submission and moderation service (Phase 7, plan items 4, 7, 8).

Rules encoded here:
- **Explicit consent** is required before anything is stored — the caller
  (route) rejects consent-less submissions; consent is recorded on the row.
- **Append-only and idempotent**: submission looks the report up by
  `client_key` first; an offline-queued retry returns the existing row and
  never duplicates it.
- **Moderation is the only path to data impact**: accepting a report creates
  a new **candidate** dataset version (never published, the active dataset is
  untouched); rejection and needs-info change nothing outside the report row.
  Accepted/rejected reports are terminal; `needs_info` can be reviewed again.
- The caller owns the commit (mirrors the other modules).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.data_ingestion.models import DatasetVersion
from app.modules.reports.models import TransportReport


class ReportAlreadyReviewed(Exception):
    """Accepted/rejected reports are terminal (a fresh report replaces them)."""


async def create_report(
    session: AsyncSession,
    *,
    category: str,
    description: str,
    consent: bool,
    client_key: str,
    subject_type: str | None = None,
    subject_id: uuid.UUID | None = None,
    dataset_version_label: str | None = None,
) -> tuple[TransportReport, bool]:
    """Create a report, or return the existing one for this `client_key`.

    Returns `(report, created)` — `created=False` means an idempotent replay
    of a previously stored (or offline-queued-then-synced) submission.
    """
    existing = (
        await session.execute(
            select(TransportReport).where(TransportReport.client_key == client_key)
        )
    ).scalar_one_or_none()
    if existing is not None:
        return existing, False

    report = TransportReport(
        category=category,
        description=description,
        consent=consent,
        client_key=client_key,
        subject_type=subject_type,
        subject_id=subject_id,
        dataset_version_label=dataset_version_label,
        status="submitted",
    )
    session.add(report)
    await session.flush()
    return report, True


async def list_reports(
    session: AsyncSession, status_filter: str | None = None
) -> list[TransportReport]:
    """Moderation/triage queue (oldest first)."""
    query = select(TransportReport).order_by(TransportReport.created_at.asc())
    if status_filter is not None:
        query = query.where(TransportReport.status == status_filter)
    return list((await session.execute(query)).scalars())


async def get_report(session: AsyncSession, report_id: uuid.UUID) -> TransportReport | None:
    return (
        await session.execute(select(TransportReport).where(TransportReport.id == report_id))
    ).scalar_one_or_none()


def serialize_report(report: TransportReport) -> dict[str, Any]:
    """Payload shared by the public and admin endpoints."""
    return {
        "id": str(report.id),
        "category": report.category,
        "subject_type": report.subject_type,
        "subject_id": str(report.subject_id) if report.subject_id else None,
        "description": report.description,
        "consent": report.consent,
        "status": report.status,
        "dataset_version_label": report.dataset_version_label,
        "review_note": report.review_note,
        "candidate_version_id": (
            str(report.candidate_version_id) if report.candidate_version_id else None
        ),
        "created_at": report.created_at.isoformat(),
        "reviewed_at": report.reviewed_at.isoformat() if report.reviewed_at else None,
    }


async def review_report(
    session: AsyncSession,
    report_id: uuid.UUID,
    decision: str,
    note: str | None = None,
) -> tuple[TransportReport, DatasetVersion | None]:
    """Apply a moderation decision.

    - `accept` → report accepted + a **candidate** dataset version created
      (status `candidate`; the active dataset is untouched until a full
      publish flow runs — never auto-published, product rule).
    - `reject` → report rejected; nothing else changes.
    - `needs_info` → back to the traveller; can be reviewed again later.
    """
    report = await get_report(session, report_id)
    if report is None:
        raise LookupError(f"report {report_id} not found")
    if report.status in ("accepted", "rejected"):
        raise ReportAlreadyReviewed(
            f"report {report_id} is already {report.status}; reviews are terminal"
        )

    now = datetime.now(UTC)
    candidate: DatasetVersion | None = None
    if decision == "accept":
        report.status = "accepted"
        candidate = DatasetVersion(
            version_label=f"field-reports-{report.id}",
            status="candidate",
            notes=(
                f"Created by accepting transport report {report.id} (category:"
                f" {report.category}). Not published — the ingestion pipeline"
                " must fold the verified field correction in and publish"
                " through the normal validation flow."
            ),
        )
        session.add(candidate)
        await session.flush()
        report.candidate_version_id = candidate.id
    elif decision == "reject":
        report.status = "rejected"
    elif decision == "needs_info":
        report.status = "needs_info"
    else:
        raise ValueError(f"unknown moderation decision: {decision}")

    report.reviewed_at = now
    report.review_note = note
    await session.flush()
    return report, candidate
