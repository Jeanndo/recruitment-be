"""Public job endpoints.

These are the only endpoints the careers site needs. They cannot
see drafts or the admin-only fields.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.schemas.common import PaginatedResponse
from backend.schemas.job import JobFilterOptions, JobListItem, JobResponse
from backend.services import job_service

router = APIRouter(prefix="/api/v1/jobs", tags=["Jobs"])


@router.get(
    "",
    response_model=PaginatedResponse[JobListItem],
    summary="List open jobs",
    description=(
        "Returns the jobs a visitor may apply to: status Open and a closing "
        "date that has not passed. Drafts, closed jobs and expired jobs are "
        "never included."
    ),
)
def list_jobs(
    filters: Annotated[JobFilterOptions, Query()],
    db: Session = Depends(get_db),
) -> PaginatedResponse[JobListItem]:
    """Browse the public job board with optional search and filters."""
    jobs, total = job_service.list_public_jobs(db, filters)

    return PaginatedResponse[JobListItem](
        items=[JobListItem.model_validate(job) for job in jobs],
        page=filters.page,
        page_size=filters.page_size,
        total=total,
    )


@router.get(
    "/{job_id}",
    response_model=JobResponse,
    summary="Get one job",
    description=(
        "Returns a single job for the details page. Closed jobs are returned "
        "so the page can explain that applications are no longer accepted. "
        "A draft is reported as not found."
    ),
)
def get_job(job_id: int, db: Session = Depends(get_db)) -> JobResponse:
    """Read the full details of one job."""
    job = job_service.get_public_job(db, job_id)
    return JobResponse.model_validate(job)
