"""Unit and integration tests for Story 2.1 — Analyze Facility State.

Verifies:
- AC-2.1.1: The system produces a human-readable facility summary from current data.
- AC-2.1.2: Summary does not introduce numbers not present in source data or calculations.
- Rejection / Boundary: Zero PHI, no hardcoded scenario templates (INV-001, FR-008).
- Failure Behavior: Identifies unavailable information and limits analysis gracefully.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from src.agent.llm_client import LLMClient
from src.agent.state_agent import FacilityStateAgent, FacilityStateAnalysis
from src.data.loader import DatasetUnavailableError, FacilityDataLoader
from src.mcp.client import MockDomoMCPClient
from src.mcp.server import MockDomoMCPServer


@pytest.fixture
def data_loader() -> FacilityDataLoader:
    return FacilityDataLoader()


@pytest.fixture
def mcp_server(data_loader: FacilityDataLoader) -> MockDomoMCPServer:
    return MockDomoMCPServer(data_loader=data_loader)


@pytest.fixture
def mcp_client(mcp_server: MockDomoMCPServer) -> MockDomoMCPClient:
    return MockDomoMCPClient(server=mcp_server)


@pytest.fixture
def state_agent(mcp_client: MockDomoMCPClient) -> FacilityStateAgent:
    return FacilityStateAgent(mcp_client=mcp_client)


@pytest.mark.asyncio
async def test_ac2_1_1_human_readable_facility_summary_generated(
    state_agent: FacilityStateAgent,
) -> None:
    """AC-2.1.1: Verify agent produces a human-readable facility summary from current data."""
    analysis: FacilityStateAnalysis = await state_agent.analyze_facility_state(
        facility_id="ignite-oak-brook",
        scenario="baseline",
    )

    assert analysis.facility_id == "ignite-oak-brook"
    assert "Oak Brook" in analysis.facility_name
    assert len(analysis.executive_summary) > 50
    assert analysis.overall_health_score >= 0 and analysis.overall_health_score <= 100
    assert analysis.overall_status in [
        "OPTIMAL",
        "STABLE",
        "ATTENTION_REQUIRED",
        "CRITICAL_RISK",
    ]

    # Verify all 8 domain narratives are present and readable
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
    for domain in expected_domains:
        assert domain in analysis.domain_narratives, (
            f"Missing domain narrative: {domain}"
        )
        narrative = analysis.domain_narratives[domain]
        assert len(narrative.headline) > 0
        assert len(narrative.narrative) > 20
        assert narrative.status in ["POSITIVE", "NEUTRAL", "ATTENTION", "CRITICAL"]

    # Verify audit receipt
    assert analysis.audit_receipt.receipt_id.startswith("REC-LLM-")
    assert analysis.audit_receipt.latency_ms >= 0


@pytest.mark.asyncio
async def test_ac2_1_2_strict_numerical_grounding_and_traceability(
    state_agent: FacilityStateAgent,
    data_loader: FacilityDataLoader,
) -> None:
    """AC-2.1.2: Verify that numbers in calculations trace exactly to source data and documented calculations."""
    snapshot = data_loader.get_snapshot("ignite-oak-brook", scenario="baseline")
    analysis: FacilityStateAnalysis = await state_agent.analyze_facility_state(
        facility_id="ignite-oak-brook",
        scenario="baseline",
    )

    calcs = analysis.verified_calculations

    # 1. Census grounding
    census_m = calcs.domains["census"].metrics
    assert census_m["current_census"].value == snapshot.census.current_census
    assert census_m["occupancy_rate_pct"].value == snapshot.census.occupancy_rate_pct
    assert census_m["available_beds"].value == snapshot.census.available_beds
    # Check calculated delta
    target_census = snapshot.census.budgeted_target_census or 90.0
    assert census_m["current_census"].delta_vs_target == round(
        snapshot.census.current_census - target_census, 1
    )

    # 2. Staffing grounding
    staff_m = calcs.domains["staffing"].metrics
    assert staff_m["hppd_actual"].value == snapshot.staffing.hppd_actual
    assert staff_m["open_shifts_count"].value == snapshot.staffing.open_shifts_count
    assert staff_m["agency_staff_pct"].value == snapshot.staffing.agency_staff_pct
    # Check calculated variance
    expected_hppd_delta = round(
        snapshot.staffing.hppd_actual - snapshot.staffing.hppd_budgeted_target, 2
    )
    assert staff_m["hppd_actual"].delta_vs_target == expected_hppd_delta

    # 3. Therapy grounding
    therapy_m = calcs.domains["therapy"].metrics
    assert (
        therapy_m["treatment_completion_rate_pct"].value
        == snapshot.therapy.treatment_completion_rate_pct
    )
    assert (
        therapy_m["avg_daily_treatment_minutes_delivered"].value
        == snapshot.therapy.avg_daily_treatment_minutes_delivered
    )

    # 4. Payer auth grounding
    payer_m = calcs.domains["payer_auth"].metrics
    assert (
        payer_m["expiring_authorizations_48h"].value
        == snapshot.payer_auth.expiring_authorizations_48h
    )

    # 5. Hospital transfers grounding
    transfer_m = calcs.domains["hospital_transfers"].metrics
    assert (
        transfer_m["readmission_rate_30d_pct"].value
        == snapshot.hospital_transfers.readmission_rate_30d_pct
    )
    assert (
        transfer_m["acute_transfers_this_week"].value
        == snapshot.hospital_transfers.acute_transfers_this_week
    )


@pytest.mark.asyncio
async def test_dynamic_scenario_sensitivity_no_hardcoding(
    state_agent: FacilityStateAgent,
) -> None:
    """INV-001 / FR-008: Verify that changing source data changes the findings and risk levels dynamically."""
    baseline_analysis = await state_agent.analyze_facility_state(
        facility_id="ignite-oak-brook", scenario="baseline"
    )
    staffing_stress_analysis = await state_agent.analyze_facility_state(
        facility_id="ignite-oak-brook", scenario="staffing_stress"
    )
    auth_cliff_analysis = await state_agent.analyze_facility_state(
        facility_id="ignite-oak-brook", scenario="auth_cliff"
    )

    # 1. Health scores must respond to operational conditions
    assert (
        baseline_analysis.overall_health_score
        > staffing_stress_analysis.overall_health_score
    )
    assert (
        baseline_analysis.overall_health_score
        > auth_cliff_analysis.overall_health_score
    )

    # 2. Staffing domain risk must escalate under staffing stress
    assert (
        baseline_analysis.verified_calculations.domains["staffing"].risk_level == "LOW"
    )
    assert (
        staffing_stress_analysis.verified_calculations.domains["staffing"].risk_level
        == "HIGH"
    )

    # 3. Payer auth risk must escalate under auth cliff
    assert (
        baseline_analysis.verified_calculations.domains["payer_auth"].risk_level
        == "LOW"
    )
    assert (
        auth_cliff_analysis.verified_calculations.domains["payer_auth"].risk_level
        == "HIGH"
    )

    # 4. Cross-domain correlations must trigger on real data conditions
    assert len(staffing_stress_analysis.cross_domain_findings) > 0
    assert any(
        "staffing" in f.lower() or "therapy" in f.lower()
        for f in staffing_stress_analysis.cross_domain_findings
    )


@pytest.mark.asyncio
async def test_llm_invocation_with_mocked_external_api() -> None:
    """Verify that when external LLM API is available, the agent calls it and integrates structured output."""
    mock_llm_response = {
        "executive_summary": "Ignite Oak Brook demonstrates solid overall operational performance with 95 occupied beds out of 110 capacity.",
        "domain_narratives": {
            "census": {
                "headline": "Strong Occupancy Exceeding Budget",
                "narrative": "Census is at 95 guests out of 110 capacity, yielding 86.4% occupancy.",
                "key_metrics_cited": [
                    "current_census: 95",
                    "occupancy_rate_pct: 86.4%",
                ],
                "status": "POSITIVE",
            }
        },
        "cross_domain_findings": [
            "Census remains stable while therapy targets are met."
        ],
        "data_limitations": "Complete 30-day history available.",
    }

    client = LLMClient(api_key="mock-api-key", model="gemini-2.0-flash")
    with patch.object(client, "_call_gemini_api", return_value=mock_llm_response):
        agent = FacilityStateAgent(llm_client=client)
        analysis = await agent.analyze_facility_state(
            "ignite-oak-brook", scenario="baseline"
        )

        assert analysis.audit_receipt.is_live_call is True
        assert analysis.audit_receipt.provider == "google-gemini"
        assert analysis.analysis_state == "ANALYSIS_COMPLETE"
        assert (
            "Ignite Oak Brook demonstrates solid overall operational performance"
            in analysis.executive_summary
        )
        assert analysis.overall_health_score == 93


@pytest.mark.asyncio
async def test_openrouter_llm_invocation_with_mocked_api() -> None:
    """Verify that OpenRouter API client correctly integrates structured analysis and receipts."""
    mock_llm_response = {
        "executive_summary": "Ignite Oak Brook demonstrates solid overall operational performance with 95 occupied beds out of 110 capacity.",
        "domain_narratives": {
            "census": {
                "headline": "Strong Occupancy Exceeding Budget",
                "narrative": "Census is at 95 guests out of 110 capacity, yielding 86.4% occupancy.",
                "key_metrics_cited": [
                    "current_census: 95",
                    "occupancy_rate_pct: 86.4%",
                ],
                "status": "POSITIVE",
            }
        },
        "cross_domain_findings": [
            "Census remains stable while therapy targets are met."
        ],
        "data_limitations": "Complete 30-day history available.",
    }

    client = LLMClient(
        api_key="sk-or-v1-mock-key",
        model="google/gemini-2.5-flash",
        provider="openrouter",
    )
    with patch.object(client, "_call_openrouter_api", return_value=mock_llm_response):
        agent = FacilityStateAgent(llm_client=client)
        analysis = await agent.analyze_facility_state(
            "ignite-oak-brook", scenario="baseline"
        )

        assert analysis.audit_receipt.is_live_call is True
        assert analysis.audit_receipt.provider == "openrouter"
        assert analysis.audit_receipt.model == "google/gemini-2.5-flash"
        assert analysis.analysis_state == "ANALYSIS_COMPLETE"
        assert (
            "Ignite Oak Brook demonstrates solid overall operational performance"
            in analysis.executive_summary
        )
        assert analysis.overall_health_score == 93


@pytest.mark.asyncio
async def test_ac2_1_2_llm_hallucination_reconciliation_and_sanitization() -> None:
    """AC-2.1.2 / F-1: Verify that LLM-invented numbers are detected and sanitized by NumericalGroundingReconciler."""
    hallucinated_llm_response = {
        "executive_summary": "Ignite Oak Brook has 999 guests out of 2000 capacity with 450 nurses on duty.",
        "domain_narratives": {
            "census": {
                "headline": "Fictional Census Surge",
                "narrative": "Census reached 999 guests with 1200 admissions today.",
                "key_metrics_cited": ["current_census: 999"],
                "status": "CRITICAL",
            }
        },
        "cross_domain_findings": ["Fictional cross-departmental correlation."],
        "data_limitations": "None.",
    }

    client = LLMClient(api_key="mock-api-key", model="gemini-2.0-flash")
    with patch.object(
        client, "_call_gemini_api", return_value=hallucinated_llm_response
    ):
        agent = FacilityStateAgent(llm_client=client)
        analysis = await agent.analyze_facility_state(
            "ignite-oak-brook", scenario="baseline"
        )

        # 1. Hallucinated numbers (999, 2000, 450, 1200) MUST NOT be present in narrative fields
        assert "999" not in analysis.executive_summary
        assert "999" not in analysis.domain_narratives["census"].narrative
        assert "999" not in "".join(
            analysis.domain_narratives["census"].key_metrics_cited
        )
        assert "2000" not in analysis.executive_summary
        assert "450" not in analysis.executive_summary
        assert "1200" not in analysis.domain_narratives["census"].narrative

        # 2. Reconciler must have substituted verified ground-truth values
        assert (
            "95" in analysis.executive_summary or "86.4" in analysis.executive_summary
        )
        assert "Reconciliation Notice" in analysis.data_limitations_and_uncertainty
        assert analysis.overall_health_score == 93


@pytest.mark.asyncio
async def test_spec_section_8_offline_ai_unavailable_state(
    state_agent: FacilityStateAgent,
) -> None:
    """Spec §8 / F-2: Verify explicit AI_ANALYSIS_UNAVAILABLE state when external AI is offline."""
    analysis = await state_agent.analyze_facility_state(
        facility_id="ignite-oak-brook", scenario="baseline"
    )

    assert analysis.analysis_state == "AI_ANALYSIS_UNAVAILABLE"
    assert analysis.audit_receipt.is_live_call is False
    assert "AI interpretation is unavailable" in analysis.executive_summary
    assert len(analysis.domain_narratives) == 8
    assert analysis.overall_health_score == 93


@pytest.mark.asyncio
async def test_failure_behavior_unavailable_facility_raises_error(
    state_agent: FacilityStateAgent,
) -> None:
    """Failure behavior: Agent rejects non-existent facility with DatasetUnavailableError."""
    with pytest.raises(DatasetUnavailableError):
        await state_agent.analyze_facility_state(facility_id="invalid-facility-999")


@pytest.mark.asyncio
async def test_boundary_no_phi_in_analysis_output(
    state_agent: FacilityStateAgent,
) -> None:
    """INV-008: Verify analysis contains aggregate statistics only with zero patient PHI."""
    analysis = await state_agent.analyze_facility_state(
        "ignite-oak-brook", scenario="baseline"
    )
    output_json = analysis.model_dump_json()

    forbidden_tokens = [
        "mrn",
        "patient_name",
        "ssn",
        "date_of_birth",
        "dob",
        "social security",
    ]
    for token in forbidden_tokens:
        assert token not in output_json.lower()


@pytest.mark.asyncio
async def test_fastapi_analyze_facility_state_endpoint() -> None:
    """Verify REST API endpoint GET /api/agent/facility-state."""
    import httpx

    from src.api.main import app

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get(
            "/api/agent/facility-state?facility_id=ignite-oak-brook&scenario=baseline"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["facility_id"] == "ignite-oak-brook"
        assert len(data["executive_summary"]) > 30
        assert "census" in data["domain_narratives"]
        assert data["overall_health_score"] >= 50
        assert data["audit_receipt"]["receipt_id"].startswith("REC-LLM-")
