"""Tests for Story 4.2 — Failure and Boundary Testing.

Verifies:
- AC-4.2.1: The system identifies missing or unavailable data rather than inventing a value.
- AC-4.2.2: The system does not produce an unsupported recommendation when evidence is insufficient.
- INV-004: Missing facts are not invented.
- INV-005: Uncertainty is communicated.
- INV-002: Numbers trace to source/calculation.
- INV-008: Zero PHI.
- Spec §8: Explicit failure states (DATA_UNAVAILABLE, AI_ANALYSIS_UNAVAILABLE, INSUFFICIENT_EVIDENCE).
"""

from __future__ import annotations

from datetime import date

import pytest

from src.agent.llm_client import LLMClient
from src.agent.recommendation_agent import (
    FacilityRecommendationAgent,
)
from src.agent.state_agent import (
    FacilityStateAgent,
    NumericalGroundingReconciler,
)
from src.analytics.calculations import calculate_facility_metrics
from src.analytics.recommendations import (
    generate_deterministic_recommendations,
)
from src.data.loader import DatasetUnavailableError, DatasetValidationError
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

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_healthy_snapshot() -> DailyFacilitySnapshot:
    """Construct a snapshot with all metrics in healthy operational range."""
    return DailyFacilitySnapshot(
        snapshot_date=date(2026, 8, 27),
        facility_id="ignite-oak-brook",
        census=CensusData(
            current_census=90,
            total_capacity=110,
            occupancy_rate_pct=81.8,
            available_beds=20,
            previous_day_census=89,
            previous_week_census=88,
            budgeted_target_census=99,
        ),
        admissions_discharges=AdmissionsDischargesData(
            today_admissions=5,
            today_discharges=3,
            pending_admissions=1,
            pending_discharges=1,
            net_flow=2,
            rolling_7d_admissions=30,
            rolling_7d_discharges=28,
        ),
        length_of_stay=LengthOfStayData(
            average_los_days=14.2,
            target_los_days=14.0,
            short_stay_count=65,
            long_stay_count=25,
            los_outliers_count=4,
            median_los_days=12.5,
        ),
        therapy=TherapyData(
            avg_daily_treatment_minutes_scheduled=45.0,
            avg_daily_treatment_minutes_delivered=43.0,
            treatment_completion_rate_pct=95.6,
            patients_meeting_weekly_goals_pct=92.0,
            patients_on_therapy_hold=2,
            functional_mobility_gain_index=7.8,
        ),
        staffing=StaffingData(
            hppd_actual=4.25,
            hppd_budgeted_target=4.20,
            rn_hours_actual=180.0,
            lpn_hours_actual=220.0,
            cna_hours_actual=350.0,
            call_in_absences_count=1,
            open_shifts_count=1,
            overtime_hours=8.0,
            agency_staff_pct=4.5,
        ),
        payer_auth=PayerAuthData(
            payer_mix_pct={
                "Medicare A": 38.0,
                "Managed Care": 30.0,
                "Medicaid": 18.0,
                "Commercial": 10.0,
                "VA": 4.0,
            },
            expiring_authorizations_48h=1,
            expiring_authorizations_72h=2,
            pending_reauthorizations_count=1,
            auth_denials_pending_appeal_count=0,
        ),
        hospitality=HospitalityData(
            dining_satisfaction_score=92.0,
            cleanliness_room_comfort_score=94.0,
            guest_satisfaction_nps=65.0,
            open_guest_service_requests=2,
            avg_request_resolution_hours=4.0,
        ),
        hospital_transfers=HospitalTransferData(
            unplanned_transfers_30d_count=3,
            readmission_rate_30d_pct=10.5,
            benchmark_readmission_rate_pct=12.0,
            acute_transfers_this_week=1,
            transfers_by_reason={
                "respiratory": 1,
                "cardiac": 0,
                "fall_trauma": 1,
                "sepsis_infection": 0,
                "altered_mental_status": 0,
                "other": 1,
            },
        ),
    )


