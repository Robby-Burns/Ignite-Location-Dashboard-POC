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

    # Specific metric-level action mappings (AC-2.5.1)
    if item.metric_name == "hppd_actual":
        action_title = f"Adjust Direct Nursing Allocation to Recover {item.current_value} HPPD toward {item.threshold_or_target} Target"
        suggested_action = f"Review shift nurse-to-patient staffing ratios and reallocate core floor RN/LPN coverage to resolve the {item.variance_or_deficit:.2f} HPPD direct care deficit."
        rationale = item.evidence_statement
        impact = "Restores bedside direct care hours to required acuity levels and prevents clinical care compromises."

    elif item.metric_name == "open_shifts_count":
        action_title = f"Mobilize Shift Coverage to Fill {int(item.current_value)} Open Nursing Shifts"
        suggested_action = "Engage internal PRN floating pool, offer voluntary incentive shift pick-ups, and review next-day roster to close schedule gaps."
        rationale = item.evidence_statement
        impact = "Eliminates unfilled shift exposure and reduces chronic overtime burden on regular floor staff."

    elif item.metric_name == "agency_staff_pct":
        action_title = f"Execute Agency Reduction Strategy to Curb Elevated Reliance ({item.current_value}%)"
        suggested_action = "Accelerate permanent staff nurse onboarding and review contract agency block bookings to transition shifts to internal staff."
        rationale = item.evidence_statement
        impact = "Decreases premium agency labor expenditures and improves care team familiarity and clinical continuity."

    elif item.metric_name == "acute_transfers_this_week":
        action_title = f"Conduct INTERACT Root-Cause Review on {int(item.current_value)} Acute Hospital Transfers"
        suggested_action = "Initiate INTERACT clinical root-cause review with attending physicians and audit change-in-condition early warning triggers."
        rationale = item.evidence_statement
        impact = "Mitigates avoidable hospital transfers and protects acute care network partnership quality standing."

    elif item.metric_name == "readmission_rate_30d_pct":
        action_title = f"Implement Readmission Reduction Action Plan ({item.current_value}% vs {item.threshold_or_target}% Benchmark)"
        suggested_action = "Strengthen post-discharge follow-up calls within 48 hours and audit bedside medication reconciliation and patient education protocols."
        rationale = item.evidence_statement
        impact = "Brings 30-day readmission rate into compliance with benchmark targets and preferred-network standards."

    elif item.metric_name == "expiring_authorizations_48h":
        action_title = f"Fast-Track Clinical Justifications for {int(item.current_value)} Expiring Authorizations"
        suggested_action = "Convene daily clinical-payer bridge huddle with physical therapy and case management to submit updated progress notes to commercial and MA payers."
        rationale = item.evidence_statement
        impact = "Prevents retroactive coverage denials, uncompensated care stays, and sudden guest discharge disruptions."

    elif item.metric_name == "treatment_completion_rate_pct":
        action_title = f"Re-Engineer Therapy Daily Schedule to Recover Completion ({item.current_value}%)"
        suggested_action = "Audit patient therapy refusal and fatigue root causes, and adjust treatment time blocks to eliminate missed sessions."
        rationale = item.evidence_statement
        impact = "Ensures guests achieve planned functional recovery milestones on schedule and protects reimbursement compliance."

    elif item.metric_name == "occupancy_rate_pct":
        c = snapshot.census
        action_title = f"Activate Intake Referral Campaign to Fill {c.available_beds} Available Beds"
        suggested_action = "Engage acute hospital discharge planners, review pending referrals, and expedite clinical intake screening."
        rationale = item.evidence_statement
        impact = "Recovers census occupancy toward target and optimizes clinical bed capacity."

    elif item.metric_name == "net_flow":
        action_title = f"Reverse Negative Throughput Deficit ({int(item.current_value):+} Net Patient Flow)"
        suggested_action = "Accelerate pending intake conversion while coordinating orderly discharge scheduling across clinical teams."
        rationale = item.evidence_statement
        impact = "Stabilizes net patient throughput and stops census erosion."

    elif item.metric_name == "los_outliers_count":
        action_title = f"Conduct Interdisciplinary Utilization Review on {int(item.current_value)} Extended-Stay Guests"
        suggested_action = "Convene structured multi-disciplinary discharge planning huddle to resolve home health, DME, or family placement bottlenecks."
        rationale = item.evidence_statement
        impact = "Reduces non-reimbursed length of stay exposure and frees short-stay rehabilitation bed capacity."

    elif item.metric_name == "dining_satisfaction_score":
        action_title = f"Conduct Culinary Quality and Meal Delivery Audit ({item.current_value} pts)"
        suggested_action = "Review meal service timing, food temperature logs, and menu choices directly with residents and executive chef."
        rationale = item.evidence_statement
        impact = (
            "Elevates guest dining sentiment and enhances overall hospitality ratings."
        )

    elif item.metric_name == "guest_satisfaction_nps":
        action_title = (
            f"Address Guest Service Feedback to Elevate NPS (+{item.current_value})"
        )
        suggested_action = "Audit open guest service requests and conduct executive rounds with guests and families to resolve dissatisfaction drivers."
        rationale = item.evidence_statement
        impact = "Strengthens resident experience and family loyalty."

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
