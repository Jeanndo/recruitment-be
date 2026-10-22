from datetime import datetime
from pydantic import BaseModel, EmailStr, Field


class AdminLoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class AdminUserResponse(BaseModel):
    id: int
    email: EmailStr
    full_name: str
    created_at: datetime




class LoginResponse(BaseModel):
    admin:AdminUserResponse
    message: str



class LogoutResponse(BaseModel):
    message: str