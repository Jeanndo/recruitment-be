from pydantic import BaseModel, EmailStr
from backend.schemas.application import ApplicationStatus
from backend.schemas.job import JobStatus



class AdminJobListItem(BaseModel):
    id: int
    title: str
    location: str
    status: JobStatus
    close_date: str
    application_count: int




class ApplicationFilterOptions(BaseModel):
    status: ApplicationStatus | None = None
    search: str | None = None
    page: int = 1
    page_size: int = 20




class PaginatedApplicants(BaseModel):
    items: list["AdminApplicantItem"]
    page: int
    page_size: int
    total: int




class AdminApplicantItem(BaseModel):
    id: int
    job_id: int
    full_name: str
    email: EmailStr
    phone: str
    status: ApplicationStatus
    submitted_at: str
    cv_available: bool


