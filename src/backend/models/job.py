"""SQLAlchemy model for a job posting.

The enums live in this module because they are part of the *domain*: the
database column, the API response and the admin interface must all agree on
what "Open" means. The Pydantic schemas import them from here, so there is
only ever one definition of each value.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from enum import Enum

from sqlalchemy import Date, DateTime, Enum as SAEnum, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


class EmploymentType(str, Enum):
    """How the job is contracted (full-time, part-time, ...)."""

    FULL_TIME = "Full-time"
    PART_TIME = "Part-time"
    CONTRACT = "Contract"
    INTERNSHIP = "Internship"


class JobStatus(str, Enum):
    """The lifecycle of a job posting.

    * it can express "Draft" - a post that is written but not published yet,
    * it removes the possibility of contradictory state (a job cannot be both
      open and closed),
    * the database can enforce it with a CHECK constraint.

    A job accepts applications while its status is `OPEN` *and* its closing
    date has not passed. That rule lives in the service layer, not here.
    """

    DRAFT = "Draft"
    OPEN = "Open"
    CLOSED = "Closed"


EMPLOYMENT_TYPE_ENUM = SAEnum(
    EmploymentType,
    name="employment_type",
    native_enum=False,
    length=20,
    create_constraint=True,
    values_callable=lambda enum_cls: [member.value for member in enum_cls],
)

JOB_STATUS_ENUM = SAEnum(
    JobStatus,
    name="job_status",
    native_enum=False,
    length=10,
    create_constraint=True,
    values_callable=lambda enum_cls: [member.value for member in enum_cls],
)


class Job(Base):
    """A job posting shown on the public jobs page."""

    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    title: Mapped[str] = mapped_column(String(150), nullable=False)
    location: Mapped[str] = mapped_column(String(150), nullable=False)
    employment_type: Mapped[EmploymentType] = mapped_column(EMPLOYMENT_TYPE_ENUM, nullable=False)

    # Short text used on the job card in the listings page.
    summary: Mapped[str] = mapped_column(String(500), nullable=False)

    # Full description shown on the job details page. `Text` has no length limit in PostgreSQL;
    # The API layer caps the length instead.
    description: Mapped[str] = mapped_column(Text, nullable=False)

    # Bullet points. `JSON` stores a real list in the column instead of
    # joining everything into one string, so a bullet can be updated without
    # rewriting the whole row.
    responsibilities: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    requirements: Mapped[list[str]] = mapped_column(JSON, nullable=False)

    status: Mapped[JobStatus] = mapped_column(
        JOB_STATUS_ENUM,
        default=JobStatus.DRAFT,
        nullable=False,
        # Indexed because the public listing always filters on the status.
        index=True,
    )

    # The last day on which an application is accepted. A *date* (not a
    # timestamp) on purpose: "we close on the 30th" is easier to reason
    # about than "we close at 23:59:59 on the 30th".
    closing_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        # `onupdate` runs automatically whenever the row is updated.
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Every application submitted for this job. `back_populates` links the two
    # sides of the relationship, so `job.applications` and
    # `application.job` always point at the same objects.
    applications: Mapped[list["Application"]] = relationship(
        back_populates="job",
    )

    def __repr__(self) -> str:
        return f"<Job id={self.id} title={self.title!r} status={self.status.value}>"


# SQLAlchemy resolves relationship targets such as "Application" by name from
# its class registry. Importing the module here guarantees that the class is
# registered no matter which model file a caller imports first.
from backend.models.application import Application
