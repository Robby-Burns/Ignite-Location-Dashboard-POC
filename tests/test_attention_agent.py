"""Tests for Story 2.4 — Identify Areas Requiring Attention.

Verifies:
- AC-2.4.1: The system identifies supported areas requiring attention across scenarios.
- AC-2.4.2: The system considers relationships between relevant datasets (cross-domain correlation) when determining significance.
- Rejection / Boundary: Healthy domains are never flagged as deficits; completely healthy facility yields 0 attention items.
- Invariants: Strict numerical grounding (INV-002, AC-2.1.2), zero hardcoded scenario narratives (INV-001), zero PHI (INV-008), Spec §8 offline fallback.
- REST API: GET /api/agent/attention-areas endpoint.
"""

from __future__ import annotations

from unittest.mock import patch

import httpx
import pytest

from src.agent.attention_agent import (
    AttentionAnalysisReport,
    FacilityAttentionAgent,
)
from src.agent.llm_client import LLMClient
from src.analytics.attention_areas import evaluate_attention_areas
from src.data.loader import DatasetUnavailableError
from src.mcp.client import MockDomoMCPClient


@pytest.mark.asyncio
async def test_ac2_4_1_identifies_supported_areas_requiring_attention() -> None:
    """AC-2.4.1: Verify system detects operational deficits across diverse scenarios."""
    agent = FacilityAttentionAgent()

    # 1. Staffing Stress scenario: Must identify HPPD deficit, agency surge, open shifts
    staffing_report = await agent.identify_attention_areas(
        "ignite-oak-brook", scenario="staffing_stress"
    )
    assert isinstance(staffing_report, AttentionAnalysisReport)
    assert staffing_report.verified_attention_summary.total_attention_count > 0

    staffing_domains = {
        it.domain for it in staffing_report.verified_attention_summary.attention_items
    }
    assert "staffing" in staffing_domains
    hppd_items = [
        it
        for it in staffing_report.verified_attention_summary.attention_items
        if it.metric_name == "hppd_actual"
    ]
    assert len(hppd_items) == 1
    assert hppd_items[0].severity in ("CRITICAL", "HIGH")
    assert hppd_items[0].current_value < hppd_items[0].threshold_or_target

    # 2. Hospital Transfer Spike scenario: Must identify acute transfer spike and elevated readmissions
    transfer_report = await agent.identify_attention_areas(
        "ignite-oak-brook", scenario="hospital_transfer_spike"
    )
    transfer_domains = {
        it.domain for it in transfer_report.verified_attention_summary.attention_items
    }
    assert "hospital_transfers" in transfer_domains
    transfer_items = [
        it
        for it in transfer_report.verified_attention_summary.attention_items
        if it.metric_name == "acute_transfers_this_week"
    ]
    assert len(transfer_items) == 1
    assert transfer_items[0].severity == "CRITICAL"

    # 3. Auth Cliff scenario: Must identify expiring authorizations in 48h
    auth_report = await agent.identify_attention_areas(
        "ignite-oak-brook", scenario="auth_cliff"
    )
    auth_domains = {
        it.domain for it in auth_report.verified_attention_summary.attention_items
    }
    assert "payer_auth" in auth_domains
    auth_items = [
        it
        for it in auth_report.verified_attention_summary.attention_items
        if it.metric_name == "expiring_authorizations_48h"
    ]
    assert len(auth_items) == 1
    assert auth_items[0].severity in ("CRITICAL", "HIGH")


@pytest.mark.asyncio
async def test_ac2_4_2_considers_cross_domain_compound_correlations() -> None:
    """AC-2.4.2: Verify system identifies multi-domain compounding risks where related data points create stronger concern."""
    mcp_client = MockDomoMCPClient()

    # 1. Staffing Stress: Staffing strain compounded with therapy disruption / operations
    snap_staff = mcp_client.get_facility_snapshot("ignite-oak-brook", "staffing_stress")
    hist_staff = mcp_client.get_facility_history(
        "ignite-oak-brook", 30, "staffing_stress"
    )
    staff_summary = evaluate_attention_areas(
        snap_staff, hist_staff, scenario="staffing_stress"
    )

    assert len(staff_summary.cross_domain_correlations) > 0
    compound_domains = {
        tuple(corr.domains) for corr in staff_summary.cross_domain_correlations
    }
    # Either staffing+therapy or census+staffing must be identified
    assert any("staffing" in d_tuple for d_tuple in compound_domains)

    # 2. Auth Cliff: Payer auth expiring combined with pending discharges
    snap_auth = mcp_client.get_facility_snapshot("ignite-oak-brook", "auth_cliff")
    hist_auth = mcp_client.get_facility_history("ignite-oak-brook", 30, "auth_cliff")
    auth_summary = evaluate_attention_areas(snap_auth, hist_auth, scenario="auth_cliff")

    auth_corr = [
        c for c in auth_summary.cross_domain_correlations if "payer_auth" in c.domains
    ]
    assert len(auth_corr) > 0
    assert (
        "discharge" in auth_corr[0].finding_summary.lower()
        or "authorization" in auth_corr[0].finding_summary.lower()
    )


