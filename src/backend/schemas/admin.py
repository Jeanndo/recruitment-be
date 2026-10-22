"""Pydantic schemas used by the admin endpoints.

These shapes are richer than the public ones because an administrator is
allowed to see information a candidate must not see (the review note, the CV
metadata) - but never the path of the file on the server.
"""

from __future__ import annotations

from datetime import date, datetime

from pydantic import EmailStr, Field

from backend.models.application import ApplicationStatus
from backend.models.job import JobStatus
from backend.schemas.application import CVMetadataResponse
from backend.schemas.common import BaseSchema, PaginationParams

__all__ = [
    "AdminApplicationDetail",
    "AdminApplicationItem",
    "AdminJobFilterOptions",
    "AdminJobListItem",
    "AdminJobReference",
    "ApplicationFilterOptions",
]


class AdminJobListItem(BaseSchema):
    """A job in the admin jobs table.

    `application_count` is counted in the database with a GROUP BY query. It
    is not a column on the `jobs` table, because a stored count would drift
    out of sync the moment an application is submitted.
    """

    id: int
    title: str
    location: str
    status: JobStatus
    closing_date: date
    application_count: int


class AdminApplicationItem(BaseSchema):
    """One row of the admin applicants table."""

    id: int
    job_id: int
    full_name: str
    email: EmailStr
    phone_number: str
    status: ApplicationStatus
    created_at: datetime
    # Tells the admin table whether the "CV" link should be enabled without
    # sending the file itself in every list request.
    cv_available: bool


class AdminJobReference(BaseSchema):
    """The job information shown on the admin application detail page."""

    id: int
    title: str
    location: str
    closing_date: date
    status: JobStatus


class AdminApplicationDetail(AdminApplicationItem):
    """Everything an administrator sees when opening a single application."""

    cover_note: str
    admin_note: str | None
    job: AdminJobReference
    cv: CVMetadataResponse | None


class ApplicationFilterOptions(PaginationParams):
    """Query parameters of `GET /api/v1/admin/jobs/{job_id}/applications`."""

    status: ApplicationStatus | None = None
    # Text search over the applicant's name and email.
    search: str | None = Field(default=None, max_length=100)


class AdminJobFilterOptions(PaginationParams):
    """Query parameters of the admin jobs table.

    Unlike the public listing this accepts a status, because an administrator
    needs to find drafts and closed jobs too.
    """

    status: JobStatus | None = None
    search: str | None = Field(default=None, max_length=100)
