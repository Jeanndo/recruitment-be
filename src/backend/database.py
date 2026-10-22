"""Database engine, session factory and the declarative base class.

This module is pure infrastructure: it knows *how* to reach the database, never
*what* the database contains. The table definitions live in `backend.models`.

"""

from __future__ import annotations

import os
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

# Read the connection string from the environment. The SQLite fallback keeps
# `pytest` and quick experiments working on a machine with no database server.
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./jobs.db")

# SQLite only allows a connection to be used from the thread that created it,
# but FastAPI may serve a request from a different worker thread.
# PostgreSQL does not know this argument, so it is only passed to SQLite.
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    # `pool_pre_ping` makes SQLAlchemy test a connection before handing it
    # out. If the database was restarted, the stale connection is replaced
    # instead of raising an error in the middle of a request.
    pool_pre_ping=True,
)

# The session factory. `bind=engine` is essential - without it SQLAlchemy does
# not know which database the sessions should use.
#   * autocommit=False -> we control transactions explicitly.
#   * autoflush=False  -> SQL is sent only when we ask for it (or commit).
#   * expire_on_commit=False -> loaded objects stay usable after a commit
#     instead of being refreshed with an extra SELECT.
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Declarative base class.

    Every ORM model in `backend.models` inherits from `Base`. SQLAlchemy uses
    this class to collect the table definitions, which is how Alembic knows
    what the database *should* look like.
    """


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that provides one database session per request.

    Usage in a route:

        @router.get("/jobs")
        def list_jobs(db: Session = Depends(get_db)):
            ...

    The session is committed when the request finishes normally and rolled
    back if the request raises, so a failed request never leaves half-written
    data in the database.
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
