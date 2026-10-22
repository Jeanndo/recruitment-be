from pydantic import BaseModel
from backend.schemas import application



class ApplicationStatusCounts(BaseModel):
    pending: int
    accepted: int
    rejected: int
    total: int



class JobDashboardSummary(BaseModel):
    job_id: int
    title: str
    job_status: str
    application_counts: ApplicationStatusCounts



class DashboardResponse(BaseModel):
    total_jobs: int
    open_jobs: int
    closed_jobs: int
    total_applications: int
    pending_applications: int
    accepted_applications: int
    rejected_applications: int
    jobs: list[JobDashboardSummary]