def _build_minimal_snapshot() -> DailyFacilitySnapshot:
    """Construct a snapshot with minimal but valid values (edge case)."""
    return DailyFacilitySnapshot(
        snapshot_date=date(2026, 8, 27),
        facility_id="ignite-oak-brook",
        census=CensusData(
            current_census=1,
            total_capacity=110,
            occupancy_rate_pct=0.9,
            available_beds=109,
            previous_day_census=1,
            previous_week_census=1,
            budgeted_target_census=99,
        ),
        admissions_discharges=AdmissionsDischargesData(
            today_admissions=0,
            today_discharges=0,
            pending_admissions=0,
            pending_discharges=0,
            net_flow=0,
            rolling_7d_admissions=0,
            rolling_7d_discharges=0,
        ),
        length_of_stay=LengthOfStayData(
            average_los_days=0.0,
            target_los_days=14.0,
            short_stay_count=0,
            long_stay_count=0,
            los_outliers_count=0,
        ),
        therapy=TherapyData(
            avg_daily_treatment_minutes_scheduled=0.0,
            avg_daily_treatment_minutes_delivered=0.0,
            treatment_completion_rate_pct=0.0,
            patients_meeting_weekly_goals_pct=0.0,
            patients_on_therapy_hold=0,
            functional_mobility_gain_index=0.0,
        ),
        staffing=StaffingData(
            hppd_actual=0.0,
            hppd_budgeted_target=4.20,
            rn_hours_actual=0.0,
            lpn_hours_actual=0.0,
            cna_hours_actual=0.0,
            call_in_absences_count=0,
            open_shifts_count=0,
            overtime_hours=0.0,
            agency_staff_pct=0.0,
        ),
        payer_auth=PayerAuthData(
            payer_mix_pct={
                "Medicare A": 38.0,
                "Managed Care": 30.0,
                "Medicaid": 18.0,
                "Commercial": 10.0,
                "VA": 4.0,
            },
            expiring_authorizations_48h=0,
            expiring_authorizations_72h=0,
            pending_reauthorizations_count=0,
            auth_denials_pending_appeal_count=0,
        ),
        hospitality=HospitalityData(
            dining_satisfaction_score=0.0,
            cleanliness_room_comfort_score=0.0,
            guest_satisfaction_nps=-100.0,
            open_guest_service_requests=0,
            avg_request_resolution_hours=0.0,
        ),
        hospital_transfers=HospitalTransferData(
            unplanned_transfers_30d_count=0,
            readmission_rate_30d_pct=0.0,
            benchmark_readmission_rate_pct=12.0,
            acute_transfers_this_week=0,
        ),
    )


# ---------------------------------------------------------------------------
# AC-4.2.1: System identifies missing or unavailable data rather than inventing
# ---------------------------------------------------------------------------


