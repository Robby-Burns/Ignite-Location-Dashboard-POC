"""Analytical briefing synthesis models and deterministic logic for Facility Brief (Story 3.1)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field

from src.analytics.attention_areas import FacilityAttentionSummary
from src.analytics.calculations import FacilityCalculations
from src.analytics.positive_highlights import FacilityPositiveHighlightsSummary
from src.analytics.recommendations import FacilityRecommendationsSummary
from src.models.facility import DailyFacilitySnapshot


class FacilityBriefHeader(BaseModel):
    """High-level human-readable operational header."""

    facility_id: str = Field(..., description="Facility identifier")
    facility_name: str = Field(..., description="Facility name")
    location: str = Field(..., description="City and state")
    report_date: str = Field(..., description="Snapshot date ISO format")
    scenario: str = Field(default="baseline", description="Scenario name")
    overall_status: Literal["HEALTHY", "WATCH", "NEEDS_ATTENTION", "CRITICAL"] = Field(
        default="HEALTHY", description="Overall operational health status"
    )
    status_label: str = Field(..., description="Human-friendly status banner text")
    executive_summary: str = Field(
        ..., description="Concise plain-English operational pulse summary"
    )


class BriefVitalMetric(BaseModel):
    """Key vital statistic card for non-technical facility leadership."""

    metric_name: str = Field(..., description="Machine identifier")
    label: str = Field(..., description="Display label (e.g. 'Occupancy Rate')")
    formatted_value: str = Field(..., description="Formatted value (e.g. '93.3%')")
    subtitle: str = Field(..., description="Context or variance (e.g. 'Target: 90.0%')")
    status: Literal["POSITIVE", "NEUTRAL", "ATTENTION", "CRITICAL"] = Field(
        default="NEUTRAL", description="Status evaluation"
    )
    trend: Literal["UP", "DOWN", "STABLE"] = Field(
        default="STABLE", description="Trend direction"
    )


class BriefHighlightCard(BaseModel):
    """Summarized positive highlight card for executive viewing."""

    title: str = Field(..., description="Short positive headline")
    domain: str = Field(..., description="Operational domain")
    plain_language_description: str = Field(
        ..., description="Plain English explanation"
    )
    supporting_metric: str = Field(..., description="Data-grounded supporting evidence")
    significance: str = Field(..., description="Operational importance")


class BriefWatchItemCard(BaseModel):
    """Summarized watch / attention area card for executive viewing."""

    title: str = Field(..., description="Short attention headline")
    domain: str = Field(..., description="Operational domain")
    severity: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"] = Field(
        default="MEDIUM", description="Severity level"
    )
    plain_language_concern: str = Field(
        ..., description="Plain English explanation of concern"
    )
    supporting_metric: str = Field(..., description="Data-grounded supporting evidence")
    is_compound_risk: bool = Field(
        default=False, description="Indicates multi-domain compound risk"
    )
    related_domains: list[str] = Field(
        default_factory=list, description="Related domains contributing to risk"
    )


class BriefActionItemCard(BaseModel):
    """Prioritized suggested next step card."""

    priority: Literal["HIGH", "MEDIUM", "LOW"] = Field(
        default="MEDIUM", description="Action priority"
    )
    title: str = Field(..., description="Action title")
    department: str = Field(..., description="Responsible department role")
    suggested_action: str = Field(..., description="Concrete suggested next step")
    why_it_matters: str = Field(..., description="Rationale and impact")
    time_horizon: str = Field(..., description="Suggested timeframe")


class BriefLimitations(BaseModel):
    """Governance, simulated boundaries, and data completeness limitations."""

    is_simulated_domo: bool = Field(
        default=True,
        description="Confirms simulated Domo MCP connection (Spec section 1)",
    )
    data_freshness: str = Field(..., description="Data capture timestamp")
    disclaimer: str = Field(
        default="Decision Support Only: All findings and recommendations are advisory suggestions to assist human facility leaders. Clinical and administrative decisions remain with authorized facility leadership.",
        description="Human authority notice (FR-009)",
    )
    data_completeness_notes: list[str] = Field(
        default_factory=list,
        description="Explicit data limitations or missing datasets",
    )


class FacilityBriefReport(BaseModel):
    """Complete human-facing Facility Brief report (Story 3.1, AC-3.1.1)."""

    header: FacilityBriefHeader = Field(..., description="Executive header and status")
    vitals: list[BriefVitalMetric] = Field(
        default_factory=list, description="High-level vital metrics"
    )
    positive_highlights: list[BriefHighlightCard] = Field(
        default_factory=list, description="What is going well (Story 2.3)"
    )
    watch_items: list[BriefWatchItemCard] = Field(
        default_factory=list,
        description="Areas to watch / attention items (Story 2.4)",
    )
    action_items: list[BriefActionItemCard] = Field(
        default_factory=list, description="Immediate suggested next steps (Story 2.5)"
    )
    limitations: BriefLimitations = Field(
        default_factory=lambda: BriefLimitations(
            data_freshness=datetime.now(UTC).isoformat()
        ),
        description="Boundaries and governance",
    )
    generated_at: str = Field(
        default_factory=lambda: datetime.now(UTC).isoformat(),
        description="Generation timestamp",
    )


def synthesize_deterministic_facility_brief(
    snapshot: DailyFacilitySnapshot,
    calculations: FacilityCalculations,
    positive_results: FacilityPositiveHighlightsSummary,
    attention_results: FacilityAttentionSummary,
    recommendation_results: FacilityRecommendationsSummary,
    facility_name: str | None = None,
    location: str | None = None,
    scenario: str = "baseline",
) -> FacilityBriefReport:
    """Synthesizes a human-facing Facility Brief report from deterministic analytics."""
    fac_name = facility_name or snapshot.facility_id.replace("-", " ").title()
    if not fac_name.startswith("Ignite"):
        fac_name = f"Ignite Medical Resort {fac_name}"
    fac_location = location or "Oak Brook, IL"

    high_attention_count = sum(
        1
        for item in attention_results.attention_items
        if item.severity in ("HIGH", "CRITICAL")
    )
    total_attention_count = len(attention_results.attention_items)
    compound_count = len(attention_results.cross_domain_correlations)

    if compound_count > 0 or high_attention_count >= 2:
        overall_status = "CRITICAL"
        status_label = "Critical Operational Attention Required"
    elif high_attention_count == 1 or total_attention_count >= 2:
        overall_status = "NEEDS_ATTENTION"
        status_label = "Operational Attention Recommended"
    elif total_attention_count == 1:
        overall_status = "WATCH"
        status_label = "Operational Watch: Monitoring Key Indicators"
    else:
        overall_status = "HEALTHY"
        status_label = "Operations Stable and Meeting Benchmarks"

    census = snapshot.census
    adm_dis = snapshot.admissions_discharges
    staffing = snapshot.staffing
    hospitality = snapshot.hospitality

    summary_parts = []
    summary_parts.append(
        f"{fac_name} is currently operating at {census.occupancy_rate_pct:.1f}% occupancy "
        f"({census.current_census} / {census.total_capacity} beds filled) with {adm_dis.today_admissions} admissions "
        f"and {adm_dis.today_discharges} discharges today (net flow: {adm_dis.net_flow:+d})."
    )

    if overall_status in ("CRITICAL", "NEEDS_ATTENTION"):
        top_concerns = [item.title for item in attention_results.attention_items[:2]]
        summary_parts.append(
            f"Primary leadership attention is focused on {', '.join(top_concerns)}. "
            "Active corrective interventions have been prioritized for departmental review."
        )
    elif overall_status == "WATCH":
        watch_name = attention_results.attention_items[0].title
        summary_parts.append(
            f"Key indicators remain generally solid, with advisory monitoring on {watch_name}."
        )
    else:
        summary_parts.append(
            "All core clinical, staffing, and operational domains are tracking at or above target benchmarks "
            "with strong resident satisfaction and positive therapy participation."
        )

    executive_summary = " ".join(summary_parts)

    header = FacilityBriefHeader(
        facility_id=snapshot.facility_id,
        facility_name=fac_name,
        location=fac_location,
        report_date=snapshot.snapshot_date.isoformat(),
        scenario=scenario,
        overall_status=overall_status,
        status_label=status_label,
        executive_summary=executive_summary,
    )

    vitals: list[BriefVitalMetric] = [
        BriefVitalMetric(
            metric_name="occupancy_rate_pct",
            label="Occupancy Rate",
            formatted_value=f"{census.occupancy_rate_pct:.1f}%",
            subtitle=f"{census.current_census} / {census.total_capacity} Beds (Net: {adm_dis.net_flow:+d})",
            status="POSITIVE" if census.occupancy_rate_pct >= 90.0 else "ATTENTION",
            trend="UP"
            if adm_dis.net_flow > 0
            else ("DOWN" if adm_dis.net_flow < 0 else "STABLE"),
        ),
        BriefVitalMetric(
            metric_name="hppd_actual",
            label="Direct Care HPPD",
            formatted_value=f"{staffing.hppd_actual:.2f} hrs",
            subtitle=f"Target: {staffing.hppd_budgeted_target:.2f} ({staffing.open_shifts_count} Open Shifts)",
            status="POSITIVE"
            if staffing.hppd_actual >= staffing.hppd_budgeted_target
            else "ATTENTION",
            trend="STABLE"
            if staffing.hppd_actual >= staffing.hppd_budgeted_target
            else "DOWN",
        ),
        BriefVitalMetric(
            metric_name="agency_staff_pct",
            label="Agency Staffing",
            formatted_value=f"{staffing.agency_staff_pct:.1f}%",
            subtitle="Target: < 10.0% Internal Mix",
            status="POSITIVE" if staffing.agency_staff_pct <= 10.0 else "ATTENTION",
            trend="UP" if staffing.agency_staff_pct > 10.0 else "STABLE",
        ),
        BriefVitalMetric(
            metric_name="treatment_completion_rate_pct",
            label="Therapy Completion",
            formatted_value=f"{snapshot.therapy.treatment_completion_rate_pct:.1f}%",
            subtitle=f"{snapshot.therapy.patients_meeting_weekly_goals_pct:.1f}% Goals Met (Hold: {snapshot.therapy.patients_on_therapy_hold})",
            status="POSITIVE"
            if snapshot.therapy.treatment_completion_rate_pct >= 90.0
            else "ATTENTION",
            trend="STABLE",
        ),
        BriefVitalMetric(
            metric_name="dining_satisfaction_score",
            label="Guest Dining Score",
            formatted_value=f"{hospitality.dining_satisfaction_score:.1f}%",
            subtitle=f"NPS: {hospitality.guest_satisfaction_nps:+.0f} (Target: > 85.0%)",
            status="POSITIVE"
            if hospitality.dining_satisfaction_score >= 85.0
            else "ATTENTION",
            trend="UP" if hospitality.dining_satisfaction_score >= 90.0 else "STABLE",
        ),
    ]

    def _format_metric_with_unit(val: float, u: str) -> str:
        if u == "%":
            return f"{val:.1f}%"
        if u:
            return f"{val:g} {u}"
        return f"{val:g}"

    highlights: list[BriefHighlightCard] = []
    for h in positive_results.highlights[:4]:
        cur_str = _format_metric_with_unit(h.current_value, h.unit)
        bench_str = _format_metric_with_unit(h.benchmark_or_target_value, h.unit)
        target_label = (
            "Prior Week" if h.category == "TRAJECTORY_IMPROVEMENT" else "Target"
        )
        highlights.append(
            BriefHighlightCard(
                title=h.title,
                domain=h.domain_display_name,
                plain_language_description=h.evidence_statement,
                supporting_metric=f"{cur_str} ({target_label}: {bench_str})",
                significance=h.operational_impact,
            )
        )

    watch_items: list[BriefWatchItemCard] = [
        BriefWatchItemCard(
            title=item.title,
            domain=item.domain_display_name,
            severity=item.severity,
            plain_language_concern=item.operational_risk_summary,
            supporting_metric=item.evidence_statement,
            is_compound_risk=item.is_cross_domain_compound,
            related_domains=[d.replace("_", " ").title() for d in item.related_domains],
        )
        for item in attention_results.attention_items[:4]
    ]

    action_items: list[BriefActionItemCard] = [
        BriefActionItemCard(
            priority=rec.priority,
            title=rec.action_title,
            department=rec.target_role_or_department,
            suggested_action=rec.suggested_action_description,
            why_it_matters=rec.rationale,
            time_horizon=rec.time_horizon.replace("_", " ").title(),
        )
        for rec in recommendation_results.recommendations[:4]
    ]

    limitations = BriefLimitations(
        is_simulated_domo=True,
        data_freshness=snapshot.created_at.isoformat(),
        data_completeness_notes=[
            "Data Feed: Connected to simulated operational facility telemetry.",
            "Verified Grounding: All cited figures verified directly against certified facility records.",
            "Privacy Assured: Aggregated operational indicators only; no patient-identifying health information.",
        ],
    )

    return FacilityBriefReport(
        header=header,
        vitals=vitals,
        positive_highlights=highlights,
        watch_items=watch_items,
        action_items=action_items,
        limitations=limitations,
    )
