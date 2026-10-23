"""Application settings.

Every value comes from an environment variable or from the `.env` file at the
project root. Nothing sensitive is written into the source code, so the same
code runs locally and in production with different configuration.

`DATABASE_URL` and `SECRET_KEY` have no default: if they are missing the
application refuses to start instead of silently running with an insecure or
wrong configuration.
"""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# config.py lives in backend/src/backend/core/, so the project root (the
# directory that contains pyproject.toml and .env) is three levels up.
PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    """All configuration the application needs, read once at startup."""

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        # Ignore unrelated variables that happen to be in the environment.
        extra="ignore",
    )

    # --- Database ---------------------------------------------------------
    # Example: postgresql+psycopg://postgres:password@localhost:5432/brightcore
    database_url: str

    # --- Authentication ---------------------------------------------------
    # Signs the session cookie. If this leaks, anyone can forge a session, so
    # it is a secret and it must be long and random.
    secret_key: str
    session_cookie_name: str = "brightcore_session"
    session_max_age_seconds: int = 8 * 60 * 60  # 8 hours
    # Only set this to true when the API is served over HTTPS. On plain
    # http://localhost a Secure cookie would never be sent back.
    cookie_secure: bool = False

    # --- First administrator ---------------------------------------------
    # Used by `python -m backend.seed`.
    admin_email: str = "admin@brightcore.com"
    admin_password: str
    admin_full_name: str = "BrightCore Admin"

    # --- Email ------------------------------------------------------------
    email_sender: str = ""
    email_sender_pass: str = ""

    # --- Frontend ---------------------------------------------------------
    # Comma-separated list, for example "http://localhost:3000".
    cors_origins: str = "http://localhost:3000"

    @property
    def cors_origin_list(self) -> list[str]:
        """The CORS origins as a list, ignoring empty entries."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
