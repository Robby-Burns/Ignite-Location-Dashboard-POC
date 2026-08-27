"""Deterministic calculation engine for facility operational indicators.

Strictly adheres to:
- FR-006: Numerical outputs are accurate and traceable.
- INV-002: Numbers trace to source or calculation; no invented calculations.
- INV-007: Uses historical context when available.
"""

from __future__ import annotations

from src.analytics.schemas import (
    CrossDomainCorrelation,
    DomainCalculationSummary,
    FacilityCalculations,
    MetricObservation,
)
from src.models.facility import DailyFacilitySnapshot, FacilityHistoricalSeries

# --- Operational Benchmark Constants (Documented Thresholds) ---
DEFAULT_BUDGET_CENSUS: float = 90.0
OCCUPANCY_POSITIVE_THRESHOLD_PCT: float = 85.0
OCCUPANCY_ATTENTION_THRESHOLD_PCT: float = 75.0

LOS_OUTLIER_ATTENTION_COUNT: int = 10

HPPD_CRITICAL_DEFICIT: float = 0.3
OPEN_SHIFTS_CRITICAL_COUNT: int = 5
AGENCY_BUDGET_TARGET_PCT: float = 5.0
AGENCY_ATTENTION_THRESHOLD_PCT: float = 15.0

THERAPY_COMPLETION_TARGET_PCT: float = 95.0
THERAPY_COMPLETION_ATTENTION_PCT: float = 90.0
THERAPY_COMPLETION_CRITICAL_PCT: float = 85.0

AUTH_EXPIRING_CRITICAL_COUNT: int = 4

DINING_SATISFACTION_TARGET: float = 90.0
DINING_SATISFACTION_ATTENTION: float = 85.0
GUEST_NPS_TARGET: float = 60.0
GUEST_NPS_ATTENTION: float = 55.0

READMISSION_RATE_BENCHMARK_PCT: float = 12.0
READMISSION_RATE_CRITICAL_PCT: float = 18.0
ACUTE_TRANSFERS_WEEK_BASELINE_TARGET: float = 2.0
ACUTE_TRANSFERS_WEEK_ATTENTION_COUNT: int = 3
ACUTE_TRANSFERS_WEEK_CRITICAL_COUNT: int = 4


