"""Pydantic schemas for job postings - the contract of the job endpoints.

The enums (`EmploymentType`, `JobStatus`) are imported from the model module
so that the value stored in the database and the value sent to the frontend
can never drift apart.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Annotated

from pydantic import Field, StringConstraints

from backend.models.job import EmploymentType, JobStatus
from backend.schemas.common import BaseSchema

__all__ = [
    "EmploymentType",
    "JobStatus",
    "JobBase",
    "JobCloseResponse",
    "JobCreate",
    "JobListItem",
    "JobResponse",
    "JobUpdate",
]

# Reusable field definitions. Defining them once means `JobCreate` and
# `JobUpdate` enforce exactly the same rules, so an administrator cannot
# create a job the update endpoint would reject.
Title = Annotated[str, StringConstraints(min_length=3, max_length=150)]
Location = Annotated[str, StringConstraints(min_length=2, max_length=150)]
Summary = Annotated[str, StringConstraints(min_length=10, max_length=500)]
Description = Annotated[str, StringConstraints(min_length=20, max_length=20_000)]
BulletPoint = Annotated[str, StringConstraints(min_length=3, max_length=500)]


class JobBase(BaseSchema):
    """The fields that describe a job, shared by every job schema."""

    title: Title
    location: Location
    employment_type: EmploymentType
    summary: Summary
    description: Description
    # A job needs at least one responsibility and one requirement, otherwise
    # the details page would be empty.
    responsibilities: list[BulletPoint] = Field(min_length=1, max_length=30)
    requirements: list[BulletPoint] = Field(min_length=1, max_length=30)
    # A date (not a timestamp): the job stays open for the whole closing day.
    closing_date: date


class JobCreate(JobBase):
    """Payload of `POST /api/v1/admin/jobs`.

    A new job starts as a draft. Publishing it is a separate, explicit step
    (`status = Open`), which prevents a half-written job from appearing on the
    public site.
    """

    status: JobStatus = JobStatus.DRAFT


class JobUpdate(BaseSchema):
    """Payload of `PATCH /api/v1/admin/jobs/{job_id}`.

    Every field is optional: this is a partial update, so an administrator can
    change the closing date without resending the whole description. A field
    that is omitted stays unchanged; a field that is sent as `null` is
    rejected by the database column it maps to.
    """

    title: Title | None = None
    location: Location | None = None
    employment_type: EmploymentType | None = None
    summary: Summary | None = None
    description: Description | None = None
    responsibilities: list[BulletPoint] | None = Field(default=None, min_length=1, max_length=30)
    requirements: list[BulletPoint] | None = Field(default=None, min_length=1, max_length=30)
    closing_date: date | None = None
    status: JobStatus | None = None


class JobResponse(JobBase):
    """A job as returned by the API."""

    id: int
    status: JobStatus
    created_at: datetime
    updated_at: datetime


class JobListItem(BaseSchema):
    """The reduced job shape used by the public listings page.

    The listings page shows a card per job, so it does not need the full
    description or the bullet points. Sending less data makes the public
    endpoint faster.
    """

    id: int
    title: str
    location: str
    employment_type: EmploymentType
    summary: str
    closing_date: date
    status: JobStatus


class JobCloseResponse(BaseSchema):
    """Result of `PATCH /api/v1/admin/jobs/{job_id}/close`."""

    id: int
    status: JobStatus
    message: str
