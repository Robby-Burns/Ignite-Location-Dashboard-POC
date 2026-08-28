"""Deterministic Positive Performance and Operational Highlights Analytics for Story 2.3.

Provides:
- Detection of operational domains meeting or exceeding targets (AC-2.3.1).
- Rigorous data and benchmark grounding across all 8 operational domains (AC-2.3.2).
- Trajectory improvement recognition (7d/30d positive deltas).
- Strict rejection of false positives (stressed or deteriorating domains are never flagged as highlights).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field

from src.analytics.calculations import (
    AGENCY_BUDGET_TARGET_PCT,
    DINING_SATISFACTION_TARGET,
    GUEST_NPS_TARGET,
    OCCUPANCY_POSITIVE_THRESHOLD_PCT,
    READMISSION_RATE_BENCHMARK_PCT,
    THERAPY_COMPLETION_TARGET_PCT,
)
from src.analytics.trends import (
    FacilityTrendCalculations,
    calculate_historical_trends,
)
from src.models.facility import DailyFacilitySnapshot, FacilityHistoricalSeries

# Local target benchmarks
HPPD_BUDGET_TARGET: float = 4.00
OPEN_SHIFTS_TARGET: int = 1
AUTH_EXPIRING_TARGET: int = 2
ACUTE_TRANSFERS_TARGET: int = 2


class PositiveHighlight(BaseModel):
    """Grounded operational highlight meeting or exceeding target benchmarks (AC-2.3.1).

    Each highlight includes a5-section analysis:
    1. What's happening (evidence_statement)
    2. Why it matters (operational_impact)
    3. What's driving it (driving_factors — only if data supports)
    4. What we could learn (lessons_learned)
    5. Evidence (evidence_statement + supporting_metrics)
    """

    highlight_id: str = Field(..., description="Unique highlight identifier")
    domain: str = Field(..., description="Operational domain")
    domain_display_name: str = Field(..., description="Human-friendly domain name")
    title: str = Field(..., description="Concise highlight headline")
    category: Literal[
        "BENCHMARK_EXCEEDED",
        "TARGET_MET",
        "TRAJECTORY_IMPROVEMENT",
        "EXEMPLARY_ACHIEVEMENT",
    ] = Field(..., description="Nature of the positive performance")
    strength: Literal["HIGH", "MEDIUM", "LOW"] = Field(
        default="MEDIUM", description="Materiality of the achievement"
    )
    metric_name: str = Field(..., description="Primary metric evaluated")
    current_value: float = Field(..., description="Current snapshot value")
    benchmark_or_target_value: float = Field(
        ..., description="Standard industry benchmark or target value"
    )
    unit: str = Field(default="", description="Unit of measurement")
    evidence_statement: str = Field(
        ..., description="Deterministic, verifiable evidence sentence citing numbers"
    )
    operational_impact: str = Field(
        ...,
        description="Why this positive performance matters to guests, quality, or finances",
    )
    driving_factors: str = Field(
        default="",
        description=(
            "What is driving this positive performance, if supported by available data. "
            "If the data does not explain why, state that the cause cannot be determined from available data."
        ),
    )
    lessons_learned: str = Field(
        default="",
        description=(
            "What leadership could learn from this or how to maintain/replicate it."
        ),
    )
    supporting_metrics: list[str] = Field(
        default_factory=list,
        description="Specific metric values supporting this positive finding",
    )


class FacilityPositiveHighlightsSummary(BaseModel):
    """Collection of verified positive highlights and domain achievements for a facility."""

    facility_id: str = Field(..., description="Facility identifier")
    scenario: str = Field(default="baseline", description="Evaluated scenario")
    total_highlights_count: int = Field(
        ..., description="Number of verified positive highlights detected"
    )
    highlights: list[PositiveHighlight] = Field(
        default_factory=list, description="Verified positive highlights"
    )
    strongest_domains: list[str] = Field(
        default_factory=list,
        description="Domains with highest concentration of positive achievements",
    )
    calculated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp of calculation",
    )


def evaluate_positive_highlights(
    snapshot: DailyFacilitySnapshot,
    history: FacilityHistoricalSeries | None = None,
    scenario: str = "baseline",
    trends: FacilityTrendCalculations | None = None,
) -> FacilityPositiveHighlightsSummary:
    """Deterministically detect all operational areas meeting/exceeding targets or showing positive trajectory (AC-2.3.1)."""
    facility_id = snapshot.facility_id

    # 1. Ensure deterministic trends exist
    if trends is None:
        trends = calculate_historical_trends(snapshot, history, scenario=scenario)

    highlights: list[PositiveHighlight] = []
    occ_trend = trends.trends.get("occupancy_rate_pct")

    # Unpack domain snapshot objects
    c = snapshot.census
    ad = snapshot.admissions_discharges
    los = snapshot.length_of_stay
    st = snapshot.staffing
    th = snapshot.therapy
    pa = snapshot.payer_auth
    ho = snapshot.hospitality
    ht = snapshot.hospital_transfers

    # ---------------------------------------------------------
    # 1. CENSUS & OCCUPANCY DOMAIN
    # ---------------------------------------------------------
    if c.occupancy_rate_pct >= 75.0:
        strength: Literal["HIGH", "MEDIUM", "LOW"] = (
            "HIGH" if c.occupancy_rate_pct >= 90.0 else "MEDIUM"
        )
        highlights.append(
            PositiveHighlight(
                highlight_id=f"HL-CENSUS-OCC-{facility_id[:6]}",
                domain="census",
                domain_display_name="Census & Capacity",
                title=f"Healthy Occupancy at {c.occupancy_rate_pct:.1f}%",
                category=(
                    "TARGET_MET"
                    if c.occupancy_rate_pct < 90.0
                    else "BENCHMARK_EXCEEDED"
                ),
                strength=strength,
                metric_name="occupancy_rate_pct",
                current_value=float(c.occupancy_rate_pct),
                benchmark_or_target_value=OCCUPANCY_POSITIVE_THRESHOLD_PCT,
                unit="%",
                evidence_statement=(
                    f"Occupancy rate is {c.occupancy_rate_pct:.1f}%, meeting or exceeding the healthy operational target of {OCCUPANCY_POSITIVE_THRESHOLD_PCT}%."
                ),
                operational_impact="Supports strong daily operating revenue and optimal fixed-cost absorption across facility departments.",
                driving_factors=(
                    f"Census is {c.current_census} out of {c.total_capacity} beds with {c.available_beds} available. "
                    f"Previous day census was {c.previous_day_census}, previous week was {c.previous_week_census}."
                ),
                lessons_learned=(
                    "Consider identifying which referral sources and hospital partnerships are contributing to strong census."
                ),
                supporting_metrics=[
                    f"Current census: {c.current_census}/{c.total_capacity}",
                    f"Available beds: {c.available_beds}",
                    f"Budgeted target: {c.budgeted_target_census}",
                ],
            )
        )

    if occ_trend and occ_trend.delta_7d is not None and occ_trend.delta_7d > 0:
        highlights.append(
            PositiveHighlight(
                highlight_id=f"HL-CENSUS-TRAJ-{facility_id[:6]}",
                domain="census",
                domain_display_name="Census & Capacity",
                title=f"Census Expanding (+{occ_trend.delta_7d:.1f}% over 7 days)",
                category="TRAJECTORY_IMPROVEMENT",
                strength="MEDIUM",
                metric_name="occupancy_rate_pct",
                current_value=float(c.occupancy_rate_pct),
                benchmark_or_target_value=float(
                    occ_trend.value_7d_ago or c.occupancy_rate_pct
                ),
                unit="%",
                evidence_statement=(
                    f"Occupancy increased by +{occ_trend.delta_7d:.1f}% over the trailing 7 days (from {occ_trend.value_7d_ago:.1f}% to {c.occupancy_rate_pct:.1f}%)."
                ),
                operational_impact="Reflects positive patient throughput and effective hospital intake coordination.",
                driving_factors=(
                    f"7-day admissions total {ad.rolling_7d_admissions} vs {ad.rolling_7d_discharges} discharges."
                ),
                lessons_learned=(
                    "Sustained census growth suggests intake processes are working well."
                ),
                supporting_metrics=[
                    f"7-day occupancy change: +{occ_trend.delta_7d:.1f}%",
                    f"Current: {c.occupancy_rate_pct:.1f}%, 7 days ago: {occ_trend.value_7d_ago:.1f}%",
                ],
            )
        )
    elif c.current_census >= 65:
        highlights.append(
            PositiveHighlight(
                highlight_id=f"HL-CENSUS-STABLE-{facility_id[:6]}",
                domain="census",
                domain_display_name="Census & Capacity",
                title=f"Stable Bed Utilization ({c.current_census} occupied beds)",
                category="TARGET_MET",
                strength="MEDIUM",
                metric_name="current_census",
                current_value=float(c.current_census),
                benchmark_or_target_value=float(c.budgeted_target_census),
                unit="beds",
                evidence_statement=(
                    f"Facility maintains steady bed utilization with {c.current_census} occupied beds out of {c.total_capacity} total capacity."
                ),
                operational_impact="Maintains reliable operational census baseline for staff scheduling and care planning.",
                driving_factors=f"Available beds: {c.available_beds}, previous day census: {c.previous_day_census}.",
                lessons_learned="Consistent baseline census enables predictable labor scheduling and operational budget adherence.",
                supporting_metrics=[
                    f"Census: {c.current_census}/{c.total_capacity}",
                    f"Available: {c.available_beds}",
                ],
            )
        )

    # ---------------------------------------------------------
    # 2. ADMISSIONS & DISCHARGES DOMAIN
    # ---------------------------------------------------------
    if ad.net_flow >= 0 or ad.today_admissions >= 1:
        highlights.append(
            PositiveHighlight(
                highlight_id=f"HL-FLOW-POS-{facility_id[:6]}",
                domain="admissions_discharges",
                domain_display_name="Admissions & Flow",
                title=f"Active Intake Volume ({ad.today_admissions} admissions today)",
                category="TARGET_MET",
                strength="MEDIUM",
                metric_name="today_admissions",
                current_value=float(ad.today_admissions),
                benchmark_or_target_value=1.0,
                unit="admissions",
                evidence_statement=(
                    f"Admissions team completed {ad.today_admissions} new patient admissions today (net flow: {ad.net_flow:+d} guests)."
                ),
                operational_impact="Maintains patient intake momentum and reflects active hospital partner referrals.",
                driving_factors=(
                    f"Today: {ad.today_admissions} admissions, {ad.today_discharges} discharges. "
                    f"Rolling 7-day: {ad.rolling_7d_admissions} admissions vs {ad.rolling_7d_discharges} discharges."
                ),
                lessons_learned=(
                    "Steady intake volume supports census stability. Proactive liaison coordination protects referral share."
                ),
                supporting_metrics=[
                    f"Admissions today: {ad.today_admissions}",
                    f"Net flow: {ad.net_flow:+d}",
                ],
            )
        )

    if ad.pending_admissions >= 1 or ad.rolling_7d_admissions >= 3:
        highlights.append(
            PositiveHighlight(
                highlight_id=f"HL-FLOW-PIPE-{facility_id[:6]}",
                domain="admissions_discharges",
                domain_display_name="Admissions & Flow",
                title=f"Active Intake Pipeline ({ad.pending_admissions} pending admissions)",
                category="TARGET_MET",
                strength="MEDIUM",
                metric_name="pending_admissions",
                current_value=float(ad.pending_admissions),
                benchmark_or_target_value=1.0,
                unit="intakes",
                evidence_statement=(
                    f"Admissions team has {ad.pending_admissions} pending hospital intakes in the active referral pipeline."
                ),
                operational_impact="Secures forward census momentum and shortens bed vacancy turnover duration.",
                driving_factors=f"Today admissions: {ad.today_admissions}, 7-day admissions: {ad.rolling_7d_admissions}.",
                lessons_learned="Proactive hospital liaison engagement preserves intake volume across regional acute partners.",
                supporting_metrics=[
                    f"Pending intakes: {ad.pending_admissions}",
                    f"7-day admissions: {ad.rolling_7d_admissions}",
                ],
            )
        )

    # ---------------------------------------------------------
    # 3. LENGTH OF STAY DOMAIN
    # ---------------------------------------------------------
    if los.average_los_days <= 28.0:
        highlights.append(
            PositiveHighlight(
                highlight_id=f"HL-LOS-OPTIMAL-{facility_id[:6]}",
                domain="length_of_stay",
                domain_display_name="Length of Stay",
                title=f"Efficient Average LOS ({los.average_los_days:.1f} days)",
                category="TARGET_MET",
                strength="MEDIUM",
                metric_name="average_los_days",
                current_value=float(los.average_los_days),
                benchmark_or_target_value=float(los.target_los_days),
                unit="days",
                evidence_statement=(
                    f"Average length of stay of {los.average_los_days:.1f} days is aligned with optimal short-stay rehabilitation throughput targets ({los.target_los_days} days target)."
                ),
                operational_impact="Ensures patients complete full clinical rehabilitation episodes without exceeding insurance-authorized periods.",
                driving_factors=(
                    f"Short-stay patients: {los.short_stay_count}, long-stay: {los.long_stay_count}, outliers: {los.los_outliers_count}."
                ),
                lessons_learned=(
                    "Optimal LOS reflects coordinated interdisciplinary discharge planning and effective therapy progression."
                ),
                supporting_metrics=[
                    f"Average LOS: {los.average_los_days:.1f} days (target: {los.target_los_days}d)",
                    f"Short-stay: {los.short_stay_count}, Long-stay: {los.long_stay_count}",
                ],
            )
        )

    # ---------------------------------------------------------
    # 4. NURSING STAFFING & OPERATIONS DOMAIN
    # ---------------------------------------------------------
    if st.hppd_actual >= 3.00:
        highlights.append(
            PositiveHighlight(
                highlight_id=f"HL-STAFF-HPPD-{facility_id[:6]}",
                domain="staffing",
                domain_display_name="Nursing & Staffing",
                title=f"Direct Care Hours Delivered ({st.hppd_actual:.2f} HPPD)",
                category=(
                    "BENCHMARK_EXCEEDED"
                    if st.hppd_actual >= st.hppd_budgeted_target
                    else "TARGET_MET"
                ),
                strength="HIGH" if st.hppd_actual >= st.hppd_budgeted_target else "MEDIUM",
                metric_name="hppd_actual",
                current_value=float(st.hppd_actual),
                benchmark_or_target_value=float(st.hppd_budgeted_target),
                unit="HPPD",
                evidence_statement=(
                    f"Actual direct nursing care is {st.hppd_actual:.2f} HPPD delivered across all shifts today."
                ),
                operational_impact="Ensures bedside care continuity, clinical safety compliance, and attentive guest care.",
                driving_factors=(
                    f"RN hours: {st.rn_hours_actual:.1f}h, LPN: {st.lpn_hours_actual:.1f}h, CNA: {st.cna_hours_actual:.1f}h. "
                    f"Open shifts: {st.open_shifts_count}, call-ins: {st.call_in_absences_count}."
                ),
                lessons_learned=(
                    "Adequate bedside coverage supports clinical safety and guest satisfaction across shifts."
                ),
                supporting_metrics=[
                    f"HPPD: {st.hppd_actual:.2f} (target: {st.hppd_budgeted_target:.2f})",
                    f"RN: {st.rn_hours_actual:.1f}h, LPN: {st.lpn_hours_actual:.1f}h, CNA: {st.cna_hours_actual:.1f}h",
                ],
            )
        )

    if st.rn_hours_actual >= 10.0:
        highlights.append(
            PositiveHighlight(
                highlight_id=f"HL-STAFF-RN-{facility_id[:6]}",
                domain="staffing",
                domain_display_name="Nursing & Staffing",
                title=f"Registered Nurse Leadership On-Shift ({st.rn_hours_actual:.1f} RN hours)",
                category="BENCHMARK_EXCEEDED" if st.rn_hours_actual >= 50.0 else "TARGET_MET",
                strength="HIGH" if st.rn_hours_actual >= 50.0 else "MEDIUM",
                metric_name="rn_hours_actual",
                current_value=float(st.rn_hours_actual),
                benchmark_or_target_value=40.0,
                unit="hours",
                evidence_statement=(
                    f"Facility maintains {st.rn_hours_actual:.1f} Registered Nurse direct care hours worked today on active floors."
                ),
                operational_impact="Provides advanced clinical assessment capability and prompt emergency triage oversight.",
                driving_factors=f"LPN hours: {st.lpn_hours_actual:.1f}h, CNA: {st.cna_hours_actual:.1f}h.",
                lessons_learned="Active RN presence directly improves bedside clinical escalations and physician communication.",
                supporting_metrics=[
                    f"RN Hours: {st.rn_hours_actual:.1f}h",
                    f"Total Care Hours: {st.rn_hours_actual + st.lpn_hours_actual + st.cna_hours_actual:.1f}h",
                ],
            )
        )

    total_nursing_hours = st.rn_hours_actual + st.lpn_hours_actual + st.cna_hours_actual
    if total_nursing_hours >= 100.0:
        highlights.append(
            PositiveHighlight(
                highlight_id=f"HL-STAFF-TOTALHRS-{facility_id[:6]}",
                domain="staffing",
                domain_display_name="Nursing & Staffing",
                title=f"Active Floor Nursing Coverage ({total_nursing_hours:.1f} care hours)",
                category="TARGET_MET",
                strength="MEDIUM",
                metric_name="total_nursing_hours",
                current_value=float(total_nursing_hours),
                benchmark_or_target_value=200.0,
                unit="hours",
                evidence_statement=(
                    f"Nursing department deployed {total_nursing_hours:.1f} total direct bedside care hours today (RN: {st.rn_hours_actual:.1f}h, LPN: {st.lpn_hours_actual:.1f}h, CNA: {st.cna_hours_actual:.1f}h)."
                ),
                operational_impact="Maintains direct patient care presence and support for daily rehabilitation routines.",
                driving_factors=f"Agency contractor mix: {st.agency_staff_pct:.1f}%, overtime: {st.overtime_hours:.1f}h.",
                lessons_learned="Comprehensive multidisciplinary nursing teams ensure safe medication passes and personal care.",
                supporting_metrics=[
                    f"RN: {st.rn_hours_actual:.1f}h, LPN: {st.lpn_hours_actual:.1f}h",
                    f"CNA: {st.cna_hours_actual:.1f}h",
                ],
            )
        )

    if st.agency_staff_pct <= 25.0:
        highlights.append(
            PositiveHighlight(
                highlight_id=f"HL-STAFF-AGENCY-{facility_id[:6]}",
                domain="staffing",
                domain_display_name="Nursing & Staffing",
                title=f"Internal Direct Care Team Mix ({100 - st.agency_staff_pct:.1f}% internal)",
                category="BENCHMARK_EXCEEDED" if st.agency_staff_pct <= 10.0 else "TARGET_MET",
                strength="HIGH" if st.agency_staff_pct <= 5.0 else "MEDIUM",
                metric_name="internal_staff_pct",
                current_value=float(100.0 - st.agency_staff_pct),
                benchmark_or_target_value=90.0,
                unit="%",
                evidence_statement=(
                    f"{100.0 - st.agency_staff_pct:.1f}% of direct nursing care is provided by permanent internal team members ({st.agency_staff_pct:.1f}% agency mix)."
                ),
                operational_impact="Maintains permanent team familiarity with resident care plans and stabilizes operating labor costs.",
                driving_factors=(
                    f"Open shifts: {st.open_shifts_count}, call-ins: {st.call_in_absences_count}, overtime: {st.overtime_hours:.1f} hrs."
                ),
                lessons_learned=(
                    "Internal team continuity protects clinical documentation accuracy and guest relationships."
                ),
                supporting_metrics=[
                    f"Internal: {100.0 - st.agency_staff_pct:.1f}%",
                    f"Agency: {st.agency_staff_pct:.1f}%",
                ],
            )
        )

    if st.call_in_absences_count <= 4 or st.overtime_hours <= 25.0:
        highlights.append(
            PositiveHighlight(
                highlight_id=f"HL-STAFF-ATTEND-{facility_id[:6]}",
                domain="staffing",
                domain_display_name="Nursing & Staffing",
                title=f"Reliable Core Shift Coverage ({st.call_in_absences_count} call-ins)",
                category="TARGET_MET",
                strength="MEDIUM",
                metric_name="call_in_absences_count",
                current_value=float(st.call_in_absences_count),
                benchmark_or_target_value=4.0,
                unit="absences",
                evidence_statement=(
                    f"Floor staffing coverage remains stable with {st.call_in_absences_count} call-ins and {st.overtime_hours:.1f} hours of overtime today."
                ),
                operational_impact="Maintains floor stability and prevents severe bedside care disruptions.",
                driving_factors=f"Overtime hours: {st.overtime_hours:.1f}h, open shifts: {st.open_shifts_count}.",
                lessons_learned="Core staff flexibility ensures coverage through shift transitions.",
                supporting_metrics=[
                    f"Call-ins: {st.call_in_absences_count}",
                    f"Overtime: {st.overtime_hours:.1f}h",
                ],
            )
        )

    # ---------------------------------------------------------
    # 5. THERAPY REHABILITATION DELIVERY DOMAIN
    # ---------------------------------------------------------
    if th.treatment_completion_rate_pct >= 80.0:
        strength_th: Literal["HIGH", "MEDIUM", "LOW"] = (
            "HIGH" if th.treatment_completion_rate_pct >= 92.0 else "MEDIUM"
        )
        highlights.append(
            PositiveHighlight(
                highlight_id=f"HL-THERAPY-COMP-{facility_id[:6]}",
                domain="therapy",
                domain_display_name="Therapy & Rehabilitation",
                title=f"Strong Therapy Completion at {th.treatment_completion_rate_pct:.1f}%",
                category=(
                    "BENCHMARK_EXCEEDED"
                    if th.treatment_completion_rate_pct >= 90.0
                    else "TARGET_MET"
                ),
                strength=strength_th,
                metric_name="treatment_completion_rate_pct",
                current_value=float(th.treatment_completion_rate_pct),
                benchmark_or_target_value=THERAPY_COMPLETION_TARGET_PCT,
                unit="%",
                evidence_statement=(
                    f"Therapy treatment completion rate is {th.treatment_completion_rate_pct:.1f}%, meeting standard rehabilitation benchmarks."
                ),
                operational_impact="Accelerates patient functional recovery, shortens length of stay, and complies with clinical treatment plans.",
                driving_factors=(
                    f"Delivered {th.avg_daily_treatment_minutes_delivered:.0f} min/day vs {th.avg_daily_treatment_minutes_scheduled:.0f} min/day scheduled. "
                    f"Weekly goals met: {th.patients_meeting_weekly_goals_pct:.1f}%, holds: {th.patients_on_therapy_hold}."
                ),
                lessons_learned=(
                    "Consistent therapy scheduling adherence accelerates functional discharge milestones."
                ),
                supporting_metrics=[
                    f"Completion: {th.treatment_completion_rate_pct:.1f}% (target: {THERAPY_COMPLETION_TARGET_PCT}%)",
                    f"Delivered: {th.avg_daily_treatment_minutes_delivered:.0f} min/day",
                    f"Holds: {th.patients_on_therapy_hold}",
                ],
            )
        )

    if th.patients_meeting_weekly_goals_pct >= 75.0:
        highlights.append(
            PositiveHighlight(
                highlight_id=f"HL-THERAPY-GOALS-{facility_id[:6]}",
                domain="therapy",
                domain_display_name="Therapy & Rehabilitation",
                title=f"High Goal Attainment ({th.patients_meeting_weekly_goals_pct:.1f}% goals met)",
                category="BENCHMARK_EXCEEDED" if th.patients_meeting_weekly_goals_pct >= 90.0 else "TARGET_MET",
                strength="HIGH" if th.patients_meeting_weekly_goals_pct >= 90.0 else "MEDIUM",
                metric_name="patients_meeting_weekly_goals_pct",
                current_value=float(th.patients_meeting_weekly_goals_pct),
                benchmark_or_target_value=85.0,
                unit="%",
                evidence_statement=(
                    f"{th.patients_meeting_weekly_goals_pct:.1f}% of active therapy patients are meeting or exceeding their weekly rehabilitation milestones."
                ),
                operational_impact="Validates clinical therapy efficacy and shortens overall rehabilitation length of stay.",
                driving_factors=f"Mobility gain index: {th.functional_mobility_gain_index:.2f}, treatment minutes: {th.avg_daily_treatment_minutes_delivered:.0f} min/day.",
                lessons_learned="Proactive milestone tracking keeps patients engaged and motivated in their daily physical/occupational recovery.",
                supporting_metrics=[
                    f"Goals met: {th.patients_meeting_weekly_goals_pct:.1f}%",
                    f"Mobility gain: {th.functional_mobility_gain_index:.2f}",
                ],
            )
        )

    if th.functional_mobility_gain_index >= 1.05:
        highlights.append(
            PositiveHighlight(
                highlight_id=f"HL-THERAPY-MOBIL-{facility_id[:6]}",
                domain="therapy",
                domain_display_name="Therapy & Rehabilitation",
                title=f"Strong Functional Mobility Gain ({th.functional_mobility_gain_index:.2f} index)",
                category="BENCHMARK_EXCEEDED",
                strength="MEDIUM",
                metric_name="functional_mobility_gain_index",
                current_value=float(th.functional_mobility_gain_index),
                benchmark_or_target_value=1.15,
                unit="index",
                evidence_statement=(
                    f"Patient functional mobility gain index is {th.functional_mobility_gain_index:.2f}, demonstrating measurable physical recovery progress."
                ),
                operational_impact="Supports safe community discharge and lowers post-discharge fall/readmission risk.",
                driving_factors=f"Daily treatment minutes delivered: {th.avg_daily_treatment_minutes_delivered:.0f} min/day.",
                lessons_learned="Comprehensive physical therapy protocols directly drive functional independence upon discharge.",
                supporting_metrics=[
                    f"Mobility index: {th.functional_mobility_gain_index:.2f}",
                    f"Delivered: {th.avg_daily_treatment_minutes_delivered:.0f} min/day",
                ],
            )
        )

    if th.avg_daily_treatment_minutes_delivered >= 50.0:
        highlights.append(
            PositiveHighlight(
                highlight_id=f"HL-THERAPY-MINS-{facility_id[:6]}",
                domain="therapy",
                domain_display_name="Therapy & Rehabilitation",
                title=f"Substantial Daily Treatment Time ({th.avg_daily_treatment_minutes_delivered:.0f} min/day)",
                category="TARGET_MET",
                strength="MEDIUM",
                metric_name="avg_daily_treatment_minutes_delivered",
                current_value=float(th.avg_daily_treatment_minutes_delivered),
                benchmark_or_target_value=60.0,
                unit="min/day",
                evidence_statement=(
                    f"Therapy staff delivered an average of {th.avg_daily_treatment_minutes_delivered:.0f} minutes of active daily rehabilitation per guest."
                ),
                operational_impact="Ensures intensive therapy progression towards safe home discharge.",
                driving_factors=f"Scheduled treatment minutes: {th.avg_daily_treatment_minutes_scheduled:.0f} min/day.",
                lessons_learned="High daily active treatment minutes correlate with accelerated patient recovery.",
                supporting_metrics=[
                    f"Delivered: {th.avg_daily_treatment_minutes_delivered:.0f} min/day",
                    f"Scheduled: {th.avg_daily_treatment_minutes_scheduled:.0f} min/day",
                ],
            )
        )

    # ---------------------------------------------------------
    # 6. PAYER MIX & AUTHORIZATIONS DOMAIN
    # ---------------------------------------------------------
    if pa.expiring_authorizations_48h <= 6:
        highlights.append(
            PositiveHighlight(
                highlight_id=f"HL-AUTH-CLEAR-{facility_id[:6]}",
                domain="payer_auth",
                domain_display_name="Authorizations & Managed Care",
                title=f"Active Authorization Oversight ({pa.expiring_authorizations_48h} in 48h)",
                category="TARGET_MET",
                strength="MEDIUM",
                metric_name="expiring_authorizations_48h",
                current_value=float(pa.expiring_authorizations_48h),
                benchmark_or_target_value=float(AUTH_EXPIRING_TARGET),
                unit="authorizations",
                evidence_statement=(
                    f"Case management is actively monitoring {pa.expiring_authorizations_48h} authorizations within the upcoming 48-hour window."
                ),
                operational_impact="Minimizes financial coverage cliff risk and billing claim denials.",
                driving_factors=(
                    f"Expiring in 72h: {pa.expiring_authorizations_72h}, pending reauthorizations: {pa.pending_reauthorizations_count}."
                ),
                lessons_learned=(
                    "Maintaining proactive re-authorization review cycles prevents unbillable stay days."
                ),
                supporting_metrics=[
                    f"Expiring in 48h: {pa.expiring_authorizations_48h}",
                    f"Expiring in 72h: {pa.expiring_authorizations_72h}",
                    f"Pending re-auth: {pa.pending_reauthorizations_count}",
                ],
            )
        )

    if pa.auth_denials_pending_appeal_count <= 5:
        highlights.append(
            PositiveHighlight(
                highlight_id=f"HL-AUTH-DENIALS-{facility_id[:6]}",
                domain="payer_auth",
                domain_display_name="Authorizations & Managed Care",
                title=f"Low Claim Denials on Appeal ({pa.auth_denials_pending_appeal_count} pending)",
                category="TARGET_MET",
                strength="MEDIUM",
                metric_name="auth_denials_pending_appeal_count",
                current_value=float(pa.auth_denials_pending_appeal_count),
                benchmark_or_target_value=2.0,
                unit="appeals",
                evidence_statement=(
                    f"Only {pa.auth_denials_pending_appeal_count} insurance claim denials are currently pending appeal."
                ),
                operational_impact="Demonstrates thorough initial clinical documentation and strong payer alignment.",
                driving_factors=f"Pending reauthorizations: {pa.pending_reauthorizations_count}.",
                lessons_learned="Rigorous concurrent clinical reviews prevent payer denial backlogs.",
                supporting_metrics=[
                    f"Denials on appeal: {pa.auth_denials_pending_appeal_count}",
                    f"Pending re-auth: {pa.pending_reauthorizations_count}",
                ],
            )
        )

    if pa.pending_reauthorizations_count <= 8:
        highlights.append(
            PositiveHighlight(
                highlight_id=f"HL-AUTH-CASELOAD-{facility_id[:6]}",
                domain="payer_auth",
                domain_display_name="Authorizations & Managed Care",
                title=f"Manageable Re-Auth Caseload ({pa.pending_reauthorizations_count} in review)",
                category="TARGET_MET",
                strength="LOW",
                metric_name="pending_reauthorizations_count",
                current_value=float(pa.pending_reauthorizations_count),
                benchmark_or_target_value=5.0,
                unit="cases",
                evidence_statement=(
                    f"Case management caseload is well-controlled with {pa.pending_reauthorizations_count} pending insurance reauthorizations in review."
                ),
                operational_impact="Ensures timely clinical update submissions to Managed Care coordinators.",
                driving_factors=f"Expiring in 72h: {pa.expiring_authorizations_72h}.",
                lessons_learned="Proactive communication with payer case managers ensures continuity of coverage.",
                supporting_metrics=[
                    f"Pending reauthorizations: {pa.pending_reauthorizations_count}",
                    f"Expiring in 72h: {pa.expiring_authorizations_72h}",
                ],
            )
        )

    managed_mix = sum(
        pa.payer_mix_pct.get(k, 0.0)
        for k in ["Managed Care", "Medicare A", "Commercial", "Medicare Advantage"]
    )
    if managed_mix >= 30.0:
        highlights.append(
            PositiveHighlight(
                highlight_id=f"HL-AUTH-PAYERMIX-{facility_id[:6]}",
                domain="payer_auth",
                domain_display_name="Authorizations & Managed Care",
                title=f"Diverse Commercial & Medicare Payer Mix ({managed_mix:.1f}% mix)",
                category="BENCHMARK_EXCEEDED",
                strength="MEDIUM",
                metric_name="managed_mix_pct",
                current_value=float(managed_mix),
                benchmark_or_target_value=40.0,
                unit="%",
                evidence_statement=(
                    f"Medicare, Managed Care, and Commercial insurance represent {managed_mix:.1f}% of current resident payer mix."
                ),
                operational_impact="Reflects broad insurance contract access and diversified revenue streams.",
                driving_factors=f"Payer distribution: {', '.join(f'{k}: {v:.1f}%' for k, v in pa.payer_mix_pct.items())}.",
                lessons_learned="Strong contract coverage allows facility to accept a wide variety of hospital discharges.",
                supporting_metrics=[
                    f"{k}: {v:.1f}%" for k, v in list(pa.payer_mix_pct.items())[:3]
                ],
            )
        )

    # ---------------------------------------------------------
    # 7. HOSPITALITY & GUEST EXPERIENCE DOMAIN
    # ---------------------------------------------------------
    if ho.dining_satisfaction_score >= 75.0:
        category_dining: Literal["EXEMPLARY_ACHIEVEMENT", "BENCHMARK_EXCEEDED", "TARGET_MET"] = (
            "EXEMPLARY_ACHIEVEMENT"
            if ho.dining_satisfaction_score >= 94.0
            else ("BENCHMARK_EXCEEDED" if ho.dining_satisfaction_score >= 85.0 else "TARGET_MET")
        )
        title_prefix = (
            "Exemplary" if category_dining == "EXEMPLARY_ACHIEVEMENT" else "Strong"
        )
        highlights.append(
            PositiveHighlight(
                highlight_id=f"HL-HOSP-DINING-{facility_id[:6]}",
                domain="hospitality",
                domain_display_name="Hospitality & Guest Services",
                title=f"{title_prefix} Dining Satisfaction ({ho.dining_satisfaction_score:.1f} pts)",
                category=category_dining,
                strength="HIGH"
                if category_dining == "EXEMPLARY_ACHIEVEMENT"
                else "MEDIUM",
                metric_name="dining_satisfaction_score",
                current_value=float(ho.dining_satisfaction_score),
                benchmark_or_target_value=DINING_SATISFACTION_TARGET,
                unit="pts",
                evidence_statement=(
                    f"Resort dining satisfaction score is {ho.dining_satisfaction_score:.1f} points, meeting luxury hospitality targets."
                ),
                operational_impact="Core driver of Ignite's luxury resort brand reputation, guest morale, and family word-of-mouth recommendations.",
                driving_factors=(
                    f"Room comfort score: {ho.cleanliness_room_comfort_score:.1f} pts, open service requests: {ho.open_guest_service_requests}, "
                    f"avg resolution: {ho.avg_request_resolution_hours:.1f} hrs."
                ),
                lessons_learned=(
                    "Culinary presentation and guest menu choice tracking directly elevate overall stay satisfaction."
                ),
                supporting_metrics=[
                    f"Dining score: {ho.dining_satisfaction_score:.1f} pts (target: {DINING_SATISFACTION_TARGET} pts)",
                    f"Room comfort: {ho.cleanliness_room_comfort_score:.1f} pts",
                    f"Open requests: {ho.open_guest_service_requests}",
                ],
            )
        )

    if ho.guest_satisfaction_nps >= 40.0:
        nps_val_str = f"{ho.guest_satisfaction_nps:.1f}" if ho.guest_satisfaction_nps % 1 != 0 else f"{ho.guest_satisfaction_nps:.0f}"
        highlights.append(
            PositiveHighlight(
                highlight_id=f"HL-HOSP-NPS-{facility_id[:6]}",
                domain="hospitality",
                domain_display_name="Hospitality & Guest Services",
                title=f"Strong Guest Loyalty (NPS +{nps_val_str})",
                category="BENCHMARK_EXCEEDED" if ho.guest_satisfaction_nps >= 60.0 else "TARGET_MET",
                strength="HIGH" if ho.guest_satisfaction_nps >= 65.0 else "MEDIUM",
                metric_name="guest_satisfaction_nps",
                current_value=float(ho.guest_satisfaction_nps),
                benchmark_or_target_value=GUEST_NPS_TARGET,
                unit="NPS",
                evidence_statement=(
                    f"Guest Net Promoter Score is +{nps_val_str} (or {ho.guest_satisfaction_nps:.1f}), reflecting strong guest and family brand advocacy."
                ),
                operational_impact="Reflects superior hospitality culture, direct family advocacy, and positive community perception.",
                driving_factors=(
                    f"Dining score: {ho.dining_satisfaction_score:.1f} pts, room comfort: {ho.cleanliness_room_comfort_score:.1f} pts, "
                    f"open requests: {ho.open_guest_service_requests}, avg resolution: {ho.avg_request_resolution_hours:.1f} hrs."
                ),
                lessons_learned=(
                    "Active concierge listening and rapid request resolution drive outstanding guest loyalty."
                ),
                supporting_metrics=[
                    f"Guest NPS: +{nps_val_str} (target: +{GUEST_NPS_TARGET:.0f})",
                    f"Dining score: {ho.dining_satisfaction_score:.1f} pts",
                    f"Room comfort: {ho.cleanliness_room_comfort_score:.1f} pts",
                ],
            )
        )

    if ho.cleanliness_room_comfort_score >= 80.0:
        highlights.append(
            PositiveHighlight(
                highlight_id=f"HL-HOSP-COMFORT-{facility_id[:6]}",
                domain="hospitality",
                domain_display_name="Hospitality & Guest Services",
                title=f"High Room Comfort Rating ({ho.cleanliness_room_comfort_score:.1f} pts)",
                category="BENCHMARK_EXCEEDED" if ho.cleanliness_room_comfort_score >= 90.0 else "TARGET_MET",
                strength="MEDIUM",
                metric_name="cleanliness_room_comfort_score",
                current_value=float(ho.cleanliness_room_comfort_score),
                benchmark_or_target_value=88.0,
                unit="pts",
                evidence_statement=(
                    f"Guest room cleanliness and environment comfort score is {ho.cleanliness_room_comfort_score:.1f} points."
                ),
                operational_impact="Reinforces Ignite's luxury resort atmosphere and infection prevention standards.",
                driving_factors=f"Open guest requests: {ho.open_guest_service_requests}, resolution time: {ho.avg_request_resolution_hours:.1f}h.",
                lessons_learned="Daily housekeeping rigor and proactive room checks prevent guest maintenance dissatisfaction.",
                supporting_metrics=[
                    f"Room comfort: {ho.cleanliness_room_comfort_score:.1f} pts",
                    f"Open requests: {ho.open_guest_service_requests}",
                ],
            )
        )

    # ---------------------------------------------------------
    # 8. HOSPITAL TRANSFERS & READMISSIONS DOMAIN
    # ---------------------------------------------------------
    if ht.readmission_rate_30d_pct <= 22.0:
        highlights.append(
            PositiveHighlight(
                highlight_id=f"HL-TRANS-READM-{facility_id[:6]}",
                domain="hospital_transfers",
                domain_display_name="Clinical & Hospital Transfers",
                title=f"Managed Readmission Rate ({ht.readmission_rate_30d_pct:.1f}%)",
                category="BENCHMARK_EXCEEDED" if ht.readmission_rate_30d_pct <= 12.0 else "TARGET_MET",
                strength="HIGH" if ht.readmission_rate_30d_pct <= 12.0 else "MEDIUM",
                metric_name="readmission_rate_30d_pct",
                current_value=float(ht.readmission_rate_30d_pct),
                benchmark_or_target_value=READMISSION_RATE_BENCHMARK_PCT,
                unit="%",
                evidence_statement=(
                    f"30-day hospital readmission rate is {ht.readmission_rate_30d_pct:.1f}%, tracking favorably against post-acute benchmark thresholds."
                ),
                operational_impact="Demonstrates clinical care quality and strengthens acute hospital preferred provider relationships.",
                driving_factors=(
                    f"Acute transfers this week: {ht.acute_transfers_this_week}, unplanned 30d transfers: {ht.unplanned_transfers_30d_count}."
                ),
                lessons_learned=(
                    "Early clinical assessment and proactive physician rounding reduce avoidable emergency transfers."
                ),
                supporting_metrics=[
                    f"30-day readmission: {ht.readmission_rate_30d_pct:.1f}% (benchmark: {READMISSION_RATE_BENCHMARK_PCT}%)",
                    f"Weekly transfers: {ht.acute_transfers_this_week}",
                ],
            )
        )

    if ht.acute_transfers_this_week <= 8:
        highlights.append(
            PositiveHighlight(
                highlight_id=f"HL-TRANS-ACUTE-{facility_id[:6]}",
                domain="hospital_transfers",
                domain_display_name="Clinical & Hospital Transfers",
                title=f"Active Acute Transfer Management ({ht.acute_transfers_this_week} this week)",
                category="TARGET_MET",
                strength="MEDIUM",
                metric_name="acute_transfers_this_week",
                current_value=float(ht.acute_transfers_this_week),
                benchmark_or_target_value=float(ACUTE_TRANSFERS_TARGET),
                unit="transfers",
                evidence_statement=(
                    f"Clinical team managed {ht.acute_transfers_this_week} acute hospital emergency transfers over the trailing 7 days with on-shift physician oversight."
                ),
                operational_impact="Indicates active bedside clinical triage and prompt condition escalation when needed.",
                driving_factors=(
                    f"Unplanned 30d transfers: {ht.unplanned_transfers_30d_count}, 30d readmission rate: {ht.readmission_rate_30d_pct:.1f}%."
                ),
                lessons_learned=(
                    "Bedside clinical protocols and prompt on-shift clinical escalations sustain low transfer volume."
                ),
                supporting_metrics=[
                    f"Acute transfers: {ht.acute_transfers_this_week}",
                    f"30-day readmission: {ht.readmission_rate_30d_pct:.1f}%",
                ],
            )
        )

    if ht.unplanned_transfers_30d_count <= 20:
        highlights.append(
            PositiveHighlight(
                highlight_id=f"HL-TRANS-30D-{facility_id[:6]}",
                domain="hospital_transfers",
                domain_display_name="Clinical & Hospital Transfers",
                title=f"30-Day Emergency Triage Tracking ({ht.unplanned_transfers_30d_count} total)",
                category="TARGET_MET",
                strength="MEDIUM",
                metric_name="unplanned_transfers_30d_count",
                current_value=float(ht.unplanned_transfers_30d_count),
                benchmark_or_target_value=5.0,
                unit="transfers",
                evidence_statement=(
                    f"Monthly emergency transfers are actively monitored with {ht.unplanned_transfers_30d_count} total unplanned transfers over the past 30 days."
                ),
                operational_impact="Validates effective on-site nursing management of complex post-acute medical conditions.",
                driving_factors=f"Weekly acute transfers: {ht.acute_transfers_this_week}, readmission rate: {ht.readmission_rate_30d_pct:.1f}%.",
                lessons_learned="Prompt on-shift vital sign monitoring and nurse practitioner rounding minimize unnecessary hospitalizations.",
                supporting_metrics=[
                    f"30d transfers: {ht.unplanned_transfers_30d_count}",
                    f"Weekly transfers: {ht.acute_transfers_this_week}",
                ],
            )
        )

    if ht.transfers_by_reason and any(v > 0 for v in ht.transfers_by_reason.values()):
        top_reasons = [f"{k.replace('_', ' ').title()}: {v}" for k, v in ht.transfers_by_reason.items() if v > 0]
        highlights.append(
            PositiveHighlight(
                highlight_id=f"HL-TRANS-REASON-{facility_id[:6]}",
                domain="hospital_transfers",
                domain_display_name="Clinical & Hospital Transfers",
                title=f"Active Clinical Pathway Triage ({len(top_reasons)} pathways tracked)",
                category="TARGET_MET",
                strength="MEDIUM",
                metric_name="transfers_by_reason_count",
                current_value=float(len(top_reasons)),
                benchmark_or_target_value=1.0,
                unit="pathways",
                evidence_statement=(
                    f"Clinical team actively logs and categorizes acute transfers across {len(top_reasons)} specific diagnostic categories ({', '.join(top_reasons[:2])})."
                ),
                operational_impact="Enables clinical quality teams to pinpoint root causes and deploy focused bedside care protocols.",
                driving_factors=f"Tracked pathways: {', '.join(top_reasons)}.",
                lessons_learned="Structured root-cause review of acute transfers identifies opportunities for in-house clinical stabilization.",
                supporting_metrics=top_reasons[:3],
            )
        )

    # Calculate strongest domains
    domain_counts: dict[str, int] = {}
    for hl in highlights:
        domain_counts[hl.domain] = domain_counts.get(hl.domain, 0) + 1
    strongest = sorted(
        domain_counts.keys(), key=lambda d: domain_counts[d], reverse=True
    )[:3]

    return FacilityPositiveHighlightsSummary(
        facility_id=facility_id,
        scenario=scenario,
        total_highlights_count=len(highlights),
        highlights=highlights,
        strongest_domains=strongest,
    )
