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

# Facility-specific operational profiles — each facility has distinct characteristics
FACILITY_PROFILES: dict[str, dict] = {
    "ignite-oak-brook": {
        # Flagship luxury rehab — high staffing, strong outcomes, premium hospitality
        "occupancy_baseline": 0.88,
        "budgeted_occupancy": 0.90,
        "target_hppd": 4.30,
        "rn_ratio": 1.05,
        "lpn_ratio": 1.30,
        "cna_ratio": 1.80,
        "base_call_ins": (0, 1),
        "base_open_shifts": (0, 1),
        "base_ot_hrs": (2.0, 6.0),
        "base_agency_pct": (1.5, 4.0),
        "target_los": 14.0,
        "short_stay_pct": 0.78,
        "outlier_pct": 0.05,
        "therapy_scheduled_min": 120.0,
        "therapy_delivery_range": (0.93, 0.99),
        "goals_range": (88.0, 96.0),
        "holds_range": (0, 2),
        "mobility_range": (8.2, 9.2),
        "payer_mix": {
            "Medicare A": 45.0,
            "Managed Care": 28.0,
            "Medicaid": 12.0,
            "Commercial / Private": 12.0,
            "Veterans Affairs": 3.0,
        },
        "base_exp_48h": (0, 1),
        "base_pending_reauth": (1, 3),
        "base_denials": (0, 1),
        "dining_range": (91.0, 97.0),
        "clean_range": (94.0, 99.0),
        "nps_range": (62.0, 80.0),
        "guest_req_range": (1, 3),
        "res_time_range": (1.0, 2.5),
        "unplanned_30d_range": (3, 6),
        "readm_pct_range": (7.0, 10.0),
        "benchmark_readm": 12.0,
        "acute_week_range": (0, 1),
        "transfer_reasons": {
            "respiratory": 1,
            "cardiac": 1,
            "fall_trauma": 1,
            "sepsis_infection": 0,
            "altered_mental_status": 0,
            "other": 1,
        },
        "admissions_range": (3, 7),
        "discharges_range": (2, 5),
    },
    "ignite-mokena": {
        # Orthopedic/cardio specialty — fast turnaround, managed-care heavy, efficient staffing
        "occupancy_baseline": 0.82,
        "budgeted_occupancy": 0.85,
        "target_hppd": 3.90,
        "rn_ratio": 0.90,
        "lpn_ratio": 1.40,
        "cna_ratio": 1.90,
        "base_call_ins": (1, 3),
        "base_open_shifts": (1, 3),
        "base_ot_hrs": (5.0, 14.0),
        "base_agency_pct": (5.0, 10.0),
        "target_los": 12.0,
        "short_stay_pct": 0.82,
        "outlier_pct": 0.04,
        "therapy_scheduled_min": 95.0,
        "therapy_delivery_range": (0.90, 0.97),
        "goals_range": (82.0, 92.0),
        "holds_range": (2, 5),
        "mobility_range": (7.0, 8.2),
        "payer_mix": {
            "Medicare A": 32.0,
            "Managed Care": 38.0,
            "Medicaid": 10.0,
            "Commercial / Private": 16.0,
            "Veterans Affairs": 4.0,
        },
        "base_exp_48h": (1, 3),
        "base_pending_reauth": (2, 5),
        "base_denials": (0, 2),
        "dining_range": (86.0, 93.0),
        "clean_range": (90.0, 96.0),
        "nps_range": (50.0, 68.0),
        "guest_req_range": (2, 6),
        "res_time_range": (1.5, 4.0),
        "unplanned_30d_range": (5, 9),
        "readm_pct_range": (9.0, 12.5),
        "benchmark_readm": 12.0,
        "acute_week_range": (1, 3),
        "transfer_reasons": {
            "respiratory": 1,
            "cardiac": 2,
            "fall_trauma": 2,
            "sepsis_infection": 1,
            "altered_mental_status": 0,
            "other": 1,
        },
        "admissions_range": (2, 5),
        "discharges_range": (2, 5),
    },
    "ignite-kansas-city": {
        # Stroke/neuro specialty — complex cases, longer stays, higher Medicaid, leaner staffing
        "occupancy_baseline": 0.90,
        "budgeted_occupancy": 0.88,
        "target_hppd": 3.75,
        "rn_ratio": 0.88,
        "lpn_ratio": 1.45,
        "cna_ratio": 2.00,
        "base_call_ins": (1, 4),
        "base_open_shifts": (2, 4),
        "base_ot_hrs": (8.0, 18.0),
        "base_agency_pct": (8.0, 15.0),
        "target_los": 21.0,
        "short_stay_pct": 0.62,
        "outlier_pct": 0.10,
        "therapy_scheduled_min": 110.0,
        "therapy_delivery_range": (0.88, 0.96),
        "goals_range": (78.0, 88.0),
        "holds_range": (3, 6),
        "mobility_range": (6.5, 7.8),
        "payer_mix": {
            "Medicare A": 35.0,
            "Managed Care": 22.0,
            "Medicaid": 28.0,
            "Commercial / Private": 10.0,
            "Veterans Affairs": 5.0,
        },
        "base_exp_48h": (1, 3),
        "base_pending_reauth": (2, 5),
        "base_denials": (1, 2),
        "dining_range": (83.0, 91.0),
        "clean_range": (88.0, 94.0),
        "nps_range": (45.0, 62.0),
        "guest_req_range": (3, 7),
        "res_time_range": (2.0, 5.0),
        "unplanned_30d_range": (6, 11),
        "readm_pct_range": (10.5, 14.0),
        "benchmark_readm": 12.0,
        "acute_week_range": (1, 3),
        "transfer_reasons": {
            "respiratory": 2,
            "cardiac": 1,
            "fall_trauma": 1,
            "sepsis_infection": 1,
            "altered_mental_status": 2,
            "other": 1,
        },
        "admissions_range": (2, 5),
        "discharges_range": (1, 4),
    },
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
        """Generate a single daily snapshot with facility-specific operational parameters."""
        facility = FACILITIES.get(facility_id, FACILITIES["ignite-oak-brook"])
        profile = FACILITY_PROFILES.get(
            facility_id, FACILITY_PROFILES["ignite-oak-brook"]
        )
        capacity = facility.certified_operational_beds

        # Census — scaled by facility-specific occupancy baseline
        base_census = int(capacity * profile["occupancy_baseline"])
        wave = math.sin((day_offset + 5) / 4.0) * 3.0
        daily_jitter = self.rng.randint(-2, 2)
        census_val = max(10, min(capacity, int(base_census + wave + daily_jitter)))

        if scenario == "high_census_strain" and day_offset >= 20:
            census_val = min(capacity, capacity - self.rng.randint(1, 3))
        elif scenario == "staffing_stress" and day_offset >= 25:
            census_val = min(capacity, int(capacity * 0.93))

        budgeted_census = int(capacity * profile["budgeted_occupancy"])
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

        # Admissions & Discharges — facility-specific ranges
        adm_lo, adm_hi = profile["admissions_range"]
        dis_lo, dis_hi = profile["discharges_range"]
        today_adm = max(
            0,
            self.rng.randint(adm_lo, adm_hi)
            if day_offset % 7 not in (5, 6)
            else self.rng.randint(0, 2),
        )
        today_dis = max(
            0,
            self.rng.randint(dis_lo, dis_hi)
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

        # Length of Stay — facility-specific target and mix
        target_los = profile["target_los"]
        avg_los = round(
            target_los
            + (math.sin(day_offset / 6.0) * 1.5)
            + self.rng.uniform(-0.5, 0.5),
            1,
        )
        short_stay = int(census_val * profile["short_stay_pct"])
        long_stay = census_val - short_stay
        outliers = max(
            1, int(census_val * profile["outlier_pct"]) + self.rng.randint(0, 2)
        )

        los = LengthOfStayData(
            average_los_days=avg_los,
            target_los_days=target_los,
            short_stay_count=short_stay,
            long_stay_count=long_stay,
            los_outliers_count=outliers,
            median_los_days=round(avg_los - 1.2, 1),
        )

        # Therapy — facility-specific scheduled minutes and delivery
        sched_min = profile["therapy_scheduled_min"]
        del_lo, del_hi = profile["therapy_delivery_range"]
        deliv_min = round(sched_min * self.rng.uniform(del_lo, del_hi), 1)
        comp_rate = round((deliv_min / sched_min) * 100.0, 1)
        goals_lo, goals_hi = profile["goals_range"]
        goals_pct = round(self.rng.uniform(goals_lo, goals_hi), 1)
        holds_lo, holds_hi = profile["holds_range"]
        holds_count = self.rng.randint(holds_lo, holds_hi)
        mob_lo, mob_hi = profile["mobility_range"]
        mobility_idx = round(self.rng.uniform(mob_lo, mob_hi), 1)

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

        # Staffing — facility-specific HPPD target and ratios
        target_hppd = profile["target_hppd"]
        actual_hppd = round(target_hppd + self.rng.uniform(-0.15, 0.25), 2)
        rn_hrs = round(census_val * profile["rn_ratio"], 1)
        lpn_hrs = round(census_val * profile["lpn_ratio"], 1)
        cna_hrs = round(census_val * profile["cna_ratio"], 1)
        ci_lo, ci_hi = profile["base_call_ins"]
        call_ins = self.rng.randint(ci_lo, ci_hi)
        os_lo, os_hi = profile["base_open_shifts"]
        open_shifts = self.rng.randint(os_lo, os_hi)
        ot_lo, ot_hi = profile["base_ot_hrs"]
        ot_hrs = round(self.rng.uniform(ot_lo, ot_hi), 1)
        ag_lo, ag_hi = profile["base_agency_pct"]
        agency_pct = round(self.rng.uniform(ag_lo, ag_hi), 1)

        if scenario == "staffing_stress" and day_offset >= 25:
            actual_hppd = round(target_hppd - 0.50, 2)
            call_ins = 6
            open_shifts = 5
            ot_hrs = round(ot_hi * 2.5, 1)
            agency_pct = round(ag_hi * 1.5, 1)

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

        # Payer & Auth — facility-specific payer mix
        payer_mix = dict(profile["payer_mix"])
        pe_lo, pe_hi = profile["base_exp_48h"]
        exp_48h = self.rng.randint(pe_lo, pe_hi)
        exp_72h = exp_48h + self.rng.randint(1, 3)
        pr_lo, pr_hi = profile["base_pending_reauth"]
        pending_reauth = self.rng.randint(pr_lo, pr_hi)
        de_lo, de_hi = profile["base_denials"]
        denials = self.rng.randint(de_lo, de_hi)

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

        # Hospitality — facility-specific satisfaction baselines
        d_lo, d_hi = profile["dining_range"]
        dining = round(self.rng.uniform(d_lo, d_hi), 1)
        cl_lo, cl_hi = profile["clean_range"]
        clean = round(self.rng.uniform(cl_lo, cl_hi), 1)
        n_lo, n_hi = profile["nps_range"]
        nps = round(self.rng.uniform(n_lo, n_hi), 1)
        gr_lo, gr_hi = profile["guest_req_range"]
        guest_req = self.rng.randint(gr_lo, gr_hi)
        rt_lo, rt_hi = profile["res_time_range"]
        res_time = round(self.rng.uniform(rt_lo, rt_hi), 1)

        hospitality = HospitalityData(
            dining_satisfaction_score=dining,
            cleanliness_room_comfort_score=clean,
            guest_satisfaction_nps=nps,
            open_guest_service_requests=guest_req,
            avg_request_resolution_hours=res_time,
        )

        # Transfers — facility-specific readmission and transfer patterns
        ut_lo, ut_hi = profile["unplanned_30d_range"]
        unplanned_30d = self.rng.randint(ut_lo, ut_hi)
        rm_lo, rm_hi = profile["readm_pct_range"]
        readm_pct = round(self.rng.uniform(rm_lo, rm_hi), 1)
        benchmark_readm = profile["benchmark_readm"]
        aw_lo, aw_hi = profile["acute_week_range"]
        acute_week = self.rng.randint(aw_lo, aw_hi)
        transfers_by_reason = dict(profile["transfer_reasons"])

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
