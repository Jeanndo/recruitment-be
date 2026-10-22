"""Pydantic schemas for the admin dashboard summary.

Every number here is calculated from the database. Nothing is hardcoded in the
frontend, so the dashboard always reflects the real data.
"""

from __future__ import annotations

from backend.models.job import JobStatus
from backend.schemas.common import BaseSchema

__all__ = [
    "ApplicationStatusCounts",
    "DashboardResponse",
    "JobDashboardSummary",
]


class ApplicationStatusCounts(BaseSchema):
    """How many applications exist in each status."""

    pending: int
    accepted: int
    rejected: int
    total: int


class JobDashboardSummary(BaseSchema):
    """The application counts of a single job."""

    job_id: int
    title: str
    status: JobStatus
    application_counts: ApplicationStatusCounts


class DashboardResponse(BaseSchema):
    """The whole dashboard payload."""

    total_jobs: int
    open_jobs: int
    closed_jobs: int
    # Draft jobs are counted separately: they are not published yet, so they
    # must not be mixed into the open or closed numbers.
    draft_jobs: int
    total_applications: int
    application_counts: ApplicationStatusCounts
    jobs: list[JobDashboardSummary]
