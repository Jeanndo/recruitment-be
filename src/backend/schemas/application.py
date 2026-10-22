from datetime import datetime
from enum import Enum
from pydantic import BaseModel, EmailStr, Field, ConfigDict



class ApplicationStatus(str, Enum):
    PENDING = "Pending"
    ACCEPTED = "Accepted"
    REJECTED = "Rejected"




class ApplicationCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=150)
    email: EmailStr
    phone: str = Field(min_length=7, max_length=10)
    cover_note: str = Field(min_length=10, max_length=5000)



class ApplicationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    job_id: int
    full_name: str
    email: EmailStr
    phone: str
    cover_note: str
    status: ApplicationStatus
    submitted_at: datetime




class ApplicationListItem(BaseModel):
    id: int
    job_id: int
    full_name: str
    email: EmailStr
    status: ApplicationStatus
    submitted_at: datetime




class ApplicationStatusUpdate(BaseModel):
    status: ApplicationStatus
    admin_note: str | None = Field(default=None, max_length=2000)




class ApplicationStatusResponse(BaseModel):
    id: int
    status: ApplicationStatus
    admin_note: str | None
    reviewed_at: datetime | None


class CVMetadataResponse(BaseModel):
    application_id: int
    filename: str
    content_type: str = "application/pdf"
    size_bytes: int
    download_urll: str