class TestAC421_MissingOrUnavailableDataIdentified:
    """Verify the system identifies missing/unavailable data without fabricating values."""

    @pytest.mark.asyncio
    async def test_unknown_facility_raises_dataset_unavailable_error(self) -> None:
        """AC-4.2.1: Requesting data for a non-existent facility raises DatasetUnavailableError."""
        agent = FacilityRecommendationAgent()
        with pytest.raises(DatasetUnavailableError, match="unavailable"):
            await agent.generate_recommendations("non-existent-facility-xyz")

    @pytest.mark.asyncio
    async def test_unknown_facility_state_agent_raises_error(self) -> None:
        """AC-4.2.1: State agent for unknown facility raises DatasetUnavailableError."""
        agent = FacilityStateAgent()
        with pytest.raises(DatasetUnavailableError, match="unavailable"):
            await agent.analyze_facility_state("non-existent-facility-xyz")

    @pytest.mark.asyncio
    async def test_llm_unavailable_produces_ai_analysis_unavailable_state(self) -> None:
        """AC-4.2.1 / Spec §8: When LLM is unavailable, analysis_state is AI_ANALYSIS_UNAVAILABLE."""
        client = LLMClient()  # No API keys
        agent = FacilityRecommendationAgent(llm_client=client)

        report = await agent.generate_recommendations(
            "ignite-oak-brook", scenario="staffing_stress"
        )

        assert report.analysis_state == "AI_ANALYSIS_UNAVAILABLE"
        assert report.audit_receipt.is_live_call is False
        assert "offline" in report.executive_action_plan_overview.lower()

    @pytest.mark.asyncio
    async def test_llm_unavailable_state_agent_produces_unavailable_state(self) -> None:
        """AC-4.2.1 / Spec §8: State agent with no LLM produces AI_ANALYSIS_UNAVAILABLE."""
        client = LLMClient()  # No API keys
        agent = FacilityStateAgent(llm_client=client)

        analysis = await agent.analyze_facility_state(
            "ignite-oak-brook", scenario="baseline"
        )

        assert analysis.analysis_state == "AI_ANALYSIS_UNAVAILABLE"
        assert analysis.audit_receipt.is_live_call is False
        assert "unavailable" in analysis.executive_summary.lower()

    @pytest.mark.asyncio
    async def test_llm_unavailable_still_produces_deterministic_recommendations(
        self,
    ) -> None:
        """AC-4.2.1: Even without LLM, deterministic recommendations are still returned."""
        client = LLMClient()  # No API keys
        agent = FacilityRecommendationAgent(llm_client=client)

        report = await agent.generate_recommendations(
            "ignite-oak-brook", scenario="staffing_stress"
        )

        # Deterministic recs must still be present
        assert report.verified_recommendations_summary.total_recommendations_count > 0
        assert len(report.top_priority_recommendations) > 0
        assert len(report.departmental_action_items) > 0

    def test_corrupt_json_raises_validation_error(self) -> None:
        """AC-4.2.1: Corrupt data payload raises DatasetValidationError."""
        from src.data.loader import FacilityDataLoader

        loader = FacilityDataLoader()
        with pytest.raises(DatasetValidationError):
            loader.load_from_json('{"invalid": "structure"}')

    def test_empty_dict_raises_validation_error(self) -> None:
        """AC-4.2.1: Empty data payload raises DatasetValidationError."""
        from src.data.loader import FacilityDataLoader

        loader = FacilityDataLoader()
        with pytest.raises(DatasetValidationError):
            loader.load_from_json({})

    def test_deterministic_engine_handles_zero_census_snapshot(self) -> None:
        """AC-4.2.1: Engine handles extreme edge case (near-zero census) without crashing."""
        snap = _build_minimal_snapshot()
        # Should not raise — engine must handle any valid snapshot
        summary = generate_deterministic_recommendations(snap, scenario="baseline")
        assert summary is not None
        assert summary.facility_id == "ignite-oak-brook"

    def test_calculations_handle_zero_values_without_error(self) -> None:
        """AC-4.2.1: Calculation engine handles zero-value snapshot without crashing."""
        snap = _build_minimal_snapshot()
        calcs = calculate_facility_metrics(snap, scenario="baseline")
        assert calcs is not None
        # All domains should be present even with zero values
        assert len(calcs.domains) > 0

    @pytest.mark.asyncio
    async def test_no_fabricated_values_in_offline_recommendation_output(self) -> None:
        """AC-4.2.1 / INV-002: Offline recommendation output contains no fabricated numbers."""
        client = LLMClient()  # No API keys
        agent = FacilityRecommendationAgent(llm_client=client)

        report = await agent.generate_recommendations(
            "ignite-oak-brook", scenario="staffing_stress"
        )

        # Verify numbers in the executive overview trace to the snapshot
        snapshot = agent.mcp_client.get_facility_snapshot(
            "ignite-oak-brook", scenario="staffing_stress"
        )
        calcs = calculate_facility_metrics(snapshot, scenario="staffing_stress")
        ground_truth = NumericalGroundingReconciler.build_ground_truth_set(
            snapshot, calcs
        )

        # The executive overview is deterministic fallback text — verify it's grounded
        _, is_valid = NumericalGroundingReconciler.reconcile_text(
            report.executive_action_plan_overview,
            ground_truth,
            report.executive_action_plan_overview,
        )
        assert is_valid, (
            "Executive overview contains ungrounded numbers — possible fabrication"
        )


