"""Business rules for job postings.

The routes stay thin: they validate the request shape, call one function from
here, and return the result. Everything that is a *decision* - which jobs are
public, which status changes are allowed, when a job accepts applications -
lives in this module so it can be tested without HTTP.
"""

from __future__ import annotations

from datetime import UTC, date, datetime

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from backend.models.application import Application
from backend.models.job import Job, JobStatus
from backend.schemas.admin import AdminJobFilterOptions
from backend.schemas.job import JobCreate, JobFilterOptions, JobUpdate
from backend.services.exceptions import (
    InvalidClosingDateError,
    InvalidStatusTransitionError,
    JobAlreadyClosedError,
    JobNotFoundError,
)

# Which status a job may move to from each current status.
# A draft can be published or discarded, an open job can be closed, and a
# closed job can be reopened. Everything else is refused, which keeps the
# lifecycle predictable.
ALLOWED_TRANSITIONS: dict[JobStatus, set[JobStatus]] = {
    JobStatus.DRAFT: {JobStatus.OPEN, JobStatus.CLOSED},
    JobStatus.OPEN: {JobStatus.CLOSED},
    JobStatus.CLOSED: {JobStatus.OPEN},
}


def today_utc() -> date:
    """The current date in UTC.

    Closing dates are compared in UTC so the rule does not change with the
    server's local timezone.
    """
    return datetime.now(UTC).date()


def _validate_transition(current: JobStatus, new: JobStatus) -> None:
    """Refuse a status change that is not in `ALLOWED_TRANSITIONS`."""
    if new is None:
        raise InvalidStatusTransitionError("A status must be provided.")
    if new is current:
        raise InvalidStatusTransitionError(f"This job is already {current.value.lower()}.")
    if new not in ALLOWED_TRANSITIONS[current]:
        raise InvalidStatusTransitionError(
            f"A job cannot move from {current.value} to {new.value}."
        )


# ---------------------------------------------------------------------------
# Public reads
# ---------------------------------------------------------------------------


def list_public_jobs(db: Session, filters: JobFilterOptions) -> tuple[list[Job], int]:
    """Return one page of jobs a visitor is allowed to see.

    Drafts are excluded entirely, and closed or expired jobs never appear in
    the listing. The second value is the total number of matches, which the
    frontend needs to draw pagination controls.
    """
    conditions = [
        Job.status == JobStatus.OPEN,
        Job.closing_date >= today_utc(),
    ]

    if filters.search:
        pattern = f"%{filters.search}%"
        conditions.append(or_(Job.title.ilike(pattern), Job.summary.ilike(pattern)))

    if filters.location:
        conditions.append(Job.location.ilike(f"%{filters.location}%"))

    if filters.employment_type:
        conditions.append(Job.employment_type == filters.employment_type)

    total = db.scalar(select(func.count()).select_from(Job).where(*conditions)) or 0

    statement = (
        select(Job)
        .where(*conditions)
        .order_by(Job.created_at.desc(), Job.id.desc())
        .offset(_offset(filters.page, filters.page_size))
        .limit(filters.page_size)
    )
    return list(db.scalars(statement).all()), total


def get_public_job(db: Session, job_id: int) -> Job:
    """Return one job for the details page.

    Closed and expired jobs are still returned so the frontend can show the
    "this job is closed" message. Drafts are treated as if they did not exist.
    """
    job = db.get(Job, job_id)
    if job is None or job.status is JobStatus.DRAFT:
        raise JobNotFoundError("Job not found.")
    return job


# ---------------------------------------------------------------------------
# Admin reads and writes
# ---------------------------------------------------------------------------


def list_admin_jobs(
    db: Session,
    filters: AdminJobFilterOptions,
) -> tuple[list[tuple[Job, int]], int]:
    """Return one page of jobs for the admin table, with their application counts.

    The count comes from a single LEFT JOIN plus GROUP BY, so the endpoint
    still runs two queries in total (one for the rows, one for the total)
    instead of one extra query per job.
    """
    conditions = []
    if filters.status:
        conditions.append(Job.status == filters.status)
    if filters.search:
        conditions.append(Job.title.ilike(f"%{filters.search}%"))

    total = db.scalar(select(func.count()).select_from(Job).where(*conditions)) or 0

    statement = (
        select(Job, func.count(Application.id))
        .outerjoin(Application, Application.job_id == Job.id)
        .where(*conditions)
        # Grouping by the primary key lets PostgreSQL select the other job
        # columns without listing all of them.
        .group_by(Job.id)
        .order_by(Job.created_at.desc(), Job.id.desc())
        .offset(_offset(filters.page, filters.page_size))
        .limit(filters.page_size)
    )

    rows = [(job, application_count) for job, application_count in db.execute(statement).all()]
    return rows, total


def get_admin_job(db: Session, job_id: int) -> Job:
    """Return a job by id, drafts included.

    Used by the admin endpoints, which are allowed to see unpublished jobs.
    """
    job = db.get(Job, job_id)
    if job is None:
        raise JobNotFoundError("Job not found.")
    return job


def create_job(db: Session, payload: JobCreate) -> Job:
    """Insert a new job and return it.

    A job cannot be published with a closing date that has already passed -
    that would create a listing nobody could apply to.
    """
    if payload.status is JobStatus.OPEN and payload.closing_date < today_utc():
        raise InvalidClosingDateError("An open job cannot have a closing date in the past.")

    job = Job(**payload.model_dump())
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def update_job(db: Session, job_id: int, payload: JobUpdate) -> Job:
    """Apply a partial update to a job.

    Only the fields the client actually sent are changed. Sending `null` for a
    field means "leave it alone", because none of these columns may be empty.

    Sending the status the job already has is accepted as a no-op. Edit forms
    commonly post the whole object back, and refusing those saves would be
    annoying; a real move to another status is still checked below.
    """
    job = get_admin_job(db, job_id)
    changes = payload.model_dump(exclude_unset=True, exclude_none=True)

    new_status: JobStatus = changes.get("status", job.status)
    new_closing_date: date = changes.get("closing_date", job.closing_date)

    if new_status is not job.status:
        _validate_transition(job.status, new_status)

    if new_status is JobStatus.OPEN and new_closing_date < today_utc():
        raise InvalidClosingDateError("An open job cannot have a closing date in the past.")

    for field_name, value in changes.items():
        setattr(job, field_name, value)

    db.commit()
    db.refresh(job)
    return job


def close_job(db: Session, job_id: int) -> Job:
    """Close a job so it stops accepting applications.

    Closing is idempotent in spirit but not silent: calling it twice returns a
    409, so an administrator notices that the state was not what they thought.
    Existing applications are never touched.
    """
    job = get_admin_job(db, job_id)
    if job.status is JobStatus.CLOSED:
        raise JobAlreadyClosedError("This job is already closed.")

    _validate_transition(job.status, JobStatus.CLOSED)

    job.status = JobStatus.CLOSED
    db.commit()
    db.refresh(job)
    return job


def _offset(page: int, page_size: int) -> int:
    """Number of rows to skip for the requested page."""
    return (page - 1) * page_size
