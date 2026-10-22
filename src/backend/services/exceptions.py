"""Errors raised by the service layer when a business rule is broken.

Keeping these separate from FastAPI means the rules can also be used by the
seed script, the tests, or a future background task. The routes (and one
exception handler in `main.py`) decide what HTTP status each error becomes.
"""

from __future__ import annotations


class JobServiceError(Exception):
    """Base class for every job-related business failure."""

    status_code: int = 400

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class JobNotFoundError(JobServiceError):
    """The job does not exist, or a draft is being requested publicly."""

    status_code = 404


class InvalidStatusTransitionError(JobServiceError):
    """The requested status change is not part of the allowed policy."""

    status_code = 409


class JobAlreadyClosedError(JobServiceError):
    """Someone tried to close a job that is already closed."""

    status_code = 409


class InvalidClosingDateError(JobServiceError):
    """A job was published with a closing date that is already in the past."""

    status_code = 422
