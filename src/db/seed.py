"""Database initialization and seeding script for Neon PostgreSQL or SQLite.

Seeds all3 POC facilities with their unique operational profiles across 6 scenarios:
- ignite-oak-brook: Flagship luxury rehab
- ignite-mokena: Orthopedic/cardio specialty
- ignite-kansas-city: Stroke/neuro specialty

Can be run standalone:
    python -m src.db.seed
"""

from __future__ import annotations

import logging

from sqlalchemy import select

from src.data.synthetic_generator import FACILITIES, SyntheticFacilityDataGenerator
from src.db.database import _get_session_factory, get_database_url, init_db
from src.db.models import DailySnapshotRecord, FacilityRecord

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("db.seed")

SCENARIOS = [
    "baseline",
    "staffing_stress",
    "auth_cliff",
    "hospital_transfer_spike",
    "therapy_disruption",
    "high_census_strain",
]


def init_and_seed_database() -> None:
    """Create all tables and seed synthetic operational records for all POC facilities."""
    db_url = get_database_url()
    safe_url = db_url.split("@")[-1] if "@" in db_url else db_url
    logger.info("Connecting to database: %s", safe_url)

    logger.info("Creating tables if not exists...")
    init_db()
    logger.info("Database tables initialized successfully.")

    generator = SyntheticFacilityDataGenerator(seed=42)

    with _get_session_factory()() as session:
        for facility_id, meta in FACILITIES.items():
            # Seed facility metadata
            existing = session.scalar(
                select(FacilityRecord).where(FacilityRecord.facility_id == facility_id)
            )
            if not existing:
                record = FacilityRecord(
                    facility_id=meta.facility_id,
                    facility_name=meta.facility_name,
                    location_region=meta.location_region,
                    total_licensed_beds=meta.total_licensed_beds,
                    certified_operational_beds=meta.certified_operational_beds,
                    active_wings=meta.active_wings,
                )
                session.add(record)
                session.commit()
                logger.info("Seeded facility: %s (%s)", meta.facility_name, facility_id)

            # Seed snapshots for all 6 scenarios (30 days each = 180 records per facility)
            snapshot_count = 0
            for scenario in SCENARIOS:
                dataset = generator.generate_facility_dataset(
                    facility_id=facility_id,
                    scenario=scenario,
                    days_history=30,
                )
                for snap in dataset.history.snapshots:
                    existing_snap = session.scalar(
                        select(DailySnapshotRecord).where(
                            DailySnapshotRecord.facility_id == facility_id,
                            DailySnapshotRecord.snapshot_date == snap.snapshot_date,
                            DailySnapshotRecord.scenario_name == scenario,
                        )
                    )
                    if not existing_snap:
                        snap_rec = DailySnapshotRecord(
                            facility_id=facility_id,
                            snapshot_date=snap.snapshot_date,
                            scenario_name=scenario,
                            data_json=snap.model_dump(mode="json"),
                        )
                        session.add(snap_rec)
                        snapshot_count += 1

            session.commit()
            logger.info(
                "Seeded %d snapshot records for %s across 6 scenarios.",
                snapshot_count,
                meta.facility_name,
            )

    logger.info("Database seeding complete for all facilities.")


if __name__ == "__main__":
    init_and_seed_database()
