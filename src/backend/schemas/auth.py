"""Pydantic schemas for the authentication endpoints.

Authentication = proving *who* you are (login).
Authorization  = deciding *what* you may do (admin routes).
Only the first is described here; the second is enforced by the route
dependencies.
"""

from __future__ import annotations

from pydantic import EmailStr, Field

from backend.schemas.common import BaseSchema
from backend.schemas.user import UserResponse

__all__ = [
    "LoginRequest",
    "LoginResponse",
    "LogoutResponse",
]


class LoginRequest(BaseSchema):
    """Credentials sent to `POST /api/v1/auth/login`.

    The password only has a minimum length of 1 here: the check that really
    matters is the hash comparison in the service layer. Refusing to say
    "your password is too short" during login also avoids leaking rules about
    stored accounts to an attacker.
    """

    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class LoginResponse(BaseSchema):
    """Result of a successful login."""

    user: UserResponse
    message: str


class LogoutResponse(BaseSchema):
    """Result of `POST /api/v1/auth/logout`."""

    message: str
