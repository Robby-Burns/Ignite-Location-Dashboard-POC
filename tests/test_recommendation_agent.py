"""Tests for Story 2.5 — Generate Data-Grounded Recommendations.

Verifies:
- AC-2.5.1: Each recommendation identifies why it was suggested (rationale & supporting data evidence).
- AC-2.5.2: Changing relevant source data dynamically changes the resulting recommendations across scenarios.
- AC-2.5.3 / FR-009: Recommendations are clearly presented as decision-support suggestions for human leadership review.
- Invariants: Strict numerical grounding (INV-002, AC-2.1.2), zero hardcoding (INV-001), zero PHI (INV-008), Spec §8 offline fallback.
- REST API: GET /api/agent/recommendations endpoint.
"""

from __future__ import annotations

from unittest.mock import patch

import httpx
import pytest

from src.agent.llm_client import LLMClient
from src.agent.recommendation_agent import (
    FacilityRecommendationAgent,
    RecommendationReport,
)
from src.data.loader import DatasetUnavailableError


@pytest.mark.asyncio
async def test_ac2_5_1_every_recommendation_has_rationale_and_evidence() -> None:
    """AC-2.5.1: Verify every generated recommendation includes explicit rationale and supporting metrics."""
    agent = FacilityRecommendationAgent()
    report = await agent.generate_recommendations(
        "ignite-oak-brook", scenario="staffing_stress"
    )

    assert isinstance(report, RecommendationReport)
    assert len(report.verified_recommendations_summary.recommendations) > 0

    for rec in report.verified_recommendations_summary.recommendations:
        assert rec.action_title, "Recommendation must have a title"
        assert rec.suggested_action_description, (
            "Recommendation must have actionable steps"
        )
        assert rec.rationale, "AC-2.5.1: Recommendation must state why it was suggested"
        assert len(rec.supporting_evidence_metrics) > 0, (
            "AC-2.5.1: Recommendation must cite supporting metrics"
        )
        assert rec.expected_operational_impact, (
            "Recommendation must state expected impact"
        )
        assert rec.target_role_or_department, (
            "Recommendation must be assigned to a departmental leader"
        )


@pytest.mark.asyncio
async def test_ac2_5_2_changing_source_data_dynamically_alters_recommendations() -> (
    None
):
    """AC-2.5.2: Verify changing scenario data changes generated recommendations (no hardcoded responses)."""
    agent = FacilityRecommendationAgent()

    # 1. Staffing Stress: Must prioritize nursing coverage & shift mobilization
    staff_report = await agent.generate_recommendations(
        "ignite-oak-brook", scenario="staffing_stress"
    )
    staff_domains = {
        r.domain for r in staff_report.verified_recommendations_summary.recommendations
    }
    assert "staffing" in staff_domains
    staff_titles = [
        r.action_title.lower()
        for r in staff_report.verified_recommendations_summary.recommendations
    ]
    assert any("nursing" in t or "shift" in t or "hppd" in t for t in staff_titles)

    # 2. Hospital Transfer Spike: Must prioritize acute transfer review / INTERACT protocols
    transfer_report = await agent.generate_recommendations(
        "ignite-oak-brook", scenario="hospital_transfer_spike"
    )
    transfer_domains = {
        r.domain
        for r in transfer_report.verified_recommendations_summary.recommendations
    }
    assert "hospital_transfers" in transfer_domains
    transfer_titles = [
        r.action_title.lower()
        for r in transfer_report.verified_recommendations_summary.recommendations
    ]
    assert any(
        "transfer" in t or "interact" in t or "readmission" in t
        for t in transfer_titles
    )

    # 3. Auth Cliff: Must prioritize payer re-authorizations
    auth_report = await agent.generate_recommendations(
        "ignite-oak-brook", scenario="auth_cliff"
    )
    auth_domains = {
        r.domain for r in auth_report.verified_recommendations_summary.recommendations
    }
    assert "payer_auth" in auth_domains
    auth_titles = [
        r.action_title.lower()
        for r in auth_report.verified_recommendations_summary.recommendations
    ]
    assert any(
        "authorization" in t or "re-auth" in t or "payer" in t for t in auth_titles
    )

    # Recommendations across scenarios must be materially distinct
    assert staff_titles != transfer_titles
    assert staff_titles != auth_titles


