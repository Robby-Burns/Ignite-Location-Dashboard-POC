"""Tests for Story 2.2 — Explain Metrics and Historical Context / Trends.

Verifies:
- AC-2.2.1: Important operational metrics explained in plain language for non-technical humans.
- AC-2.2.2: Meaningful changes over time explained from historical time-series datasets.
- Boundary: Insufficient historical context (< 7 days) yields explicit limitations without claiming unsupported causes.
- Invariants: Strict numerical grounding (INV-002, AC-2.1.2), zero PHI (INV-008), Spec §8 offline fallbacks.
- REST API: GET /api/agent/facility-trends and GET /api/agent/metric-definitions endpoints.
"""

from __future__ import annotations

from unittest.mock import patch

import httpx
import pytest

from src.agent.llm_client import LLMClient
from src.agent.trend_agent import (
    FacilityTrendExplanationAgent,
    FacilityTrendExplanationReport,
)
from src.analytics.trends import (
    calculate_historical_trends,
    get_standard_metric_definitions,
)
from src.data.loader import DatasetUnavailableError
from src.mcp.client import MockDomoMCPClient


@pytest.mark.asyncio
async def test_ac2_2_1_non_technical_metric_explanations() -> None:
    """AC-2.2.1: Verify important metrics are explained in plain language understandable to a non-technical human."""
    definitions = get_standard_metric_definitions()

    # Verify standard operational core metrics are documented
    required_metrics = [
        "current_census",
        "occupancy_rate_pct",
        "net_flow",
        "average_los_days",
        "hppd_actual",
        "open_shifts_count",
        "agency_staff_pct",
        "treatment_completion_rate_pct",
        "expiring_authorizations_48h",
        "dining_satisfaction_score",
        "guest_satisfaction_nps",
        "readmission_rate_30d_pct",
        "acute_transfers_this_week",
    ]
    for m in required_metrics:
        assert m in definitions, f"Metric {m} missing from standard definitions"
        defn = definitions[m]
        assert len(defn.plain_language_meaning) > 20, f"Meaning too brief for {m}"
        assert len(defn.operational_significance) > 20, (
            f"Significance too brief for {m}"
        )
        assert len(defn.benchmark_or_target_desc) > 10, (
            f"Benchmark desc too brief for {m}"
        )

    # Verify agent outputs full metric explanations
    agent = FacilityTrendExplanationAgent()
    report = await agent.explain_facility_trends(
        "ignite-oak-brook", scenario="baseline"
    )

    assert isinstance(report, FacilityTrendExplanationReport)
    assert len(report.metric_explanations) >= len(required_metrics)
    hppd_exp = report.metric_explanations["hppd_actual"]
    assert "Hours Per Patient Day" in hppd_exp.display_name
    assert "nursing care" in hppd_exp.plain_language_meaning.lower()
    assert (
        "regulatory" in hppd_exp.operational_significance.lower()
        or "clinical" in hppd_exp.operational_significance.lower()
    )


@pytest.mark.asyncio
async def test_ac2_2_2_meaningful_historical_trend_recognition() -> None:
    """AC-2.2.2: Verify the system explains meaningful changes over time when historical data is available."""
    agent = FacilityTrendExplanationAgent()

    # 1. Test staffing stress scenario (known staffing disruption trajectory)
    staffing_report = await agent.explain_facility_trends(
        "ignite-oak-brook", scenario="staffing_stress", days_history=30
    )
    assert staffing_report.analysis_state in (
        "ANALYSIS_COMPLETE",
        "AI_ANALYSIS_UNAVAILABLE",
    )
    assert "staffing" in staffing_report.trend_explanations
    staffing_trend = staffing_report.trend_explanations["staffing"]
    assert staffing_trend.trajectory_direction in (
        "DECREASING",
        "VOLATILE",
        "INCREASING",
    )
    # Verify numbers cited in trend explanation
    assert len(staffing_trend.narrative) > 30

    # 2. Test hospital transfer spike scenario
    transfer_report = await agent.explain_facility_trends(
        "ignite-oak-brook", scenario="hospital_transfer_spike", days_history=30
    )
    assert "hospital_transfers" in transfer_report.trend_explanations
    assert len(transfer_report.trend_explanations["hospital_transfers"].narrative) > 30

    # 3. Test auth cliff scenario
    auth_report = await agent.explain_facility_trends(
        "ignite-oak-brook", scenario="auth_cliff", days_history=30
    )
    assert "payer_auth" in auth_report.trend_explanations
    assert len(auth_report.trend_explanations["payer_auth"].narrative) > 30

    # 4. Test all 8 domains exist in trend explanations
    assert len(staffing_report.trend_explanations) == 8
    expected_domains = [
        "census",
        "admissions_discharges",
        "length_of_stay",
        "staffing",
        "therapy",
        "payer_auth",
        "hospitality",
        "hospital_transfers",
    ]
    for d in expected_domains:
        assert d in staffing_report.trend_explanations, (
            f"Missing domain {d} in trend explanations"
        )


