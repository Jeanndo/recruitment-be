"""SQLAlchemy models for the BrightCore application.

Importing this package imports every model module. That matters because
SQLAlchemy resolves relationships such as `Job.applications` by looking the
target class up by name in its class registry. A model that was never
imported cannot be found, so always import models through this package:

    from backend.models import Application, Job, User

This is also what the Alembic environment does, so `alembic revision
--autogenerate` sees every table.
"""

from backend.models.application import APPLICATION_STATUS_ENUM, Application, ApplicationStatus
from backend.models.job import EMPLOYMENT_TYPE_ENUM, JOB_STATUS_ENUM, EmploymentType, Job, JobStatus
from backend.models.user import ROLE_ENUM, User, UserRole

__all__ = [
    "APPLICATION_STATUS_ENUM",
    "EMPLOYMENT_TYPE_ENUM",
    "JOB_STATUS_ENUM",
    "ROLE_ENUM",
    "Application",
    "ApplicationStatus",
    "EmploymentType",
    "Job",
    "JobStatus",
    "User",
    "UserRole",
]
