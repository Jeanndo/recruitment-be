"""Business rules for job applications.

The routes stay thin and this module holds the decisions: can this job receive
an application, is this candidate a duplicate, which review-status changes are
allowed. Everything here works on SQLAlchemy objects, so it can be tested
without HTTP.

The unique constraint on `(job_id, normalized_email)` is the authority on
duplicates. The query below it is only a friendlier early answer for the common
case; if two requests race, PostgreSQL still refuses the second one and the
`IntegrityError` is translated into the same 409.
"""

from __future__ import annotations

import logging

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.models.application import Application, ApplicationStatus
from backend.models.job import Job, JobStatus
from backend.schemas.admin import ApplicationFilterOptions
from backend.schemas.application import ApplicationCreate, ApplicationStatusUpdate
from backend.services.application_exceptions import (
    ApplicationError,
    ApplicationNotFoundError,
    DuplicateApplicationError,
    InvalidApplicationStatusTransitionError,
    JobNotAcceptingApplicationsError,
)
from backend.services.cv_storage import StoredCV
from backend.services.exceptions import JobNotFoundError

logger = logging.getLogger(__name__)

# Review workflow:
#   Pending  -> Accepted or Rejected   (the first decision)
#   Accepted -> Rejected               (correct a mistake)
#   Rejected -> Accepted               (correct a mistake)
# Nothing may go back to Pending: that would erase the fact that a decision was
# made. Setting the status the application already has is a no-op, so the note
# can still be edited without a fake transition.
ALLOWED_STATUS_TRANSITIONS: dict[ApplicationStatus, set[ApplicationStatus]] = {
    ApplicationStatus.PENDING: {ApplicationStatus.ACCEPTED, ApplicationStatus.REJECTED},
    ApplicationStatus.ACCEPTED: {ApplicationStatus.REJECTED},
    ApplicationStatus.REJECTED: {ApplicationStatus.ACCEPTED},
}

# The constraint names PostgreSQL generates for this table. Used to tell an
# "already applied" error apart from any other integrity problem.
_DUPLICATE_CONSTRAINT = "applications_job_id_normalized_email"
_CV_CONSTRAINT = "applications_cv_storage_name_key"


def get_job_for_application(db: Session, job_id: int) -> Job:
    """Return the job if a candidate is allowed to apply to it.

    A draft is reported as not found, exactly like the public job endpoints, so
    an unpublished job is not even confirmed to exist. A closed or expired job
    returns 409 because the visitor can legitimately see that page.
    """
    job = db.get(Job, job_id)

    if job is None or job.status is JobStatus.DRAFT:
        raise JobNotFoundError("Job not found.")

    if not job.is_accepting_applications:
        raise JobNotAcceptingApplicationsError(
            "This job is no longer accepting applications."
        )

    return job


def create_application(
    db: Session,
    job: Job,
    payload: ApplicationCreate,
    stored_cv: StoredCV,
) -> Application:
    """Insert an application for a job that is already known to be open.

    The CV has been written to disk by the caller. If the insert fails the
    caller deletes that file again, so no orphan is left behind.
    """
    normalized_email = payload.email.strip().lower()

    already_applied = db.scalar(
        select(Application.id).where(
            Application.job_id == job.id,
            Application.normalized_email == normalized_email,
        )
    )
    if already_applied is not None:
        raise DuplicateApplicationError("You have already applied for this job.")

    application = Application(
        job_id=job.id,
        full_name=payload.full_name,
        email=str(payload.email),
        normalized_email=normalized_email,
        phone_number=payload.phone_number,
        cover_note=payload.cover_note,
        cv_storage_name=stored_cv.storage_name,
        cv_original_filename=stored_cv.original_filename,
        cv_content_type=stored_cv.content_type,
        cv_size_bytes=stored_cv.size_bytes,
        status=ApplicationStatus.PENDING,
    )

    db.add(application)

    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        constraint = getattr(getattr(error.orig, "diag", None), "constraint_name", None)

        if constraint == _DUPLICATE_CONSTRAINT:
            raise DuplicateApplicationError(
                "You have already applied for this job."
            ) from error

        if constraint == _CV_CONSTRAINT:
            # A UUID collision is practically impossible, but saying so is
            # better than a confusing 500 page.
            logger.error("CV storage name collision while saving an application")
            raise ApplicationError(
                "The CV could not be stored. Please try again.",
                status_code=409,
            ) from error

        logger.exception("Unexpected integrity error while saving an application")
        raise ApplicationError(
            "The application could not be saved. Please try again.",
            status_code=500,
        ) from error

    db.refresh(application)
    return application


def list_job_applications(
    db: Session,
    job_id: int,
    filters: ApplicationFilterOptions,
) -> tuple[list[Application], int]:
    """Return one page of applications for a job, newest first.

    The job must exist, but its status does not matter: an administrator still
    needs to review applications after a job is closed. The second value is the
    total number of matches for the pagination controls.
    """
    if db.get(Job, job_id) is None:
        raise JobNotFoundError("Job not found.")

    conditions = [Application.job_id == job_id]

    if filters.status is not None:
        conditions.append(Application.status == filters.status)

    if filters.search:
        pattern = f"%{filters.search}%"
        conditions.append(
            or_(
                Application.full_name.ilike(pattern),
                Application.email.ilike(pattern),
            )
        )

    total = db.scalar(select(func.count()).select_from(Application).where(*conditions)) or 0

    statement = (
        select(Application)
        .where(*conditions)
        .order_by(Application.created_at.desc(), Application.id.desc())
        .offset((filters.page - 1) * filters.page_size)
        .limit(filters.page_size)
    )

    return list(db.scalars(statement).all()), total


def get_application(db: Session, application_id: int) -> Application:
    """Return one application or raise a 404."""
    application = db.get(Application, application_id)

    if application is None:
        raise ApplicationNotFoundError("Application not found.")

    return application


def update_review_status(
    db: Session,
    application_id: int,
    payload: ApplicationStatusUpdate,
) -> Application:
    """Change the review status and/or the internal note.

    Only the fields present in the request are touched, so omitting
    `admin_note` keeps the old note while sending `null` clears it.
    """
    application = get_application(db, application_id)

    new_status = payload.status

    if new_status is not application.status:
        _validate_status_transition(application.status, new_status)

    application.status = new_status

    # `model_fields_set` tells "the field was omitted" apart from "the client
    # sent null". Omitting it keeps the old note; null clears it.
    if "admin_note" in payload.model_fields_set:
        application.admin_note = payload.admin_note

    db.commit()
    db.refresh(application)

    _log_mock_notification(application)
    return application


def _validate_status_transition(
    current: ApplicationStatus,
    new: ApplicationStatus,
) -> None:
    if new not in ALLOWED_STATUS_TRANSITIONS[current]:
        raise InvalidApplicationStatusTransitionError(
            f"An application cannot move from {current.value} to {new.value}."
        )


def _log_mock_notification(application: Application) -> None:
    """Pretend to email the candidate about the decision.

    A real integration would call an email provider here. The assessment only
    asks for a mocked notification, and it must never make the status change
    fail - hence the broad guard around a logging call. Only the application id
    and the new status are logged: no name, email address or cover note ever
    reaches the logs.
    """
    try:
        logger.info(
            "Mock notification: application %s is now %s.",
            application.id,
            application.status.value,
        )
    except Exception:  # pragma: no cover - logging must never break the request
        logger.debug("Mock notification could not be logged", exc_info=True)