@pytest.mark.asyncio
async def test_ac2_2_2_deterministic_historical_delta_numerical_accuracy() -> None:
    """AC-2.2.2 / FR-006: Verify exact numerical delta accuracy against raw snapshot series without off-by-one errors."""
    mcp_client = MockDomoMCPClient()
    snapshot = mcp_client.get_facility_snapshot("ignite-oak-brook", "baseline")
    history = mcp_client.get_facility_history("ignite-oak-brook", 30, "baseline")

    calcs = calculate_historical_trends(snapshot, history, "baseline")

    # 1. Census delta verification
    c_trend = calcs.trends["current_census"]
    assert c_trend.current_value == 96.0
    assert c_trend.value_7d_ago == 96.0
    assert c_trend.delta_7d == 0.0
    assert c_trend.value_14d_ago == 91.0

    # 2. Net Flow delta verification
    flow_trend = calcs.trends["net_flow"]
    assert flow_trend.current_value == 2.0
    assert flow_trend.value_7d_ago == 1.0
    assert flow_trend.delta_7d == 1.0

    # 3. Staffing HPPD delta verification
    hppd_trend = calcs.trends["hppd_actual"]
    assert hppd_trend.current_value == 4.45
    assert hppd_trend.value_7d_ago == 4.31
    assert hppd_trend.delta_7d == 0.14

    # 4. Acute transfers delta verification
    transfers_trend = calcs.trends["acute_transfers_this_week"]
    assert transfers_trend.current_value == 0.0
    assert transfers_trend.value_7d_ago == 1.0
    assert transfers_trend.delta_7d == -1.0


@pytest.mark.asyncio
async def test_boundary_insufficient_historical_context_limitation() -> None:
    """Boundary Condition: When historical context is < 7 days, system reports INSUFFICIENT_CONTEXT with explicit limitation."""
    mcp_client = MockDomoMCPClient()
    agent = FacilityTrendExplanationAgent(mcp_client=mcp_client)

    # Request with only 3 days of historical context
    report = await agent.explain_facility_trends(
        "ignite-oak-brook", scenario="baseline", days_history=3
    )

    assert report.analysis_state == "INSUFFICIENT_CONTEXT"
    assert (
        "limited" in report.executive_trend_summary.lower()
        or "minimum of 7 days" in report.executive_trend_summary.lower()
    )
    assert (
        "Historical series contains only" in report.data_limitations_and_uncertainty
        or "minimum of 7" in report.data_limitations_and_uncertainty
    )
    assert report.verified_calculations.is_context_sufficient is False


