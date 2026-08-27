"""Tests for Story 2.3 — Identify Positive Performance (Highlights).

Verifies:
- AC-2.3.1: The system identifies operational areas meeting or exceeding targets.
- AC-2.3.2: Highlights are grounded in verified data metrics and deterministic benchmarks.
- Rejection / Boundary: Stressed or failing domains are NEVER flagged as positive highlights (no false praise).
- Invariants: Strict numerical grounding (INV-002, AC-2.1.2), zero PHI (INV-008), Spec §8 offline fallback.
- REST API: GET /api/agent/positive-highlights endpoint.
"""

from __future__ import annotations

from unittest.mock import patch

import httpx
import pytest

from src.agent.llm_client import LLMClient
from src.agent.positive_agent import (
    FacilityPositiveHighlightAgent,
    PositivePerformanceReport,
)
from src.analytics.positive_highlights import evaluate_positive_highlights
from src.data.loader import DatasetUnavailableError
from src.mcp.client import MockDomoMCPClient


@pytest.mark.asyncio
async def test_ac2_3_1_identifies_operational_areas_meeting_or_exceeding_targets() -> (
    None
):
    """AC-2.3.1: Verify system detects operational domains meeting or exceeding targets."""
    agent = FacilityPositiveHighlightAgent()
    report = await agent.identify_positive_performance(
        "ignite-oak-brook", scenario="baseline"
    )

    assert isinstance(report, PositivePerformanceReport)
    assert report.verified_highlights.total_highlights_count > 0

    # Verify baseline highlights exist for high-performing areas
    domains_highlighted = {hl.domain for hl in report.verified_highlights.highlights}
    assert "hospitality" in domains_highlighted  # Dining score 4.65+ / NPS 66+
    assert "census" in domains_highlighted  # Occupancy 86.4% >= 85.0%

    # Verify standup notes are populated
    assert len(report.standup_recognition_notes) > 0
    assert len(report.key_achievements) > 0


@pytest.mark.asyncio
async def test_ac2_3_2_highlights_grounded_in_verified_metrics_and_benchmarks() -> None:
    """AC-2.3.2: Verify positive highlights cite exact snapshot values and correct benchmark targets."""
    mcp_client = MockDomoMCPClient()
    snapshot = mcp_client.get_facility_snapshot("ignite-oak-brook", "baseline")
    history = mcp_client.get_facility_history("ignite-oak-brook", 30, "baseline")

    summary = evaluate_positive_highlights(snapshot, history, "baseline")
    assert summary.total_highlights_count >= 4

    for hl in summary.highlights:
        # 1. Metric must be numeric and non-zero
        assert isinstance(hl.current_value, float)
        assert isinstance(hl.benchmark_or_target_value, float)

        # 2. Evidence statement must cite the current value
        assert (
            str(hl.current_value) in hl.evidence_statement
            or f"{hl.current_value:.1f}" in hl.evidence_statement
            or str(int(hl.current_value)) in hl.evidence_statement
        )
        assert len(hl.operational_impact) > 20
        assert hl.category in (
            "BENCHMARK_EXCEEDED",
            "TARGET_MET",
            "TRAJECTORY_IMPROVEMENT",
            "EXEMPLARY_ACHIEVEMENT",
        )


