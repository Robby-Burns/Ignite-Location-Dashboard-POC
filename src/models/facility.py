"""Facility data models for Ignite Facility Operational Decision Agent POC.

Defines typed data structures covering all required operational domains:
1. Census and Occupancy
2. Admissions and Discharges
3. Length-of-Stay (LOS)
4. Therapy Participation and Progress
5. Staffing Coverage and Changes
6. Payer and Authorization Information
7. Guest Experience and Hospitality
8. Hospital Transfer Indicators
Plus complete daily snapshots, historical time series, and scenario datasets.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator


class FacilityMetadata(BaseModel):
    """Metadata describing a medical facility."""

    facility_id: str = Field(
        ..., description="Unique facility identifier, e.g., 'ignite-oak-brook'"
    )
    facility_name: str = Field(..., description="Human-readable facility name")
    location_region: str = Field(..., description="Geographic region or metro area")
    total_licensed_beds: int = Field(
        ..., ge=1, description="Total licensed bed capacity"
    )
    certified_operational_beds: int = Field(
        ..., ge=1, description="Currently staffed and operational bed capacity"
    )
    active_wings: list[str] = Field(
        default_factory=lambda: ["North Wing", "South Wing", "Transitional Care"],
        description="List of active units/wings",
    )


class CensusData(BaseModel):
    """Census and occupancy operational data."""

    current_census: int = Field(..., ge=0, description="Current occupied bed count")
    total_capacity: int = Field(..., ge=1, description="Operational bed capacity")
    occupancy_rate_pct: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Occupancy percentage (census / capacity * 100)",
    )
    available_beds: int = Field(..., ge=0, description="Available operational beds")
    previous_day_census: int | None = Field(
        None, ge=0, description="Census count from 1 day prior"
    )
    previous_week_census: int | None = Field(
        None, ge=0, description="Census count from 7 days prior"
    )
    budgeted_target_census: int | None = Field(
        None, ge=0, description="Target budgeted census"
    )

    @model_validator(mode="before")
    @classmethod
    def compute_defaults(cls, data: Any) -> Any:
        if isinstance(data, dict):
            census = data.get("current_census")
            capacity = data.get("total_capacity")
            if census is not None and capacity is not None and capacity > 0:
                if (
                    "occupancy_rate_pct" not in data
                    or data["occupancy_rate_pct"] is None
                ):
                    data["occupancy_rate_pct"] = round((census / capacity) * 100.0, 1)
                if "available_beds" not in data or data["available_beds"] is None:
                    data["available_beds"] = max(0, capacity - census)
        return data


class AdmissionsDischargesData(BaseModel):
    """Admissions and discharges operational metrics."""

    today_admissions: int = Field(..., ge=0, description="Confirmed admissions today")
    today_discharges: int = Field(..., ge=0, description="Confirmed discharges today")
    pending_admissions: int = Field(
        default=0, ge=0, description="Admissions in intake/transport pipeline today"
    )
    pending_discharges: int = Field(
        default=0,
        ge=0,
        description="Planned/pending discharges awaiting discharge clearance",
    )
    net_flow: int = Field(
        default=0, description="Net census change (today_admissions - today_discharges)"
    )
    rolling_7d_admissions: int = Field(
        ..., ge=0, description="Total admissions over trailing 7 days"
    )
    rolling_7d_discharges: int = Field(
        ..., ge=0, description="Total discharges over trailing 7 days"
    )

    @model_validator(mode="before")
    @classmethod
    def compute_net_flow(cls, data: Any) -> Any:
        if isinstance(data, dict):
            adm = data.get("today_admissions", 0)
            dis = data.get("today_discharges", 0)
            if "net_flow" not in data or data["net_flow"] is None:
                data["net_flow"] = adm - dis
        return data


class LengthOfStayData(BaseModel):
    """Length-of-Stay (LOS) operational metrics."""

    average_los_days: float = Field(
        ..., ge=0.0, description="Current average length of stay in days"
    )
    target_los_days: float = Field(
        ..., ge=0.0, description="Target/budgeted average length of stay in days"
    )
    short_stay_count: int = Field(
        ...,
        ge=0,
        description="Count of short-stay rehabilitation guests (LOS < 20 days)",
    )
    long_stay_count: int = Field(
        ..., ge=0, description="Count of extended/long-stay guests (LOS >= 20 days)"
    )
    los_outliers_count: int = Field(
        ..., ge=0, description="Count of guests exceeding clinical pathway target LOS"
    )
    median_los_days: float | None = Field(
        None, ge=0.0, description="Median length of stay in days"
    )


class TherapyData(BaseModel):
    """Therapy participation and progress operational indicators (non-diagnostic)."""

    avg_daily_treatment_minutes_scheduled: float = Field(
        ..., ge=0.0, description="Average scheduled therapy minutes per patient day"
    )
    avg_daily_treatment_minutes_delivered: float = Field(
        ..., ge=0.0, description="Average delivered therapy minutes per patient day"
    )
    treatment_completion_rate_pct: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Percentage of scheduled therapy successfully delivered",
    )
    patients_meeting_weekly_goals_pct: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Percentage of patients meeting weekly rehab milestones",
    )
    patients_on_therapy_hold: int = Field(
        ..., ge=0, description="Patients temporarily on clinical hold / refusal"
    )
    functional_mobility_gain_index: float = Field(
        ...,
        ge=0.0,
        le=10.0,
        description="Standardized 0-10 operational mobility progression index",
    )


class StaffingData(BaseModel):
    """Staffing coverage and operational shift metrics."""

    hppd_actual: float = Field(
        ..., ge=0.0, description="Actual nursing Hours Per Patient Day (HPPD)"
    )
    hppd_budgeted_target: float = Field(
        ..., ge=0.0, description="Budgeted target nursing Hours Per Patient Day (HPPD)"
    )
    rn_hours_actual: float = Field(
        ..., ge=0.0, description="Registered Nurse hours worked today"
    )
    lpn_hours_actual: float = Field(
        ..., ge=0.0, description="Licensed Practical Nurse hours worked today"
    )
    cna_hours_actual: float = Field(
        ..., ge=0.0, description="Certified Nursing Assistant hours worked today"
    )
    call_in_absences_count: int = Field(
        ..., ge=0, description="Unplanned staff call-ins or absences across shifts"
    )
    open_shifts_count: int = Field(
        ..., ge=0, description="Unfilled shifts requiring coverage or overtime"
    )
    overtime_hours: float = Field(
        ..., ge=0.0, description="Total overtime hours logged across shifts"
    )
    agency_staff_pct: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Percentage of worked hours covered by external agency staff",
    )


class PayerAuthData(BaseModel):
    """Payer distribution and authorization operational metrics."""

    payer_mix_pct: dict[str, float] = Field(
        ...,
        description="Percentage breakdown across payer categories (e.g. Medicare A, Managed Care, Medicaid, Commercial, VA)",
    )
    expiring_authorizations_48h: int = Field(
        ..., ge=0, description="Count of guest authorizations expiring within 48 hours"
    )
    expiring_authorizations_72h: int = Field(
        ..., ge=0, description="Count of guest authorizations expiring within 72 hours"
    )
    pending_reauthorizations_count: int = Field(
        ...,
        ge=0,
        description="Count of submitted reauthorizations awaiting payer response",
    )
    auth_denials_pending_appeal_count: int = Field(
        ..., ge=0, description="Count of denied authorizations under active appeal"
    )

    @field_validator("payer_mix_pct")
    @classmethod
    def validate_payer_mix(cls, v: dict[str, float]) -> dict[str, float]:
        if not v:
            raise ValueError("Payer mix cannot be empty")
        total = sum(v.values())
        if not (99.0 <= total <= 101.0):
            # Allow slight rounding tolerance
            raise ValueError(
                f"Payer mix percentages must sum to ~100.0%, got {total:.2f}%"
            )
        return v


class HospitalityData(BaseModel):
    """Guest experience, hospitality, and dining satisfaction metrics."""

    dining_satisfaction_score: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Dining/food quality satisfaction score (0-100)",
    )
    cleanliness_room_comfort_score: float = Field(
        ..., ge=0.0, le=100.0, description="Room comfort and cleanliness score (0-100)"
    )
    guest_satisfaction_nps: float = Field(
        ...,
        ge=-100.0,
        le=100.0,
        description="Net Promoter Score or guest satisfaction index (-100 to +100)",
    )
    open_guest_service_requests: int = Field(
        ..., ge=0, description="Active guest hospitality requests pending resolution"
    )
    avg_request_resolution_hours: float = Field(
        ..., ge=0.0, description="Average turnaround time in hours for guest requests"
    )


class HospitalTransferData(BaseModel):
    """Hospital acute transfer and 30-day readmission indicators."""

    unplanned_transfers_30d_count: int = Field(
        ...,
        ge=0,
        description="Count of unplanned acute hospital transfers over trailing 30 days",
    )
    readmission_rate_30d_pct: float = Field(
        ..., ge=0.0, le=100.0, description="30-day hospital readmission rate percentage"
    )
    benchmark_readmission_rate_pct: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Regional or national target benchmark readmission rate",
    )
    acute_transfers_this_week: int = Field(
        ...,
        ge=0,
        description="Unplanned hospital transfers occurring in the current week",
    )
    transfers_by_reason: dict[str, int] = Field(
        default_factory=lambda: {
            "respiratory": 0,
            "cardiac": 0,
            "fall_trauma": 0,
            "sepsis_infection": 0,
            "altered_mental_status": 0,
            "other": 0,
        },
        description="Categorized count of transfer reasons",
    )


class DailyFacilitySnapshot(BaseModel):
    """Unified operational snapshot for a single date."""

    snapshot_date: date = Field(..., description="Date of the operational observation")
    facility_id: str = Field(..., description="Facility identifier")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Record creation timestamp",
    )

    census: CensusData
    admissions_discharges: AdmissionsDischargesData
    length_of_stay: LengthOfStayData
    therapy: TherapyData
    staffing: StaffingData
    payer_auth: PayerAuthData
    hospitality: HospitalityData
    hospital_transfers: HospitalTransferData


class FacilityHistoricalSeries(BaseModel):
    """Time-series container of daily snapshots for trend analysis."""

    facility_id: str
    start_date: date
    end_date: date
    snapshots: list[DailyFacilitySnapshot] = Field(
        ..., min_length=1, description="Chronologically ordered daily snapshots"
    )

    @model_validator(mode="after")
    def sort_snapshots(self) -> FacilityHistoricalSeries:
        self.snapshots.sort(key=lambda s: s.snapshot_date)
        if self.snapshots:
            self.start_date = self.snapshots[0].snapshot_date
            self.end_date = self.snapshots[-1].snapshot_date
        return self


class FacilityDataset(BaseModel):
    """Top-level dataset container representing facility data supplied to the agent."""

    facility: FacilityMetadata
    current_snapshot: DailyFacilitySnapshot
    history: FacilityHistoricalSeries
    scenario_name: str = Field(
        default="baseline",
        description="Operational scenario name (e.g. baseline, staffing_stress, auth_cliff)",
    )
    scenario_description: str = Field(
        default="Standard operating conditions",
        description="Human-readable scenario description",
    )
    data_source: str = Field(
        default="mock_domo_mcp", description="Source boundary identifier"
    )
    is_synthetic: bool = Field(
        default=True, description="Strict synthetic data verification flag"
    )
