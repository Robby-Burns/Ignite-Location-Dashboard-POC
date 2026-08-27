"""Deterministic Historical Trend Analytics and Metric Definitions for Story 2.2.

Provides:
- Non-technical plain-language operational metric definitions (AC-2.2.1).
- Time-series rolling averages, variance trajectories, volatility, and inflection analysis (AC-2.2.2).
- Explicit data sufficiency boundary checks (insufficient context detection).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field

from src.models.facility import DailyFacilitySnapshot, FacilityHistoricalSeries


class MetricDefinition(BaseModel):
    """Plain-language, non-technical explanation of an operational metric (AC-2.2.1)."""

    metric_name: str = Field(..., description="Unique technical metric key")
    domain: str = Field(..., description="Operational domain")
    display_name: str = Field(..., description="Human-friendly label")
    plain_language_meaning: str = Field(
        ...,
        description="What this metric measures in terms understandable to non-technical leaders",
    )
    operational_significance: str = Field(
        ...,
        description="Why this number matters to facility health, quality, compliance, or finances",
    )
    benchmark_or_target_desc: str = Field(
        ..., description="Standard industry benchmark or budgeted target description"
    )
    ideal_direction: Literal[
        "HIGHER_IS_BETTER", "LOWER_IS_BETTER", "TARGET_IS_OPTIMAL"
    ] = Field(
        default="TARGET_IS_OPTIMAL", description="Direction of operational health"
    )


class MetricTrendSummary(BaseModel):
    """Deterministic time-series analytics for a specific metric over historical periods (AC-2.2.2)."""

    metric_name: str = Field(..., description="Metric key")
    display_name: str = Field(..., description="Human-friendly label")
    domain: str = Field(..., description="Operational domain")
    unit: str = Field(default="", description="Unit of measurement")
    current_value: float = Field(..., description="Latest snapshot value")
    value_7d_ago: float | None = Field(
        default=None, description="Value exactly 7 days prior"
    )
    value_14d_ago: float | None = Field(
        default=None, description="Value exactly 14 days prior"
    )
    value_30d_ago: float | None = Field(default=None, description="Value 30 days prior")
    delta_7d: float | None = Field(
        default=None, description="Absolute change over past 7 days"
    )
    delta_30d: float | None = Field(
        default=None, description="Absolute change over past 30 days"
    )
    pct_change_7d: float | None = Field(
        default=None, description="Percentage change over past 7 days"
    )
    pct_change_30d: float | None = Field(
        default=None, description="Percentage change over past 30 days"
    )
    rolling_7d_avg: float = Field(..., description="7-day rolling average")
    rolling_30d_avg: float = Field(..., description="30-day rolling average")
    min_30d: float = Field(..., description="30-day minimum value")
    max_30d: float = Field(..., description="30-day maximum value")
    trend_direction: Literal["INCREASING", "DECREASING", "STABLE", "VOLATILE"] = Field(
        default="STABLE", description="Overall trajectory direction"
    )
    is_meaningful_shift: bool = Field(
        default=False,
        description="Whether the change exceeds operational materiality thresholds",
    )
    shift_summary: str = Field(
        ..., description="Deterministic factual summary of historical trajectory"
    )


class FacilityTrendCalculations(BaseModel):
    """Complete collection of deterministic trend analytics and metric definitions across all domains."""

    facility_id: str = Field(..., description="Facility identifier")
    scenario: str = Field(default="baseline", description="Evaluated scenario")
    days_analyzed: int = Field(..., description="Number of historical days evaluated")
    is_context_sufficient: bool = Field(
        ...,
        description="True if at least 7 days of history exist to substantiate trend claims",
    )
    metric_definitions: dict[str, MetricDefinition] = Field(
        default_factory=dict,
        description="Standard plain-language metric definitions (AC-2.2.1)",
    )
    trends: dict[str, MetricTrendSummary] = Field(
        default_factory=dict,
        description="Deterministic metric trend computations (AC-2.2.2)",
    )
    meaningful_shifts: list[str] = Field(
        default_factory=list,
        description="Factual list of significant historical shifts",
    )
    context_limitations: list[str] = Field(
        default_factory=list,
        description="Explicit disclosures when historical depth is limited",
    )
    calculated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp of trend computation",
    )


# Standard Plain-Language Operational Metric Knowledge Base (AC-2.2.1)
STANDARD_METRIC_DEFINITIONS: dict[str, MetricDefinition] = {
    "current_census": MetricDefinition(
        metric_name="current_census",
        domain="census",
        display_name="Current Census",
        plain_language_meaning="The total number of patients/guests residing in the facility and occupying a bed today.",
        operational_significance="Directly drives daily operating revenue, staffing requirements, dining volume, and facility bed capacity utilization.",
        benchmark_or_target_desc="Target is set by the annual operating budget (typically 85% to 90% of certified bed capacity).",
        ideal_direction="TARGET_IS_OPTIMAL",
    ),
    "occupancy_rate_pct": MetricDefinition(
        metric_name="occupancy_rate_pct",
        domain="census",
        display_name="Occupancy Rate (%)",
        plain_language_meaning="The percentage of available licensed/certified beds currently occupied by active patients.",
        operational_significance="Key indicator of market demand, referral partner relationships, and fixed-cost absorption efficiency.",
        benchmark_or_target_desc="85.0% or higher is considered healthy; below 75.0% signals severe census pressure.",
        ideal_direction="HIGHER_IS_BETTER",
    ),
    "net_flow": MetricDefinition(
        metric_name="net_flow",
        domain="admissions_discharges",
        display_name="Net Daily Patient Flow",
        plain_language_meaning="The net change in facility census today, calculated as admissions minus discharges.",
        operational_significance="Indicates whether the facility is gaining or losing patient volume on a daily throughput basis.",
        benchmark_or_target_desc="Positive or zero net flow maintains or grows census; consecutive negative days erode occupancy.",
        ideal_direction="HIGHER_IS_BETTER",
    ),
    "average_los_days": MetricDefinition(
        metric_name="average_los_days",
        domain="length_of_stay",
        display_name="Average Length of Stay (Days)",
        plain_language_meaning="The average number of days short-stay rehabilitation guests spend from admission to safe discharge home.",
        operational_significance="Critical for managed care authorization alignment and throughput. Extending beyond target increases non-covered stay risks.",
        benchmark_or_target_desc="Target typically 20 to 24 days for short-stay orthopedic/rehabilitation episodes.",
        ideal_direction="TARGET_IS_OPTIMAL",
    ),
    "hppd_actual": MetricDefinition(
        metric_name="hppd_actual",
        domain="staffing",
        display_name="Hours Per Patient Day (HPPD)",
        plain_language_meaning="The average hours of direct nursing care (RN, LPN, and CNA combined) delivered per patient over a 24-hour period.",
        operational_significance="Core measure of clinical care quality, state regulatory compliance, and resident safety. Deficits increase fall and transfer risks.",
        benchmark_or_target_desc="Must meet or exceed budgeted staffing matrix (typically 3.80 to 4.20 HPPD depending on patient acuity).",
        ideal_direction="TARGET_IS_OPTIMAL",
    ),
    "open_shifts_count": MetricDefinition(
        metric_name="open_shifts_count",
        domain="staffing",
        display_name="Open Nursing Shifts",
        plain_language_meaning="The number of scheduled nursing shifts in the last 24 hours that were unfilled by core facility staff.",
        operational_significance="High open shifts force excessive overtime and expensive agency contractor usage, driving up labor costs.",
        benchmark_or_target_desc="Target is 0 to 1 open shifts per day; 4 or more indicates acute staffing disruption.",
        ideal_direction="LOWER_IS_BETTER",
    ),
    "agency_staff_pct": MetricDefinition(
        metric_name="agency_staff_pct",
        domain="staffing",
        display_name="Agency Staffing Utilization (%)",
        plain_language_meaning="The percentage of nursing care hours provided by third-party agency contractors rather than permanent staff.",
        operational_significance="Agency labor is significantly more costly than permanent staff and can impact clinical care continuity.",
        benchmark_or_target_desc="Target is under 5.0%; exceeding 15.0% severely strains facility labor budgets.",
        ideal_direction="LOWER_IS_BETTER",
    ),
    "treatment_completion_rate_pct": MetricDefinition(
        metric_name="treatment_completion_rate_pct",
        domain="therapy",
        display_name="Therapy Treatment Completion (%)",
        plain_language_meaning="The percentage of prescribed physical, occupational, and speech therapy minutes successfully delivered to patients.",
        operational_significance="Directly impacts patient functional recovery, discharge readiness, and Medicare/managed care reimbursement compliance.",
        benchmark_or_target_desc="Target is 95.0% or higher; below 85.0% indicates therapy delivery disruption.",
        ideal_direction="HIGHER_IS_BETTER",
    ),
    "expiring_authorizations_48h": MetricDefinition(
        metric_name="expiring_authorizations_48h",
        domain="payer_auth",
        display_name="Authorizations Expiring in 48 Hours",
        plain_language_meaning="The number of managed care patients whose insurance treatment coverage authorization expires within the next 48 hours.",
        operational_significance="If extensions are not approved before expiration, the facility risks uncompensated care or billing denials.",
        benchmark_or_target_desc="Target is 0 to 2 actively managed cases; 4 or more creates an urgent financial coverage cliff.",
        ideal_direction="LOWER_IS_BETTER",
    ),
    "dining_satisfaction_score": MetricDefinition(
        metric_name="dining_satisfaction_score",
        domain="hospitality",
        display_name="Dining Satisfaction Rating",
        plain_language_meaning="Guest satisfaction rating for resort dining quality, meal temperature, and culinary presentation (rated 0 to 100 points).",
        operational_significance="Dining is a primary driver of overall guest satisfaction, resort brand reputation, and family recommendations.",
        benchmark_or_target_desc="Target is 90.0 points or higher (out of 100).",
        ideal_direction="HIGHER_IS_BETTER",
    ),
    "guest_satisfaction_nps": MetricDefinition(
        metric_name="guest_satisfaction_nps",
        domain="hospitality",
        display_name="Guest Net Promoter Score (NPS)",
        plain_language_meaning="A standard loyalty metric measuring how likely guests and family members are to recommend Ignite Medical Resorts.",
        operational_significance="Reflects the resort-like experience and hospitality differentiator; drives direct word-of-mouth admissions.",
        benchmark_or_target_desc="Target is +60 NPS or higher; +70 is world-class hospitality.",
        ideal_direction="HIGHER_IS_BETTER",
    ),
    "readmission_rate_30d_pct": MetricDefinition(
        metric_name="readmission_rate_30d_pct",
        domain="hospital_transfers",
        display_name="30-Day Hospital Readmission Rate (%)",
        plain_language_meaning="The percentage of discharged or active patients who require unplanned readmission to an acute care hospital within 30 days.",
        operational_significance="Primary clinical quality indicator scrutinized by hospital health system partners, Medicare, and ACO networks.",
        benchmark_or_target_desc="National benchmark is 12.0%; rates above 18.0% risk hospital partner penalties and reduced referrals.",
        ideal_direction="LOWER_IS_BETTER",
    ),
    "acute_transfers_this_week": MetricDefinition(
        metric_name="acute_transfers_this_week",
        domain="hospital_transfers",
        display_name="Acute Hospital Transfers (Past 7 Days)",
        plain_language_meaning="The count of urgent transfers sent to acute hospital emergency departments over the trailing 7 days.",
        operational_significance="Early warning indicator of clinical acuity instability, infection outbreaks, or after-hours clinical triage challenges.",
        benchmark_or_target_desc="Target is 0 to 2 transfers per week for a 100-bed short-stay resort.",
        ideal_direction="LOWER_IS_BETTER",
    ),
}


# --- Trend Materiality Threshold Constants (Documented Thresholds) ---
TREND_CENSUS_MATERIALITY_DELTA: float = 3.0
TREND_OCCUPANCY_MATERIALITY_DELTA: float = 2.5
TREND_NET_FLOW_MATERIALITY_DELTA: float = 2.0
TREND_LOS_MATERIALITY_DELTA: float = 1.5
TREND_HPPD_MATERIALITY_DELTA: float = 0.15
TREND_OPEN_SHIFTS_MATERIALITY_DELTA: float = 2.0
TREND_AGENCY_MATERIALITY_DELTA: float = 4.0
TREND_THERAPY_MATERIALITY_DELTA: float = 3.0
TREND_AUTH_MATERIALITY_DELTA: float = 2.0
TREND_DINING_MATERIALITY_DELTA: float = 2.0
TREND_NPS_MATERIALITY_DELTA: float = 5.0
TREND_READMISSION_MATERIALITY_DELTA: float = 1.5
TREND_ACUTE_TRANSFERS_MATERIALITY_DELTA: float = 2.0


def get_standard_metric_definitions() -> dict[str, MetricDefinition]:
    """Retrieve all standard non-technical operational metric definitions (AC-2.2.1)."""
    return dict(STANDARD_METRIC_DEFINITIONS)


def calculate_historical_trends(
    snapshot: DailyFacilitySnapshot,
    history: FacilityHistoricalSeries | None = None,
    scenario: str = "baseline",
) -> FacilityTrendCalculations:
    """Compute deterministic time-series metrics, rolling averages, and shift classifications (AC-2.2.2)."""
    facility_id = snapshot.facility_id
    definitions = get_standard_metric_definitions()
    trends: dict[str, MetricTrendSummary] = {}
    meaningful_shifts: list[str] = []
    limitations: list[str] = []

    history_days = len(history.snapshots) if (history and history.snapshots) else 0
    is_sufficient = history_days >= 7

    if not is_sufficient:
        limitations.append(
            f"Historical series contains only {history_days} days of data. A minimum of 7 trailing days is required to substantiate multi-week trend trajectories."
        )

    def get_series(metric_key: str) -> list[float]:
        if not history or not history.snapshots:
            return []
        vals: list[float] = []
        for snap in history.snapshots:
            if metric_key == "current_census":
                vals.append(float(snap.census.current_census))
            elif metric_key == "occupancy_rate_pct":
                vals.append(float(snap.census.occupancy_rate_pct))
            elif metric_key == "net_flow":
                vals.append(float(snap.admissions_discharges.net_flow))
            elif metric_key == "average_los_days":
                vals.append(float(snap.length_of_stay.average_los_days))
            elif metric_key == "hppd_actual":
                vals.append(float(snap.staffing.hppd_actual))
            elif metric_key == "open_shifts_count":
                vals.append(float(snap.staffing.open_shifts_count))
            elif metric_key == "agency_staff_pct":
                vals.append(float(snap.staffing.agency_staff_pct))
            elif metric_key == "treatment_completion_rate_pct":
                vals.append(float(snap.therapy.treatment_completion_rate_pct))
            elif metric_key == "expiring_authorizations_48h":
                vals.append(float(snap.payer_auth.expiring_authorizations_48h))
            elif metric_key == "dining_satisfaction_score":
                vals.append(float(snap.hospitality.dining_satisfaction_score))
            elif metric_key == "guest_satisfaction_nps":
                vals.append(float(snap.hospitality.guest_satisfaction_nps))
            elif metric_key == "readmission_rate_30d_pct":
                vals.append(float(snap.hospital_transfers.readmission_rate_30d_pct))
            elif metric_key == "acute_transfers_this_week":
                vals.append(float(snap.hospital_transfers.acute_transfers_this_week))
        return vals

    def evaluate_metric_trend(
        metric_key: str,
        current_val: float,
        unit: str,
        materiality_delta: float,
    ) -> MetricTrendSummary:
        definition = definitions.get(
            metric_key,
            MetricDefinition(
                metric_name=metric_key,
                domain="general",
                display_name=metric_key.replace("_", " ").title(),
                plain_language_meaning="Operational metric indicator.",
                operational_significance="Operational monitoring.",
                benchmark_or_target_desc="Standard target.",
            ),
        )

        series = get_series(metric_key)
        # Avoid duplicate current value if history.snapshots already terminates at snapshot_date
        if (
            history
            and history.snapshots
            and history.snapshots[-1].snapshot_date == snapshot.snapshot_date
        ):
            full_series = series
        else:
            full_series = series + [current_val] if series else [current_val]

        n = len(full_series)
        val_7d_ago = full_series[-8] if n >= 8 else (full_series[0] if n > 1 else None)
        val_14d_ago = (
            full_series[-15] if n >= 15 else (full_series[0] if n > 7 else None)
        )
        val_30d_ago = full_series[0] if n >= 30 else None

        delta_7d = (
            round(current_val - val_7d_ago, 2) if val_7d_ago is not None else None
        )
        delta_30d = (
            round(current_val - val_30d_ago, 2) if val_30d_ago is not None else None
        )

        pct_change_7d = (
            round((delta_7d / val_7d_ago) * 100.0, 1)
            if (val_7d_ago is not None and val_7d_ago != 0)
            else None
        )
        pct_change_30d = (
            round((delta_30d / val_30d_ago) * 100.0, 1)
            if (val_30d_ago is not None and val_30d_ago != 0)
            else None
        )

        last_7 = full_series[-7:] if n >= 7 else full_series
        last_30 = full_series[-30:] if n >= 30 else full_series

        rolling_7d = round(sum(last_7) / len(last_7), 2)
        rolling_30d = round(sum(last_30) / len(last_30), 2)
        min_30 = round(min(last_30), 2)
        max_30 = round(max(last_30), 2)

        if delta_7d is not None and abs(delta_7d) >= materiality_delta:
            direction: Literal["INCREASING", "DECREASING", "STABLE", "VOLATILE"] = (
                "INCREASING" if delta_7d > 0 else "DECREASING"
            )
            is_meaningful = True
        else:
            if (max_30 - min_30) > (materiality_delta * 2.5):
                direction = "VOLATILE"
                is_meaningful = True
            else:
                direction = "STABLE"
                is_meaningful = False

        pct_7d_str = f"{pct_change_7d:+}%" if pct_change_7d is not None else "N/A"

        if delta_7d is not None and val_7d_ago is not None:
            shift_text = (
                f"{definition.display_name} is currently {current_val} {unit} (7d rolling avg: {rolling_7d} {unit}). "
                f"Trailing 7-day delta is {delta_7d:+} {unit} ({pct_7d_str}), shifting from {val_7d_ago} {unit}."
            )
            if val_14d_ago is not None:
                shift_text += f" Trailing 14-day value was {val_14d_ago} {unit}."
            if delta_30d is not None and val_30d_ago is not None:
                shift_text += f" Trailing 30-day change is {delta_30d:+} {unit} (range: {min_30} - {max_30} {unit})."
        else:
            shift_text = f"{definition.display_name} is currently {current_val} {unit} (insufficient historical records for multi-week trajectory)."

        return MetricTrendSummary(
            metric_name=metric_key,
            display_name=definition.display_name,
            domain=definition.domain,
            unit=unit,
            current_value=current_val,
            value_7d_ago=val_7d_ago,
            value_14d_ago=val_14d_ago,
            value_30d_ago=val_30d_ago,
            delta_7d=delta_7d,
            delta_30d=delta_30d,
            pct_change_7d=pct_change_7d,
            pct_change_30d=pct_change_30d,
            rolling_7d_avg=rolling_7d,
            rolling_30d_avg=rolling_30d,
            min_30d=min_30,
            max_30d=max_30,
            trend_direction=direction,
            is_meaningful_shift=is_meaningful,
            shift_summary=shift_text,
        )

    # 1. Census Domain
    c = snapshot.census
    trends["current_census"] = evaluate_metric_trend(
        "current_census",
        float(c.current_census),
        "guests",
        materiality_delta=TREND_CENSUS_MATERIALITY_DELTA,
    )
    trends["occupancy_rate_pct"] = evaluate_metric_trend(
        "occupancy_rate_pct",
        float(c.occupancy_rate_pct),
        "%",
        materiality_delta=TREND_OCCUPANCY_MATERIALITY_DELTA,
    )

    # 2. Admissions & Discharges Flow Domain
    ad = snapshot.admissions_discharges
    trends["net_flow"] = evaluate_metric_trend(
        "net_flow",
        float(ad.net_flow),
        "guests",
        materiality_delta=TREND_NET_FLOW_MATERIALITY_DELTA,
    )

    # 3. Length of Stay Domain
    los = snapshot.length_of_stay
    trends["average_los_days"] = evaluate_metric_trend(
        "average_los_days",
        float(los.average_los_days),
        "days",
        materiality_delta=TREND_LOS_MATERIALITY_DELTA,
    )

    # 4. Nursing Staffing & Operations Domain
    st = snapshot.staffing
    trends["hppd_actual"] = evaluate_metric_trend(
        "hppd_actual",
        float(st.hppd_actual),
        "HPPD",
        materiality_delta=TREND_HPPD_MATERIALITY_DELTA,
    )
    trends["open_shifts_count"] = evaluate_metric_trend(
        "open_shifts_count",
        float(st.open_shifts_count),
        "shifts",
        materiality_delta=TREND_OPEN_SHIFTS_MATERIALITY_DELTA,
    )
    trends["agency_staff_pct"] = evaluate_metric_trend(
        "agency_staff_pct",
        float(st.agency_staff_pct),
        "%",
        materiality_delta=TREND_AGENCY_MATERIALITY_DELTA,
    )

    # 5. Therapy Rehabilitation Delivery Domain
    th = snapshot.therapy
    trends["treatment_completion_rate_pct"] = evaluate_metric_trend(
        "treatment_completion_rate_pct",
        float(th.treatment_completion_rate_pct),
        "%",
        materiality_delta=TREND_THERAPY_MATERIALITY_DELTA,
    )

    # 6. Payer Mix & Authorizations Domain
    pa = snapshot.payer_auth
    trends["expiring_authorizations_48h"] = evaluate_metric_trend(
        "expiring_authorizations_48h",
        float(pa.expiring_authorizations_48h),
        "authorizations",
        materiality_delta=TREND_AUTH_MATERIALITY_DELTA,
    )

    # 7. Hospitality & Guest Experience Domain
    ho = snapshot.hospitality
    trends["dining_satisfaction_score"] = evaluate_metric_trend(
        "dining_satisfaction_score",
        float(ho.dining_satisfaction_score),
        "pts",
        materiality_delta=TREND_DINING_MATERIALITY_DELTA,
    )
    trends["guest_satisfaction_nps"] = evaluate_metric_trend(
        "guest_satisfaction_nps",
        float(ho.guest_satisfaction_nps),
        "NPS",
        materiality_delta=TREND_NPS_MATERIALITY_DELTA,
    )

    # 8. Hospital Transfers & Readmissions Domain
    ht = snapshot.hospital_transfers
    trends["readmission_rate_30d_pct"] = evaluate_metric_trend(
        "readmission_rate_30d_pct",
        float(ht.readmission_rate_30d_pct),
        "%",
        materiality_delta=TREND_READMISSION_MATERIALITY_DELTA,
    )
    trends["acute_transfers_this_week"] = evaluate_metric_trend(
        "acute_transfers_this_week",
        float(ht.acute_transfers_this_week),
        "transfers",
        materiality_delta=TREND_ACUTE_TRANSFERS_MATERIALITY_DELTA,
    )

    for m_trend in trends.values():
        if m_trend.is_meaningful_shift and m_trend.delta_7d is not None:
            meaningful_shifts.append(
                f"{m_trend.display_name}: {m_trend.trend_direction.title()} by {abs(m_trend.delta_7d)} {m_trend.unit} over 7 days ({m_trend.current_value} vs {m_trend.value_7d_ago})."
            )

    return FacilityTrendCalculations(
        facility_id=facility_id,
        scenario=scenario,
        days_analyzed=history_days,
        is_context_sufficient=is_sufficient,
        metric_definitions=definitions,
        trends=trends,
        meaningful_shifts=meaningful_shifts,
        context_limitations=limitations,
    )
