"""Unit and integration tests for Story 1.1 — Facility Data Model.

Verifies:
- AC-1.1.1: Representative data across all 8 required operational domains
- AC-1.1.2: Historical values for trend analysis (30-day series)
- Rejection / Boundary Conditions: Zero PHI, non-fabricated data, mathematical consistency
- Failure Behavior: DatasetUnavailableError and DatasetValidationError handling
- Scenario Differentiation: Data changes across scenarios for data-driven evaluation
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.data.loader import (
    DatasetUnavailableError,
    DatasetValidationError,
    FacilityDataLoader,
)
from src.data.synthetic_generator import SyntheticFacilityDataGenerator
from src.models.facility import (
    CensusData,
    PayerAuthData,
)


@pytest.fixture
def data_loader() -> FacilityDataLoader:
    return FacilityDataLoader()


@pytest.fixture
def generator() -> SyntheticFacilityDataGenerator:
    return SyntheticFacilityDataGenerator(seed=123)


def test_ac1_1_1_all_required_operational_domains_exist(
    data_loader: FacilityDataLoader,
) -> None:
    """AC-1.1.1: Verify representative data exists for each required operational area."""
    dataset = data_loader.load_dataset(
        facility_id="ignite-oak-brook", scenario="baseline"
    )
    snapshot = dataset.current_snapshot

    # 1. Facility Metadata
    assert dataset.facility.facility_id == "ignite-oak-brook"
    assert dataset.facility.certified_operational_beds > 0
    assert len(dataset.facility.active_wings) >= 1

    # 2. Census & Occupancy
    assert snapshot.census.current_census > 0
    assert snapshot.census.total_capacity == dataset.facility.certified_operational_beds
    assert 0.0 <= snapshot.census.occupancy_rate_pct <= 100.0
    assert snapshot.census.available_beds >= 0
    assert snapshot.census.previous_day_census is not None
    assert snapshot.census.previous_week_census is not None

    # 3. Admissions & Discharges
    assert snapshot.admissions_discharges.today_admissions >= 0
    assert snapshot.admissions_discharges.today_discharges >= 0
    assert (
        snapshot.admissions_discharges.rolling_7d_admissions
        >= snapshot.admissions_discharges.today_admissions
    )
    assert (
        snapshot.admissions_discharges.rolling_7d_discharges
        >= snapshot.admissions_discharges.today_discharges
    )
    assert snapshot.admissions_discharges.net_flow == (
        snapshot.admissions_discharges.today_admissions
        - snapshot.admissions_discharges.today_discharges
    )

    # 4. Length-of-Stay (LOS)
    assert snapshot.length_of_stay.average_los_days > 0.0
    assert snapshot.length_of_stay.target_los_days > 0.0
    assert snapshot.length_of_stay.short_stay_count >= 0
    assert snapshot.length_of_stay.long_stay_count >= 0
    assert snapshot.length_of_stay.los_outliers_count >= 0

    # 5. Therapy Participation & Progress Indicators
    assert snapshot.therapy.avg_daily_treatment_minutes_scheduled > 0.0
    assert snapshot.therapy.avg_daily_treatment_minutes_delivered > 0.0
    assert 0.0 <= snapshot.therapy.treatment_completion_rate_pct <= 100.0
    assert 0.0 <= snapshot.therapy.patients_meeting_weekly_goals_pct <= 100.0
    assert snapshot.therapy.patients_on_therapy_hold >= 0
    assert 0.0 <= snapshot.therapy.functional_mobility_gain_index <= 10.0

    # 6. Staffing Coverage & Shifts
    assert snapshot.staffing.hppd_actual > 0.0
    assert snapshot.staffing.hppd_budgeted_target > 0.0
    assert snapshot.staffing.rn_hours_actual > 0.0
    assert snapshot.staffing.lpn_hours_actual > 0.0
    assert snapshot.staffing.cna_hours_actual > 0.0
    assert snapshot.staffing.call_in_absences_count >= 0
    assert snapshot.staffing.open_shifts_count >= 0
    assert 0.0 <= snapshot.staffing.agency_staff_pct <= 100.0

    # 7. Payer & Authorization
    assert len(snapshot.payer_auth.payer_mix_pct) >= 4
    assert sum(snapshot.payer_auth.payer_mix_pct.values()) >= 99.0
    assert snapshot.payer_auth.expiring_authorizations_48h >= 0
    assert (
        snapshot.payer_auth.expiring_authorizations_72h
        >= snapshot.payer_auth.expiring_authorizations_48h
    )
    assert snapshot.payer_auth.pending_reauthorizations_count >= 0

    # 8. Guest Experience & Hospitality
    assert 0.0 <= snapshot.hospitality.dining_satisfaction_score <= 100.0
    assert 0.0 <= snapshot.hospitality.cleanliness_room_comfort_score <= 100.0
    assert -100.0 <= snapshot.hospitality.guest_satisfaction_nps <= 100.0
    assert snapshot.hospitality.open_guest_service_requests >= 0

    # 9. Hospital Transfers
    assert snapshot.hospital_transfers.unplanned_transfers_30d_count >= 0
    assert 0.0 <= snapshot.hospital_transfers.readmission_rate_30d_pct <= 100.0
    assert len(snapshot.hospital_transfers.transfers_by_reason) >= 4


def test_ac1_1_2_historical_values_exist_for_trend_analysis(
    data_loader: FacilityDataLoader,
) -> None:
    """AC-1.1.2: Confirm multiple dated observations exist for trend and change analysis."""
    dataset = data_loader.load_dataset(facility_id="ignite-oak-brook", days_history=30)
    history = dataset.history

    assert len(history.snapshots) == 30
    assert history.start_date < history.end_date

    # Verify chronological sorting
    dates = [s.snapshot_date for s in history.snapshots]
    assert dates == sorted(dates)

    # Verify census and staffing trends across history
    censuses = [s.census.current_census for s in history.snapshots]
    assert len(set(censuses)) > 1, "Census should vary naturally over 30 days"

    hppd_vals = [s.staffing.hppd_actual for s in history.snapshots]
    assert len(set(hppd_vals)) > 1, (
        "Staffing HPPD should vary across daily observations"
    )


def test_boundary_no_phi_present(data_loader: FacilityDataLoader) -> None:
    """Rejection / Boundary: Ensure zero real PHI (no names, SSNs, DOBs, MRNs)."""
    dataset = data_loader.load_dataset(facility_id="ignite-oak-brook")
    raw_json = dataset.model_dump_json()

    phi_keywords = [
        "patient_name",
        "first_name",
        "last_name",
        "ssn",
        "social_security",
        "date_of_birth",
        "mrn",
        "diagnosis_code",
    ]
    for kw in phi_keywords:
        assert kw not in raw_json.lower(), (
            f"Potential PHI attribute '{kw}' detected in dataset payload"
        )


def test_mathematical_consistency_and_validation() -> None:
    """Verify built-in validators enforce mathematical integrity."""
    # Net flow auto-calculation
    snap_census = CensusData(current_census=90, total_capacity=100)
    assert snap_census.occupancy_rate_pct == 90.0
    assert snap_census.available_beds == 10

    # Invalid payer mix sum must raise ValidationError
    with pytest.raises(ValidationError):
        PayerAuthData(
            payer_mix_pct={
                "Medicare A": 30.0,
                "Medicaid": 30.0,
            },  # Sums to 60%, must fail
            expiring_authorizations_48h=2,
            expiring_authorizations_72h=4,
            pending_reauthorizations_count=3,
            auth_denials_pending_appeal_count=0,
        )


def test_failure_behavior_unavailable_facility(data_loader: FacilityDataLoader) -> None:
    """Failure behavior: Missing or invalid facility ID raises explicit DatasetUnavailableError."""
    with pytest.raises(DatasetUnavailableError) as exc_info:
        data_loader.load_dataset(facility_id="non-existent-facility")
    assert "not configured or unavailable" in str(
        exc_info.value
    ) or "facility not found" in str(exc_info.value)


def test_failure_behavior_corrupt_json(data_loader: FacilityDataLoader) -> None:
    """Failure behavior: Corrupt JSON payload raises explicit DatasetValidationError."""
    with pytest.raises(DatasetValidationError):
        data_loader.load_from_json("{corrupt json payload: missing-quotes}")

    with pytest.raises(DatasetValidationError):
        data_loader.load_from_json({"invalid": "missing required fields"})


def test_scenario_differentiation(data_loader: FacilityDataLoader) -> None:
    """Verify distinct operational scenarios produce materially different metrics (supporting data-driven AI)."""
    baseline = data_loader.load_dataset(
        facility_id="ignite-oak-brook", scenario="baseline", use_cache=False
    )
    staffing_stress = data_loader.load_dataset(
        facility_id="ignite-oak-brook", scenario="staffing_stress", use_cache=False
    )
    auth_cliff = data_loader.load_dataset(
        facility_id="ignite-oak-brook", scenario="auth_cliff", use_cache=False
    )
    transfers = data_loader.load_dataset(
        facility_id="ignite-oak-brook",
        scenario="hospital_transfer_spike",
        use_cache=False,
    )

    # Staffing stress scenario
    assert (
        staffing_stress.current_snapshot.staffing.call_in_absences_count
        > baseline.current_snapshot.staffing.call_in_absences_count
    )
    assert (
        staffing_stress.current_snapshot.staffing.overtime_hours
        > baseline.current_snapshot.staffing.overtime_hours
    )

    # Auth cliff scenario
    assert (
        auth_cliff.current_snapshot.payer_auth.expiring_authorizations_48h
        > baseline.current_snapshot.payer_auth.expiring_authorizations_48h
    )
    assert (
        auth_cliff.current_snapshot.payer_auth.pending_reauthorizations_count
        > baseline.current_snapshot.payer_auth.pending_reauthorizations_count
    )

    # Transfer spike scenario
    assert (
        transfers.current_snapshot.hospital_transfers.acute_transfers_this_week
        > baseline.current_snapshot.hospital_transfers.acute_transfers_this_week
    )


def test_database_initialization_and_orm_persistence(
    tmp_path: pytest.TempPathFactory,
) -> None:
    """Verify SQLAlchemy ORM tables initialize idempotently and persist facility data."""
    import uuid

    from sqlalchemy import create_engine, select
    from sqlalchemy.orm import sessionmaker

    from src.db.database import Base
    from src.db.models import FacilityRecord

    test_db_path = tmp_path / "test_isolated.db"
    test_engine = create_engine(f"sqlite:///{test_db_path}")
    Base.metadata.create_all(bind=test_engine)
    TestSessionFactory = sessionmaker(bind=test_engine)

    test_fac_id = f"ignite-test-{uuid.uuid4().hex[:8]}"

    with TestSessionFactory() as session:
        # Create facility record
        fac = FacilityRecord(
            facility_id=test_fac_id,
            facility_name="Ignite Test Resort",
            location_region="Test Region",
            total_licensed_beds=100,
            certified_operational_beds=90,
            active_wings=["Wing A", "Wing B"],
        )
        session.add(fac)
        session.commit()

        # Query back
        res = session.execute(
            select(FacilityRecord).where(FacilityRecord.facility_id == test_fac_id)
        )
        record = res.scalar_one_or_none()
        assert record is not None
        assert record.facility_name == "Ignite Test Resort"
        assert record.certified_operational_beds == 90
