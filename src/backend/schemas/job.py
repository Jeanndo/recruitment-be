from datetime import date, datetime
from enum import Enum
from pydantic import BaseModel, ConfigDict, Field


class Employment_Type(str, Enum):
    FULL_TIME = "Full-time"
    PART_TIME = "Part-time"
    CONTRACT = "Contract"
    INTERNSHIP = "Internship"

class JobStatus(str, Enum):
    DRAFT = "Draft"
    OPEN = "Open"
    CLOSED = "Closed"

class JobBase(BaseModel):
    title: str = Field(min_length=3, max_length=150)
    location: str = Field(min_length=2, max_length=150)
    employment_type: Employment_Type
    summary: str = Field(min_length=10, max_length=500)
    description: str = Field(min_length=20)
    responsibilities: list[str] = Field(min_length=1)
    requirements: list[str] = Field(min_length=1)
    closing_date: date


class JobCreate(JobBase):
    status: JobStatus = JobStatus.DRAFT



class JobUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=150)
    location: str | None = Field(default=None, max_length=150)
    employment_type: Employment_Type | None = None
    summary: str | None = Field(default=None, max_length=500)
    description: str | None = None
    responsibilities: list[str] | None = None
    requirements: list[str] | None = None
    closing_date: date | None = None
    status: JobStatus | None = None



class JobResponse(JobBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    status: JobStatus
    created_at: datetime
    updated_at: datetime



class JobListItem(BaseModel):
    id: int
    title: str
    location: str
    employment_type: Employment_Type
    summary: str
    closing_date: date
    status: JobStatus


class JobCloseResponse(BaseModel):
    id: int
    status:JobStatus
    Message: str