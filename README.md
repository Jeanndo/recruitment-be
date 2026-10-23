# BrightCore e-Recruitment API

The API behind the BrightCore careers site: a public job board, application
submission with CV uploads, staff authentication, and a protected admin
workspace for managing jobs and reviewing applicants.

The matching frontend lives in the `recruitment-web-fe/` repository and runs at
`http://localhost:3000` during development.

## What it does

- **Public careers site**
  - Lists only open jobs whose closing date has not passed.
  - Returns full job details, including closed jobs so the page can explain
    that applications are no longer accepted.
  - Accepts applications as `multipart/form-data` with a PDF CV (max 5 MB).
  - Prevents the same email address from applying to the same job twice.
- **Staff authentication**
  - Session-based login with a signed, HttpOnly cookie.
  - Passwords are hashed with Argon2.
  - Only administrators and recruiters can reach `/api/v1/admin/*`.
- **Admin workspace**
  - Dashboard totals by job and by application status.
  - Create, edit, open, and close jobs.
  - Review applications, filter by status, search applicants, and keep an
    internal note.
  - Accept or reject applications and download CVs through a protected route.
- **Email notifications**
  - Confirmation email when an application is submitted.
  - Acceptance or rejection email when the status actually changes.
  - Internal admin notes are never included in applicant emails.
  - Sending is best-effort and never fails the underlying request.

## Tech stack

| Layer | Choice |
| --- | --- |
| Language | Python 3.14 |
| Framework | FastAPI |
| ORM | SQLAlchemy 2 |
| Migrations | Alembic |
| Database | PostgreSQL |
| Configuration | Pydantic Settings + `.env` |
| Auth | Argon2 passwords, signed session cookie |
| Email | Gmail SMTP (App Password) |

## Project layout

```text
backend/
├── alembic/                  # Migration environment and versions
├── src/backend/
│   ├── api/
│   │   ├── dependencies.py   # Authentication dependencies
│   │   └── routes/           # Public, auth, and admin endpoints
│   ├── core/                 # Settings and password hashing
│   ├── models/               # SQLAlchemy table definitions
│   ├── schemas/              # Request/response validation
│   ├── services/             # Business rules, CV storage, email
│   ├── database.py           # Engine, session factory, declarative base
│   ├── main.py               # FastAPI application and middleware
│   └── seed.py               # First admin account and demo jobs
├── var/cvs/                  # Uploaded CVs (gitignored, private)
├── .env.example
├── alembic.ini
├── pyproject.toml
└── README.md
```

## Prerequisites

