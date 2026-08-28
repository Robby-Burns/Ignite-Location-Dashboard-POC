"""Facility Data Loader for Ignite Facility Operational Decision Agent POC.

Provides retrieval, caching, scenario loading, and validation for facility operational datasets.
Reads from the database first; falls back to on-the-fly generation if no DB data exists.

Satisfies Story 1.1 acceptance criteria:
- AC-1.1.1: Representative operational data across all 8 domains
- AC-1.1.2: Historical values for trend analysis
- Rejection / Boundary: Zero PHI, explicit representation of missing fields
- Failure Behavior: Explicit error raised when data is unavailable or corrupt
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from pydantic import ValidationError
from sqlalchemy import select

from src.data.synthetic_generator import FACILITIES, SyntheticFacilityDataGenerator
from src.models.facility import (
    DailyFacilitySnapshot,
    FacilityDataset,
    FacilityHistoricalSeries,
    FacilityMetadata,
)

logger = logging.getLogger(__name__)


class DatasetUnavailableError(Exception):
    """Raised when a requested facility dataset cannot be loaded or is missing."""


class DatasetValidationError(Exception):
    """Raised when dataset payload fails schema or mathematical invariants."""


class FacilityDataLoader:
    """Loads facility datasets from DB first, falls back to on-the-fly generation."""

    def __init__(self, fixtures_dir: Path | None = None):
        self.fixtures_dir = fixtures_dir or Path("data/fixtures")
        self.generator = SyntheticFacilityDataGenerator(seed=42)
        self._memory_cache: dict[str, FacilityDataset] = {}

    def clear_cache(self, facility_id: str | None = None) -> None:
        """Invalidate in-memory cache for a specific facility or all facilities."""
        if facility_id:
            keys_to_remove = [
                k for k in self._memory_cache if k.startswith(f"{facility_id}:")
            ]
            for k in keys_to_remove:
                self._memory_cache.pop(k, None)
        else:
            self._memory_cache.clear()

    def get_supported_facilities(self) -> list[FacilityMetadata]:
        """Return list of supported facilities."""
        return list(FACILITIES.values())

    def get_facility_metadata(self, facility_id: str) -> FacilityMetadata:
        """Retrieve metadata for a specific facility."""
        if facility_id not in FACILITIES:
            raise DatasetUnavailableError(
                f"Facility '{facility_id}' is not configured or unavailable. "
                f"Available facilities: {list(FACILITIES.keys())}"
            )
        return FACILITIES[facility_id]

    def load_dataset(
        self,
        facility_id: str = "ignite-oak-brook",
        scenario: str = "baseline",
        days_history: int = 90,
        use_cache: bool = True,
    ) -> FacilityDataset:
        """Load a complete facility dataset from DB first, fall back to generator."""
        if facility_id not in FACILITIES:
            raise DatasetUnavailableError(
                f"Cannot load dataset for facility '{facility_id}': facility not found."
            )

        cache_key = f"{facility_id}:{scenario}:{days_history}"
        if use_cache and cache_key in self._memory_cache:
            return self._memory_cache[cache_key]

        # Try loading from DB first
        dataset = self._load_from_db(facility_id, scenario, days_history)

        # Fall back to on-the-fly generation if DB has no data
        if dataset is None:
            try:
                dataset = self.generator.generate_facility_dataset(
                    facility_id=facility_id,
                    days_history=days_history,
                    scenario=scenario,
                )
            except Exception as e:
                raise DatasetUnavailableError(
                    f"Failed to generate/load facility dataset for '{facility_id}' (scenario: '{scenario}'): {e!s}"
                ) from e

        if use_cache:
            self._memory_cache[cache_key] = dataset
        return dataset

    def _load_from_db(
        self, facility_id: str, scenario: str, days_history: int
    ) -> FacilityDataset | None:
        """Attempt to load dataset from the database. Returns None if unavailable."""
        try:
            from src.db.database import _get_session_factory, get_database_url, init_db
            from src.db.models import DailySnapshotRecord, FacilityRecord

            # Re-check DB URL each call (TESTING env var may have changed)
            db_url = get_database_url()
            if "sample-pool" in db_url:
                return None

            # Ensure tables exist
            init_db()

            with _get_session_factory()() as session:
                # Check if facility exists in DB
                fac_record = session.scalar(
                    select(FacilityRecord).where(
                        FacilityRecord.facility_id == facility_id
                    )
                )
                if not fac_record:
                    return None

                # Load most recent snapshots for this facility and scenario
                snapshot_records = (
                    session.execute(
                        select(DailySnapshotRecord)
                        .where(
                            DailySnapshotRecord.facility_id == facility_id,
                            DailySnapshotRecord.scenario_name == scenario,
                        )
                        .order_by(DailySnapshotRecord.snapshot_date.desc())
                        .limit(days_history)
                    )
                    .scalars()
                    .all()
                )

                if not snapshot_records or len(snapshot_records) < min(30, days_history):
                    return None

                # Reverse to chronological order (oldest to newest)
                snapshot_records = list(reversed(snapshot_records))

                # Parse snapshots from DB JSON
                snapshots: list[DailyFacilitySnapshot] = []
                for rec in snapshot_records:
                    try:
                        snap = DailyFacilitySnapshot.model_validate(rec.data_json)
                        snapshots.append(snap)
                    except ValidationError:
                        logger.warning(
                            "Invalid snapshot in DB for %s/%s on %s, skipping",
                            facility_id,
                            scenario,
                            rec.snapshot_date,
                        )
                        return None

                if len(snapshots) < days_history:
                    return None

                # Build FacilityMetadata from DB record
                facility = FacilityMetadata(
                    facility_id=fac_record.facility_id,
                    facility_name=fac_record.facility_name,
                    location_region=fac_record.location_region,
                    total_licensed_beds=fac_record.total_licensed_beds,
                    certified_operational_beds=fac_record.certified_operational_beds,
                    active_wings=fac_record.active_wings
                    if isinstance(fac_record.active_wings, list)
                    else json.loads(fac_record.active_wings)
                    if isinstance(fac_record.active_wings, str)
                    else [],
                )

                history = FacilityHistoricalSeries(
                    facility_id=facility_id,
                    start_date=snapshots[0].snapshot_date,
                    end_date=snapshots[-1].snapshot_date,
                    snapshots=snapshots,
                )

                scenario_descriptions = {
                    "baseline": "Standard operating baseline with stable census and strong clinical/therapy metrics.",
                    "staffing_stress": "Severe shift call-ins, elevated overtime, and nurse staffing coverage deficit.",
                    "auth_cliff": "Surge in managed care and Medicare authorizations expiring within 48-72 hours.",
                    "hospital_transfer_spike": "Cluster of acute respiratory and cardiac hospital transfers requiring clinical review.",
                    "therapy_disruption": "Weekend therapy delivery shortfall and elevated patient hold count.",
                    "high_census_strain": "Occupancy approaching 98% capacity with backlog in admissions intake.",
                }

                logger.info(
                    "Loaded %d snapshots from DB for %s/%s",
                    len(snapshots),
                    facility_id,
                    scenario,
                )

                return FacilityDataset(
                    facility=facility,
                    current_snapshot=snapshots[-1],
                    history=history,
                    scenario_name=scenario,
                    scenario_description=scenario_descriptions.get(
                        scenario, "Synthetic operational dataset"
                    ),
                    data_source="mock_domo_mcp",
                    is_synthetic=True,
                )

        except Exception as e:  # noqa: BLE001
            logger.warning("DB load failed, falling back to generator: %s", e)
            return None

    def load_from_json(self, json_data: str | bytes | dict) -> FacilityDataset:
        """Parse and validate a facility dataset from raw JSON or dictionary."""
        try:
            if isinstance(json_data, (str, bytes)):
                raw_dict = json.loads(json_data)
            else:
                raw_dict = json_data
            return FacilityDataset.model_validate(raw_dict)
        except (json.JSONDecodeError, ValidationError) as e:
            raise DatasetValidationError(
                f"Invalid facility dataset structure: {e!s}"
            ) from e

    def get_snapshot(
        self,
        facility_id: str = "ignite-oak-brook",
        scenario: str = "baseline",
    ) -> DailyFacilitySnapshot:
        """Retrieve the latest operational snapshot for a facility."""
        dataset = self.load_dataset(facility_id=facility_id, scenario=scenario)
        return dataset.current_snapshot
