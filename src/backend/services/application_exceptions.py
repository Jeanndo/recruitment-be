"""Errors raised by the application service and the CV storage helpers.

They follow the same idea as `backend.services.exceptions`: the error knows
which HTTP status it deserves, and one handler in `main.py` turns it into a
response. That keeps FastAPI out of the service layer, so the rules can also be
called from a script or a test without an HTTP request.

`detail` is either a human-readable sentence or, for the CV, a list shaped like
FastAPI's own validation errors so the frontend can attach the message to the
file field.
"""

from __future__ import annotations

from typing import Any


class ApplicationError(Exception):
    """Base class for every application-related failure."""

    status_code: int = 400

    def __init__(self, message: Any, status_code: int | None = None) -> None:
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        super().__init__(str(message))


class ApplicationNotFoundError(ApplicationError):
    """No application with that id."""

    status_code = 404


class JobNotAcceptingApplicationsError(ApplicationError):
    """The job exists publicly but is closed or past its closing date."""

    status_code = 409


class DuplicateApplicationError(ApplicationError):
    """This email already applied for this job."""

    status_code = 409


class InvalidApplicationStatusTransitionError(ApplicationError):
    """The requested review status change is not allowed."""

    status_code = 409


class CVValidationError(ApplicationError):
    """The uploaded file is not an acceptable CV.

    The message is wrapped in a list with a `loc` of `["body", "cv"]`, the same
    shape FastAPI uses for its own 422 responses. The frontend can therefore
    show the problem next to the upload field without special-casing it.
    """

    status_code = 422

    def __init__(self, message: str) -> None:
        super().__init__(
            [{"loc": ["body", "cv"], "msg": message, "type": "value_error"}]
        )


class CVFileMissingError(ApplicationError):
    """The database row exists but the stored file cannot be served."""

    status_code = 404
