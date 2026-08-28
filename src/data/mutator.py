"""Database mutator for synthetic facility operational data.

Enables the POC 'Try New Facility Data' demonstration feature by mutating actual
underlying database records in `daily_facility_snapshots` for the active facility
without changing the facility, scenario, or prompts.
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm.attributes import flag_modified

from src.data.synthetic_generator import FACILITIES, SyntheticFacilityDataGenerator
from src.db.database import _get_session_factory, init_db
from src.db.models import DailySnapshotRecord, FacilityRecord
from src.models.facility import DailyFacilitySnapshot

logger = logging.getLogger("db.mutator")


def mutate_facility_data(
    facility_id: str = "ignite-oak-brook",
    scenario: str = "baseline",
) -> dict[str, Any]:
    """Mutate actual database records for the specified facility and scenario in-place.

    Performs an immediate database update on the latest snapshot (and recent history)
    in `daily_facility_snapshots` with controlled synthetic operational variations.
    Does NOT invoke any LLM calls or predetermined responses.
    """
    if facility_id not in FACILITIES:
        raise ValueError(
            f"Facility '{facility_id}' is not recognized. "
            f"Available facilities: {list(FACILITIES.keys())}"
        )

    init_db()

    with _get_session_factory()() as session:
        # Ensure FacilityRecord exists
        fac_rec = session.scalar(
            select(FacilityRecord).where(FacilityRecord.facility_id == facility_id)
        )
        if not fac_rec:
            meta = FACILITIES[facility_id]
            fac_rec = FacilityRecord(
                facility_id=meta.facility_id,
                facility_name=meta.facility_name,
                location_region=meta.location_region,
                total_licensed_beds=meta.total_licensed_beds,
                certified_operational_beds=meta.certified_operational_beds,
                active_wings=meta.active_wings,
            )
            session.add(fac_rec)
            session.commit()

        # Query snapshot records
        snapshot_records = (
            session.execute(
                select(DailySnapshotRecord)
                .where(
                    DailySnapshotRecord.facility_id == facility_id,
                    DailySnapshotRecord.scenario_name == scenario,
                )
                .order_by(DailySnapshotRecord.snapshot_date)
            )
            .scalars()
            .all()
        )

        # If no snapshot records exist in DB yet, seed them first
        if not snapshot_records or len(snapshot_records) < 30:
            generator = SyntheticFacilityDataGenerator(seed=42)
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
            session.commit()

            snapshot_records = (
                session.execute(
                    select(DailySnapshotRecord)
                    .where(
                        DailySnapshotRecord.facility_id == facility_id,
                        DailySnapshotRecord.scenario_name == scenario,
                    )
                    .order_by(DailySnapshotRecord.snapshot_date)
                )
                .scalars()
                .all()
            )

        latest_rec = snapshot_records[-1]
        latest_data = dict(latest_rec.data_json)
        latest_snap = DailyFacilitySnapshot.model_validate(latest_data)

        # Inspect current state and create controlled synthetic operational shifts
        # 1. Staffing Coverage
        curr_hppd = latest_snap.staffing.hppd_actual
        target_hppd = latest_snap.staffing.hppd_budgeted_target
        if curr_hppd >= (target_hppd - 0.05):
            # Shift to staffing pressure
            new_hppd = round(target_hppd - 0.52, 2)
            new_call_ins = 5
            new_open_shifts = 4
            new_ot_hrs = 14.5
            new_agency_pct = 7.2
        else:
            # Shift to strong coverage
            new_hppd = round(target_hppd + 0.18, 2)
            new_call_ins = 0
            new_open_shifts = 0
            new_ot_hrs = 2.5
            new_agency_pct = 1.8

        # 2. Census & Flow
        capacity = latest_snap.census.total_capacity
        curr_census = latest_snap.census.current_census
        if curr_census >= int(capacity * 0.90):
            new_census = int(capacity * 0.83)
            new_admissions = 2
            new_discharges = 5
        else:
            new_census = int(capacity * 0.94)
            new_admissions = 6
            new_discharges = 2
        new_occ_rate = round((new_census / capacity) * 100.0, 1)
        new_avail_beds = max(0, capacity - new_census)
        new_net_flow = new_admissions - new_discharges

        # Staffing hours based on new census & HPPD
        rn_ratio = 1.10 if new_hppd > target_hppd else 0.85
        lpn_ratio = 1.35 if new_hppd > target_hppd else 1.15
        cna_ratio = 1.90 if new_hppd > target_hppd else 1.65
        new_rn_hours = round(new_census * rn_ratio, 1)
        new_lpn_hours = round(new_census * lpn_ratio, 1)
        new_cna_hours = round(new_census * cna_ratio, 1)

        # 3. Therapy Delivery
        sched_min = latest_snap.therapy.avg_daily_treatment_minutes_scheduled or 120.0
        if latest_snap.therapy.treatment_completion_rate_pct >= 93.0:
            new_deliv_min = round(sched_min * 0.865, 1)
            new_comp_rate = round((new_deliv_min / sched_min) * 100.0, 1)
            new_holds = 4
            new_goals_pct = 82.5
            new_mobility = 7.3
        else:
            new_deliv_min = round(sched_min * 0.975, 1)
            new_comp_rate = round((new_deliv_min / sched_min) * 100.0, 1)
            new_holds = 0
            new_goals_pct = 95.0
            new_mobility = 9.0

        # 4. Hospital Transfers
        if latest_snap.hospital_transfers.acute_transfers_this_week >= 2:
            new_acute_week = 0
            new_unplanned_30d = 3
            new_readm_rate = 7.4
            new_reasons = {
                "respiratory": 0,
                "cardiac": 0,
                "fall_trauma": 1,
                "sepsis_infection": 0,
                "altered_mental_status": 0,
                "other": 0,
            }
        else:
            new_acute_week = 3
            new_unplanned_30d = 8
            new_readm_rate = 14.1
            new_reasons = {
                "respiratory": 2,
                "cardiac": 1,
                "fall_trauma": 0,
                "sepsis_infection": 0,
                "altered_mental_status": 0,
                "other": 0,
            }

        # 5. Payer Authorizations
        if latest_snap.payer_auth.expiring_authorizations_48h >= 4:
            new_exp_48h = 1
            new_exp_72h = 3
            new_pending_reauth = 2
            new_denials = 0
        else:
            new_exp_48h = 6
            new_exp_72h = 12
            new_pending_reauth = 8
            new_denials = 2

        # Apply changes to latest snapshot dict and validate with Pydantic
        updated_dict = latest_snap.model_dump(mode="json")
        updated_dict["staffing"].update({
            "hppd_actual": new_hppd,
            "call_in_absences_count": new_call_ins,
            "open_shifts_count": new_open_shifts,
            "overtime_hours": new_ot_hrs,
            "agency_staff_pct": new_agency_pct,
            "rn_hours_actual": new_rn_hours,
            "lpn_hours_actual": new_lpn_hours,
            "cna_hours_actual": new_cna_hours,
        })
        updated_dict["census"].update({
            "current_census": new_census,
            "occupancy_rate_pct": new_occ_rate,
            "available_beds": new_avail_beds,
        })
        updated_dict["admissions_discharges"].update({
            "today_admissions": new_admissions,
            "today_discharges": new_discharges,
            "net_flow": new_net_flow,
        })
        updated_dict["therapy"].update({
            "avg_daily_treatment_minutes_delivered": new_deliv_min,
            "treatment_completion_rate_pct": new_comp_rate,
            "patients_meeting_weekly_goals_pct": new_goals_pct,
            "patients_on_therapy_hold": new_holds,
            "functional_mobility_gain_index": new_mobility,
        })
        updated_dict["hospital_transfers"].update({
            "unplanned_transfers_30d_count": new_unplanned_30d,
            "readmission_rate_30d_pct": new_readm_rate,
            "acute_transfers_this_week": new_acute_week,
            "transfers_by_reason": new_reasons,
        })
        updated_dict["payer_auth"].update({
            "expiring_authorizations_48h": new_exp_48h,
            "expiring_authorizations_72h": new_exp_72h,
            "pending_reauthorizations_count": new_pending_reauth,
            "auth_denials_pending_appeal_count": new_denials,
        })

        # Validate structured model
        validated_snap = DailyFacilitySnapshot.model_validate(updated_dict)
        latest_rec.data_json = validated_snap.model_dump(mode="json")
        flag_modified(latest_rec, "data_json")

        # Smooth last 3 snapshots for trend continuity
        if len(snapshot_records) >= 4:
            for idx, rec in enumerate(snapshot_records[-4:-1], start=1):
                rec_dict = dict(rec.data_json)
                interp_factor = idx / 4.0
                interp_hppd = round(curr_hppd + (new_hppd - curr_hppd) * interp_factor, 2)
                interp_census = int(curr_census + (new_census - curr_census) * interp_factor)
                rec_dict["staffing"]["hppd_actual"] = interp_hppd
                rec_dict["census"]["current_census"] = interp_census
                rec_dict["census"]["occupancy_rate_pct"] = round((interp_census / capacity) * 100.0, 1)
                rec_dict["census"]["available_beds"] = max(0, capacity - interp_census)
                v_snap = DailyFacilitySnapshot.model_validate(rec_dict)
                rec.data_json = v_snap.model_dump(mode="json")
                flag_modified(rec, "data_json")

        session.commit()

        logger.info(
            "Mutated facility data in DB for %s (scenario: %s): HPPD=%s, Census=%s, Therapy=%s%%, Transfers=%s",
            facility_id,
            scenario,
            new_hppd,
            new_census,
            new_comp_rate,
            new_acute_week,
        )

        return {
            "success": True,
            "facility_id": facility_id,
            "scenario": scenario,
            "snapshot_date": str(latest_rec.snapshot_date),
            "modified_fields": {
                "staffing_hppd_actual": new_hppd,
                "staffing_call_ins": new_call_ins,
                "staffing_open_shifts": new_open_shifts,
                "census_current": new_census,
                "occupancy_rate_pct": new_occ_rate,
                "therapy_completion_rate_pct": new_comp_rate,
                "therapy_holds": new_holds,
                "acute_transfers_this_week": new_acute_week,
                "expiring_authorizations_48h": new_exp_48h,
            },
        }
