"""Public application submission.

This is the only public endpoint that writes applicant data. It accepts
`multipart/form-data` because the CV travels with the form, and it never
returns anything the candidate did not already know (no CV path, no review
note, no internal fields).
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.schemas.application import ApplicationCreate, ApplicationCreatedResponse
from backend.services import application_service, cv_storage, email_service

router = APIRouter(prefix="/api/v1/jobs", tags=["Applications"])


@router.post(
    "/{job_id}/applications",
    response_model=ApplicationCreatedResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Apply for a job",
    description=(
        "Submit an application as `multipart/form-data`: the four text fields "
        "plus the CV. The CV must be a PDF no larger than 5 MB. A job only "
        "accepts applications while it is open and its closing date has not "
        "passed, and the same email address cannot apply twice for the same job."
    ),
)
async def submit_application(
    job_id: int,
    data: Annotated[ApplicationCreate, Form()],
    cv: Annotated[UploadFile, File(description="The CV, as a PDF of at most 5 MB.")],
    db: Session = Depends(get_db),
) -> ApplicationCreatedResponse:
    """Validate the job and the file, then save the application."""
    # Check the job before writing the file: there is no reason to touch the
    # disk for a draft, a closed job, or an expired one.
    job = application_service.get_job_for_application(db, job_id)

    stored_cv = await cv_storage.store_cv(cv)

    try:
        application = application_service.create_application(db, job, data, stored_cv)
    except Exception:
        # The row was not saved, so the file must not stay behind.
        cv_storage.delete_cv(stored_cv.storage_name)
        raise

    # Best-effort: the application is already saved and must not fail because
    # the mail provider is unreachable.
    await email_service.send_application_confirmation_email(
        to_email=application.email,
        full_name=application.full_name,
        job_title=job.title,
    )

    return ApplicationCreatedResponse(
        id=application.id,
        job_id=application.job_id,
        status=application.status,
        message="Your application was submitted successfully.",
    )