@pytest.mark.asyncio
async def test_rejection_boundary_no_false_alarms_on_healthy_domains() -> None:
    """Rejection Boundary: Healthy metrics must NEVER be flagged as attention deficits."""
    agent = FacilityAttentionAgent()

    # In baseline scenario, occupancy (86.4%), dining (93.0 pts), and therapy (96.5%) are healthy
    baseline_report = await agent.identify_attention_areas(
        "ignite-oak-brook", scenario="baseline"
    )
    baseline_items = baseline_report.verified_attention_summary.attention_items

    # Baseline healthy metrics must NOT appear in attention items
    low_occ_items = [
        it for it in baseline_items if it.metric_name == "occupancy_rate_pct"
    ]
    assert len(low_occ_items) == 0, f"False alarm on healthy occupancy: {low_occ_items}"

    dining_items = [
        it for it in baseline_items if it.metric_name == "dining_satisfaction_score"
    ]
    assert len(dining_items) == 0, (
        f"False alarm on healthy dining satisfaction: {dining_items}"
    )

    therapy_items = [
        it for it in baseline_items if it.metric_name == "treatment_completion_rate_pct"
    ]
    assert len(therapy_items) == 0, (
        f"False alarm on healthy therapy completion: {therapy_items}"
    )


@pytest.mark.asyncio
async def test_zero_attention_all_healthy_facility_graceful_handling() -> None:
    """Verify that when a facility is completely healthy across all 8 domains, 0 attention items are produced."""
    from datetime import date

    from src.models.facility import (
        AdmissionsDischargesData,
        CensusData,
        DailyFacilitySnapshot,
        HospitalityData,
        HospitalTransferData,
        LengthOfStayData,
        PayerAuthData,
        StaffingData,
        TherapyData,
    )

    # Construct an ideal benchmark-exceeding facility snapshot
    pristine_snapshot = DailyFacilitySnapshot(
        snapshot_date=date(2026, 8, 27),
        facility_id="ignite-oak-brook",
        census=CensusData(
            current_census=95,
            total_capacity=105,
            occupancy_rate_pct=90.5,
            available_beds=10,
            previous_day_census=94,
            previous_week_census=92,
            budgeted_target_census=90,
        ),
        admissions_discharges=AdmissionsDischargesData(
            today_admissions=4,
            today_discharges=2,
            pending_admissions=3,
            pending_discharges=1,
            net_flow=2,
            rolling_7d_admissions=24,
            rolling_7d_discharges=18,
        ),
        length_of_stay=LengthOfStayData(
            average_los_days=21.5,
            target_los_days=22.0,
            short_stay_count=70,
            long_stay_count=25,
            los_outliers_count=1,
            median_los_days=20.0,
        ),
        therapy=TherapyData(
            avg_daily_treatment_minutes_scheduled=90.0,
            avg_daily_treatment_minutes_delivered=89.0,
            treatment_completion_rate_pct=98.0,
            patients_meeting_weekly_goals_pct=95.0,
            patients_on_therapy_hold=1,
            functional_mobility_gain_index=8.5,
        ),
        staffing=StaffingData(
            hppd_actual=4.25,
            hppd_budgeted_target=4.00,
            rn_hours_actual=95.0,
            lpn_hours_actual=110.0,
            cna_hours_actual=200.0,
            call_in_absences_count=0,
            open_shifts_count=0,
            overtime_hours=4.0,
            agency_staff_pct=2.0,
        ),
        payer_auth=PayerAuthData(
            payer_mix_pct={
                "Medicare A": 45.0,
                "Managed Care": 35.0,
                "Commercial": 20.0,
            },
            expiring_authorizations_48h=1,
            expiring_authorizations_72h=3,
            pending_reauthorizations_count=2,
            auth_denials_pending_appeal_count=0,
        ),
        hospitality=HospitalityData(
            dining_satisfaction_score=95.0,
            cleanliness_room_comfort_score=96.0,
            guest_satisfaction_nps=75.0,
            open_guest_service_requests=2,
            avg_request_resolution_hours=1.2,
        ),
        hospital_transfers=HospitalTransferData(
            unplanned_transfers_30d_count=3,
            readmission_rate_30d_pct=8.5,
            benchmark_readmission_rate_pct=12.0,
            acute_transfers_this_week=1,
            transfers_by_reason={"cardiac": 1},
        ),
    )

    summary = evaluate_attention_areas(pristine_snapshot, scenario="baseline")
    assert summary.total_attention_count == 0
    assert len(summary.attention_items) == 0

    client = LLMClient()  # offline
    agent = FacilityAttentionAgent(llm_client=client)
    with patch.object(
        agent.mcp_client, "get_facility_snapshot", return_value=pristine_snapshot
    ):
        report = await agent.identify_attention_areas(
            "ignite-oak-brook", scenario="baseline"
        )
        assert report.verified_attention_summary.total_attention_count == 0
        assert (
            "zero active deficit conditions"
            in report.executive_attention_summary.lower()
        )


