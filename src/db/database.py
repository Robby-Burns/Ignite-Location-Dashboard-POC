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
        # Clean path from any query params attached incorrectly
        path = parsed.path
        return f"postgresql+pg8000://{parsed.username}:{parsed.password}@{parsed.hostname}{port_part}{path}"

    return raw_url


DATABASE_URL = get_database_url()

# Engine creation with connection pool settings
engine_kwargs = {"echo": False}
if "sqlite" in DATABASE_URL:
    engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    engine_kwargs["pool_size"] = 5
    engine_kwargs["max_overflow"] = 10
    engine_kwargs["pool_recycle"] = 300

engine = create_engine(DATABASE_URL, **engine_kwargs)
SessionFactory = sessionmaker(
    bind=engine,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


def get_db():
    """FastAPI dependency for yielding database sessions."""
    session = SessionFactory()
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
    # Ensure models are imported so Base has table definitions
    from src.db.models import DailySnapshotRecord, FacilityRecord  # noqa: F401

    Base.metadata.create_all(bind=engine)