@pytest.mark.asyncio
async def test_ac2_5_3_decision_support_framing_and_human_authority() -> None:
    """AC-2.5.3 / FR-009: Verify output explicitly maintains human decision authority and avoids autonomous execution claims."""
    agent = FacilityRecommendationAgent()
    report = await agent.generate_recommendations(
        "ignite-oak-brook", scenario="staffing_stress"
    )

    # 1. Report-level decision authority notice
    assert (
        "human" in report.decision_authority_notice.lower()
        or "leadership review" in report.decision_authority_notice.lower()
    )

    # 2. Every recommendation includes governance disclaimer
    for rec in report.verified_recommendations_summary.recommendations:
        assert "decision-support" in rec.governance_disclaimer.lower()
        assert (
            "does not replace" in rec.governance_disclaimer.lower()
            or "human" in rec.governance_disclaimer.lower()
        )

    # 3. No autonomous claims
    report_json = report.model_dump_json().lower()
    prohibited_claims = [
        "action executed",
        "system decided",
        "automatically resolved",
        "dispatched nurse",
    ]
    for claim in prohibited_claims:
        assert claim not in report_json, f"Prohibited autonomous claim found: {claim}"


@pytest.mark.asyncio
async def test_ac2_5_strict_numerical_grounding_reconciliation() -> None:
    """AC-2.1.2 / INV-002: Verify reconciler detects and purges hallucinated numbers in recommendation reports."""
    hallucinated_llm_response = {
        "executive_action_plan_overview": "Ignite Oak Brook must immediately execute 9999 critical interventions to save 8888 patients.",
        "recommended_action_priorities": [
            {
                "domain": "staffing",
                "action_title": "Hire 7777 agency nurses immediately",
                "suggested_action": "Fill 5555 open shifts with emergency bonuses.",
                "rationale": "Direct hours fell by 4444 HPPD.",
                "expected_impact": "Recovers 3333 beds.",
            }
        ],
    }

    client = LLMClient(api_key="mock-api-key", model="gemini-2.0-flash")
    with patch.object(
        client, "_call_gemini_api", return_value=hallucinated_llm_response
    ):
        agent = FacilityRecommendationAgent(llm_client=client)
        report = await agent.generate_recommendations(
            "ignite-oak-brook", scenario="staffing_stress"
        )

        # 1. Hallucinated numbers (9999, 8888, 7777, 5555, 4444, 3333) MUST NOT be present
        assert "9999" not in report.executive_action_plan_overview
        assert "8888" not in report.executive_action_plan_overview

        # 2. Reconciler notice must be recorded
        assert "Reconciliation Notice" in report.data_limitations_and_uncertainty


@pytest.mark.asyncio
async def test_spec_section_8_offline_recommendations_fallback() -> None:
    """Spec §8: Verify that when API key is missing, agent returns AI_ANALYSIS_UNAVAILABLE without fake AI claims."""
    client = LLMClient()  # No API key
    agent = FacilityRecommendationAgent(llm_client=client)

    report = await agent.generate_recommendations(
        "ignite-oak-brook", scenario="staffing_stress"
    )

    assert report.analysis_state == "AI_ANALYSIS_UNAVAILABLE"
    assert report.audit_receipt.is_live_call is False
    assert "AI interpretation is offline" in report.executive_action_plan_overview
    assert len(report.top_priority_recommendations) > 0
    assert len(report.departmental_action_items) > 0


@pytest.mark.asyncio
async def test_boundary_no_phi_in_recommendation_output() -> None:
    """INV-008: Verify recommendation output contains 0 patient names or health identifiers."""
    agent = FacilityRecommendationAgent()
    report = await agent.generate_recommendations(
        "ignite-oak-brook", scenario="staffing_stress"
    )
    output_text = report.model_dump_json().lower()

    prohibited_terms = [
        "ssn",
        "mrn",
        "patient_name",
        "date_of_birth",
        "john doe",
        "jane doe",
    ]
    for term in prohibited_terms:
        assert term not in output_text, f"Potential PHI leakage detected: {term}"


@pytest.mark.asyncio
async def test_failure_behavior_unavailable_facility_raises_error() -> None:
    """Failure behavior: Requesting recommendations for unknown facility raises DatasetUnavailableError."""
    agent = FacilityRecommendationAgent()
    with pytest.raises(DatasetUnavailableError):
        await agent.generate_recommendations("non-existent-facility-xyz")


@pytest.mark.asyncio
async def test_fastapi_recommendations_endpoint() -> None:
    """Verify REST API endpoint GET /api/agent/recommendations."""
    from src.api.main import app

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        res = await client.get(
            "/api/agent/recommendations",
            params={
                "facility_id": "ignite-oak-brook",
                "scenario": "staffing_stress",
                "days_history": 30,
            },
        )
        assert res.status_code == 200
        data = res.json()
        assert data["facility_id"] == "ignite-oak-brook"
        assert "verified_recommendations_summary" in data
        assert (
            data["verified_recommendations_summary"]["total_recommendations_count"] > 0
        )
        assert len(data["top_priority_recommendations"]) > 0
        assert len(data["departmental_action_items"]) > 0