# ---------------------------------------------------------------------------
# AC-4.2.2: No unsupported recommendations when evidence is insufficient
# ---------------------------------------------------------------------------


class TestAC422_NoUnsupportedRecommendationsWhenEvidenceInsufficient:
    """Verify the system does not produce unsupported recommendations for ambiguous/healthy data."""

    def test_healthy_snapshot_produces_zero_deficit_recommendations(self) -> None:
        """AC-4.2.2: A fully healthy snapshot produces zero HIGH/MEDIUM deficit recommendations."""
        snap = _build_healthy_snapshot()
        summary = generate_deterministic_recommendations(snap, scenario="baseline")

        # Only LOW proactive recommendations should exist
        assert summary.high_priority_count == 0, (
            f"Healthy snapshot produced {summary.high_priority_count} HIGH recs — "
            f"unsupported by any deficit"
        )
        assert summary.medium_priority_count == 0, (
            f"Healthy snapshot produced {summary.medium_priority_count} MEDIUM recs — "
            f"unsupported by any deficit"
        )
        # All recs should be LOW (proactive)
        for rec in summary.recommendations:
            assert rec.priority == "LOW", (
                f"Healthy snapshot produced non-LOW recommendation: {rec.action_title} "
                f"(priority={rec.priority})"
            )

    def test_healthy_snapshot_recommendations_are_proactive_not_deficit(self) -> None:
        """AC-4.2.2: Healthy snapshot recommendations are proactive improvement, not deficit response."""
        snap = _build_healthy_snapshot()
        summary = generate_deterministic_recommendations(snap, scenario="baseline")

        # Should have exactly 2 proactive recommendations
        assert summary.total_recommendations_count == 2
        titles = [r.action_title for r in summary.recommendations]
        assert any("pipeline" in t.lower() or "referral" in t.lower() for t in titles)
        assert any("guest" in t.lower() or "experience" in t.lower() for t in titles)

    def test_ambiguous_scenario_no_high_recs_without_deficit(self) -> None:
        """AC-4.2.2: An ambiguous snapshot (all metrics at threshold, not below) produces no HIGH recs."""
        snap = _build_healthy_snapshot()
        # Set metrics exactly at attention thresholds (not below)
        snap.staffing.hppd_actual = 4.20  # Exactly at target
        snap.therapy.treatment_completion_rate_pct = (
            90.0  # Exactly at attention threshold
        )
        snap.hospitality.dining_satisfaction_score = (
            85.0  # Exactly at attention threshold
        )

        summary = generate_deterministic_recommendations(snap, scenario="baseline")

        # At-threshold metrics should not trigger HIGH severity
        assert summary.high_priority_count == 0, (
            f"At-threshold snapshot produced {summary.high_priority_count} HIGH recs — "
            f"metrics are at target, not below"
        )

    @pytest.mark.asyncio
    async def test_baseline_scenario_no_stress_domain_recommendations(self) -> None:
        """AC-4.2.2: Baseline scenario does not produce recommendations in stress-specific domains."""
        agent = FacilityRecommendationAgent()
        report = await agent.generate_recommendations(
            "ignite-oak-brook", scenario="baseline"
        )

        stress_domains = {"staffing", "payer_auth", "hospital_transfers", "therapy"}
        rec_domains = {
            r.domain for r in report.verified_recommendations_summary.recommendations
        }
        unexpected = rec_domains & stress_domains
        assert not unexpected, f"Baseline produced recs in stress domains: {unexpected}"

    def test_no_fabricated_clinical_facts_in_recommendations(self) -> None:
        """AC-4.2.2 / INV-004: Recommendations contain no fabricated clinical facts."""
        snap = _build_healthy_snapshot()
        summary = generate_deterministic_recommendations(snap, scenario="baseline")

        prohibited_terms = [
            "diagnosed",
            "patient name",
            "medical record",
            "prescription",
            "clinical trial",
            "mortality",
            "prognosis",
        ]
        for rec in summary.recommendations:
            rec_text = (
                f"{rec.action_title} {rec.suggested_action_description} "
                f"{rec.rationale} {rec.expected_operational_impact}"
            ).lower()
            for term in prohibited_terms:
                assert term not in rec_text, (
                    f"Prohibited clinical term '{term}' found in recommendation: "
                    f"{rec.action_title}"
                )

    def test_no_phi_in_any_recommendation_output(self) -> None:
        """AC-4.2.2 / INV-008: No patient-identifying information in recommendation output."""
        snap = _build_healthy_snapshot()
        summary = generate_deterministic_recommendations(snap, scenario="baseline")
        output_text = summary.model_dump_json().lower()

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

    def test_recommendation_evidence_traces_to_snapshot_data(self) -> None:
        """AC-4.2.2 / INV-002: Recommendation evidence metrics trace to actual snapshot values."""
        snap = _build_healthy_snapshot()
        summary = generate_deterministic_recommendations(snap, scenario="baseline")

        # Collect all numbers from the snapshot
        snapshot_numbers = set()
        for obj in [
            snap.census,
            snap.admissions_discharges,
            snap.length_of_stay,
            snap.therapy,
            snap.staffing,
            snap.payer_auth,
            snap.hospitality,
            snap.hospital_transfers,
        ]:
            for val in obj.model_dump().values():
                if isinstance(val, (int, float)):
                    snapshot_numbers.add(round(float(val), 1))

        # Every recommendation's evidence should cite numbers from the snapshot
        for rec in summary.recommendations:
            for evidence_str in rec.supporting_evidence_metrics:
                # Extract numbers from evidence string
                import re

                nums = re.findall(r"\d+(?:\.\d+)?", evidence_str)
                for num_str in nums:
                    num_val = round(float(num_str), 1)
                    # Allow structural numbers (0, 1, 2, etc.) and snapshot-derived numbers
                    if num_val > 5:  # Skip trivial small numbers
                        assert num_val in snapshot_numbers or any(
                            abs(num_val - sn) < 0.2 for sn in snapshot_numbers
                        ), (
                            f"Evidence number {num_val} not traceable to snapshot data. "
                            f"Evidence: '{evidence_str}'"
                        )

    def test_governance_disclaimer_present_on_all_recommendations(self) -> None:
        """AC-4.2.2: Every recommendation includes a governance disclaimer (decision-support framing)."""
        snap = _build_healthy_snapshot()
        summary = generate_deterministic_recommendations(snap, scenario="baseline")

        for rec in summary.recommendations:
            assert rec.governance_disclaimer, (
                f"Recommendation '{rec.action_title}' missing governance disclaimer"
            )
            assert "decision-support" in rec.governance_disclaimer.lower(), (
                f"Governance disclaimer missing 'decision-support' framing: "
                f"{rec.governance_disclaimer}"
            )

    @pytest.mark.asyncio
    async def test_offline_report_includes_limitations_statement(self) -> None:
        """AC-4.2.2 / INV-005: Offline report explicitly communicates data limitations."""
        client = LLMClient()  # No API keys
        agent = FacilityRecommendationAgent(llm_client=client)

        report = await agent.generate_recommendations(
            "ignite-oak-brook", scenario="baseline"
        )

        assert report.data_limitations_and_uncertainty, (
            "Report missing data limitations statement"
        )
        assert "offline" in report.data_limitations_and_uncertainty.lower(), (
            "Limitations statement should mention offline status"
        )

    @pytest.mark.asyncio
    async def test_offline_state_report_includes_limitations(self) -> None:
        """AC-4.2.2 / INV-005: Offline state analysis explicitly communicates limitations."""
        client = LLMClient()  # No API keys
        agent = FacilityStateAgent(llm_client=client)

        analysis = await agent.analyze_facility_state(
            "ignite-oak-brook", scenario="baseline"
        )

        assert analysis.data_limitations_and_uncertainty, (
            "State analysis missing data limitations"
        )
        assert "unavailable" in analysis.data_limitations_and_uncertainty.lower(), (
            "Limitations should mention AI unavailability"
        )
