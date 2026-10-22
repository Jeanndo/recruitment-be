"""Admin job management endpoints.

Every route here is behind `require_staff`, which rejects requests without a
valid session before the route body runs. Administrators can see drafts, edit
jobs and close them; closing never deletes anything, so existing applications
stay intact.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from backend.api.dependencies import require_staff
from backend.database import get_db
from backend.models.job import Job
from backend.schemas.admin import AdminJobFilterOptions, AdminJobListItem
from backend.schemas.common import PaginatedResponse
from backend.schemas.job import JobCloseResponse, JobCreate, JobResponse, JobUpdate
from backend.services import job_service

# Protecting the whole router at once is less error-prone than remembering a
# dependency on every route: a new admin endpoint is secure by default.
router = APIRouter(
    prefix="/api/v1/admin/jobs",
    tags=["Admin - Jobs"],
    dependencies=[Depends(require_staff)],
)


@router.get(
    "",
    response_model=PaginatedResponse[AdminJobListItem],
    summary="List all jobs",
    description="Includes drafts, open and closed jobs, with application counts.",
)
def list_jobs(
    filters: Annotated[AdminJobFilterOptions, Query()],
    db: Session = Depends(get_db),
) -> PaginatedResponse[AdminJobListItem]:
    """Return the admin jobs table, optionally filtered by status or title."""
    rows, total = job_service.list_admin_jobs(db, filters)

    items = [
        AdminJobListItem(
            id=job.id,
            title=job.title,
            location=job.location,
            status=job.status,
            closing_date=job.closing_date,
            application_count=application_count,
        )
        for job, application_count in rows
    ]

    return PaginatedResponse[AdminJobListItem](
        items=items,
        page=filters.page,
        page_size=filters.page_size,
        total=total,
    )


@router.post(
    "",
    response_model=JobResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a job",
    description=(
        "Creates a job. It starts as a draft unless the payload sets another "
        "status, so a half-written job never reaches the public site."
    ),
)
def create_job(payload: JobCreate, db: Session = Depends(get_db)) -> JobResponse:
    """Create a new job."""
    job = job_service.create_job(db, payload)
    return JobResponse.model_validate(job)


@router.get(
    "/{job_id}",
    response_model=JobResponse,
    summary="Get one job (drafts included)",
)
def get_job(job_id: int, db: Session = Depends(get_db)) -> JobResponse:
    """Read a job for the edit form."""
    job = job_service.get_admin_job(db, job_id)
    return JobResponse.model_validate(job)


@router.patch(
    "/{job_id}",
    response_model=JobResponse,
    summary="Update a job",
    description=(
        "Partial update: only the fields in the request body change. Status "
        "changes must follow the allowed transitions (Draft to Open, Open to "
        "Closed, Closed to Open)."
    ),
)
def update_job(job_id: int, payload: JobUpdate, db: Session = Depends(get_db)) -> JobResponse:
    """Change some fields of an existing job."""
    job = job_service.update_job(db, job_id, payload)
    return JobResponse.model_validate(job)


@router.patch(
    "/{job_id}/close",
    response_model=JobCloseResponse,
    summary="Close a job",
    description="Stops the job from accepting applications. Applications are kept.",
)
def close_job(job_id: int, db: Session = Depends(get_db)) -> JobCloseResponse:
    """Close a job that is currently open."""
    job: Job = job_service.close_job(db, job_id)
    return JobCloseResponse(
        id=job.id,
        status=job.status,
        message="Job closed successfully.",
    )
