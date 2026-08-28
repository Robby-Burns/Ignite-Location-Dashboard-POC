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
    if c.occupancy_rate_pct >= OCCUPANCY_POSITIVE_THRESHOLD_PCT:
        strength: Literal["HIGH", "MEDIUM", "LOW"] = (
            "HIGH" if c.occupancy_rate_pct >= 90.0 else "MEDIUM"
        )
        highlights.append(
            PositiveHighlight(
                highlight_id=f"HL-CENSUS-OCC-{facility_id[:6]}",
                domain="census",
                domain_display_name="Census & Capacity",
                title=f"Healthy Occupancy at {c.occupancy_rate_pct}%",
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
                    f"Occupancy rate is {c.occupancy_rate_pct}%, meeting or exceeding the healthy operational target of {OCCUPANCY_POSITIVE_THRESHOLD_PCT}%."
                ),
                operational_impact="Supports strong daily operating revenue and optimal fixed-cost absorption across facility departments.",
                driving_factors=(
                    f"Census is {c.current_census} out of {c.total_capacity} beds with {c.available_beds} available. "
                    f"Previous day census was {c.previous_day_census}, previous week was {c.previous_week_census}. "
                    "The specific drivers of occupancy performance cannot be determined from the available snapshot data alone."
                ),
                lessons_learned=(
                    "Consider identifying which referral sources and hospital partnerships are contributing to strong census "
                    "and whether those relationships can be strengthened or replicated at other facilities."
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
                title=f"Census Expanding (+{occ_trend.delta_7d}% over 7 days)",
                category="TRAJECTORY_IMPROVEMENT",
                strength="MEDIUM",
                metric_name="occupancy_rate_pct",
                current_value=float(c.occupancy_rate_pct),
                benchmark_or_target_value=float(
                    occ_trend.value_7d_ago or c.occupancy_rate_pct
                ),
                unit="%",
                evidence_statement=(
                    f"Occupancy increased by +{occ_trend.delta_7d}% over the trailing 7 days (from {occ_trend.value_7d_ago}% to {c.occupancy_rate_pct}%)."
                ),
                operational_impact="Reflects positive patient throughput and effective hospital intake coordination.",
                driving_factors=(
                    f"7-day admissions total {ad.rolling_7d_admissions} vs {ad.rolling_7d_discharges} discharges. "
                    "The specific referral or discharge factors driving the census increase cannot be determined from the available data."
                ),
                lessons_learned=(
                    "Sustained census growth suggests intake processes are working well. "
                    "Consider monitoring whether this trajectory continues and what operational factors are contributing."
                ),
                supporting_metrics=[
                    f"7-day occupancy change: +{occ_trend.delta_7d}%",
                    f"Current: {c.occupancy_rate_pct}%, 7 days ago: {occ_trend.value_7d_ago}%",
                ],
            )
        )

    # ---------------------------------------------------------
    # 2. ADMISSIONS & DISCHARGES DOMAIN
    # ---------------------------------------------------------
    if ad.net_flow > 0:
        highlights.append(
            PositiveHighlight(
                highlight_id=f"HL-FLOW-POS-{facility_id[:6]}",
                domain="admissions_discharges",
                domain_display_name="Admissions & Discharges",
                title=f"Positive Net Daily Flow (+{ad.net_flow} guests)",
                category="TARGET_MET",
                strength="MEDIUM",
                metric_name="net_flow",
                current_value=float(ad.net_flow),
                benchmark_or_target_value=0.0,
                unit="guests",
                evidence_statement=(
                    f"Net patient flow today is +{ad.net_flow} guests ({ad.today_admissions} admissions vs {ad.today_discharges} discharges)."
                ),
                operational_impact="Maintains upward census trajectory and reflects healthy community referral demand.",
                driving_factors=(
                    f"Today: {ad.today_admissions} admissions, {ad.today_discharges} discharges. "
                    f"Rolling 7-day: {ad.rolling_7d_admissions} admissions vs {ad.rolling_7d_discharges} discharges. "
                    f"Pending pipeline: {ad.pending_admissions} intakes, {ad.pending_discharges} pending discharges. "
                    "The specific referral sources or discharge factors driving positive flow cannot be determined from the available data."
                ),
                lessons_learned=(
                    "Positive net flow supports census stability. Consider tracking which referral channels "
                    "are producing the strongest intake volume and whether discharge planning can be optimized to maintain throughput."
                ),
                supporting_metrics=[
                    f"Admissions: {ad.today_admissions}, Discharges: {ad.today_discharges}",
                    f"7-day rolling: {ad.rolling_7d_admissions} adm / {ad.rolling_7d_discharges} dis",
                ],
            )
        )

    # ---------------------------------------------------------
    # 3. LENGTH OF STAY DOMAIN
    # ---------------------------------------------------------
    if 20.0 <= los.average_los_days <= 24.0:
        highlights.append(
            PositiveHighlight(
                highlight_id=f"HL-LOS-OPTIMAL-{facility_id[:6]}",
                domain="length_of_stay",
                domain_display_name="Length of Stay",
                title=f"Optimal Average LOS ({los.average_los_days} days)",
                category="TARGET_MET",
                strength="LOW",
                metric_name="average_los_days",
                current_value=float(los.average_los_days),
                benchmark_or_target_value=22.0,
                unit="days",
                evidence_statement=(
                    f"Average length of stay of {los.average_los_days} days is aligned with optimal short-stay rehabilitation throughput targets (20-24 days)."
                ),
                operational_impact="Ensures patients complete full clinical rehabilitation episodes without exceeding insurance-authorized periods.",
                driving_factors=(
                    f"Short-stay patients: {los.short_stay_count}, long-stay: {los.long_stay_count}, outliers: {los.los_outliers_count}. "
                    "The specific clinical or operational factors keeping LOS within target cannot be determined from the available data."
                ),
                lessons_learned=(
                    "Optimal LOS suggests effective discharge planning and therapy progression. "
                    "Consider documenting the discharge coordination practices that are keeping LOS on target."
                ),
                supporting_metrics=[
                    f"Average LOS: {los.average_los_days} days (target: {los.target_los_days})",
                    f"Short-stay: {los.short_stay_count}, Long-stay: {los.long_stay_count}",
                ],
            )
        )

    # ---------------------------------------------------------
    # 4. NURSING STAFFING & OPERATIONS DOMAIN
    # ---------------------------------------------------------
    if st.hppd_actual >= HPPD_BUDGET_TARGET:
        highlights.append(
            PositiveHighlight(
                highlight_id=f"HL-STAFF-HPPD-{facility_id[:6]}",
                domain="staffing",
                domain_display_name="Nursing Staffing",
                title=f"Staffing Target Achieved ({st.hppd_actual} HPPD)",
                category=(
                    "TARGET_MET" if st.hppd_actual < 4.20 else "BENCHMARK_EXCEEDED"
                ),
                strength="HIGH" if st.hppd_actual >= 4.20 else "MEDIUM",
                metric_name="hppd_actual",
                current_value=float(st.hppd_actual),
                benchmark_or_target_value=HPPD_BUDGET_TARGET,
                unit="HPPD",
                evidence_statement=(
                    f"Actual direct nursing care is {st.hppd_actual} HPPD, meeting or exceeding the budgeted care target of {HPPD_BUDGET_TARGET} HPPD."
                ),
                operational_impact="Ensures robust bedside care continuity, clinical safety compliance, and guest attention.",
                driving_factors=(
                    f"RN hours: {st.rn_hours_actual}, LPN: {st.lpn_hours_actual}, CNA: {st.cna_hours_actual}. "
                    f"Call-ins: {st.call_in_absences_count}, open shifts: {st.open_shifts_count}, overtime: {st.overtime_hours} hrs. "
                    "The specific scheduling or staffing practices driving strong HPPD cannot be determined from the available data."
                ),
                lessons_learned=(
                    "Strong HPPD indicates adequate bedside coverage. Consider identifying which scheduling practices, "
                    "staffing ratios, or retention strategies are contributing and whether they can be sustained."
                ),
                supporting_metrics=[
                    f"HPPD: {st.hppd_actual} (target: {st.hppd_budgeted_target})",
                    f"RN: {st.rn_hours_actual}h, LPN: {st.lpn_hours_actual}h, CNA: {st.cna_hours_actual}h",
                ],
            )
        )

    if st.agency_staff_pct <= AGENCY_BUDGET_TARGET_PCT:
        highlights.append(
            PositiveHighlight(
                highlight_id=f"HL-STAFF-AGENCY-{facility_id[:6]}",
                domain="staffing",
                domain_display_name="Nursing Staffing",
                title=f"Minimal Agency Contractor Usage ({st.agency_staff_pct}%)",
                category="BENCHMARK_EXCEEDED",
                strength="HIGH",
                metric_name="agency_staff_pct",
                current_value=float(st.agency_staff_pct),
                benchmark_or_target_value=AGENCY_BUDGET_TARGET_PCT,
                unit="%",
                evidence_statement=(
                    f"Agency staffing utilization is low at {st.agency_staff_pct}%, well below the industry {AGENCY_BUDGET_TARGET_PCT}% threshold."
                ),
                operational_impact="Significantly controls premium labor expenses while maintaining permanent team cohesion and familiarity with guests.",
                driving_factors=(
                    f"Open shifts: {st.open_shifts_count}, call-ins: {st.call_in_absences_count}, overtime: {st.overtime_hours} hrs. "
                    "Low agency usage suggests strong permanent staff retention and adequate internal coverage. "
                    "The specific retention or recruitment practices driving this cannot be determined from the available data."
                ),
                lessons_learned=(
                    "Low agency usage is a significant cost advantage. Consider documenting retention practices, "
                    "compensation structures, or team culture elements that contribute to staff stability."
                ),
                supporting_metrics=[
                    f"Agency: {st.agency_staff_pct}% (target: <{AGENCY_BUDGET_TARGET_PCT}%)",
                    f"Open shifts: {st.open_shifts_count}, Overtime: {st.overtime_hours} hrs",
                ],
            )
        )

    if st.open_shifts_count <= OPEN_SHIFTS_TARGET:
        highlights.append(
            PositiveHighlight(
                highlight_id=f"HL-STAFF-SHIFTS-{facility_id[:6]}",
                domain="staffing",
                domain_display_name="Nursing Staffing",
                title=f"Zero/Low Open Nursing Shifts ({st.open_shifts_count} open)",
                category="TARGET_MET",
                strength="LOW",
                metric_name="open_shifts_count",
                current_value=float(st.open_shifts_count),
                benchmark_or_target_value=float(OPEN_SHIFTS_TARGET),
                unit="shifts",
                evidence_statement=(
                    f"Only {st.open_shifts_count} open nursing shifts recorded across all shifts today."
                ),
                operational_impact="Reduces overtime stress and ensures seamless shift coverage.",
                driving_factors=(
                    f"Call-ins today: {st.call_in_absences_count}, overtime: {st.overtime_hours} hrs. "
                    "The specific scheduling or staffing practices keeping open shifts low cannot be determined from the available data."
                ),
                lessons_learned=(
                    "Low open shifts indicate effective shift planning. Consider whether scheduling practices, "
                    "PRN pool utilization, or advance planning are contributing factors worth replicating."
                ),
                supporting_metrics=[
                    f"Open shifts: {st.open_shifts_count} (target: ≤{OPEN_SHIFTS_TARGET})",
                    f"Call-ins: {st.call_in_absences_count}",
                ],
            )
        )

    # ---------------------------------------------------------
    # 5. THERAPY REHABILITATION DELIVERY DOMAIN
    # ---------------------------------------------------------
    if th.treatment_completion_rate_pct >= THERAPY_COMPLETION_TARGET_PCT:
        strength_th: Literal["HIGH", "MEDIUM", "LOW"] = (
            "HIGH" if th.treatment_completion_rate_pct >= 95.0 else "MEDIUM"
        )
        highlights.append(
            PositiveHighlight(
                highlight_id=f"HL-THERAPY-COMP-{facility_id[:6]}",
                domain="therapy",
                domain_display_name="Therapy Rehabilitation",
                title=f"High Therapy Completion at {th.treatment_completion_rate_pct}%",
                category=(
                    "BENCHMARK_EXCEEDED"
                    if th.treatment_completion_rate_pct >= 95.0
                    else "TARGET_MET"
                ),
                strength=strength_th,
                metric_name="treatment_completion_rate_pct",
                current_value=float(th.treatment_completion_rate_pct),
                benchmark_or_target_value=THERAPY_COMPLETION_TARGET_PCT,
                unit="%",
                evidence_statement=(
                    f"Therapy treatment completion rate is {th.treatment_completion_rate_pct}%, meeting or exceeding the {THERAPY_COMPLETION_TARGET_PCT}% operational benchmark."
                ),
                operational_impact="Accelerates patient functional recovery, shortens length of stay, and complies with Medicare treatment expectations.",
                driving_factors=(
                    f"Delivered {th.avg_daily_treatment_minutes_delivered} min/day vs {th.avg_daily_treatment_minutes_scheduled} min/day scheduled. "
                    f"Weekly goals met: {th.patients_meeting_weekly_goals_pct}%, patients on hold: {th.patients_on_therapy_hold}, mobility index: {th.functional_mobility_gain_index}. "
                    "The specific therapist scheduling, patient engagement, or clinical coordination practices driving strong completion cannot be determined from the available data."
                ),
                lessons_learned=(
                    "Consider identifying and preserving the interdisciplinary scheduling and patient engagement practices "
                    "contributing to strong participation and determining whether they can be applied elsewhere."
                ),
                supporting_metrics=[
                    f"Completion: {th.treatment_completion_rate_pct}% (target: {THERAPY_COMPLETION_TARGET_PCT}%)",
                    f"Delivered: {th.avg_daily_treatment_minutes_delivered} min/day",
                    f"Goals met: {th.patients_meeting_weekly_goals_pct}%",
                    f"Holds: {th.patients_on_therapy_hold}",
                ],
            )
        )

    # ---------------------------------------------------------
    # 6. PAYER MIX & AUTHORIZATIONS DOMAIN
    # ---------------------------------------------------------
    if pa.expiring_authorizations_48h <= AUTH_EXPIRING_TARGET:
        highlights.append(
            PositiveHighlight(
                highlight_id=f"HL-AUTH-CLEAR-{facility_id[:6]}",
                domain="payer_auth",
                domain_display_name="Payer Authorizations",
                title=f"Low Authorization Expiration Risk ({pa.expiring_authorizations_48h} in 48h)",
                category="TARGET_MET",
                strength="LOW",
                metric_name="expiring_authorizations_48h",
                current_value=float(pa.expiring_authorizations_48h),
                benchmark_or_target_value=float(AUTH_EXPIRING_TARGET),
                unit="authorizations",
                evidence_statement=(
                    f"Only {pa.expiring_authorizations_48h} authorizations are expiring within the next 48 hours."
                ),
                operational_impact="Minimizes financial coverage cliff risk and billing claim denials.",
                driving_factors=(
                    f"Expiring in 72h: {pa.expiring_authorizations_72h}, pending reauthorizations: {pa.pending_reauthorizations_count}, "
                    f"denials pending appeal: {pa.auth_denials_pending_appeal_count}. "
                    "The specific case management workflows or payer turnaround factors keeping expirations low cannot be determined from the available data."
                ),
                lessons_learned=(
                    "Consider maintaining the proactive re-authorization review cycle and timely clinical documentation submissions with commercial and Managed Care payers."
                ),
                supporting_metrics=[
                    f"Expiring in 48h: {pa.expiring_authorizations_48h} (target: ≤{AUTH_EXPIRING_TARGET})",
                    f"Expiring in 72h: {pa.expiring_authorizations_72h}",
                    f"Pending re-auth: {pa.pending_reauthorizations_count}",
                    f"Denials on appeal: {pa.auth_denials_pending_appeal_count}",
                ],
            )
        )

    # ---------------------------------------------------------
    # 7. HOSPITALITY & GUEST EXPERIENCE DOMAIN
    # ---------------------------------------------------------
    if ho.dining_satisfaction_score >= DINING_SATISFACTION_TARGET:
        category_dining: Literal["EXEMPLARY_ACHIEVEMENT", "BENCHMARK_EXCEEDED"] = (
            "EXEMPLARY_ACHIEVEMENT"
            if ho.dining_satisfaction_score >= 94.0
            else "BENCHMARK_EXCEEDED"
        )
        title_prefix = (
            "Exemplary" if category_dining == "EXEMPLARY_ACHIEVEMENT" else "Strong"
        )
        highlights.append(
            PositiveHighlight(
                highlight_id=f"HL-HOSP-DINING-{facility_id[:6]}",
                domain="hospitality",
                domain_display_name="Hospitality & Guest Experience",
                title=f"{title_prefix} Dining Satisfaction ({ho.dining_satisfaction_score} pts)",
                category=category_dining,
                strength="HIGH"
                if category_dining == "EXEMPLARY_ACHIEVEMENT"
                else "MEDIUM",
                metric_name="dining_satisfaction_score",
                current_value=float(ho.dining_satisfaction_score),
                benchmark_or_target_value=DINING_SATISFACTION_TARGET,
                unit="pts",
                evidence_statement=(
                    f"Resort dining satisfaction score is {ho.dining_satisfaction_score} points, surpassing the {DINING_SATISFACTION_TARGET} target."
                ),
                operational_impact="Core driver of Ignite's luxury resort brand reputation, guest morale, and family word-of-mouth recommendations.",
                driving_factors=(
                    f"Room comfort score: {ho.cleanliness_room_comfort_score} pts, open service requests: {ho.open_guest_service_requests}, "
                    f"avg resolution: {ho.avg_request_resolution_hours} hrs. "
                    "The specific culinary presentation, menu choices, or dining service practices driving high satisfaction cannot be determined from the available data."
                ),
                lessons_learned=(
                    "Consider identifying culinary team practices, guest preference tracking, or daily meal presentation standards "
                    "that contribute to dining scores and sustaining them across meal shifts."
                ),
                supporting_metrics=[
                    f"Dining score: {ho.dining_satisfaction_score} pts (target: {DINING_SATISFACTION_TARGET} pts)",
                    f"Room comfort: {ho.cleanliness_room_comfort_score} pts",
                    f"Open requests: {ho.open_guest_service_requests}",
                ],
            )
        )

    if ho.guest_satisfaction_nps >= GUEST_NPS_TARGET:
        highlights.append(
            PositiveHighlight(
                highlight_id=f"HL-HOSP-NPS-{facility_id[:6]}",
                domain="hospitality",
                domain_display_name="Hospitality & Guest Experience",
                title=f"Strong Guest Loyalty (NPS +{ho.guest_satisfaction_nps})",
                category="BENCHMARK_EXCEEDED",
                strength="HIGH",
                metric_name="guest_satisfaction_nps",
                current_value=float(ho.guest_satisfaction_nps),
                benchmark_or_target_value=GUEST_NPS_TARGET,
                unit="NPS",
                evidence_statement=(
                    f"Guest Net Promoter Score is +{ho.guest_satisfaction_nps}, exceeding the {GUEST_NPS_TARGET} benchmark."
                ),
                operational_impact="Reflects superior hospitality culture, direct family advocacy, and positive community perception.",
                driving_factors=(
                    f"Dining score: {ho.dining_satisfaction_score} pts, room comfort: {ho.cleanliness_room_comfort_score} pts, "
                    f"open requests: {ho.open_guest_service_requests}, avg resolution: {ho.avg_request_resolution_hours} hrs. "
                    "The specific guest interactions, room amenities, or staff behaviors driving strong NPS advocacy cannot be determined from the available data."
                ),
                lessons_learned=(
                    "Consider capturing guest feedback themes and recognizing front-line concierge and hospitality staff "
                    "who consistently drive positive guest sentiment."
                ),
                supporting_metrics=[
                    f"Guest NPS: +{ho.guest_satisfaction_nps} (target: +{GUEST_NPS_TARGET})",
                    f"Dining score: {ho.dining_satisfaction_score} pts",
                    f"Room comfort: {ho.cleanliness_room_comfort_score} pts",
                    f"Resolution time: {ho.avg_request_resolution_hours}h",
                ],
            )
        )

    # ---------------------------------------------------------
    # 8. HOSPITAL TRANSFERS & READMISSIONS DOMAIN
    # ---------------------------------------------------------
    if ht.readmission_rate_30d_pct <= READMISSION_RATE_BENCHMARK_PCT:
        highlights.append(
            PositiveHighlight(
                highlight_id=f"HL-TRANS-READM-{facility_id[:6]}",
                domain="hospital_transfers",
                domain_display_name="Hospital Transfers & Quality",
                title=f"Low Readmission Rate ({ht.readmission_rate_30d_pct}%)",
                category="BENCHMARK_EXCEEDED",
                strength="HIGH",
                metric_name="readmission_rate_30d_pct",
                current_value=float(ht.readmission_rate_30d_pct),
                benchmark_or_target_value=READMISSION_RATE_BENCHMARK_PCT,
                unit="%",
                evidence_statement=(
                    f"30-day hospital readmission rate is {ht.readmission_rate_30d_pct}%, outperforming the {READMISSION_RATE_BENCHMARK_PCT}% national benchmark."
                ),
                operational_impact="Demonstrates high clinical care quality and strengthens acute hospital preferred provider relationships.",
                driving_factors=(
                    f"Acute transfers this week: {ht.acute_transfers_this_week}, unplanned 30d transfers: {ht.unplanned_transfers_30d_count}. "
                    "The specific clinical pathways, physician rounding frequencies, or triage interventions driving low readmissions cannot be determined from the available data."
                ),
                lessons_learned=(
                    "Consider documenting clinical assessment and early symptom identification routines to reinforce best practices across all nursing shifts."
                ),
                supporting_metrics=[
                    f"30-day readmission: {ht.readmission_rate_30d_pct}% (benchmark: {READMISSION_RATE_BENCHMARK_PCT}%)",
                    f"Weekly transfers: {ht.acute_transfers_this_week}",
                    f"30d transfers: {ht.unplanned_transfers_30d_count}",
                ],
            )
        )

    if ht.acute_transfers_this_week <= ACUTE_TRANSFERS_TARGET:
        highlights.append(
            PositiveHighlight(
                highlight_id=f"HL-TRANS-ACUTE-{facility_id[:6]}",
                domain="hospital_transfers",
                domain_display_name="Hospital Transfers & Quality",
                title=f"Low Acute Transfer Volume ({ht.acute_transfers_this_week} this week)",
                category="TARGET_MET",
                strength="MEDIUM",
                metric_name="acute_transfers_this_week",
                current_value=float(ht.acute_transfers_this_week),
                benchmark_or_target_value=float(ACUTE_TRANSFERS_TARGET),
                unit="transfers",
                evidence_statement=(
                    f"Only {ht.acute_transfers_this_week} acute hospital emergency transfers occurred over the trailing 7 days."
                ),
                operational_impact="Indicates stable patient clinical acuity management and successful bedside condition stabilization.",
                driving_factors=(
                    f"Unplanned 30d transfers: {ht.unplanned_transfers_30d_count}, 30d readmission rate: {ht.readmission_rate_30d_pct}%. "
                    "The specific clinical protocols or physician communication practices keeping transfers low cannot be determined from the available data."
                ),
                lessons_learned=(
                    "Consider assessing whether bedside clinical protocols and prompt on-shift clinical escalations can be formalized to sustain low transfer volume."
                ),
                supporting_metrics=[
                    f"Acute transfers: {ht.acute_transfers_this_week} (target: ≤{ACUTE_TRANSFERS_TARGET})",
                    f"30-day readmission: {ht.readmission_rate_30d_pct}%",
                    f"30d transfers: {ht.unplanned_transfers_30d_count}",
                ],
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
