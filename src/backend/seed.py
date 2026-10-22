"""Create the first staff account and a few demo jobs.

Run it with:
    uv run python -m backend.seed

The script is safe to run more than once. It looks for an existing account by
email and for existing jobs by title, so a second run does not create
duplicates. Pass `--reset-password` to set the administrator's password back to
the value in `.env` (useful if you forget the development password).

None of the credentials are written in this file - they come from `.env`,
which is gitignored.
"""

from __future__ import annotations

import argparse
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.core.config import settings
from backend.core.security import hash_password
from backend.database import SessionLocal
from backend.models.job import EmploymentType, Job, JobStatus
from backend.models.user import User, UserRole


def _sample_jobs() -> list[dict]:
    """The demo jobs, built at run time so the closing dates stay relative to today."""
    today = date.today()

    return [
        {
            "title": "Senior Backend Engineer",
            "location": "Remote (East Africa)",
            "employment_type": EmploymentType.FULL_TIME,
            "summary": "Design and build the APIs that power BrightCore's hiring platform.",
            "description": (
                "You will join a small platform team that owns the services behind "
                "our job board and applicant tracking tools. We care about clear "
                "code, solid tests and databases that make invalid states hard to "
                "represent."
            ),
            "responsibilities": [
                "Design and ship REST APIs with FastAPI",
                "Review database schemas and write migrations",
                "Mentor junior engineers and improve our engineering practices",
            ],
            "requirements": [
                "5+ years building backend services in Python",
                "Strong SQL and PostgreSQL knowledge",
                "Experience with automated testing and CI",
            ],
            "closing_date": today + timedelta(days=21),
            "status": JobStatus.OPEN,
        },
        {
            "title": "Product Designer",
            "location": "Kigali, Rwanda",
            "employment_type": EmploymentType.CONTRACT,
            "summary": "Shape how candidates and recruiters experience BrightCore.",
            "description": (
                "This is a six-month contract for a designer who likes working close "
                "to the code. You will own the end-to-end experience of applying for "
                "a job and of reviewing applicants, from the first sketch to the "
                "final accessibility check."
            ),
            "responsibilities": [
                "Turn research into clear, testable designs",
                "Maintain and extend our design system",
                "Work closely with engineers during implementation",
            ],
            "requirements": [
                "A portfolio of shipped product work",
                "Confidence with Figma and design tokens",
                "Experience testing designs with real users",
            ],
            "closing_date": today + timedelta(days=14),
            "status": JobStatus.OPEN,
        },
        {
            "title": "Data Analyst",
            "location": "London, United Kingdom",
            "employment_type": EmploymentType.FULL_TIME,
            "summary": "Turn recruitment data into decisions our customers can act on.",
            "description": (
                "You will own the reporting layer of our recruitment product: the "
                "dashboards recruiters use every morning and the monthly insights "
                "our leadership team relies on. This role is already filled, so the "
                "posting is kept as a closed example."
            ),
            "responsibilities": [
                "Build dashboards for recruiters and hiring managers",
                "Maintain the reporting pipeline and data quality checks",
                "Present monthly insights to the leadership team",
            ],
            "requirements": [
                "Strong SQL and spreadsheet skills",
                "Experience with a BI tool such as Metabase",
                "Comfortable explaining data to non-technical colleagues",
            ],
            "closing_date": today - timedelta(days=5),
            "status": JobStatus.CLOSED,
        },
    ]


def create_or_update_admin(db: Session, *, reset_password: bool) -> tuple[User, str]:
    """Make sure the administrator from `.env` exists.

    Returns the user and a short word describing what happened:
    "created", "password reset" or "already existed".
    """
    # Emails are always stored lowercase so the login lookup is unambiguous.
    email = settings.admin_email.strip().lower()
    existing = db.scalar(select(User).where(User.email == email))

    if existing is None:
        user = User(
            email=email,
            full_name=settings.admin_full_name,
            password_hash=hash_password(settings.admin_password),
            role=UserRole.ADMIN,
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user, "created"

    if reset_password:
        existing.password_hash = hash_password(settings.admin_password)
        db.commit()
        db.refresh(existing)
        return existing, "password reset"

    return existing, "already existed"


def create_missing_jobs(db: Session) -> tuple[int, int]:
    """Insert the demo jobs that are not in the database yet.

    Returns (created, skipped). A job counts as present when its title
    matches, which is enough for demo data.
    """
    created = 0
    skipped = 0

    for job_data in _sample_jobs():
        already_there = db.scalar(select(Job.id).where(Job.title == job_data["title"]))
        if already_there is not None:
            skipped += 1
            continue

        db.add(Job(**job_data))
        created += 1

    db.commit()
    return created, skipped


def main() -> None:
    """Entry point of `python -m backend.seed`."""
    parser = argparse.ArgumentParser(description="Seed the BrightCore database.")
    parser.add_argument(
        "--reset-password",
        action="store_true",
        help="reset the administrator password to ADMIN_PASSWORD from .env",
    )
    args = parser.parse_args()

    with SessionLocal() as db:
        admin, admin_result = create_or_update_admin(db, reset_password=args.reset_password)
        created, skipped = create_missing_jobs(db)

    print(f"Admin {admin.email}: {admin_result}.")
    print(f"Demo jobs: {created} created, {skipped} already present.")


    print("\nYou can now log in at POST /api/v1/auth/login with that email and password.")


if __name__ == "__main__":
    main()
