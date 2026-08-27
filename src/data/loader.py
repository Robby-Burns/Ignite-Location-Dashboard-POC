"""Facility Data Loader for Ignite Facility Operational Decision Agent POC.

Provides retrieval, caching, scenario loading, and validation for facility operational datasets.
Satisfies Story 1.1 acceptance criteria:
- AC-1.1.1: Representative operational data across all 8 domains
- AC-1.1.2: Historical values for trend analysis
- Rejection / Boundary: Zero PHI, explicit representation of missing fields
- Failure Behavior: Explicit error raised when data is unavailable or corrupt
"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import ValidationError

from src.data.synthetic_generator import FACILITIES, SyntheticFacilityDataGenerator
from src.models.facility import DailyFacilitySnapshot, FacilityDataset, FacilityMetadata


class DatasetUnavailableError(Exception):
    """Raised when a requested facility dataset cannot be loaded or is missing."""


class DatasetValidationError(Exception):
    """Raised when dataset payload fails schema or mathematical invariants."""


class FacilityDataLoader:
    """Loads and caches facility datasets across supported scenarios."""

    def __init__(self, fixtures_dir: Path | None = None):
        self.fixtures_dir = fixtures_dir or Path("data/fixtures")
        self.generator = SyntheticFacilityDataGenerator(seed=42)
        self._memory_cache: dict[str, FacilityDataset] = {}

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
        days_history: int = 30,
        use_cache: bool = True,
    ) -> FacilityDataset:
        """Load a complete facility dataset (current snapshot + history) for a given scenario."""
        if facility_id not in FACILITIES:
            raise DatasetUnavailableError(
                f"Cannot load dataset for facility '{facility_id}': facility not found."
            )

        cache_key = f"{facility_id}:{scenario}:{days_history}"
        if use_cache and cache_key in self._memory_cache:
            return self._memory_cache[cache_key]

        try:
            dataset = self.generator.generate_facility_dataset(
                facility_id=facility_id,
                days_history=days_history,
                scenario=scenario,
            )
            if use_cache:
                self._memory_cache[cache_key] = dataset
            return dataset
        except Exception as e:
            raise DatasetUnavailableError(
                f"Failed to generate/load facility dataset for '{facility_id}' (scenario: '{scenario}'): {e!s}"
            ) from e

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
