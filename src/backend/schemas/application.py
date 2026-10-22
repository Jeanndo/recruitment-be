"""Pydantic schemas for job applications.

The application form is sent as `multipart/form-data` because it carries a
file. The text fields are described by `ApplicationCreate` and validated by
Pydantic; the CV arrives as a separate `UploadFile` in the route and is
validated by the service layer (size, extension, MIME type and PDF signature).
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import EmailStr, Field, StringConstraints

from backend.models.application import ApplicationStatus
from backend.schemas.common import BaseSchema

__all__ = [
    "CV_MAX_SIZE_BYTES",
    "ApplicationCreatedResponse",
    "ApplicationCreate",
    "ApplicationListItem",
    "ApplicationResponse",
    "ApplicationStatus",
    "ApplicationStatusResponse",
    "ApplicationStatusUpdate",
    "CVMetadataResponse",
]

# The largest CV we accept: 5 MB. The same limit is enforced again when the
# file is read, so the browser's check can never be bypassed.
CV_MAX_SIZE_BYTES = 5 * 1024 * 1024

FullName = Annotated[str, StringConstraints(min_length=2, max_length=150)]
CoverNote = Annotated[str, StringConstraints(min_length=10, max_length=2_000)]

# A permissive phone format: an optional leading "+", then digits and the
# separators people actually use. The rule rejects obvious nonsense
# ("abcdefgh") without turning away international applicants.
PhoneNumber = Annotated[
    str,
    StringConstraints(
        min_length=7,
        max_length=20,
        pattern=r"^\+?[0-9][0-9\s\-()]{6,19}$",
    ),
]


class ApplicationCreate(BaseSchema):
    """The text fields of the application form.

    This schema describes the *form fields* only. The CV is uploaded next to
    them in the same multipart request and is handled separately, because a
    file needs different checks (magic bytes, size) than a text field.
    """

    full_name: FullName
    email: EmailStr
    phone_number: PhoneNumber
    cover_note: CoverNote


class ApplicationCreatedResponse(BaseSchema):
    """Confirmation returned after a successful submission."""

    id: int
    job_id: int
    status: ApplicationStatus
    message: str


class ApplicationResponse(BaseSchema):
    """An application as seen by the applicant.

    Note what is *not* here: `admin_note` is an internal comment and is
    never exposed in a public response.
    """

    id: int
    job_id: int
    full_name: str
    email: EmailStr
    phone_number: str
    cover_note: str
    status: ApplicationStatus
    created_at: datetime
    updated_at: datetime


class ApplicationListItem(BaseSchema):
    """The reduced application shape used in list views."""

    id: int
    job_id: int
    full_name: str
    email: EmailStr
    status: ApplicationStatus
    created_at: datetime


class ApplicationStatusUpdate(BaseSchema):
    """Payload of `PATCH /api/v1/admin/applications/{application_id}/status`."""

    status: ApplicationStatus
    admin_note: str | None = Field(default=None, max_length=2_000)


class ApplicationStatusResponse(BaseSchema):
    """Result of a status change."""

    id: int
    status: ApplicationStatus
    admin_note: str | None
    updated_at: datetime


class CVMetadataResponse(BaseSchema):
    """Information about a stored CV, for the admin application detail page.

    `download_url` is the *protected* admin endpoint, not a public file URL.
    The real path of the file on the server is never part of any response.
    """

    application_id: int
    filename: str
    content_type: str = "application/pdf"
    size_bytes: int
    download_url: str
