"""BrightCore recruitment API.

This module assembles the application: it creates the FastAPI instance, adds
the middleware and mounts the routers. The actual endpoint code lives in
`backend/api/routes`, the business rules in `backend/services`, and the table
definitions in `backend/models`.

Start it with:
    uv run fastapi dev src/backend/main.py
"""

from __future__ import annotations

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.sessions import SessionMiddleware

from backend.api.routes import admin_applications, admin_jobs, applications, auth, jobs
from backend.core.config import settings
from backend.services.application_exceptions import ApplicationError
from backend.services.exceptions import JobServiceError

app = FastAPI(
    title="BrightCore Recruitment API",
    version="1.0.0",
    description=(
        "Public job board and administrator endpoints for the BrightCore "
        "recruitment site.\n\n"
        "Public endpoints can be called by anyone. Every `/api/v1/admin` "
        "endpoint requires a session cookie created by `/api/v1/auth/login`."
    ),
)

# --- Middleware -------------------------------------------------------------
# Signed session cookie. `same_site="lax"` stops another site from making
# state-changing requests with the user's cookie, which is our main CSRF
# defence. `https_only` is controlled by COOKIE_SECURE in .env.
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.secret_key,
    session_cookie=settings.session_cookie_name,
    max_age=settings.session_max_age_seconds,
    same_site="lax",
    https_only=settings.cookie_secure,
)

# CORS is added last so it wraps every response, including error responses.
# `allow_origins` is an explicit list - never "*" when cookies are involved.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Routers ----------------------------------------------------------------
app.include_router(jobs.router)
app.include_router(applications.router)
app.include_router(admin_jobs.router)
app.include_router(admin_applications.router)
app.include_router(auth.router)


@app.get("/health", tags=["Health"], summary="Liveness check")
def health_check() -> dict[str, str]:
    """Used by Docker and uptime checks to confirm the process is alive."""
    return {"status": "healthy"}


# --- Error handling ---------------------------------------------------------
# Every error leaves the API in the same shape: {"detail": "..."}. The
# frontend can therefore handle errors in one place.


@app.exception_handler(StarletteHTTPException)
def http_exception_handler(request: Request, exception: StarletteHTTPException) -> JSONResponse:
    """Return HTTP errors as `{"detail": ...}` for every path."""
    message = exception.detail or "An error occurred. Please check your request and try again."
    return JSONResponse(
        status_code=exception.status_code,
        content={"detail": message},
    )


@app.exception_handler(RequestValidationError)
def validation_exception_handler(
    request: Request,
    exception: RequestValidationError,
) -> JSONResponse:
    """Turn Pydantic errors into a readable list of field-level problems."""
    errors = [
        {
            "loc": list(error["loc"]),
            "msg": error["msg"],
            "type": error["type"],
        }
        for error in exception.errors()
    ]
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={"detail": errors},
    )


@app.exception_handler(JobServiceError)
def job_service_error_handler(request: Request, exception: JobServiceError) -> JSONResponse:
    """Map a broken business rule to the status code it declares.

    For example `JobNotFoundError` becomes a 404 and
    `InvalidStatusTransitionError` becomes a 409, without every route
    repeating the same try/except.
    """
    return JSONResponse(
        status_code=exception.status_code,
        content={"detail": exception.message},
    )


@app.exception_handler(ApplicationError)
def application_error_handler(request: Request, exception: ApplicationError) -> JSONResponse:
    """Do the same for application rules (duplicates, closed jobs, bad CVs).

    The message is passed through unchanged. For a bad CV it is a list with a
    `loc` of `["body", "cv"]`, mirroring FastAPI's own validation errors so the
    frontend can put the message under the file field.
    """
    return JSONResponse(
        status_code=exception.status_code,
        content={"detail": exception.message},
    )
