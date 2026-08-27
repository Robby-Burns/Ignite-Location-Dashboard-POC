"""Synthetic Facility Data Generator for Ignite Facility Operational Decision Agent POC.

Generates realistic, PHI-free facility operational data across 8+ operational domains
with 30-day historical time-series and configurable operational scenarios:
- baseline: Healthy, stable facility operations
- staffing_stress: Nurse call-ins, overtime spike, open shifts, HPPD deficit
- auth_cliff: Imminent expiration of Managed Care / Medicare authorizations
- hospital_transfer_spike: Acute respiratory / cardiac transfer increase
- therapy_disruption: Weekend/holiday therapy completion drop and hold increases
- high_census_strain: 96%+ occupancy with high pending admissions
"""

from __future__ import annotations

import math
import random
from datetime import date, timedelta

from src.models.facility import (
    AdmissionsDischargesData,
    CensusData,
    DailyFacilitySnapshot,
    FacilityDataset,
    FacilityHistoricalSeries,
    FacilityMetadata,
    HospitalityData,
    HospitalTransferData,
    LengthOfStayData,
    PayerAuthData,
    StaffingData,
    TherapyData,
)

FACILITIES: dict[str, FacilityMetadata] = {
    "ignite-oak-brook": FacilityMetadata(
        facility_id="ignite-oak-brook",
        facility_name="Ignite Medical Resort Oak Brook",
        location_region="Midwest / Chicago Metro",
        total_licensed_beds=120,
        certified_operational_beds=110,
        active_wings=["Rehab Pavilion", "Luxe Suites", "Transitional Care Center"],
    ),
    "ignite-mokena": FacilityMetadata(
        facility_id="ignite-mokena",
        facility_name="Ignite Medical Resort Mokena",
        location_region="Midwest / South Chicagoland",
        total_licensed_beds=100,
        certified_operational_beds=92,
        active_wings=["Orthopedic Wing", "Cardiopulmonary Unit", "Short Stay Unit"],
    ),
    "ignite-kansas-city": FacilityMetadata(
        facility_id="ignite-kansas-city",
        facility_name="Ignite Medical Resort Kansas City",
        location_region="Midwest / Greater Kansas City",
        total_licensed_beds=114,
        certified_operational_beds=104,
        active_wings=["Stroke & Neuro Wing", "Post-Surgical Suites", "Therapy Loft"],
    ),
}