@pytest.mark.asyncio
async def test_rejection_boundary_no_false_positives_in_stressed_domains() -> None:
    """Rejection Boundary: Stressed or failing operational metrics must NEVER be flagged as positive highlights."""
    agent = FacilityPositiveHighlightAgent()

    # 1. Staffing Stress scenario: Staffing HPPD (3.62 < 4.00), Agency (18.5% > 5%), Open shifts (5 > 1) MUST NOT be highlighted
    staffing_stress_report = await agent.identify_positive_performance(
        "ignite-oak-brook", scenario="staffing_stress"
    )
    staffing_highlights = [
        hl
        for hl in staffing_stress_report.verified_highlights.highlights
        if hl.domain == "staffing"
    ]
    # Stressed staffing metrics MUST NOT appear as positive highlights
    assert len(staffing_highlights) == 0, (
        f"False positive staffing highlights generated during staffing_stress: {staffing_highlights}"
    )

    # 2. Hospital Transfer Spike scenario: Acute transfers (6 > 2) and Readmissions (19.2% > 12%) MUST NOT be highlighted
    transfer_spike_report = await agent.identify_positive_performance(
        "ignite-oak-brook", scenario="hospital_transfer_spike"
    )
    transfer_highlights = [
        hl
        for hl in transfer_spike_report.verified_highlights.highlights
        if hl.domain == "hospital_transfers"
    ]
    assert len(transfer_highlights) == 0, (
        f"False positive transfer highlights generated during transfer spike: {transfer_highlights}"
    )

    # 3. Auth Cliff scenario: Expiring 48h (7 > 2) MUST NOT be highlighted as positive
    auth_cliff_report = await agent.identify_positive_performance(
        "ignite-oak-brook", scenario="auth_cliff"
    )
    auth_highlights = [
        hl
        for hl in auth_cliff_report.verified_highlights.highlights
        if hl.domain == "payer_auth"
    ]
    assert len(auth_highlights) == 0, (
        f"False positive auth highlights generated during auth cliff: {auth_highlights}"
    )


@pytest.mark.asyncio
async def test_ac2_3_strict_numerical_grounding_reconciliation() -> None:
    """AC-2.1.2 / INV-002: Verify reconciler detects and purges hallucinated numbers in positive narratives."""
    hallucinated_llm_response = {
        "executive_highlights_summary": "Ignite Oak Brook achieved 9999% satisfaction with 8888 awards across 7777 beds.",
        "key_achievements": [
            "Invented 5555 flawless therapy sessions.",
            "Record 4444 guest compliments.",
        ],
        "standup_recognition_notes": [
            {
                "domain": "hospitality",
                "team_or_role": "Culinary Team",
                "achievement_headline": "Invented 9999 Star Dining",
                "talking_point": "Congratulations on 9999 points today!",
            }
        ],
        "replication_insights": "Replicate the 8888 protocols across all shifts.",
    }

    client = LLMClient(api_key="mock-api-key", model="gemini-2.0-flash")
    with patch.object(
        client, "_call_gemini_api", return_value=hallucinated_llm_response
    ):
        agent = FacilityPositiveHighlightAgent(llm_client=client)
        report = await agent.identify_positive_performance(
            "ignite-oak-brook", scenario="baseline"
        )

        # 1. Hallucinated numbers (9999, 8888, 7777, 5555, 4444) MUST NOT be present
        assert "9999" not in report.executive_highlights_summary
        assert "8888" not in report.executive_highlights_summary
        assert "7777" not in report.executive_highlights_summary
        assert "5555" not in "".join(report.key_achievements)
        assert "9999" not in "".join(
            [n.talking_point for n in report.standup_recognition_notes]
        )
        assert "9999" not in "".join(
            [n.achievement_headline for n in report.standup_recognition_notes]
        )

        # 2. Reconciler notice must be logged
        assert "Reconciliation Notice" in report.data_limitations_and_uncertainty


