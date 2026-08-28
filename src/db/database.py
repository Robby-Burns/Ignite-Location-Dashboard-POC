"""Database configuration and session factory for Ignite Facility Operational Decision Agent POC.

Supports:
- Neon PostgreSQL / Railway (via DATABASE_URL / NEON_DATABASE_URL with pg8000 pure-Python driver)
- Local SQLite fallback (aiosqlite/sqlite3) for instant local dev and automated tests
"""

from __future__ import annotations

import os
import urllib.parse

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv()

Base = declarative_base()

# Lazy-initialized engine and session factory
_engine = None
_session_factory = None


def get_database_url() -> str:
    """Derive clean database URL, normalizing PostgreSQL URLs for Neon/Railway with pg8000."""
    raw_url = os.getenv("NEON_DATABASE_URL") or os.getenv("DATABASE_URL")

    # If no URL or sample placeholder is present, or testing, fallback to SQLite
    if not raw_url or "sample-pool" in raw_url or os.getenv("TESTING") == "1":
        return "sqlite:///./ignite_facility.db"

    # Normalize PostgreSQL URL for pg8000 (pure-Python, works seamlessly on Windows/ARM64 and Linux)
    if raw_url.startswith(("postgres://", "postgresql://")):
        parsed = urllib.parse.urlparse(raw_url)
        port_part = f":{parsed.port}" if parsed.port else ""
        path = parsed.path
        return f"postgresql+pg8000://{parsed.username}:{parsed.password}@{parsed.hostname}{port_part}{path}"

    return raw_url


def _get_engine():
    """Get or create the SQLAlchemy engine (lazy initialization)."""
    global _engine
    if _engine is None:
        db_url = get_database_url()
        engine_kwargs = {"echo": False}
        if "sqlite" in db_url:
            engine_kwargs["connect_args"] = {"check_same_thread": False}
        else:
            engine_kwargs["pool_size"] = 5
            engine_kwargs["max_overflow"] = 10
            engine_kwargs["pool_recycle"] = 300
        _engine = create_engine(db_url, **engine_kwargs)
    return _engine


def _get_session_factory():
    """Get or create the session factory (lazy initialization)."""
    global _session_factory
    if _session_factory is None:
        _session_factory = sessionmaker(
            bind=_get_engine(),
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )
    return _session_factory


# Backward-compatible module-level access
@property
def engine():
    return _get_engine()


@property
def SessionFactory():
    return _get_session_factory()


def get_db():
    """FastAPI dependency for yielding database sessions."""
    session = _get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db() -> None:
    """Initialize database tables idempotently."""
    from src.db.models import DailySnapshotRecord, FacilityRecord  # noqa: F401

    Base.metadata.create_all(bind=_get_engine())
