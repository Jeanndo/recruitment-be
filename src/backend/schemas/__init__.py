"""Pydantic schemas - the API contract of the BrightCore backend.

Every schema describes the JSON that travels between the frontend and the
backend:

* request schemas validate what a client sends,
* response schemas describe what the client receives.

The schemas never touch the database directly and the SQLAlchemy models never
import a schema. The only thing they share are the enums, which live in the
model modules because they are part of the domain.
"""

from backend.schemas.admin import (
    AdminApplicationDetail,
    AdminApplicationItem,
    AdminJobFilterOptions,
    AdminJobListItem,
    AdminJobReference,
    ApplicationFilterOptions,
)
from backend.schemas.application import (
    CV_MAX_SIZE_BYTES,
    ApplicationCreatedResponse,
    ApplicationCreate,
    ApplicationListItem,
    ApplicationResponse,
    ApplicationStatusResponse,
    ApplicationStatusUpdate,
    CVMetadataResponse,
)
from backend.schemas.auth import LoginRequest, LoginResponse, LogoutResponse
from backend.schemas.common import (
    BaseSchema,
    PaginatedResponse,
    PaginationParams,
    TimestampSchema,
)
from backend.schemas.dashboard import (
    ApplicationStatusCounts,
    DashboardResponse,
    JobDashboardSummary,
)
from backend.schemas.job import (
    EmploymentType,
    JobBase,
    JobCloseResponse,
    JobCreate,
    JobFilterOptions,
    JobListItem,
    JobResponse,
    JobStatus,
    JobUpdate,
)
from backend.schemas.user import UserBase, UserCreate, UserResponse, UserRole, UserUpdate

__all__ = [
    "CV_MAX_SIZE_BYTES",
    "AdminApplicationDetail",
    "AdminApplicationItem",
    "AdminJobFilterOptions",
    "AdminJobListItem",
    "AdminJobReference",
    "ApplicationCreatedResponse",
    "ApplicationCreate",
    "ApplicationFilterOptions",
    "ApplicationListItem",
    "ApplicationResponse",
    "ApplicationStatusCounts",
    "ApplicationStatusResponse",
    "ApplicationStatusUpdate",
    "BaseSchema",
    "CVMetadataResponse",
    "DashboardResponse",
    "EmploymentType",
    "JobBase",
    "JobCloseResponse",
    "JobCreate",
    "JobDashboardSummary",
    "JobFilterOptions",
    "JobListItem",
    "JobResponse",
    "JobStatus",
    "JobUpdate",
    "LoginRequest",
    "LoginResponse",
    "LogoutResponse",
    "PaginatedResponse",
    "PaginationParams",
    "TimestampSchema",
    "UserBase",
    "UserCreate",
    "UserResponse",
    "UserRole",
    "UserUpdate",
]