@pytest.mark.asyncio
async def test_all_negative_zero_highlights_graceful_handling() -> None:
    """Verify that when a facility has 0 positive highlights, system renders a clean deficit-focused message without crashing."""
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

    # Construct an all-negative snapshot where every domain is severely distressed
    distressed_snapshot = DailyFacilitySnapshot(
        snapshot_date=date(2026, 8, 27),
        facility_id="ignite-oak-brook",
        census=CensusData(
            current_census=65,
            total_capacity=110,
            occupancy_rate_pct=59.1,
            available_beds=45,
            previous_day_census=67,
            previous_week_census=72,
            budgeted_target_census=95,
        ),
        admissions_discharges=AdmissionsDischargesData(
            today_admissions=0,
            today_discharges=4,
            pending_admissions=0,
            pending_discharges=3,
            net_flow=-4,
            rolling_7d_admissions=5,
            rolling_7d_discharges=18,
        ),
        length_of_stay=LengthOfStayData(
            average_los_days=32.0,
            target_los_days=17.5,
            short_stay_count=20,
            long_stay_count=45,
            los_outliers_count=12,
            median_los_days=30.0,
        ),
        therapy=TherapyData(
            avg_daily_treatment_minutes_scheduled=90.0,
            avg_daily_treatment_minutes_delivered=68.0,
            treatment_completion_rate_pct=75.5,
            patients_meeting_weekly_goals_pct=60.0,
            patients_on_therapy_hold=5,
            functional_mobility_gain_index=3.5,
        ),
        staffing=StaffingData(
            hppd_actual=3.20,
            hppd_budgeted_target=4.00,
            rn_hours_actual=40.0,
            lpn_hours_actual=60.0,
            cna_hours_actual=108.0,
            call_in_absences_count=6,
            open_shifts_count=8,
            overtime_hours=45.0,
            agency_staff_pct=28.0,
        ),
        payer_auth=PayerAuthData(
            payer_mix_pct={"Medicare A": 30.0, "Medicaid": 50.0, "Managed Care": 20.0},
            expiring_authorizations_48h=12,
            expiring_authorizations_72h=18,
            pending_reauthorizations_count=15,
            auth_denials_pending_appeal_count=8,
        ),
        hospitality=HospitalityData(
            dining_satisfaction_score=72.0,
            cleanliness_room_comfort_score=70.0,
            guest_satisfaction_nps=25.0,
            open_guest_service_requests=14,
            avg_request_resolution_hours=8.5,
        ),
        hospital_transfers=HospitalTransferData(
            unplanned_transfers_30d_count=14,
            readmission_rate_30d_pct=24.5,
            benchmark_readmission_rate_pct=12.0,
            acute_transfers_this_week=9,
            transfers_by_reason={"cardiac": 5, "respiratory": 9},
        ),
    )

    summary = evaluate_positive_highlights(distressed_snapshot, scenario="baseline")
    assert summary.total_highlights_count == 0
    assert len(summary.highlights) == 0

    client = LLMClient()  # offline
    agent = FacilityPositiveHighlightAgent(llm_client=client)
    with patch.object(
        agent.mcp_client, "get_facility_snapshot", return_value=distressed_snapshot
    ):
        report = await agent.identify_positive_performance(
            "ignite-oak-brook", scenario="baseline"
        )
        assert report.verified_highlights.total_highlights_count == 0
        assert (
            "no operational indicators meeting positive highlight criteria"
            in report.executive_highlights_summary.lower()
        )


@pytest.mark.asyncio
async def test_spec_section_8_offline_positive_highlights_fallback() -> None:
    """Spec §8: Verify that when API key is missing, agent returns AI_ANALYSIS_UNAVAILABLE without fake AI claims."""
    client = LLMClient()  # No API key
    agent = FacilityPositiveHighlightAgent(llm_client=client)

    report = await agent.identify_positive_performance(
        "ignite-oak-brook", scenario="baseline"
    )

    assert report.analysis_state == "AI_ANALYSIS_UNAVAILABLE"
    assert report.audit_receipt.is_live_call is False
    assert "AI interpretation is unavailable" in report.executive_highlights_summary
    assert len(report.key_achievements) > 0
    assert len(report.standup_recognition_notes) > 0


@pytest.mark.asyncio
async def test_boundary_no_phi_in_positive_output() -> None:
    """INV-008: Verify positive performance output contains 0 patient names or health identifiers."""
    agent = FacilityPositiveHighlightAgent()
    report = await agent.identify_positive_performance(
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
async def test_failure_behavior_unavailable_facility_raises_error() -> None:
    """Failure behavior: Requesting positive highlights for unknown facility raises DatasetUnavailableError."""
    agent = FacilityPositiveHighlightAgent()
    with pytest.raises(DatasetUnavailableError):
        await agent.identify_positive_performance("non-existent-facility-xyz")


@pytest.mark.asyncio
async def test_fastapi_positive_highlights_endpoint() -> None:
    """Verify REST API endpoint GET /api/agent/positive-highlights."""
    from src.api.main import app

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        res = await client.get(
            "/api/agent/positive-highlights",
            params={
                "facility_id": "ignite-oak-brook",
                "scenario": "baseline",
                "days_history": 30,
            },
        )
        assert res.status_code == 200
        data = res.json()
        assert data["facility_id"] == "ignite-oak-brook"
        assert "verified_highlights" in data
        assert data["verified_highlights"]["total_highlights_count"] > 0
        assert "standup_recognition_notes" in data