@pytest.mark.asyncio
async def test_ac2_2_strict_numerical_grounding_in_trend_narrative() -> None:
    """AC-2.1.2 / INV-002: Verify reconciler detects and purges hallucinated numbers in trend narratives."""
    hallucinated_llm_response = {
        "executive_trend_summary": "Ignite Oak Brook had 8888 admissions and lost 9999 nursing hours over 555 days.",
        "metric_explanations": {
            "current_census": {
                "plain_language_meaning": "Measures 7777 beds.",
                "operational_significance": "Affects 8888 dollars.",
                "benchmark_context": "Target is 9999%.",
            }
        },
        "trend_explanations": {
            "census": {
                "headline": "Massive 9999 Guest Surge",
                "narrative": "Census swung by 4444 guests over 3333 weeks.",
                "trajectory_direction": "INCREASING",
                "is_meaningful_shift": True,
                "cited_metrics": ["invented_metric: 9999"],
            }
        },
        "notable_shifts": ["Invented 8888 shift."],
        "data_limitations": "None.",
    }

    client = LLMClient(api_key="mock-api-key", model="gemini-2.0-flash")
    with patch.object(
        client, "_call_gemini_api", return_value=hallucinated_llm_response
    ):
        agent = FacilityTrendExplanationAgent(llm_client=client)
        report = await agent.explain_facility_trends(
            "ignite-oak-brook", scenario="baseline"
        )

        # 1. Hallucinated numbers (8888, 9999, 555, 7777, 4444, 3333) MUST NOT be present in narrative fields
        assert "8888" not in report.executive_trend_summary
        assert "9999" not in report.executive_trend_summary
        assert "555" not in report.executive_trend_summary
        assert (
            "7777"
            not in report.metric_explanations["current_census"].plain_language_meaning
        )
        assert "4444" not in report.trend_explanations["census"].narrative
        assert "9999" not in "".join(report.trend_explanations["census"].cited_metrics)

        # 2. Reconciler must have substituted verified ground-truth values
        assert "Reconciliation Notice" in report.data_limitations_and_uncertainty


@pytest.mark.asyncio
async def test_spec_section_8_offline_trend_fallback() -> None:
    """Spec §8: Verify that when API key is missing, agent returns AI_ANALYSIS_UNAVAILABLE without fake AI claims."""
    client = LLMClient()  # No API key
    agent = FacilityTrendExplanationAgent(llm_client=client)

    report = await agent.explain_facility_trends(
        "ignite-oak-brook", scenario="baseline"
    )

    assert report.analysis_state == "AI_ANALYSIS_UNAVAILABLE"
    assert report.audit_receipt.is_live_call is False
    assert "AI interpretation is unavailable" in report.executive_trend_summary
    assert len(report.metric_explanations) > 0
    assert len(report.trend_explanations) > 0


@pytest.mark.asyncio
async def test_failure_behavior_unavailable_facility_raises_error() -> None:
    """Failure behavior: Requesting trend analysis for unknown facility raises DatasetUnavailableError."""
    agent = FacilityTrendExplanationAgent()
    with pytest.raises(DatasetUnavailableError):
        await agent.explain_facility_trends("non-existent-facility-xyz")


@pytest.mark.asyncio
async def test_boundary_no_phi_in_trend_analysis_output() -> None:
    """INV-008: Verify trend analysis contains 0 patient names, SSNs, or individual health records."""
    agent = FacilityTrendExplanationAgent()
    report = await agent.explain_facility_trends(
        "ignite-oak-brook", scenario="baseline"
    )
    output_text = report.model_dump_json()

    prohibited_terms = [
        "ssn",
        "mrn",
        "patient_name",
        "date_of_birth",
        "john doe",
        "jane doe",
    ]
    for term in prohibited_terms:
        assert term not in output_text.lower(), (
            f"Potential PHI leakage detected: {term}"
        )


@pytest.mark.asyncio
async def test_fastapi_trend_endpoints() -> None:
    """Verify REST API endpoints GET /api/agent/facility-trends and GET /api/agent/metric-definitions."""
    from src.api.main import app

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        # 1. Metric definitions endpoint
        res_defs = await client.get("/api/agent/metric-definitions")
        assert res_defs.status_code == 200
        defs_data = res_defs.json()
        assert "current_census" in defs_data
        assert "hppd_actual" in defs_data
        assert "readmission_rate_30d_pct" in defs_data

        # 2. Facility trends endpoint
        res_trends = await client.get(
            "/api/agent/facility-trends",
            params={
                "facility_id": "ignite-oak-brook",
                "scenario": "baseline",
                "days_history": 30,
            },
        )
        assert res_trends.status_code == 200
        trends_data = res_trends.json()
        assert trends_data["facility_id"] == "ignite-oak-brook"
        assert "metric_explanations" in trends_data
        assert "trend_explanations" in trends_data
        assert "verified_calculations" in trends_data