class SyntheticFacilityDataGenerator:
    """Generates synthetic operational records with mathematical consistency and scenario support."""

    def __init__(self, seed: int = 42):
        self.seed = seed
        self.rng = random.Random(seed)

    def generate_daily_snapshot(
        self,
        facility_id: str,
        snapshot_date: date,
        day_offset: int = 0,
        scenario: str = "baseline",
    ) -> DailyFacilitySnapshot:
        """Generate a single daily snapshot with realistic domain values and scenario modifiers."""
        facility = FACILITIES.get(facility_id, FACILITIES["ignite-oak-brook"])
        capacity = facility.certified_operational_beds

        # Baseline parameters
        base_census = int(capacity * 0.86)
        # Seasonal/day wave
        wave = math.sin((day_offset + 5) / 4.0) * 3.0
        daily_jitter = self.rng.randint(-2, 2)
        census_val = max(10, min(capacity, int(base_census + wave + daily_jitter)))

        # Scenario modifiers
        if scenario == "high_census_strain" and day_offset >= 20:
            census_val = min(capacity, capacity - self.rng.randint(1, 3))
        elif scenario == "staffing_stress" and day_offset >= 25:
            # High census combined with low staffing
            census_val = min(capacity, int(capacity * 0.93))

        budgeted_census = int(capacity * 0.88)
        occ_rate = round((census_val / capacity) * 100.0, 1)
        avail_beds = max(0, capacity - census_val)

        census = CensusData(
            current_census=census_val,
            total_capacity=capacity,
            occupancy_rate_pct=occ_rate,
            available_beds=avail_beds,
            previous_day_census=max(0, census_val - self.rng.randint(-2, 3)),
            previous_week_census=max(0, census_val - self.rng.randint(-4, 4)),
            budgeted_target_census=budgeted_census,
        )

        # Admissions & Discharges
        today_adm = max(
            0,
            self.rng.randint(2, 6)
            if day_offset % 7 not in (5, 6)
            else self.rng.randint(0, 2),
        )
        today_dis = max(
            0,
            self.rng.randint(1, 5)
            if day_offset % 7 not in (0, 6)
            else self.rng.randint(0, 2),
        )
        pending_adm = self.rng.randint(1, 4)
        pending_dis = self.rng.randint(1, 4)

        if scenario == "high_census_strain" and day_offset >= 25:
            today_adm += 3
            pending_adm += 4

        rolling_7d_adm = max(today_adm, today_adm * 4 + self.rng.randint(10, 18))
        rolling_7d_dis = max(today_dis, today_dis * 4 + self.rng.randint(8, 16))

        adm_dis = AdmissionsDischargesData(
            today_admissions=today_adm,
            today_discharges=today_dis,
            pending_admissions=pending_adm,
            pending_discharges=pending_dis,
            net_flow=today_adm - today_dis,
            rolling_7d_admissions=rolling_7d_adm,
            rolling_7d_discharges=rolling_7d_dis,
        )

        # Length of Stay
        target_los = 17.5
        avg_los = round(
            target_los
            + (math.sin(day_offset / 6.0) * 1.5)
            + self.rng.uniform(-0.5, 0.5),
            1,
        )
        short_stay = int(census_val * 0.72)
        long_stay = census_val - short_stay
        outliers = max(1, int(census_val * 0.08) + self.rng.randint(0, 2))

        los = LengthOfStayData(
            average_los_days=avg_los,
            target_los_days=target_los,
            short_stay_count=short_stay,
            long_stay_count=long_stay,
            los_outliers_count=outliers,
            median_los_days=round(avg_los - 1.2, 1),
        )

        # Therapy
        sched_min = 105.0
        deliv_min = round(sched_min * self.rng.uniform(0.92, 0.98), 1)
        comp_rate = round((deliv_min / sched_min) * 100.0, 1)
        goals_pct = round(self.rng.uniform(84.0, 94.0), 1)
        holds_count = self.rng.randint(1, 4)
        mobility_idx = round(self.rng.uniform(7.8, 8.9), 1)

        if scenario == "therapy_disruption" and day_offset >= 24:
            deliv_min = round(sched_min * 0.78, 1)
            comp_rate = round((deliv_min / sched_min) * 100.0, 1)
            goals_pct = 71.5
            holds_count = 8
            mobility_idx = 6.4

        therapy = TherapyData(
            avg_daily_treatment_minutes_scheduled=sched_min,
            avg_daily_treatment_minutes_delivered=deliv_min,
            treatment_completion_rate_pct=comp_rate,
            patients_meeting_weekly_goals_pct=goals_pct,
            patients_on_therapy_hold=holds_count,
            functional_mobility_gain_index=mobility_idx,
        )

        # Staffing
        target_hppd = 4.10
        actual_hppd = round(target_hppd + self.rng.uniform(-0.15, 0.25), 2)
        rn_hrs = round(census_val * 0.95, 1)
        lpn_hrs = round(census_val * 1.35, 1)
        cna_hrs = round(census_val * 1.85, 1)
        call_ins = self.rng.randint(0, 2)
        open_shifts = self.rng.randint(0, 2)
        ot_hrs = round(self.rng.uniform(2.0, 10.0), 1)
        agency_pct = round(self.rng.uniform(2.0, 6.5), 1)

        if scenario == "staffing_stress" and day_offset >= 25:
            actual_hppd = 3.62
            call_ins = 6
            open_shifts = 5
            ot_hrs = 36.5
            agency_pct = 18.5

        staffing = StaffingData(
            hppd_actual=actual_hppd,
            hppd_budgeted_target=target_hppd,
            rn_hours_actual=rn_hrs,
            lpn_hours_actual=lpn_hrs,
            cna_hours_actual=cna_hrs,
            call_in_absences_count=call_ins,
            open_shifts_count=open_shifts,
            overtime_hours=ot_hrs,
            agency_staff_pct=agency_pct,
        )

        # Payer & Auth
        payer_mix = {
            "Medicare A": 42.0,
            "Managed Care": 33.0,
            "Medicaid": 14.0,
            "Commercial / Private": 8.0,
            "Veterans Affairs": 3.0,
        }
        exp_48h = self.rng.randint(0, 2)
        exp_72h = exp_48h + self.rng.randint(1, 3)
        pending_reauth = self.rng.randint(1, 4)
        denials = self.rng.randint(0, 1)

        if scenario == "auth_cliff" and day_offset >= 26:
            exp_48h = 9
            exp_72h = 16
            pending_reauth = 12
            denials = 4

        payer_auth = PayerAuthData(
            payer_mix_pct=payer_mix,
            expiring_authorizations_48h=exp_48h,
            expiring_authorizations_72h=exp_72h,
            pending_reauthorizations_count=pending_reauth,
            auth_denials_pending_appeal_count=denials,
        )

        # Hospitality
        dining = round(self.rng.uniform(88.0, 96.0), 1)
        clean = round(self.rng.uniform(91.0, 98.0), 1)
        nps = round(self.rng.uniform(55.0, 78.0), 1)
        guest_req = self.rng.randint(1, 5)
        res_time = round(self.rng.uniform(1.2, 3.5), 1)

        hospitality = HospitalityData(
            dining_satisfaction_score=dining,
            cleanliness_room_comfort_score=clean,
            guest_satisfaction_nps=nps,
            open_guest_service_requests=guest_req,
            avg_request_resolution_hours=res_time,
        )

        # Transfers
        unplanned_30d = self.rng.randint(4, 8)
        readm_pct = round(self.rng.uniform(7.0, 11.5), 1)
        benchmark_readm = 12.0
        acute_week = self.rng.randint(0, 2)
        transfers_by_reason = {
            "respiratory": 2,
            "cardiac": 1,
            "fall_trauma": 1,
            "sepsis_infection": 1,
            "altered_mental_status": 0,
            "other": 1,
        }

        if scenario == "hospital_transfer_spike" and day_offset >= 25:
            unplanned_30d = 14
            readm_pct = 16.8
            acute_week = 5
            transfers_by_reason["respiratory"] = 6
            transfers_by_reason["cardiac"] = 4

        transfers = HospitalTransferData(
            unplanned_transfers_30d_count=unplanned_30d,
            readmission_rate_30d_pct=readm_pct,
            benchmark_readmission_rate_pct=benchmark_readm,
            acute_transfers_this_week=acute_week,
            transfers_by_reason=transfers_by_reason,
        )

        return DailyFacilitySnapshot(
            snapshot_date=snapshot_date,
            facility_id=facility.facility_id,
            census=census,
            admissions_discharges=adm_dis,
            length_of_stay=los,
            therapy=therapy,
            staffing=staffing,
            payer_auth=payer_auth,
            hospitality=hospitality,
            hospital_transfers=transfers,
        )

    def generate_facility_dataset(
        self,
        facility_id: str = "ignite-oak-brook",
        end_date: date | None = None,
        days_history: int = 30,
        scenario: str = "baseline",
    ) -> FacilityDataset:
        """Generate a full facility dataset with 30-day historical time-series."""
        if end_date is None:
            end_date = date(2026, 8, 27)

        facility = FACILITIES.get(facility_id, FACILITIES["ignite-oak-brook"])
        start_date = end_date - timedelta(days=days_history - 1)

        snapshots: list[DailyFacilitySnapshot] = []
        for i in range(days_history):
            curr_date = start_date + timedelta(days=i)
            snap = self.generate_daily_snapshot(
                facility_id=facility.facility_id,
                snapshot_date=curr_date,
                day_offset=i,
                scenario=scenario,
            )
            snapshots.append(snap)

        history_series = FacilityHistoricalSeries(
            facility_id=facility.facility_id,
            start_date=start_date,
            end_date=end_date,
            snapshots=snapshots,
        )

        current_snapshot = snapshots[-1]

        scenario_descriptions = {
            "baseline": "Standard operating baseline with stable census and strong clinical/therapy metrics.",
            "staffing_stress": "Severe shift call-ins, elevated overtime, and nurse staffing coverage deficit.",
            "auth_cliff": "Surge in managed care and Medicare authorizations expiring within 48-72 hours.",
            "hospital_transfer_spike": "Cluster of acute respiratory and cardiac hospital transfers requiring clinical review.",
            "therapy_disruption": "Weekend therapy delivery shortfall and elevated patient hold count.",
            "high_census_strain": "Occupancy approaching 98% capacity with backlog in admissions intake.",
        }

        return FacilityDataset(
            facility=facility,
            current_snapshot=current_snapshot,
            history=history_series,
            scenario_name=scenario,
            scenario_description=scenario_descriptions.get(
                scenario, "Synthetic operational dataset"
            ),
            data_source="mock_domo_mcp",
            is_synthetic=True,
        )
