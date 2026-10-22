"""Pydantic schemas for the authenticated staff accounts.

One entity, one file: the `users` table holds the accounts that can sign in to
the admin area. Candidates are not users - they are applicants, and they are
described by `backend.schemas.application`.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import EmailStr, StringConstraints

from backend.models.user import UserRole
from backend.schemas.common import BaseSchema

__all__ = [
    "UserBase",
    "UserCreate",
    "UserResponse",
    "UserRole",
    "UserUpdate",
]

FullName = Annotated[str, StringConstraints(min_length=2, max_length=150)]
Password = Annotated[str, StringConstraints(min_length=8, max_length=128)]


class UserBase(BaseSchema):
    """Fields shared by every user schema."""

    email: EmailStr
    full_name: FullName


class UserCreate(UserBase):
    """Payload used by the seed command to create the first account."""

    # The plain password is only accepted here, at the very edge of the
    # application. The service layer hashes it immediately and only ever
    # stores the hash.
    password: Password
    role: UserRole = UserRole.ADMIN


class UserUpdate(BaseSchema):
    """Partial update of a user. Every field is optional."""

    full_name: FullName | None = None
    email: EmailStr | None = None
    password: Password | None = None
    role: UserRole | None = None
    is_active: bool | None = None


class UserResponse(UserBase):
    """A user as returned by the API.

    There is no `password_hash` field on purpose: the hash must never leave
    the backend.
    """

    id: int
    role: UserRole
    is_active: bool
    created_at: datetime
