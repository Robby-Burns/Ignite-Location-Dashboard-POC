"""SQLAlchemy ORM models for persistent storage in Neon PostgreSQL or SQLite."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import JSON, Column, Date, DateTime, Integer, String

from src.db.database import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


class FacilityRecord(Base):
    """Stores facility configuration and metadata."""

    __tablename__ = "facilities"

    facility_id = Column(String(64), primary_key=True, index=True)
    facility_name = Column(String(128), nullable=False)
    location_region = Column(String(128), nullable=False)
    total_licensed_beds = Column(Integer, nullable=False)
    certified_operational_beds = Column(Integer, nullable=False)
    active_wings = Column(JSON, nullable=False, default=list)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)


class DailySnapshotRecord(Base):
    """Stores daily facility snapshots with structured JSON payloads."""

    __tablename__ = "daily_facility_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    facility_id = Column(String(64), index=True, nullable=False)
    snapshot_date = Column(Date, index=True, nullable=False)
    scenario_name = Column(String(64), default="baseline", index=True, nullable=False)
    data_json = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=utc_now)