- Python **3.14** (declared in `.python-version`)
- [`uv`](https://docs.astral.sh/uv/) **0.13+**
- PostgreSQL **14+** running locally (or a hosted database)
- A database named `brightcore`

Create the database once:

```bash
createdb -U postgres brightcore
```

Or with `psql`:

```bash
psql -U postgres -c "CREATE DATABASE brightcore;"
```

## Quick start

```bash
cd recruitment-be

# 1. Local configuration
cp .env.example .env
# Edit .env: DATABASE_URL, SECRET_KEY, ADMIN_PASSWORD are required.

# 2. Install dependencies and create the virtual environment
uv sync

# 3. Create the tables
uv run alembic upgrade head

# 4. Create the first admin account and demo jobs (safe to re-run)
uv run python -m backend.seed

# 5. Start the API with auto-reload
uv run fastapi dev src/backend/main.py
```

Once it starts:

| URL | Purpose |
| --- | --- |
| `http://localhost:8000` | API root |
| `http://localhost:8000/docs` | Swagger UI |
| `http://localhost:8000/redoc` | ReDoc |
| `http://localhost:8000/health` | Liveness check |

The seed script creates the account from `ADMIN_EMAIL` / `ADMIN_PASSWORD` and
three demo jobs. Run it with `--reset-password` to restore the administrator
password to the value in `.env`:

```bash
uv run python -m backend.seed --reset-password
```

## Environment variables

Copy `.env.example` to `.env` and fill in real values. `.env` is gitignored;
never commit real credentials.

| Variable | Required | Default | Description |
| --- | --- | --- | --- |
| `DATABASE_URL` | Yes | — | SQLAlchemy URL, e.g. `postgresql+psycopg://postgres:password@localhost:5432/brightcore` |
| `SECRET_KEY` | Yes | — | Signs the session cookie. Must be long and random. |
| `ADMIN_EMAIL` | No | `admin@brightcore.com` | Email of the seeded administrator. |
| `ADMIN_PASSWORD` | Yes | — | Password of the seeded administrator. |
| `ADMIN_FULL_NAME` | No | `BrightCore Admin` | Display name of the seeded administrator. |
| `CORS_ORIGINS` | No | `http://localhost:3000` | Comma-separated allowed frontend origins. |
| `COOKIE_SECURE` | No | `false` | Set `true` only when the API is served over HTTPS. |
| `EMAIL_SENDER` | No | empty | Gmail address used to send applicant emails. |
| `EMAIL_SENDER_PASS` | No | empty | Gmail App Password for `EMAIL_SENDER`. |
| `CV_UPLOAD_DIR` | No | `var/cvs` | Directory where uploaded CVs are stored. Read from the process environment, not from `.env`; export it before starting the API. |

> **Email is optional.** With `EMAIL_SENDER` or `EMAIL_SENDER_PASS` empty, the
> API still works; it logs that the email was skipped. For real delivery,
> enable 2-Step Verification on the Gmail account and create an App Password at
> <https://myaccount.google.com/apppasswords>.

Generate a suitable secret key:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

## API overview

All endpoints are under `http://localhost:8000`. Interactive documentation is
available at `/docs`.

### Public

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/api/v1/jobs` | List open, non-expired jobs. Supports `search`, `location`, `employment_type`, `page`, and `page_size`. |
| `GET` | `/api/v1/jobs/{job_id}` | Get one job. Closed jobs are visible; drafts are not. |
| `POST` | `/api/v1/jobs/{job_id}/applications` | Apply with `full_name`, `email`, `phone_number`, `cover_note`, and `cv` as `multipart/form-data`. |

### Authentication

| Method | Path | Description |
| --- | --- | --- |
| `POST` | `/api/v1/auth/login` | Log in with JSON `{ "email": "...", "password": "..." }`. Sets the session cookie. |
| `POST` | `/api/v1/auth/logout` | Clear the session cookie. |
| `GET` | `/api/v1/auth/me` | Return the account behind the current session. |

The session cookie is named `brightcore_session`, is HttpOnly, uses
`SameSite=Lax`, and lasts 8 hours by default.

### Admin (session required)

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/api/v1/admin/dashboard` | Totals for jobs, applications, and applications by status. |
| `GET` | `/api/v1/admin/jobs` | List all jobs, including drafts and closed roles. |
| `POST` | `/api/v1/admin/jobs` | Create a job. Starts as a draft by default. |
| `GET` | `/api/v1/admin/jobs/{job_id}` | Read a job for editing. |
| `PATCH` | `/api/v1/admin/jobs/{job_id}` | Partially update a job, including reopening a closed one. |
| `PATCH` | `/api/v1/admin/jobs/{job_id}/close` | Close an open job. Applications are kept. |
| `GET` | `/api/v1/admin/jobs/{job_id}/applications` | List applications, newest first. Supports `status`, `search`, `page`, `page_size`. |
| `GET` | `/api/v1/admin/applications/{application_id}` | Full application detail, including the internal note and CV metadata. |
| `PATCH` | `/api/v1/admin/applications/{application_id}/status` | Change the review status and optionally the internal note. |
| `GET` | `/api/v1/admin/applications/{application_id}/cv` | Download the applicant's CV as a PDF. |

Requests without a valid session return `401`. A signed-in account without a
staff role returns `403`.

## Domain rules

### Job lifecycle

Allowed transitions:

- **Draft → Open** — publish the role.
- **Draft → Closed** — discard a draft without publishing it.
- **Open → Closed** — stop accepting applications.
- **Closed → Open** — reopen the role.

A job accepts applications only while its status is **Open** and its closing
date has not passed. A new job starts as **Draft** unless the request sets
another status. Closing never deletes a job or its applications.

### Application review

Allowed transitions:

- **Pending → Accepted**
- **Pending → Rejected**
- **Accepted → Rejected** and **Rejected → Accepted** to correct a mistake.

Every application starts as **Pending**.

- Returning to **Pending** is not allowed.
- Sending the current status is accepted and only updates the internal note.
- Omitting `admin_note` keeps the existing note; sending `null` clears it.

### Files and privacy

- CVs are stored outside the source tree under `var/cvs/` with generated names.
- The stored path is never exposed to clients.
- Downloads go through the authenticated admin endpoint only.
- Validation checks the `.pdf` extension, the declared MIME type, the `%PDF-`
  signature, and the 5 MB limit.

## Development

Create a migration after changing a model:

```bash
uv run alembic revision --autogenerate -m "describe the change"
uv run alembic upgrade head
```

Inspect or roll back migrations:

```bash
uv run alembic current
uv run alembic history
uv run alembic downgrade -1
```

Uploaded files are written to `var/cvs` by default. Export `CV_UPLOAD_DIR` to
store them somewhere else (for example a persistent volume in production).
Keep that directory writable by the API process.

There is no automated test suite checked in yet. Use Swagger at `/docs` for
manual checks of the public and admin flows.

## Troubleshooting

| Symptom | Likely cause / fix |
| --- | --- |
| `DATABASE_URL` or `SECRET_KEY` validation error on startup | `.env` is missing or incomplete. Copy `.env.example` and fill it in. |
| `relation "jobs" does not exist` | Run `uv run alembic upgrade head`. |
| Login returns `401` | Run the seed script; check the email and password in `.env`. |
| Browser requests fail with CORS | Add the frontend origin to `CORS_ORIGINS` (comma-separated, no trailing slash). |
| Session cookie not sent over HTTP | Keep `COOKIE_SECURE=false` locally; set it to `true` only behind HTTPS. |
| Emails are not delivered | Check `EMAIL_SENDER`, the Gmail App Password, and the backend logs. A mail failure does not fail the request. |
| CV upload fails | Only PDFs up to 5 MB are accepted; make sure `var/cvs` (or `CV_UPLOAD_DIR`) is writable. |

## Production notes

- Set `COOKIE_SECURE=true` and serve the API over HTTPS.
- Use a strong, unique `SECRET_KEY`.
- Set `CORS_ORIGINS` to the exact production frontend origin.
- Run `uv run alembic upgrade head` during deployment.
- Keep the CV directory on persistent storage, or replace the storage service
  with an object store.
- Run behind a process manager or container orchestrator instead of
  `fastapi dev`.
