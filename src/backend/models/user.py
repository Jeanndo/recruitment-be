"""SQLAlchemy model for the staff accounts that can sign in to the admin area.

Important design decision
-------------------------
BrightCore has exactly one kind of account: a member of staff. Candidates
never create an account - they submit an *application*

The table is called `users` and the class is called `User` as there should be more than one staff members.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum

from sqlalchemy import Boolean, DateTime, Enum as SAEnum, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class UserRole(str, Enum):
    """Roles a signed-in staff member can have.

    The values are the strings that end up in the database.
    """

    ADMIN = "admin"
    RECRUITER = "recruiter"


# `native_enum=False` stores the role as a VARCHAR instead of creating a
# PostgreSQL ENUM type. Adding a role later is then an ordinary Alembic
# migration rather than a type rewrite.
# `create_constraint=True` adds a CHECK constraint, so the *database* also
# refuses a role that does not exist ("database-level integrity").
#`values_callable` makes SQLAlchemy store `"admin"` instead of
# the Python name `"ADMIN"`, which keeps the stored data readable.

ROLE_ENUM = SAEnum(
    UserRole,
    name="user_role",
    native_enum=False,
    length=20,
    create_constraint=True,
    values_callable=lambda enum_cls: [member.value for member in enum_cls],
)


class User(Base):
    """A staff account that can log in to the admin area."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # 254 characters is the maximum length of a valid email address
    # The column is unique.
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True, nullable=False)

    full_name: Mapped[str] = mapped_column(String(150), nullable=False)

    # ONLY the hash of the password is stored. The plain password is never
    # written to the database.
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    role: Mapped[UserRole] = mapped_column(ROLE_ENUM, default=UserRole.ADMIN, nullable=False)

    # Let's disable an account without deleting it, so historic data
    # (for example "reviewed by") keeps its meaning.
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    def __repr__(self) -> str:
        # Never print the password hash.
        return f"<User id={self.id} email={self.email!r} role={self.role.value}>"
