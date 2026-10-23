"""Business rules for the admin overview.

The dashboard is a read-only aggregation of jobs and applications. Doing the
counting in SQL keeps the frontend from making one request per job just to
show a status breakdown.
"""

from __future__ import annotations

from collections import defaultdict

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.models.application import Application, ApplicationStatus
from backend.models.job import Job, JobStatus
from backend.schemas.dashboard import (
    ApplicationStatusCounts,
    DashboardResponse,
    JobDashboardSummary,
)


def _empty_counts() -> ApplicationStatusCounts:
    return ApplicationStatusCounts(pending=0, accepted=0, rejected=0, total=0)


def _add_status(
    counts: ApplicationStatusCounts,
    status: ApplicationStatus,
    amount: int,
) -> None:
    counts.total += amount
    if status is ApplicationStatus.PENDING:
        counts.pending += amount
    elif status is ApplicationStatus.ACCEPTED:
        counts.accepted += amount
    elif status is ApplicationStatus.REJECTED:
        counts.rejected += amount


def get_dashboard(db: Session) -> DashboardResponse:
    """Return every number shown on the admin overview in one query set."""
    jobs = list(db.scalars(select(Job).order_by(Job.created_at.desc(), Job.id.desc())).all())

    job_counts: dict[int, ApplicationStatusCounts] = defaultdict(_empty_counts)
    application_counts = _empty_counts()

    rows = db.execute(
        select(Application.job_id, Application.status, func.count(Application.id))
        .group_by(Application.job_id, Application.status)
    ).all()

    for job_id, status, amount in rows:
        _add_status(job_counts[job_id], status, amount)
        _add_status(application_counts, status, amount)

    summaries = [
        JobDashboardSummary(
            job_id=job.id,
            title=job.title,
            location=job.location,
            closing_date=job.closing_date,
            status=job.status,
            application_counts=job_counts[job.id],
        )
        for job in jobs
    ]
    summaries.sort(
        key=lambda job: (
            -job.application_counts.pending,
            -job.application_counts.total,
            job.title.lower(),
        )
    )

    return DashboardResponse(
        total_jobs=len(jobs),
        open_jobs=sum(job.status is JobStatus.OPEN for job in jobs),
        closed_jobs=sum(job.status is JobStatus.CLOSED for job in jobs),
        draft_jobs=sum(job.status is JobStatus.DRAFT for job in jobs),
        total_applications=application_counts.total,
        application_counts=application_counts,
        jobs=summaries,
    )