def calculate_facility_metrics(
    snapshot: DailyFacilitySnapshot,
    history: FacilityHistoricalSeries | None = None,
    scenario: str = "baseline",
) -> FacilityCalculations:
    """Perform deterministic mathematical analysis on facility snapshot and history."""
    domains: dict[str, DomainCalculationSummary] = {}
    correlations: list[CrossDomainCorrelation] = []

    # 1. Census & Occupancy Domain
    census_metrics: dict[str, MetricObservation] = {}
    c = snapshot.census
    target_census = c.budgeted_target_census or DEFAULT_BUDGET_CENSUS
    census_delta_target = round(c.current_census - target_census, 1)
    census_delta_prev_day = (
        round(c.current_census - c.previous_day_census, 1)
        if c.previous_day_census
        else None
    )
    census_delta_prev_week = (
        round(c.current_census - c.previous_week_census, 1)
        if c.previous_week_census
        else None
    )

    census_trend = "STABLE"
    if census_delta_prev_week is not None:
        if census_delta_prev_week > 1.0:
            census_trend = "UP"
        elif census_delta_prev_week < -1.0:
            census_trend = "DOWN"

    census_status = (
        "POSITIVE"
        if c.occupancy_rate_pct >= OCCUPANCY_POSITIVE_THRESHOLD_PCT
        else (
            "ATTENTION"
            if c.occupancy_rate_pct < OCCUPANCY_ATTENTION_THRESHOLD_PCT
            else "NEUTRAL"
        )
    )

    census_metrics["current_census"] = MetricObservation(
        metric_name="current_census",
        display_name="Current Census",
        value=float(c.current_census),
        unit="guests",
        target_or_budget=target_census,
        delta_vs_target=census_delta_target,
        delta_vs_prev_day=census_delta_prev_day,
        delta_vs_prev_week=census_delta_prev_week,
        trend_direction=census_trend,
        status=census_status,
    )
    census_metrics["occupancy_rate_pct"] = MetricObservation(
        metric_name="occupancy_rate_pct",
        display_name="Occupancy Rate",
        value=c.occupancy_rate_pct,
        unit="%",
        target_or_budget=OCCUPANCY_POSITIVE_THRESHOLD_PCT,
        delta_vs_target=round(
            c.occupancy_rate_pct - OCCUPANCY_POSITIVE_THRESHOLD_PCT, 1
        ),
        trend_direction=census_trend,
        status=census_status,
    )
    census_metrics["available_beds"] = MetricObservation(
        metric_name="available_beds",
        display_name="Available Beds",
        value=float(c.available_beds),
        unit="beds",
        status="NEUTRAL" if c.available_beds > 5 else "ATTENTION",
    )

    census_findings = [
        f"Facility census is {c.current_census} guests across {c.total_capacity} beds ({c.occupancy_rate_pct}% occupancy).",
        f"Variance against budgeted target ({target_census} guests) is {census_delta_target:+} guests.",
    ]
    if census_delta_prev_week is not None:
        census_findings.append(
            f"7-day census change is {census_delta_prev_week:+} guests."
        )

    domains["census"] = DomainCalculationSummary(
        domain="census",
        domain_display_name="Census & Occupancy",
        metrics=census_metrics,
        key_findings=census_findings,
        risk_level="HIGH"
        if c.occupancy_rate_pct < OCCUPANCY_ATTENTION_THRESHOLD_PCT - 5.0
        else (
            "MEDIUM"
            if c.occupancy_rate_pct < OCCUPANCY_POSITIVE_THRESHOLD_PCT - 5.0
            else "LOW"
        ),
    )

    # 2. Admissions & Discharges
    ad = snapshot.admissions_discharges
    ad_metrics: dict[str, MetricObservation] = {}
    ad_metrics["today_admissions"] = MetricObservation(
        metric_name="today_admissions",
        display_name="Today Admissions",
        value=float(ad.today_admissions),
        unit="admissions",
        status="POSITIVE" if ad.today_admissions >= 3 else "NEUTRAL",
    )
    ad_metrics["today_discharges"] = MetricObservation(
        metric_name="today_discharges",
        display_name="Today Discharges",
        value=float(ad.today_discharges),
        unit="discharges",
        status="NEUTRAL",
    )
    ad_metrics["net_flow"] = MetricObservation(
        metric_name="net_flow",
        display_name="Net Daily Census Flow",
        value=float(ad.net_flow),
        unit="guests",
        status="POSITIVE"
        if ad.net_flow > 0
        else ("ATTENTION" if ad.net_flow < 0 else "NEUTRAL"),
    )
    domains["admissions_discharges"] = DomainCalculationSummary(
        domain="admissions_discharges",
        domain_display_name="Admissions & Discharges Flow",
        metrics=ad_metrics,
        key_findings=[
            f"Daily throughput: {ad.today_admissions} admissions and {ad.today_discharges} discharges (net flow: {ad.net_flow:+}).",
            f"Pipeline: {ad.pending_admissions} pending intakes and {ad.pending_discharges} pending discharges.",
            f"Rolling 7-day volume: {ad.rolling_7d_admissions} admissions vs {ad.rolling_7d_discharges} discharges.",
        ],
        risk_level="MEDIUM"
        if ad.rolling_7d_discharges > ad.rolling_7d_admissions + 5
        else "LOW",
    )

    # 3. Length of Stay (LOS)
    los = snapshot.length_of_stay
    los_metrics: dict[str, MetricObservation] = {}
    los_variance = round(los.average_los_days - los.target_los_days, 1)
    los_metrics["average_los_days"] = MetricObservation(
        metric_name="average_los_days",
        display_name="Average Length of Stay",
        value=los.average_los_days,
        unit="days",
        target_or_budget=los.target_los_days,
        delta_vs_target=los_variance,
        status="ATTENTION" if los_variance > 3.0 else "POSITIVE",
    )
    domains["length_of_stay"] = DomainCalculationSummary(
        domain="length_of_stay",
        domain_display_name="Length of Stay (LOS)",
        metrics=los_metrics,
        key_findings=[
            f"Average LOS is {los.average_los_days} days vs {los.target_los_days} day target (variance: {los_variance:+} days).",
            f"Guest mix: {los.short_stay_count} short-stay guests (<21d) and {los.long_stay_count} extended stay guests.",
            f"Outliers: {los.los_outliers_count} guests exceeding length of stay threshold.",
        ],
        risk_level="MEDIUM" if los.los_outliers_count > 5 else "LOW",
    )

    # 4. Nursing Staffing & Shift Operations
    st = snapshot.staffing
    st_metrics: dict[str, MetricObservation] = {}
    hppd_delta = round(st.hppd_actual - st.hppd_budgeted_target, 2)
    st_status = (
        "CRITICAL"
        if st.hppd_actual < (st.hppd_budgeted_target - 0.3)
        else (
            "ATTENTION"
            if st.open_shifts_count > 3 or st.call_in_absences_count > 2
            else "POSITIVE"
        )
    )
    st_risk = (
        "HIGH"
        if st_status == "CRITICAL"
        else ("MEDIUM" if st_status == "ATTENTION" else "LOW")
    )

    st_metrics["hppd_actual"] = MetricObservation(
        metric_name="hppd_actual",
        display_name="Nursing HPPD Actual",
        value=st.hppd_actual,
        unit="hours/patient-day",
        target_or_budget=st.hppd_budgeted_target,
        delta_vs_target=hppd_delta,
        status="CRITICAL"
        if hppd_delta < -0.3
        else ("ATTENTION" if hppd_delta < 0 else "POSITIVE"),
    )
    st_metrics["open_shifts_count"] = MetricObservation(
        metric_name="open_shifts_count",
        display_name="Open Shifts",
        value=float(st.open_shifts_count),
        unit="shifts",
        status="CRITICAL"
        if st.open_shifts_count >= 5
        else ("ATTENTION" if st.open_shifts_count > 0 else "POSITIVE"),
    )
    st_metrics["call_in_absences_count"] = MetricObservation(
        metric_name="call_in_absences_count",
        display_name="Call-In Absences",
        value=float(st.call_in_absences_count),
        unit="staff",
        status="ATTENTION" if st.call_in_absences_count > 2 else "POSITIVE",
    )
    st_metrics["agency_staff_pct"] = MetricObservation(
        metric_name="agency_staff_pct",
        display_name="Agency Staffing %",
        value=st.agency_staff_pct,
        unit="%",
        target_or_budget=AGENCY_BUDGET_TARGET_PCT,
        delta_vs_target=round(st.agency_staff_pct - AGENCY_BUDGET_TARGET_PCT, 1),
        status="ATTENTION"
        if st.agency_staff_pct > AGENCY_ATTENTION_THRESHOLD_PCT
        else "POSITIVE",
    )

    domains["staffing"] = DomainCalculationSummary(
        domain="staffing",
        domain_display_name="Nursing Staffing & Shift Operations",
        metrics=st_metrics,
        key_findings=[
            f"Nursing HPPD delivered is {st.hppd_actual} vs budgeted {st.hppd_budgeted_target} target (variance: {hppd_delta:+} HPPD).",
            f"Shift disruptions: {st.call_in_absences_count} unplanned call-ins and {st.open_shifts_count} open shifts.",
            f"Overtime & Agency: {st.overtime_hours} overtime hours logged; agency utilization at {st.agency_staff_pct}%.",
        ],
        risk_level=st_risk,
    )

    # 5. Therapy Participation & Delivery
    th = snapshot.therapy
    th_metrics: dict[str, MetricObservation] = {}
    minutes_variance = round(
        th.avg_daily_treatment_minutes_delivered
        - th.avg_daily_treatment_minutes_scheduled,
        1,
    )
    th_status = (
        "CRITICAL"
        if th.treatment_completion_rate_pct < THERAPY_COMPLETION_CRITICAL_PCT
        else (
            "ATTENTION"
            if th.treatment_completion_rate_pct < THERAPY_COMPLETION_ATTENTION_PCT
            else "POSITIVE"
        )
    )
    th_risk = (
        "HIGH"
        if th.treatment_completion_rate_pct < THERAPY_COMPLETION_CRITICAL_PCT
        else (
            "MEDIUM"
            if th.treatment_completion_rate_pct < THERAPY_COMPLETION_ATTENTION_PCT
            else "LOW"
        )
    )

    th_metrics["treatment_completion_rate_pct"] = MetricObservation(
        metric_name="treatment_completion_rate_pct",
        display_name="Therapy Treatment Completion",
        value=th.treatment_completion_rate_pct,
        unit="%",
        target_or_budget=THERAPY_COMPLETION_TARGET_PCT,
        delta_vs_target=round(
            th.treatment_completion_rate_pct - THERAPY_COMPLETION_TARGET_PCT, 1
        ),
        status=th_status,
    )
    th_metrics["avg_daily_treatment_minutes_delivered"] = MetricObservation(
        metric_name="avg_daily_treatment_minutes_delivered",
        display_name="Delivered Therapy Minutes",
        value=th.avg_daily_treatment_minutes_delivered,
        unit="minutes/patient",
        target_or_budget=th.avg_daily_treatment_minutes_scheduled,
        delta_vs_target=minutes_variance,
        status="POSITIVE" if minutes_variance >= 0 else "ATTENTION",
    )
    domains["therapy"] = DomainCalculationSummary(
        domain="therapy",
        domain_display_name="Therapy Rehabilitation Delivery",
        metrics=th_metrics,
        key_findings=[
            f"Treatment delivery completion rate is {th.treatment_completion_rate_pct}% ({th.avg_daily_treatment_minutes_delivered} delivered vs {th.avg_daily_treatment_minutes_scheduled} scheduled minutes).",
            f"Goal attainment: {th.patients_meeting_weekly_goals_pct}% of guests meeting weekly functional rehabilitation goals.",
            f"Active holds: {th.patients_on_therapy_hold} guests currently on therapy medical hold.",
        ],
        risk_level=th_risk,
    )

    # 6. Payer Mix & Insurance Authorizations
    pa = snapshot.payer_auth
    pa_metrics: dict[str, MetricObservation] = {}
    auth_risk_count = pa.expiring_authorizations_48h + pa.expiring_authorizations_72h
    pa_status = (
        "CRITICAL"
        if pa.expiring_authorizations_48h > AUTH_EXPIRING_CRITICAL_COUNT
        else ("ATTENTION" if auth_risk_count > 3 else "POSITIVE")
    )
    pa_risk = (
        "HIGH"
        if pa.expiring_authorizations_48h > AUTH_EXPIRING_CRITICAL_COUNT
        else ("MEDIUM" if auth_risk_count > 3 else "LOW")
    )

    pa_metrics["expiring_authorizations_48h"] = MetricObservation(
        metric_name="expiring_authorizations_48h",
        display_name="Authorizations Expiring in 48 Hours",
        value=float(pa.expiring_authorizations_48h),
        unit="authorizations",
        status=pa_status,
    )
    pa_metrics["pending_reauthorizations_count"] = MetricObservation(
        metric_name="pending_reauthorizations_count",
        display_name="Pending Re-Authorizations",
        value=float(pa.pending_reauthorizations_count),
        unit="authorizations",
        status="ATTENTION" if pa.pending_reauthorizations_count > 5 else "NEUTRAL",
    )
    domains["payer_auth"] = DomainCalculationSummary(
        domain="payer_auth",
        domain_display_name="Payer Mix & Authorizations",
        metrics=pa_metrics,
        key_findings=[
            f"Authorization cliff: {pa.expiring_authorizations_48h} authorizations expiring within 48h; {pa.expiring_authorizations_72h} within 72h.",
            f"Active appeals / denials: {pa.auth_denials_pending_appeal_count} cases under active appeal.",
            f"Payer distribution: Medicare A ({pa.payer_mix_pct.get('medicare_a', 0)}%), Managed Care ({pa.payer_mix_pct.get('managed_care', 0)}%), Commercial ({pa.payer_mix_pct.get('commercial', 0)}%).",
        ],
        risk_level=pa_risk,
    )

    # 7. Hospitality & Guest Experience
    ho = snapshot.hospitality
    ho_metrics: dict[str, MetricObservation] = {}
    ho_metrics["dining_satisfaction_score"] = MetricObservation(
        metric_name="dining_satisfaction_score",
        display_name="Dining Satisfaction",
        value=ho.dining_satisfaction_score,
        unit="pts",
        target_or_budget=DINING_SATISFACTION_TARGET,
        delta_vs_target=round(
            ho.dining_satisfaction_score - DINING_SATISFACTION_TARGET, 2
        ),
        status="POSITIVE"
        if ho.dining_satisfaction_score >= DINING_SATISFACTION_ATTENTION
        else "ATTENTION",
    )
    ho_metrics["guest_satisfaction_nps"] = MetricObservation(
        metric_name="guest_satisfaction_nps",
        display_name="Guest Experience NPS",
        value=ho.guest_satisfaction_nps,
        unit="NPS",
        target_or_budget=GUEST_NPS_TARGET,
        delta_vs_target=round(ho.guest_satisfaction_nps - GUEST_NPS_TARGET, 1),
        status="POSITIVE"
        if ho.guest_satisfaction_nps >= GUEST_NPS_ATTENTION
        else "ATTENTION",
    )
    domains["hospitality"] = DomainCalculationSummary(
        domain="hospitality",
        domain_display_name="Hospitality & Guest Experience",
        metrics=ho_metrics,
        key_findings=[
            f"Guest sentiment: Dining satisfaction is {ho.dining_satisfaction_score} pts; Room comfort & cleanliness is {ho.cleanliness_room_comfort_score} pts.",
            f"Overall guest Net Promoter Score (NPS) is {ho.guest_satisfaction_nps}.",
            f"Service requests: {ho.open_guest_service_requests} open requests with an average resolution time of {ho.avg_request_resolution_hours} hours.",
        ],
        risk_level="MEDIUM" if ho.open_guest_service_requests > 10 else "LOW",
    )

    # 8. Hospital Transfers & Readmissions
    ht = snapshot.hospital_transfers
    ht_metrics: dict[str, MetricObservation] = {}
    readmission_variance = round(
        ht.readmission_rate_30d_pct - READMISSION_RATE_BENCHMARK_PCT, 1
    )
    ht_status = (
        "CRITICAL"
        if ht.readmission_rate_30d_pct > READMISSION_RATE_CRITICAL_PCT
        or ht.acute_transfers_this_week >= ACUTE_TRANSFERS_WEEK_CRITICAL_COUNT
        else ("ATTENTION" if readmission_variance > 0 else "POSITIVE")
    )
    ht_risk = (
        "HIGH"
        if ht_status == "CRITICAL"
        else ("MEDIUM" if ht_status == "ATTENTION" else "LOW")
    )

    ht_metrics["readmission_rate_30d_pct"] = MetricObservation(
        metric_name="readmission_rate_30d_pct",
        display_name="30-Day Readmission Rate",
        value=ht.readmission_rate_30d_pct,
        unit="%",
        target_or_budget=READMISSION_RATE_BENCHMARK_PCT,
        delta_vs_target=readmission_variance,
        status=ht_status,
    )
    ht_metrics["acute_transfers_this_week"] = MetricObservation(
        metric_name="acute_transfers_this_week",
        display_name="Acute Hospital Transfers (7d)",
        value=float(ht.acute_transfers_this_week),
        unit="transfers",
        status="CRITICAL"
        if ht.acute_transfers_this_week >= ACUTE_TRANSFERS_WEEK_CRITICAL_COUNT
        else ("ATTENTION" if ht.acute_transfers_this_week > 1 else "POSITIVE"),
    )
    domains["hospital_transfers"] = DomainCalculationSummary(
        domain="hospital_transfers",
        domain_display_name="Hospital Transfers & Readmissions",
        metrics=ht_metrics,
        key_findings=[
            f"30-day readmission rate is {ht.readmission_rate_30d_pct}% vs {READMISSION_RATE_BENCHMARK_PCT}% national benchmark ({readmission_variance:+} variance).",
            f"Acute transfers: {ht.acute_transfers_this_week} transfers to acute hospital in past 7 days ({ht.unplanned_transfers_30d_count} over 30 days).",
            f"Primary transfer drivers: Respiratory ({ht.transfers_by_reason.get('respiratory', 0)}), Cardiac ({ht.transfers_by_reason.get('cardiac', 0)}), Sepsis ({ht.transfers_by_reason.get('sepsis', 0)}).",
        ],
        risk_level=ht_risk,
    )

    # Cross-domain Correlations
    # Correlation 1: Staffing Strain & Therapy Delivery / Operations
    if (
        st.call_in_absences_count >= 3 or st.open_shifts_count >= 4 or hppd_delta < -0.3
    ) and (th.treatment_completion_rate_pct < 94.0 or st.agency_staff_pct > 15.0):
        correlations.append(
            CrossDomainCorrelation(
                domains=["staffing", "therapy"],
                finding_summary="Nursing staffing shortage and open shifts impact operational stability and rehabilitation support.",
                evidence_facts=[
                    f"Staffing open shifts: {st.open_shifts_count}, call-ins: {st.call_in_absences_count} (HPPD: {st.hppd_actual} vs {st.hppd_budgeted_target}).",
                    f"Agency utilization elevated at {st.agency_staff_pct}%; therapy completion at {th.treatment_completion_rate_pct}%.",
                ],
                impact_level="CRITICAL" if hppd_delta < -0.4 else "MODERATE",
            )
        )

    # Correlation 2: Payer Auth Expirations & Pending Discharges
    if pa.expiring_authorizations_48h >= 5 and ad.pending_discharges > 0:
        correlations.append(
            CrossDomainCorrelation(
                domains=["payer_auth", "admissions_discharges"],
                finding_summary="Authorization cliff threatens discharge timing and reimbursement coverage.",
                evidence_facts=[
                    f"Expiring authorizations within 48h: {pa.expiring_authorizations_48h}.",
                    f"Pending discharges in pipeline: {ad.pending_discharges}.",
                ],
                impact_level="CRITICAL"
                if pa.expiring_authorizations_48h > 7
                else "MODERATE",
            )
        )

    # Correlation 3: Acute Transfers Spike & Clinical Stability
    if ht.acute_transfers_this_week >= 3:
        correlations.append(
            CrossDomainCorrelation(
                domains=["hospital_transfers", "census"],
                finding_summary="Acute transfer acceleration impacts clinical quality indicators and bed occupancy stability.",
                evidence_facts=[
                    f"Acute transfers this week: {ht.acute_transfers_this_week}.",
                    f"30-day readmission rate: {ht.readmission_rate_30d_pct}% vs {ht.benchmark_readmission_rate_pct}% benchmark.",
                ],
                impact_level="CRITICAL"
                if ht.readmission_rate_30d_pct > 18.0
                else "MODERATE",
            )
        )

    facility_name = snapshot.facility_id.replace("-", " ").title()

    return FacilityCalculations(
        facility_id=snapshot.facility_id,
        facility_name=facility_name,
        snapshot_date=snapshot.snapshot_date.isoformat(),
        scenario=scenario,
        domains=domains,
        correlations=correlations,
    )
