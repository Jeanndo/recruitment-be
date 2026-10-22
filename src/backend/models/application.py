"""SQLAlchemy model for a candidate's application to a job.

This is the heart of the data model: it links a candidate to a job, stores the
answers from the application form and keeps a reference to the uploaded CV.

Two integrity rules are enforced *by the database*, not only by the API:

1. `UNIQUE (job_id, normalized_email)` - one candidate can apply to a given
   job only once, even if two requests arrive at the same moment.
2. `cv_storage_name` is unique - two applications can never point at the same
   stored file, which would let one applicant download somebody else's CV.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum

from sqlalchemy import (
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


class ApplicationStatus(str, Enum):
    """Where an application is in the review process."""

    PENDING = "Pending"
    ACCEPTED = "Accepted"
    REJECTED = "Rejected"


APPLICATION_STATUS_ENUM = SAEnum(
    ApplicationStatus,
    name="application_status",
    native_enum=False,
    length=20,
    create_constraint=True,
    values_callable=lambda enum_cls: [member.value for member in enum_cls],
)


class Application(Base):
    """A single application submitted for a job."""

    __tablename__ = "applications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Foreign key to the job this application belongs to.
    # `ondelete="RESTRICT"` refuses to delete a job that still has
    # applications, which protects the applicant data.
    job_id: Mapped[int] = mapped_column(
        ForeignKey("jobs.id", ondelete="RESTRICT"),
        nullable=False,
        # Indexed because the admin list is always "applications of job X".
        index=True,
    )

    full_name: Mapped[str] = mapped_column(String(150), nullable=False)

    # The address exactly as the candidate typed it (trimmed). It is what the
    # admin sees, so it is kept for display purposes.
    email: Mapped[str] = mapped_column(String(254), nullable=False)

    # The same address lowercased. The duplicate check compares this column,
    # so "Jane.Doe@example.com" and "jane.doe@example.com" count as the same person.
    # `normalized_email` is what the unique constraint uses.
    normalized_email: Mapped[str] = mapped_column(String(254), nullable=False)

    phone_number: Mapped[str] = mapped_column(String(20), nullable=False)

    cover_note: Mapped[str] = mapped_column(Text, nullable=False)

    # The *server generated* name of the stored CV file (for example
    # "3f9a1c2e.pdf"). The original filename is kept separately for display.
    # The real path on disk is never stored in the database and never leaves
    # the backend.
    cv_storage_name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    cv_original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    cv_content_type: Mapped[str] = mapped_column(
        String(100),
        default="application/pdf",
        nullable=False,
    )
    cv_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)

    status: Mapped[ApplicationStatus] = mapped_column(
        APPLICATION_STATUS_ENUM,
        default=ApplicationStatus.PENDING,
        nullable=False,
        # Indexed because the admin filters the list by status.
        index=True,
    )

    # Optional note written by an administrator. Internal only: 
    # it is never part of the public response schema.
    admin_note: Mapped[str | None] = mapped_column(Text, nullable=True)

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

    # The job this application was submitted for.
    job: Mapped["Job"] = relationship(back_populates="applications")

    __table_args__ = (
        # The duplicate-application rule, enforced by PostgreSQL itself.
        UniqueConstraint(
            "job_id",
            "normalized_email",
            name="applications_job_id_normalized_email",
        ),
        # Squupports the most common admin ery: "applications of job X with status Y".
        # 
        Index("ix_applications_job_id_status", "job_id", "status"),
        # Supports sorting a list by submission date.
        Index("ix_applications_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<Application id={self.id} job_id={self.job_id} "
            f"email={self.email!r} status={self.status.value}>"
        )


# Imported at the end of the module so SQLAlchemy can resolve the "Job"
# relationship target by name. See the same note in `backend/models/job.py`.
from backend.models.job import Job 