@pytest.mark.asyncio
async def test_ac2_4_strict_numerical_grounding_reconciliation() -> None:
    """AC-2.1.2 / INV-002: Verify reconciler detects and purges hallucinated numbers in attention reports."""
    hallucinated_llm_response = {
        "executive_attention_summary": "Ignite Oak Brook faces 9999 critical violations with 8888 staffing failures.",
        "critical_risk_factors": [
            "Severe 7777 missed therapy sessions.",
            "Unprecedented 5555 acute hospital readmissions.",
        ],
        "cross_domain_impact_narrative": "Disruption across 4444 departments caused 3333 operational bottlenecks.",
        "immediate_focus_areas": ["Audit 2222 open clinical shifts immediately."],
    }

    client = LLMClient(api_key="mock-api-key", model="gemini-2.0-flash")
    with patch.object(
        client, "_call_gemini_api", return_value=hallucinated_llm_response
    ):
        agent = FacilityAttentionAgent(llm_client=client)
        report = await agent.identify_attention_areas(
            "ignite-oak-brook", scenario="staffing_stress"
        )

        # 1. Hallucinated numbers (9999, 8888, 7777, 5555, 4444, 3333, 2222) MUST NOT be present
        assert "9999" not in report.executive_attention_summary
        assert "8888" not in report.executive_attention_summary
        assert "7777" not in "".join(report.critical_risk_factors)
        assert "5555" not in "".join(report.critical_risk_factors)
        assert "4444" not in report.cross_domain_impact_narrative
        assert "3333" not in report.cross_domain_impact_narrative
        assert "2222" not in "".join(report.immediate_focus_areas)

        # 2. Reconciler notice must be logged
        assert "Reconciliation Notice" in report.data_limitations_and_uncertainty


@pytest.mark.asyncio
async def test_spec_section_8_offline_attention_fallback() -> None:
    """Spec §8: Verify that when API key is missing, agent returns AI_ANALYSIS_UNAVAILABLE without fake AI claims."""
    client = LLMClient()  # No API key
    agent = FacilityAttentionAgent(llm_client=client)

    report = await agent.identify_attention_areas(
        "ignite-oak-brook", scenario="staffing_stress"
    )

    assert report.analysis_state == "AI_ANALYSIS_UNAVAILABLE"
    assert report.audit_receipt.is_live_call is False
    assert "AI interpretation is unavailable" in report.executive_attention_summary
    assert len(report.critical_risk_factors) > 0
    assert len(report.immediate_focus_areas) > 0


@pytest.mark.asyncio
async def test_boundary_no_phi_in_attention_output() -> None:
    """INV-008: Verify attention report output contains 0 patient names or health identifiers."""
    agent = FacilityAttentionAgent()
    report = await agent.identify_attention_areas(
        "ignite-oak-brook", scenario="staffing_stress"
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
async def test_failure_behavior_unavailable_facility_raises_error() -> None:
    """Failure behavior: Requesting attention areas for unknown facility raises DatasetUnavailableError."""
    agent = FacilityAttentionAgent()
    with pytest.raises(DatasetUnavailableError):
        await agent.identify_attention_areas("non-existent-facility-xyz")


@pytest.mark.asyncio
async def test_fastapi_attention_areas_endpoint() -> None:
    """Verify REST API endpoint GET /api/agent/attention-areas."""
    from src.api.main import app

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        res = await client.get(
            "/api/agent/attention-areas",
            params={
                "facility_id": "ignite-oak-brook",
                "scenario": "staffing_stress",
                "days_history": 30,
            },
        )
        assert res.status_code == 200
        data = res.json()
        assert data["facility_id"] == "ignite-oak-brook"
        assert "verified_attention_summary" in data
        assert data["verified_attention_summary"]["total_attention_count"] > 0
        assert len(data["prioritized_operational_concerns"]) > 0
