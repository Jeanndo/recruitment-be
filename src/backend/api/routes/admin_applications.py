"""Admin endpoints for reviewing applications.

The whole router is behind `require_staff`, including the CV download. That is
deliberate: applicant data and CVs must never be reachable without a valid
session. The download streams the file from the private storage directory and
never exposes the path or the generated storage name.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from backend.api.dependencies import require_staff
from backend.database import get_db
from backend.schemas.admin import (
    AdminApplicationDetail,
    AdminApplicationItem,
    AdminJobReference,
    ApplicationFilterOptions,
)
from backend.schemas.application import (
    ApplicationStatusResponse,
    ApplicationStatusUpdate,
    CVMetadataResponse,
)
from backend.schemas.common import PaginatedResponse
from backend.services import application_service, cv_storage

router = APIRouter(
    prefix="/api/v1/admin",
    tags=["Admin - Applications"],
    dependencies=[Depends(require_staff)],
)


@router.get(
    "/jobs/{job_id}/applications",
    response_model=PaginatedResponse[AdminApplicationItem],
    summary="List a job's applications",
    description=(
        "Newest first. Filter by review status, or search the applicant's name "
        "and email. Closed jobs are included on purpose: their applications "
        "still need to be reviewed."
    ),
)
def list_applications(
    job_id: int,
    filters: Annotated[ApplicationFilterOptions, Query()],
    db: Session = Depends(get_db),
) -> PaginatedResponse[AdminApplicationItem]:
    """Return one page of applications for a job."""
    applications, total = application_service.list_job_applications(db, job_id, filters)

    return PaginatedResponse[AdminApplicationItem](
        items=[
            AdminApplicationItem.model_validate(application)
            for application in applications
        ],
        page=filters.page,
        page_size=filters.page_size,
        total=total,
    )


@router.get(
    "/applications/{application_id}",
    response_model=AdminApplicationDetail,
    summary="Get one application",
    description=(
        "Everything needed to review the application, including the job it was "
        "sent for and a protected download link for the CV."
    ),
)
def get_application(
    application_id: int,
    db: Session = Depends(get_db),
) -> AdminApplicationDetail:
    """Return the full review view of an application."""
    application = application_service.get_application(db, application_id)
    summary = AdminApplicationItem.model_validate(application)

    cv = None
    if application.cv_available:
        cv = CVMetadataResponse(
            application_id=application.id,
            filename=application.cv_original_filename,
            content_type=application.cv_content_type,
            size_bytes=application.cv_size_bytes,
            download_url=f"/api/v1/admin/applications/{application.id}/cv",
        )

    return AdminApplicationDetail(
        **summary.model_dump(),
        cover_note=application.cover_note,
        admin_note=application.admin_note,
        job=AdminJobReference.model_validate(application.job),
        cv=cv,
    )


@router.patch(
    "/applications/{application_id}/status",
    response_model=ApplicationStatusResponse,
    summary="Accept or reject an application",
    description=(
        "Allowed moves: Pending to Accepted or Rejected, and between Accepted "
        "and Rejected to correct a mistake. Returning to Pending is refused. "
        "Sending the current status is accepted and only changes the note. "
        "Omitting `admin_note` keeps the existing note; `null` clears it."
    ),
)
def update_status(
    application_id: int,
    payload: ApplicationStatusUpdate,
    db: Session = Depends(get_db),
) -> ApplicationStatusResponse:
    """Save the new review status and optional internal note."""
    application = application_service.update_review_status(db, application_id, payload)

    return ApplicationStatusResponse(
        id=application.id,
        status=application.status,
        admin_note=application.admin_note,
        updated_at=application.updated_at,
    )


@router.get(
    "/applications/{application_id}/cv",
    response_class=FileResponse,
    summary="Download an applicant's CV",
    responses={
        200: {
            "content": {"application/pdf": {}},
            "description": "The CV, sent as a download.",
        }
    },
)
def download_cv(application_id: int, db: Session = Depends(get_db)) -> FileResponse:
    """Stream the stored PDF; the file path never leaves the server."""
    application = application_service.get_application(db, application_id)
    path = cv_storage.resolve_cv_path(application.cv_storage_name)

    return FileResponse(
        path,
        media_type="application/pdf",
        # Starlette builds a safe Content-Disposition header from this name.
        filename=application.cv_original_filename,
        headers={"X-Content-Type-Options": "nosniff"},
    )
