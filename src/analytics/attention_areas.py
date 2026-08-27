"""Deterministic Operational Attention Areas and Cross-Domain Risk Analytics for Story 2.4.

Provides:
- Detection of operational conditions, deficits, and threshold breaches requiring human attention (AC-2.4.1).
- Cross-domain compound correlation analysis linking related operational metrics (AC-2.4.2).
- Severity and urgency prioritization (CRITICAL/HIGH/MEDIUM/LOW; IMMEDIATE/SAME_DAY/MONITOR).
- Strict rejection of false positives (healthy metrics within benchmarks are never flagged as attention areas).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field

from src.analytics.calculations import (
    ACUTE_TRANSFERS_WEEK_ATTENTION_COUNT,
    ACUTE_TRANSFERS_WEEK_BASELINE_TARGET,
    ACUTE_TRANSFERS_WEEK_CRITICAL_COUNT,
    AGENCY_ATTENTION_THRESHOLD_PCT,
    AUTH_EXPIRING_CRITICAL_COUNT,
    DINING_SATISFACTION_ATTENTION,
    GUEST_NPS_ATTENTION,
    HPPD_CRITICAL_DEFICIT,
    LOS_OUTLIER_ATTENTION_COUNT,
    OCCUPANCY_ATTENTION_THRESHOLD_PCT,
    OPEN_SHIFTS_CRITICAL_COUNT,
    READMISSION_RATE_BENCHMARK_PCT,
    READMISSION_RATE_CRITICAL_PCT,
    THERAPY_COMPLETION_ATTENTION_PCT,
    THERAPY_COMPLETION_CRITICAL_PCT,
    CrossDomainCorrelation,
    FacilityCalculations,
    calculate_facility_metrics,
)
from src.analytics.trends import (
    FacilityTrendCalculations,
    calculate_historical_trends,
)
from src.models.facility import DailyFacilitySnapshot, FacilityHistoricalSeries


class AttentionAreaItem(BaseModel):
    """Grounded operational condition or deficit requiring human review (AC-2.4.1, AC-2.4.2)."""

    item_id: str = Field(..., description="Unique attention item identifier")
    domain: str = Field(..., description="Primary operational domain")
    domain_display_name: str = Field(..., description="Human-friendly domain name")
    title: str = Field(..., description="Concise attention headline")
    severity: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"] = Field(
        ..., description="Clinical or financial risk severity"
    )
    urgency: Literal["IMMEDIATE", "SAME_DAY", "MONITOR"] = Field(
        ..., description="Time horizon for administrative or clinical intervention"
    )
    metric_name: str = Field(
        ..., description="Primary metric exhibiting variance or risk"
    )
    current_value: float = Field(..., description="Current snapshot value")
    threshold_or_target: float = Field(
        ..., description="Operational threshold or target benchmark"
    )
    variance_or_deficit: float = Field(
        ..., description="Calculated variance or deficit vs threshold/target"
    )
    unit: str = Field(default="", description="Unit of measurement")
    evidence_statement: str = Field(
        ...,
        description="Deterministic, verifiable evidence sentence citing exact numbers",
    )
    operational_risk_summary: str = Field(
        ...,
        description="Clinical, financial, or regulatory risks if this condition goes unaddressed",
    )
    related_domains: list[str] = Field(
        default_factory=list,
        description="Related operational domains linked to this condition",
    )
    is_cross_domain_compound: bool = Field(
        default=False,
        description="True if this condition represents a multi-domain compounding risk",
    )


class FacilityAttentionSummary(BaseModel):
    """Collection of verified operational attention areas and cross-domain risks for a facility."""

    facility_id: str = Field(..., description="Facility identifier")
    scenario: str = Field(default="baseline", description="Evaluated scenario")
    total_attention_count: int = Field(
        ..., description="Total count of operational conditions requiring attention"
    )
    critical_count: int = Field(
        ..., description="Count of CRITICAL severity conditions"
    )
    high_count: int = Field(..., description="Count of HIGH severity conditions")
    medium_count: int = Field(..., description="Count of MEDIUM severity conditions")
    low_count: int = Field(..., description="Count of LOW severity conditions")
    attention_items: list[AttentionAreaItem] = Field(
        default_factory=list, description="Prioritized operational attention items"
    )
    cross_domain_correlations: list[CrossDomainCorrelation] = Field(
        default_factory=list,
        description="Cross-domain compound relationships identified across data",
    )
    top_risk_domains: list[str] = Field(
        default_factory=list,
        description="Domains with highest concentration of attention items",
    )
    calculated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp of calculation",
    )


def evaluate_attention_areas(
    snapshot: DailyFacilitySnapshot,
    history: FacilityHistoricalSeries | None = None,
    scenario: str = "baseline",
    calculations: FacilityCalculations | None = None,
    trends: FacilityTrendCalculations | None = None,
) -> FacilityAttentionSummary:
    """Deterministically detect and prioritize all operational deficits, threshold breaches, and cross-domain risks (AC-2.4.1, AC-2.4.2)."""
    facility_id = snapshot.facility_id

    # 1. Compute underlying metrics and historical trends if not provided
    if calculations is None:
        calculations = calculate_facility_metrics(snapshot, scenario=scenario)
    if trends is None:
        trends = calculate_historical_trends(snapshot, history, scenario=scenario)

    items: list[AttentionAreaItem] = []

    # ---------------------------------------------------------
    # 1. CENSUS & OCCUPANCY DOMAIN
    # ---------------------------------------------------------
    c = snapshot.census
    if c.occupancy_rate_pct < OCCUPANCY_ATTENTION_THRESHOLD_PCT:
        deficit = round(OCCUPANCY_ATTENTION_THRESHOLD_PCT - c.occupancy_rate_pct, 1)
        sev: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"] = (
            "HIGH" if c.occupancy_rate_pct < 70.0 else "MEDIUM"
        )
        urg: Literal["IMMEDIATE", "SAME_DAY", "MONITOR"] = (
            "SAME_DAY" if c.occupancy_rate_pct < 70.0 else "MONITOR"
        )
        items.append(
            AttentionAreaItem(
                item_id=f"ATT-CENSUS-LOW-{facility_id[:6]}",
                domain="census",
                domain_display_name="Census & Capacity",
                title=f"Low Occupancy Rate ({c.occupancy_rate_pct}%)",
                severity=sev,
                urgency=urg,
                metric_name="occupancy_rate_pct",
                current_value=float(c.occupancy_rate_pct),
                threshold_or_target=OCCUPANCY_ATTENTION_THRESHOLD_PCT,
                variance_or_deficit=deficit,
                unit="%",
                evidence_statement=(
                    f"Occupancy rate is {c.occupancy_rate_pct}%, which is {deficit}% below the healthy operational threshold of {OCCUPANCY_ATTENTION_THRESHOLD_PCT}% ({c.available_beds} beds available)."
                ),
                operational_risk_summary="Sub-optimal census depresses daily operational revenue and under-utilizes clinical capacity.",
                related_domains=["admissions_discharges"],
            )
        )

    # ---------------------------------------------------------
    # 2. ADMISSIONS & DISCHARGES DOMAIN
    # ---------------------------------------------------------
    ad = snapshot.admissions_discharges
    if ad.net_flow <= -3:
        items.append(
            AttentionAreaItem(
                item_id=f"ATT-FLOW-NEG-{facility_id[:6]}",
                domain="admissions_discharges",
                domain_display_name="Admissions & Discharges",
                title=f"Negative Patient Flow Deficit ({ad.net_flow:+} guests)",
                severity="MEDIUM",
                urgency="SAME_DAY",
                metric_name="net_flow",
                current_value=float(ad.net_flow),
                threshold_or_target=0.0,
                variance_or_deficit=float(abs(ad.net_flow)),
                unit="guests",
                evidence_statement=(
                    f"Net patient flow is {ad.net_flow:+} guests today ({ad.today_admissions} admissions vs {ad.today_discharges} discharges)."
                ),
                operational_risk_summary="Sustained negative net flow leads to rapid census erosion and revenue decline.",
                related_domains=["census"],
            )
        )

    # ---------------------------------------------------------
    # 3. LENGTH OF STAY DOMAIN
    # ---------------------------------------------------------
    los = snapshot.length_of_stay
    if los.los_outliers_count >= LOS_OUTLIER_ATTENTION_COUNT:
        items.append(
            AttentionAreaItem(
                item_id=f"ATT-LOS-OUTLIER-{facility_id[:6]}",
                domain="length_of_stay",
                domain_display_name="Length of Stay",
                title=f"Elevated LOS Outliers ({los.los_outliers_count} patients)",
                severity="MEDIUM",
                urgency="SAME_DAY",
                metric_name="los_outliers_count",
                current_value=float(los.los_outliers_count),
                threshold_or_target=float(LOS_OUTLIER_ATTENTION_COUNT),
                variance_or_deficit=float(
                    los.los_outliers_count - LOS_OUTLIER_ATTENTION_COUNT
                ),
                unit="patients",
                evidence_statement=(
                    f"Facility currently has {los.los_outliers_count} patients exceeding expected length of stay (threshold: {LOS_OUTLIER_ATTENTION_COUNT})."
                ),
                operational_risk_summary="Outlier patients increase insurance denial risk, uncompensated care exposure, and block short-stay bed availability.",
                related_domains=["payer_auth", "admissions_discharges"],
            )
        )

    # ---------------------------------------------------------
    # 4. NURSING STAFFING & OPERATIONS DOMAIN
    # ---------------------------------------------------------
    st = snapshot.staffing
    hppd_delta = round(st.hppd_actual - st.hppd_budgeted_target, 2)
    if hppd_delta <= -HPPD_CRITICAL_DEFICIT:
        items.append(
            AttentionAreaItem(
                item_id=f"ATT-STAFF-HPPD-{facility_id[:6]}",
                domain="staffing",
                domain_display_name="Nursing Staffing",
                title=f"Direct Care Nursing Deficit ({st.hppd_actual} HPPD vs {st.hppd_budgeted_target} target)",
                severity="CRITICAL" if hppd_delta <= -0.40 else "HIGH",
                urgency="IMMEDIATE",
                metric_name="hppd_actual",
                current_value=float(st.hppd_actual),
                threshold_or_target=float(st.hppd_budgeted_target),
                variance_or_deficit=float(abs(hppd_delta)),
                unit="HPPD",
                evidence_statement=(
                    f"Actual nursing care hours are {st.hppd_actual} HPPD, representing a deficit of {abs(hppd_delta):.2f} HPPD below the {st.hppd_budgeted_target} target."
                ),
                operational_risk_summary="Under-staffing risks clinical care compromises, medication delivery delays, and regulatory non-compliance.",
                related_domains=["hospital_transfers", "therapy"],
            )
        )

    if st.open_shifts_count >= OPEN_SHIFTS_CRITICAL_COUNT:
        items.append(
            AttentionAreaItem(
                item_id=f"ATT-STAFF-SHIFTS-{facility_id[:6]}",
                domain="staffing",
                domain_display_name="Nursing Staffing",
                title=f"Severe Open Shifts Volume ({st.open_shifts_count} open)",
                severity="HIGH",
                urgency="IMMEDIATE",
                metric_name="open_shifts_count",
                current_value=float(st.open_shifts_count),
                threshold_or_target=float(OPEN_SHIFTS_CRITICAL_COUNT),
                variance_or_deficit=float(
                    st.open_shifts_count - OPEN_SHIFTS_CRITICAL_COUNT
                ),
                unit="shifts",
                evidence_statement=(
                    f"{st.open_shifts_count} open nursing shifts recorded across current operating schedules (critical threshold: {OPEN_SHIFTS_CRITICAL_COUNT})."
                ),
                operational_risk_summary="High unfilled shift volume drives excessive overtime burn, staff fatigue, and call-in escalation.",
                related_domains=["hospitality"],
            )
        )

    if st.agency_staff_pct >= AGENCY_ATTENTION_THRESHOLD_PCT:
        items.append(
            AttentionAreaItem(
                item_id=f"ATT-STAFF-AGENCY-{facility_id[:6]}",
                domain="staffing",
                domain_display_name="Nursing Staffing",
                title=f"High Agency Staff Utilization ({st.agency_staff_pct}%)",
                severity="HIGH" if st.agency_staff_pct >= 20.0 else "MEDIUM",
                urgency="SAME_DAY",
                metric_name="agency_staff_pct",
                current_value=float(st.agency_staff_pct),
                threshold_or_target=AGENCY_ATTENTION_THRESHOLD_PCT,
                variance_or_deficit=round(
                    st.agency_staff_pct - AGENCY_ATTENTION_THRESHOLD_PCT, 1
                ),
                unit="%",
                evidence_statement=(
                    f"External agency staffing utilization is {st.agency_staff_pct}%, exceeding the attention threshold of {AGENCY_ATTENTION_THRESHOLD_PCT}%."
                ),
                operational_risk_summary="Extensive premium agency labor increases operating costs and challenges clinical care continuity.",
                related_domains=["census"],
            )
        )

    # ---------------------------------------------------------
    # 5. THERAPY REHABILITATION DELIVERY DOMAIN
    # ---------------------------------------------------------
    th = snapshot.therapy
    if th.treatment_completion_rate_pct < THERAPY_COMPLETION_ATTENTION_PCT:
        deficit_th = round(
            THERAPY_COMPLETION_ATTENTION_PCT - th.treatment_completion_rate_pct, 1
        )
        sev_th: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"] = (
            "CRITICAL"
            if th.treatment_completion_rate_pct < THERAPY_COMPLETION_CRITICAL_PCT
            else "HIGH"
        )
        items.append(
            AttentionAreaItem(
                item_id=f"ATT-THERAPY-COMP-{facility_id[:6]}",
                domain="therapy",
                domain_display_name="Therapy Rehabilitation",
                title=f"Therapy Delivery Completion Lag ({th.treatment_completion_rate_pct}%)",
                severity=sev_th,
                urgency="IMMEDIATE" if sev_th == "CRITICAL" else "SAME_DAY",
                metric_name="treatment_completion_rate_pct",
                current_value=float(th.treatment_completion_rate_pct),
                threshold_or_target=THERAPY_COMPLETION_ATTENTION_PCT,
                variance_or_deficit=deficit_th,
                unit="%",
                evidence_statement=(
                    f"Therapy completion rate dropped to {th.treatment_completion_rate_pct}%, falling {deficit_th}% below the {THERAPY_COMPLETION_ATTENTION_PCT}% target."
                ),
                operational_risk_summary="Missed therapy sessions delay patient functional progress, extend length of stay, and risk reimbursement audits.",
                related_domains=["staffing", "length_of_stay"],
            )
        )

    # ---------------------------------------------------------
    # 6. PAYER MIX & AUTHORIZATIONS DOMAIN
    # ---------------------------------------------------------
    pa = snapshot.payer_auth
    if pa.expiring_authorizations_48h >= AUTH_EXPIRING_CRITICAL_COUNT:
        items.append(
            AttentionAreaItem(
                item_id=f"ATT-AUTH-CLIFF-{facility_id[:6]}",
                domain="payer_auth",
                domain_display_name="Payer Authorizations",
                title=f"Payer Authorization Expiration Cliff ({pa.expiring_authorizations_48h} in 48h)",
                severity="CRITICAL" if pa.expiring_authorizations_48h >= 7 else "HIGH",
                urgency="IMMEDIATE",
                metric_name="expiring_authorizations_48h",
                current_value=float(pa.expiring_authorizations_48h),
                threshold_or_target=float(AUTH_EXPIRING_CRITICAL_COUNT),
                variance_or_deficit=float(
                    pa.expiring_authorizations_48h - AUTH_EXPIRING_CRITICAL_COUNT
                ),
                unit="authorizations",
                evidence_statement=(
                    f"{pa.expiring_authorizations_48h} insurance coverage authorizations are expiring within the next 48 hours (critical threshold: {AUTH_EXPIRING_CRITICAL_COUNT})."
                ),
                operational_risk_summary="Failure to secure timely re-authorizations creates immediate financial coverage gaps, billing denials, or forced patient transfers.",
                related_domains=["admissions_discharges", "length_of_stay"],
            )
        )

    # ---------------------------------------------------------
    # 7. HOSPITALITY & GUEST EXPERIENCE DOMAIN
    # ---------------------------------------------------------
    ho = snapshot.hospitality
    if ho.dining_satisfaction_score < DINING_SATISFACTION_ATTENTION:
        items.append(
            AttentionAreaItem(
                item_id=f"ATT-HOSP-DINING-{facility_id[:6]}",
                domain="hospitality",
                domain_display_name="Hospitality & Guest Experience",
                title=f"Dining Satisfaction Decline ({ho.dining_satisfaction_score} pts)",
                severity="MEDIUM",
                urgency="SAME_DAY",
                metric_name="dining_satisfaction_score",
                current_value=float(ho.dining_satisfaction_score),
                threshold_or_target=DINING_SATISFACTION_ATTENTION,
                variance_or_deficit=round(
                    DINING_SATISFACTION_ATTENTION - ho.dining_satisfaction_score, 1
                ),
                unit="pts",
                evidence_statement=(
                    f"Resort dining satisfaction score fell to {ho.dining_satisfaction_score} points, below the {DINING_SATISFACTION_ATTENTION} attention threshold."
                ),
                operational_risk_summary="Culinary dissatisfaction damages guest morale, brand reputation, and family referral rates.",
                related_domains=["staffing"],
            )
        )

    if ho.guest_satisfaction_nps < GUEST_NPS_ATTENTION:
        items.append(
            AttentionAreaItem(
                item_id=f"ATT-HOSP-NPS-{facility_id[:6]}",
                domain="hospitality",
                domain_display_name="Hospitality & Guest Experience",
                title=f"Guest Loyalty Index Compression (NPS +{ho.guest_satisfaction_nps})",
                severity="MEDIUM",
                urgency="SAME_DAY",
                metric_name="guest_satisfaction_nps",
                current_value=float(ho.guest_satisfaction_nps),
                threshold_or_target=GUEST_NPS_ATTENTION,
                variance_or_deficit=round(
                    GUEST_NPS_ATTENTION - ho.guest_satisfaction_nps, 1
                ),
                unit="NPS",
                evidence_statement=(
                    f"Guest Net Promoter Score is +{ho.guest_satisfaction_nps}, falling below the +{GUEST_NPS_ATTENTION} attention threshold."
                ),
                operational_risk_summary="Indicates declining guest and family satisfaction, threatening community goodwill.",
                related_domains=["hospitality"],
            )
        )

    # ---------------------------------------------------------
    # 8. HOSPITAL TRANSFERS & READMISSIONS DOMAIN
    # ---------------------------------------------------------
    ht = snapshot.hospital_transfers
    if ht.acute_transfers_this_week >= ACUTE_TRANSFERS_WEEK_ATTENTION_COUNT:
        items.append(
            AttentionAreaItem(
                item_id=f"ATT-TRANS-ACUTE-{facility_id[:6]}",
                domain="hospital_transfers",
                domain_display_name="Hospital Transfers & Quality",
                title=f"Spike in Acute Emergency Transfers ({ht.acute_transfers_this_week} this week)",
                severity=(
                    "CRITICAL"
                    if ht.acute_transfers_this_week
                    >= ACUTE_TRANSFERS_WEEK_CRITICAL_COUNT
                    else "HIGH"
                ),
                urgency="IMMEDIATE",
                metric_name="acute_transfers_this_week",
                current_value=float(ht.acute_transfers_this_week),
                threshold_or_target=ACUTE_TRANSFERS_WEEK_BASELINE_TARGET,
                variance_or_deficit=float(
                    ht.acute_transfers_this_week - ACUTE_TRANSFERS_WEEK_BASELINE_TARGET
                ),
                unit="transfers",
                evidence_statement=(
                    f"Acute hospital transfers surged to {ht.acute_transfers_this_week} this week (exceeding baseline benchmark of {int(ACUTE_TRANSFERS_WEEK_BASELINE_TARGET)} transfers)."
                ),
                operational_risk_summary="High acute transfer frequency indicates acute patient condition deterioration and challenges bedside clinical triage.",
                related_domains=["staffing", "census"],
                is_cross_domain_compound=True,
            )
        )

    if ht.readmission_rate_30d_pct > READMISSION_RATE_BENCHMARK_PCT:
        readm_def = round(
            ht.readmission_rate_30d_pct - READMISSION_RATE_BENCHMARK_PCT, 1
        )
        items.append(
            AttentionAreaItem(
                item_id=f"ATT-TRANS-READM-{facility_id[:6]}",
                domain="hospital_transfers",
                domain_display_name="Hospital Transfers & Quality",
                title=f"Elevated 30-Day Readmission Rate ({ht.readmission_rate_30d_pct}%)",
                severity="CRITICAL"
                if ht.readmission_rate_30d_pct >= READMISSION_RATE_CRITICAL_PCT
                else "HIGH",
                urgency="IMMEDIATE"
                if ht.readmission_rate_30d_pct >= READMISSION_RATE_CRITICAL_PCT
                else "SAME_DAY",
                metric_name="readmission_rate_30d_pct",
                current_value=float(ht.readmission_rate_30d_pct),
                threshold_or_target=READMISSION_RATE_BENCHMARK_PCT,
                variance_or_deficit=readm_def,
                unit="%",
                evidence_statement=(
                    f"30-day readmission rate is {ht.readmission_rate_30d_pct}%, which is {readm_def}% above the national benchmark of {READMISSION_RATE_BENCHMARK_PCT}%."
                ),
                operational_risk_summary="High readmission rates jeopardize hospital network preferred-provider partnerships and quality penalty ratings.",
                related_domains=["hospital_transfers"],
            )
        )

    # ---------------------------------------------------------
    # 9. CROSS-DOMAIN COMPOUND CORRELATIONS (AC-2.4.2)
    # ---------------------------------------------------------
    correlations = list(calculations.correlations)

    # Correlation: High Census Strain + Staffing Deficit
    if c.occupancy_rate_pct >= 90.0 and (
        st.open_shifts_count >= 3 or hppd_delta < -0.2
    ):
        correlations.append(
            CrossDomainCorrelation(
                domains=["census", "staffing"],
                finding_summary="High census density combined with nursing staffing strain amplifies bedside workload.",
                evidence_facts=[
                    f"Occupancy is high at {c.occupancy_rate_pct}% ({c.current_census} beds filled).",
                    f"Nursing staffing faces {st.open_shifts_count} open shifts with {st.hppd_actual} HPPD vs {st.hppd_budgeted_target} target.",
                ],
                impact_level="CRITICAL" if hppd_delta < -0.3 else "MODERATE",
            )
        )

    # Mark cross-domain compound items consistently (F-3)
    active_compound_domains = {d for corr in correlations for d in corr.domains}
    for it in items:
        if it.domain in active_compound_domains:
            it.is_cross_domain_compound = True

    # Sort attention items by severity (CRITICAL > HIGH > MEDIUM > LOW)
    severity_rank = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    items.sort(key=lambda it: severity_rank.get(it.severity, 4))

    # Tally counts
    critical_c = sum(1 for it in items if it.severity == "CRITICAL")
    high_c = sum(1 for it in items if it.severity == "HIGH")
    med_c = sum(1 for it in items if it.severity == "MEDIUM")
    low_c = sum(1 for it in items if it.severity == "LOW")

    # Determine top risk domains
    domain_weights: dict[str, int] = {}
    for it in items:
        weight = 4 if it.severity == "CRITICAL" else (3 if it.severity == "HIGH" else 1)
        domain_weights[it.domain] = domain_weights.get(it.domain, 0) + weight
    top_risk = sorted(
        domain_weights.keys(), key=lambda d: domain_weights[d], reverse=True
    )[:3]

    return FacilityAttentionSummary(
        facility_id=facility_id,
        scenario=scenario,
        total_attention_count=len(items),
        critical_count=critical_c,
        high_count=high_c,
        medium_count=med_c,
        low_count=low_c,
        attention_items=items,
        cross_domain_correlations=correlations,
        top_risk_domains=top_risk,
    )
