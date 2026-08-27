"""Database initialization and seeding script for Neon PostgreSQL or SQLite.

Seeds the single POC facility (Ignite Medical Resort Oak Brook) and its 6 operational scenarios:
- baseline
- staffing_stress
- auth_cliff
- hospital_transfer_spike
- therapy_disruption
- high_census_strain

Can be run standalone:
    python -m src.db.seed
"""

from __future__ import annotations

import logging

from sqlalchemy import select

from src.data.synthetic_generator import FACILITIES, SyntheticFacilityDataGenerator
from src.db.database import SessionFactory, get_database_url, init_db
from src.db.models import DailySnapshotRecord, FacilityRecord

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("db.seed")

# Single target facility for the POC
POC_FACILITY_ID = "ignite-oak-brook"


def init_and_seed_database(target_facility_id: str = POC_FACILITY_ID) -> None:
    """Create all tables and seed synthetic operational records for the single POC facility."""
    db_url = get_database_url()
    # Mask password for secure logging
    safe_url = db_url.split("@")[-1] if "@" in db_url else db_url
    logger.info("Connecting to database: %s", safe_url)

    # 1. Create tables idempotently
    logger.info("Creating tables if not exists...")
    init_db()
    logger.info("Database tables initialized successfully.")

    # 2. Seed single facility metadata
    generator = SyntheticFacilityDataGenerator(seed=42)
    meta = FACILITIES[target_facility_id]
    scenarios = [
        "baseline",
        "staffing_stress",
        "auth_cliff",
        "hospital_transfer_spike",
        "therapy_disruption",
        "high_census_strain",
    ]

    with SessionFactory() as session:
        # Seed Facility metadata
        existing = session.scalar(
            select(FacilityRecord).where(
                FacilityRecord.facility_id == target_facility_id
            )
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
            logger.info(
                "Seeded POC facility: %s (%s)", meta.facility_name, target_facility_id
            )

        # Seed Snapshots for all 6 scenarios (30 days each = 180 total records)
        snapshot_count = 0
        for scenario in scenarios:
            dataset = generator.generate_facility_dataset(
                facility_id=target_facility_id,
                scenario=scenario,
                days_history=30,
            )
            for snap in dataset.history.snapshots:
                existing_snap = session.scalar(
                    select(DailySnapshotRecord).where(
                        DailySnapshotRecord.facility_id == target_facility_id,
                        DailySnapshotRecord.snapshot_date == snap.snapshot_date,
                        DailySnapshotRecord.scenario_name == scenario,
                    )
                )
                if not existing_snap:
                    snap_rec = DailySnapshotRecord(
                        facility_id=target_facility_id,
                        snapshot_date=snap.snapshot_date,
                        scenario_name=scenario,
                        data_json=snap.model_dump(mode="json"),
                    )
                    session.add(snap_rec)
                    snapshot_count += 1

        session.commit()
        logger.info(
            "Successfully seeded %d snapshot records for %s across 6 operational scenarios.",
            snapshot_count,
            meta.facility_name,
        )


if __name__ == "__main__":
    init_and_seed_database()
