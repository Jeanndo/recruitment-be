"""Alembic environment.

Alembic runs this file for every migration command. It connects to the same
database as the application by reading `DATABASE_URL` from `.env` through
`backend.core.config`, so the connection string and the password exist in
exactly one place and never in a tracked file.

Typical use:
    uv run alembic revision --autogenerate -m "describe the change"
    uv run alembic upgrade head
"""

from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# Importing the models package registers every table on Base.metadata.
# Without this import, autogenerate would think the database should be empty
# and would generate a migration that drops everything.
import backend.models  # noqa: F401
from backend.core.config import settings
from backend.database import Base

config = context.config

# `alembic.ini` does not contain the URL. Inject it from the application
# settings. A literal "%" is escaped because configparser treats it specially.
config.set_main_option("sqlalchemy.url", settings.database_url.replace("%", "%%"))

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# What autogenerate compares the real database against.
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Write the SQL to stdout instead of running it.

    Useful when a database administrator wants to review the statements before
    they touch a production database.
    """
    context.configure(
        url=settings.database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Connect to the database and apply the migrations."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        # Migrations are a one-off job, so a small pool is all we need.
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            # Also detect changes to column types, not only added/removed ones.
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
