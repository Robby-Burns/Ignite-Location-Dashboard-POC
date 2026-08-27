"""Analytical calculation schemas for deterministic facility data processing."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field


class MetricObservation(BaseModel):
    """A deterministic numerical observation with mathematical delta and status."""

    metric_name: str = Field(..., description="Machine readable metric identifier")
    display_name: str = Field(..., description="Human-friendly metric label")
    value: float = Field(..., description="Current calculated or recorded value")
    unit: str = Field(
        default="", description="Measurement unit (e.g. '%', 'beds', 'hours', 'guests')"
    )
    target_or_budget: float | None = Field(
        None, description="Target, budget, or benchmark value if available"
    )
    delta_vs_target: float | None = Field(
        None, description="Variance against target/budget"
    )
    delta_vs_prev_day: float | None = Field(None, description="Day-over-day change")
    delta_vs_prev_week: float | None = Field(None, description="Week-over-week change")
    trend_direction: Literal["UP", "DOWN", "STABLE"] = Field(
        default="STABLE", description="Directional trend"
    )
    status: Literal["POSITIVE", "NEUTRAL", "ATTENTION", "CRITICAL"] = Field(
        default="NEUTRAL", description="Operational status evaluation"
    )


class DomainCalculationSummary(BaseModel):
    """Calculated metrics and observations for a specific operational area."""

    domain: str = Field(
        ..., description="Domain identifier (e.g. 'census', 'staffing')"
    )
    domain_display_name: str = Field(
        ..., description="Domain title (e.g. 'Census & Capacity')"
    )
    metrics: dict[str, MetricObservation] = Field(
        default_factory=dict, description="Key metric observations"
    )
    key_findings: list[str] = Field(
        default_factory=list, description="Data-grounded bullet findings"
    )
    risk_level: Literal["LOW", "MEDIUM", "HIGH"] = Field(
        default="LOW", description="Assessed operational risk"
    )


class CrossDomainCorrelation(BaseModel):
    """Correlation or inter-departmental interaction between operational domains."""

    domains: list[str] = Field(..., description="List of related domain names")
    finding_summary: str = Field(
        ..., description="Brief statement of the correlated condition"
    )
    evidence_facts: list[str] = Field(
        ..., description="Supporting source metrics and deltas"
    )
    impact_level: Literal["INFO", "MODERATE", "CRITICAL"] = Field(
        default="INFO", description="Impact severity"
    )


class FacilityCalculations(BaseModel):
    """Comprehensive verified calculations for a facility snapshot."""

    facility_id: str = Field(..., description="Facility identifier")
    facility_name: str = Field(..., description="Facility name")
    snapshot_date: str = Field(..., description="Snapshot date in ISO format")
    scenario: str = Field(default="baseline", description="Operational scenario name")
    domains: dict[str, DomainCalculationSummary] = Field(
        default_factory=dict, description="Domain calculation summaries"
    )
    correlations: list[CrossDomainCorrelation] = Field(
        default_factory=list, description="Cross-domain operational interactions"
    )
    calculation_timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Calculation UTC timestamp",
    )
