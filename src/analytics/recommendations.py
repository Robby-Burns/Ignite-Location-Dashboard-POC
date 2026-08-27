"""Deterministic Operational Recommendations Engine for Story 2.5.

Provides:
- Translation of identified attention areas and compound cross-domain risks into actionable recommendations (AC-2.5.1).
- Clear rationale and supporting metric evidence for each suggested action (AC-2.5.1).
- Time horizon and departmental role assignment (e.g. Director of Nursing, Case Management).
- Clear decision-support governance framing respecting human decision authority (AC-2.5.3, FR-009).
- Dynamic data-responsiveness across operational scenarios (AC-2.5.2).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field

from src.analytics.attention_areas import (
    AttentionAreaItem,
    FacilityAttentionSummary,
    evaluate_attention_areas,
)
from src.analytics.calculations import (
    CrossDomainCorrelation,
    FacilityCalculations,
    calculate_facility_metrics,
)
from src.analytics.trends import (
    FacilityTrendCalculations,
    calculate_historical_trends,
)
from src.models.facility import DailyFacilitySnapshot, FacilityHistoricalSeries

DEFAULT_GOVERNANCE_DISCLAIMER = (
    "Decision-support recommendation suggested for facility administrative and clinical review. "
    "Maintains human decision authority; does not execute autonomous operational changes."
)


class OperationalRecommendation(BaseModel):
    """Actionable operational recommendation grounded in facility metrics (AC-2.5.1, AC-2.5.3)."""

    recommendation_id: str = Field(..., description="Unique recommendation identifier")
    domain: str = Field(..., description="Primary operational domain")
    domain_display_name: str = Field(..., description="Human-friendly domain name")
    target_role_or_department: str = Field(
        ...,
        description="Facility leader or department responsible for reviewing this action (e.g. Director of Nursing)",
    )
    priority: Literal["HIGH", "MEDIUM", "LOW"] = Field(
        ..., description="Operational or clinical priority level"
    )
    time_horizon: Literal["IMMEDIATE_24H", "SHORT_TERM_7D", "STRATEGIC_30D"] = Field(
        ..., description="Suggested implementation timeframe"
    )
    action_title: str = Field(
        ..., description="Concise, actionable recommendation title"
    )
    suggested_action_description: str = Field(
        ..., description="Detailed practical steps suggested for leadership review"
    )
    rationale: str = Field(
        ...,
        description="Explicit clinical, financial, or operational justification for why this action was suggested (AC-2.5.1)",
    )
    supporting_evidence_metrics: list[str] = Field(
        default_factory=list,
        description="Verifiable metric facts supporting this recommendation (AC-2.5.1)",
    )
    expected_operational_impact: str = Field(
        ...,
        description="Projected operational, financial, or clinical benefit upon human execution",
    )
    governance_disclaimer: str = Field(
        default=DEFAULT_GOVERNANCE_DISCLAIMER,
        description="Explicit declaration of decision-support status (AC-2.5.3)",
    )


class FacilityRecommendationsSummary(BaseModel):
    """Collection of verified operational recommendations for a facility."""

    facility_id: str = Field(..., description="Facility identifier")
    scenario: str = Field(default="baseline", description="Evaluated scenario")
    total_recommendations_count: int = Field(
        ..., description="Total count of generated operational recommendations"
    )
    high_priority_count: int = Field(
        ..., description="Count of HIGH priority recommendations"
    )
    medium_priority_count: int = Field(
        ..., description="Count of MEDIUM priority recommendations"
    )
    low_priority_count: int = Field(
        ..., description="Count of LOW priority recommendations"
    )
    recommendations: list[OperationalRecommendation] = Field(
        default_factory=list,
        description="Prioritized list of operational recommendations",
    )
    calculated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp of calculation",
    )


def generate_deterministic_recommendations(
    snapshot: DailyFacilitySnapshot,
    history: FacilityHistoricalSeries | None = None,
    scenario: str = "baseline",
    calculations: FacilityCalculations | None = None,
    trends: FacilityTrendCalculations | None = None,
    attention_summary: FacilityAttentionSummary | None = None,
) -> FacilityRecommendationsSummary:
    """Deterministically generate data-grounded recommendations from attention areas and snapshot metrics (AC-2.5.1, AC-2.5.2)."""
    facility_id = snapshot.facility_id
    rec_counter = 1

    if calculations is None:
        calculations = calculate_facility_metrics(snapshot, scenario=scenario)
    if trends is None:
        trends = calculate_historical_trends(snapshot, history, scenario=scenario)
    if attention_summary is None:
        attention_summary = evaluate_attention_areas(
            snapshot=snapshot,
            history=history,
            scenario=scenario,
            calculations=calculations,
            trends=trends,
        )

    recommendations: list[OperationalRecommendation] = []

    # Map each Attention Area into a concrete actionable recommendation
    for item in attention_summary.attention_items:
        rec = _map_attention_item_to_recommendation(
            item=item,
            snapshot=snapshot,
            facility_id=facility_id,
            rec_id_num=rec_counter,
        )
        recommendations.append(rec)
        rec_counter += 1

    # Map Cross-Domain Compound Correlations into multi-department recommendations (AC-2.5.1, AC-2.5.2)
    for corr in attention_summary.cross_domain_correlations:
        corr_rec = _map_correlation_to_recommendation(
            corr=corr,
            snapshot=snapshot,
            facility_id=facility_id,
            rec_id_num=rec_counter,
        )
        recommendations.append(corr_rec)
        rec_counter += 1

    # If facility is operating completely healthy with 0 deficits, provide proactive quality optimization recommendations
    if not recommendations:
        recommendations.extend(
            _build_proactive_baseline_recommendations(snapshot, facility_id)
        )

    # Sort recommendations by priority (HIGH > MEDIUM > LOW) and time horizon (IMMEDIATE_24H > SHORT_TERM_7D > STRATEGIC_30D)
    priority_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    time_order = {"IMMEDIATE_24H": 0, "SHORT_TERM_7D": 1, "STRATEGIC_30D": 2}
    recommendations.sort(
        key=lambda r: (
            priority_order.get(r.priority, 3),
            time_order.get(r.time_horizon, 3),
        )
    )

    high_c = sum(1 for r in recommendations if r.priority == "HIGH")
    med_c = sum(1 for r in recommendations if r.priority == "MEDIUM")
    low_c = sum(1 for r in recommendations if r.priority == "LOW")

    return FacilityRecommendationsSummary(
        facility_id=facility_id,
        scenario=scenario,
        total_recommendations_count=len(recommendations),
        high_priority_count=high_c,
        medium_priority_count=med_c,
        low_priority_count=low_c,
        recommendations=recommendations,
    )


def _map_attention_item_to_recommendation(
    item: AttentionAreaItem,
    snapshot: DailyFacilitySnapshot,
    facility_id: str,
    rec_id_num: int,
) -> OperationalRecommendation:
    """Transform an individual operational deficit into a specific, grounded recommendation."""
    priority: Literal["HIGH", "MEDIUM", "LOW"] = (
        "HIGH" if item.severity in ("CRITICAL", "HIGH") else "MEDIUM"
    )
    time_horizon: Literal["IMMEDIATE_24H", "SHORT_TERM_7D", "STRATEGIC_30D"] = (
        "IMMEDIATE_24H" if item.urgency == "IMMEDIATE" else "SHORT_TERM_7D"
    )

    role_map = {
        "census": "Director of Admissions & Marketing",
        "admissions_discharges": "Admissions & Case Management Team",
        "length_of_stay": "Director of Case Management & Utilization Review",
        "staffing": "Director of Nursing (DON) & Staffing Coordinator",
        "therapy": "Director of Rehabilitation (DOR)",
        "payer_auth": "Business Office Manager & Case Management",
        "hospitality": "Director of Hospitality & Culinary Services",
        "hospital_transfers": "Director of Nursing & Medical Director",
    }
    target_role = role_map.get(item.domain, "Facility Executive Director")

    # Domain-specific action mappings
    if item.domain == "staffing":
        st = snapshot.staffing
        action_title = (
            f"Mobilize Nursing Coverage to Resolve {st.open_shifts_count} Open Shifts"
        )
        suggested_action = (
            f"Review on-call PRN roster, offer voluntary shift bonuses for critical shifts, "
            f"and evaluate core floor nurse-to-patient allocation to restore direct care HPPD to the {st.hppd_budgeted_target} target."
        )
        rationale = (
            f"Direct nursing hours are currently {st.hppd_actual} HPPD against a budget of {st.hppd_budgeted_target} HPPD "
            f"with {st.open_shifts_count} open shifts and {st.agency_staff_pct}% agency reliance, increasing burnout and clinical care risks."
        )
        impact = "Restores nursing coverage to target ratios, mitigates overtime burnout, and safeguards clinical care delivery."

    elif item.domain == "hospital_transfers":
        ht = snapshot.hospital_transfers
        action_title = f"Conduct Clinical Root-Cause Review on {ht.acute_transfers_this_week} Acute Hospital Transfers"
        suggested_action = (
            "Initiate INTERACT 30-day transfer root-cause huddle with attending physicians, "
            "audit change-in-condition early warning triggers, and ensure on-site respiratory and IV hydration protocols are utilized."
        )
        rationale = (
            f"Facility experienced {ht.acute_transfers_this_week} acute hospital transfers in 7 days and has a 30-day readmission rate "
            f"of {ht.readmission_rate_30d_pct}% vs the {ht.benchmark_readmission_rate_pct}% benchmark."
        )
        impact = "Reduces avoidable emergency room readmissions and strengthens acute hospital network preferred-provider partnership standing."

    elif item.domain == "payer_auth":
        pa = snapshot.payer_auth
        action_title = f"Fast-Track Urgent Re-Authorizations for {pa.expiring_authorizations_48h} Expiring Policies"
        suggested_action = (
            "Convene daily clinical-payer bridge huddle with physical therapy and case management to submit updated therapy progress notes "
            "and clinical justifications to commercial and Medicare Advantage payers."
        )
        rationale = f"{pa.expiring_authorizations_48h} payer authorizations are expiring within the next 48 hours, exposing the facility to uncompensated care and claim denials."
        impact = "Protects reimbursement coverage, prevents retroactive claim denials, and ensures orderly guest transition timing."

    elif item.domain == "therapy":
        th = snapshot.therapy
        action_title = f"Optimize Rehabilitation Scheduling to Restore Completion ({th.treatment_completion_rate_pct}%)"
        suggested_action = (
            "Re-align therapy morning time blocks, address patient refusal and fatigue root causes, "
            "and cross-cover therapist caseloads during peak guest morning routines."
        )
        rationale = f"Therapy treatment completion dropped to {th.treatment_completion_rate_pct}%, falling below the clinical target of 95.0%."
        impact = "Accelerates functional mobility gains, shortens rehabilitation stay duration, and ensures full therapy compliance."

    elif item.domain == "census":
        c = snapshot.census
        action_title = f"Activate Referral Partner Outreach to Fill {c.available_beds} Available Beds"
        suggested_action = (
            "Engage acute hospital discharge planners, review pending hospital referrals, "
            "and expedite clinical intake screening to recover bed occupancy toward target."
        )
        rationale = f"Occupancy is currently {c.occupancy_rate_pct}% ({c.current_census} occupied beds), with {c.available_beds} beds available."
        impact = "Improves bed capacity utilization and stabilizes operational revenue."

    elif item.domain == "length_of_stay":
        los = snapshot.length_of_stay
        action_title = f"Interdisciplinary Utilization Review on {los.los_outliers_count} Extended-Stay Guests"
        suggested_action = (
            "Conduct structured multi-disciplinary discharge planning huddle (Nursing, Therapy, Social Services) "
            "to resolve home health, DME, or family placement bottlenecks."
        )
        rationale = f"Facility has {los.los_outliers_count} patients exceeding expected length of stay (average LOS is {los.average_los_days} days)."
        impact = "Clears short-stay rehabilitation bed bottlenecks and reduces non-reimbursed length of stay exposure."

    elif item.domain == "hospitality":
        ho = snapshot.hospitality
        action_title = f"Conduct Guest Culinary and Service Satisfaction Huddle ({ho.dining_satisfaction_score} pts)"
        suggested_action = "Review food temperature logs, meal delivery timing, and open guest service requests with executive culinary staff."
        rationale = f"Dining satisfaction is {ho.dining_satisfaction_score} points and Guest NPS is +{ho.guest_satisfaction_nps}."
        impact = "Boosts resident dining experience and guest satisfaction ratings."

    else:
        action_title = f"Review Departmental Operations for {item.domain_display_name}"
        suggested_action = f"Evaluate key operational workflows and resolve root causes identified in {item.title}."
        rationale = item.evidence_statement
        impact = item.operational_risk_summary

    return OperationalRecommendation(
        recommendation_id=f"REC-{item.domain.upper()[:4]}-{rec_id_num:02d}-{facility_id[:6]}",
        domain=item.domain,
        domain_display_name=item.domain_display_name,
        target_role_or_department=target_role,
        priority=priority,
        time_horizon=time_horizon,
        action_title=action_title,
        suggested_action_description=suggested_action,
        rationale=rationale,
        supporting_evidence_metrics=[item.evidence_statement],
        expected_operational_impact=impact,
    )


def _map_correlation_to_recommendation(
    corr: CrossDomainCorrelation,
    snapshot: DailyFacilitySnapshot,
    facility_id: str,
    rec_id_num: int,
) -> OperationalRecommendation:
    """Transform a cross-domain correlation into a joint departmental recommendation."""
    priority: Literal["HIGH", "MEDIUM", "LOW"] = (
        "HIGH" if corr.impact_level == "CRITICAL" else "MEDIUM"
    )
    time_horizon: Literal["IMMEDIATE_24H", "SHORT_TERM_7D", "STRATEGIC_30D"] = (
        "IMMEDIATE_24H" if corr.impact_level == "CRITICAL" else "SHORT_TERM_7D"
    )

    domain_str = "_".join(corr.domains)
    roles = "Interdisciplinary Leadership Team (DON, DOR, Case Management)"

    return OperationalRecommendation(
        recommendation_id=f"REC-CROSS-{rec_id_num:02d}-{facility_id[:6]}",
        domain=domain_str,
        domain_display_name="Cross-Department Operations",
        target_role_or_department=roles,
        priority=priority,
        time_horizon=time_horizon,
        action_title=f"Cross-Department Alignment: {corr.finding_summary[:60]}...",
        suggested_action_description=(
            f"Hold joint interdisciplinary briefing connecting {', '.join([d.title() for d in corr.domains])} "
            f"to establish coordinated mitigation strategies and synchronize daily floor workflows."
        ),
        rationale=f"Cross-domain friction detected: {corr.finding_summary}",
        supporting_evidence_metrics=corr.evidence_facts,
        expected_operational_impact="Prevents operational friction in one department from cascading into secondary clinical or financial deficits.",
    )


def _build_proactive_baseline_recommendations(
    snapshot: DailyFacilitySnapshot, facility_id: str
) -> list[OperationalRecommendation]:
    """Generate proactive continuous improvement suggestions when facility is operating normally."""
    return [
        OperationalRecommendation(
            recommendation_id=f"REC-PROACT-01-{facility_id[:6]}",
            domain="census",
            domain_display_name="Census & Admissions",
            target_role_or_department="Director of Admissions",
            priority="LOW",
            time_horizon="SHORT_TERM_7D",
            action_title="Maintain Proactive Referral Channel Pipeline",
            suggested_action_description="Continue active outreach to regional health system case managers to sustain healthy bed turnover and intake momentum.",
            rationale=f"Facility occupancy is operating well at {snapshot.census.occupancy_rate_pct}% with {snapshot.census.available_beds} beds available.",
            supporting_evidence_metrics=[
                f"Current census: {snapshot.census.current_census} / {snapshot.census.total_capacity} ({snapshot.census.occupancy_rate_pct}% occupancy)."
            ],
            expected_operational_impact="Sustains stable census volume and optimizes guest throughput.",
        ),
        OperationalRecommendation(
            recommendation_id=f"REC-PROACT-02-{facility_id[:6]}",
            domain="hospitality",
            domain_display_name="Hospitality & Guest Experience",
            target_role_or_department="Director of Hospitality",
            priority="LOW",
            time_horizon="STRATEGIC_30D",
            action_title="Evaluate Guest Experience Best-Practice Sharing",
            suggested_action_description="Document culinary and guest satisfaction workflows to standardize resort-style service across neighboring facilities.",
            rationale=f"Guest NPS is strong at +{snapshot.hospitality.guest_satisfaction_nps} and dining satisfaction is {snapshot.hospitality.dining_satisfaction_score} pts.",
            supporting_evidence_metrics=[
                f"Guest NPS: +{snapshot.hospitality.guest_satisfaction_nps}, Dining satisfaction: {snapshot.hospitality.dining_satisfaction_score} pts."
            ],
            expected_operational_impact="Promotes organizational best-practice sharing and reinforces high guest satisfaction.",
        ),
    ]
