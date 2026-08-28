"""Tests for Story 4.1 — Recommendation Evaluation.

Verifies:
- AC-4.1.1: Known input changes produce corresponding changes in analysis when the changed
  data is materially relevant. Run paired datasets and compare results.
- AC-4.1.2: The system does not repeatedly produce the same predetermined recommendation when
  the supporting data is removed or changed. Remove or alter the evidence behind a known
  recommendation and verify the recommendation changes or is withdrawn.
- INV-001: No hard-coded scenario-specific intelligence.
- INV-002: Numbers trace to source/calculation.
- FR-008: Changing relevant source data can change findings and recommendations.
"""

from __future__ import annotations

from datetime import date

import pytest

from src.agent.recommendation_agent import (
    FacilityRecommendationAgent,
    RecommendationReport,
)
from src.analytics.recommendations import (
    FacilityRecommendationsSummary,
    generate_deterministic_recommendations,
)
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

SCENARIOS = [
    "baseline",
    "staffing_stress",
    "auth_cliff",
    "hospital_transfer_spike",
    "therapy_disruption",
    "high_census_strain",
]


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


def _build_staffing_deficit_snapshot() -> DailyFacilitySnapshot:
    """Construct a snapshot with severe staffing deficits matching staffing_stress scenario."""
    snap = _build_healthy_snapshot()
    snap.staffing = StaffingData(
        hppd_actual=3.62,
        hppd_budgeted_target=4.20,
        rn_hours_actual=140.0,
        lpn_hours_actual=180.0,
        cna_hours_actual=280.0,
        call_in_absences_count=6,
        open_shifts_count=5,
        overtime_hours=36.5,
        agency_staff_pct=18.5,
    )
    snap.census = CensusData(
        current_census=102,
        total_capacity=110,
        occupancy_rate_pct=92.7,
        available_beds=8,
        previous_day_census=100,
        previous_week_census=95,
        budgeted_target_census=99,
    )
    return snap


def _build_auth_cliff_snapshot() -> DailyFacilitySnapshot:
    """Construct a snapshot with imminent authorization expirations."""
    snap = _build_healthy_snapshot()
    snap.payer_auth = PayerAuthData(
        payer_mix_pct={
            "Medicare A": 38.0,
            "Managed Care": 30.0,
            "Medicaid": 18.0,
            "Commercial": 10.0,
            "VA": 4.0,
        },
        expiring_authorizations_48h=9,
        expiring_authorizations_72h=16,
        pending_reauthorizations_count=12,
        auth_denials_pending_appeal_count=4,
    )
    return snap


def _build_transfer_spike_snapshot() -> DailyFacilitySnapshot:
    """Construct a snapshot with acute hospital transfer cluster."""
    snap = _build_healthy_snapshot()
    snap.hospital_transfers = HospitalTransferData(
        unplanned_transfers_30d_count=14,
        readmission_rate_30d_pct=16.8,
        benchmark_readmission_rate_pct=12.0,
        acute_transfers_this_week=5,
        transfers_by_reason={
            "respiratory": 6,
            "cardiac": 4,
            "fall_trauma": 2,
            "sepsis_infection": 1,
            "altered_mental_status": 1,
            "other": 0,
        },
    )
    return snap


def _get_domain_set(summary: FacilityRecommendationsSummary) -> set[str]:
    """Extract unique domains from a recommendations summary."""
    return {r.domain for r in summary.recommendations}


def _get_titles(summary: FacilityRecommendationsSummary) -> list[str]:
    """Extract recommendation titles from a recommendations summary."""
    return [r.action_title for r in summary.recommendations]


def _get_high_priority_domains(summary: FacilityRecommendationsSummary) -> set[str]:
    """Extract domains that have at least one HIGH priority recommendation."""
    return {r.domain for r in summary.recommendations if r.priority == "HIGH"}


# ---------------------------------------------------------------------------
# AC-4.1.1: Known input changes produce corresponding changes in analysis
# ---------------------------------------------------------------------------


class TestAC411_InputChangesProduceAnalysisChanges:
    """Verify that materially different input data produces different recommendations."""

    @pytest.mark.asyncio
    async def test_all_six_scenarios_produce_distinct_recommendation_sets(self) -> None:
        """AC-4.1.1 / FR-008: Each scenario with a material deficit must produce a different recommendation set.

        Note: high_census_strain is excluded from pairwise comparison because the attention engine
        does not flag near-capacity occupancy as a deficit (known limitation, Checker 3.3 F-1).
        """
        agent = FacilityRecommendationAgent()
        reports: dict[str, RecommendationReport] = {}

        for scenario in SCENARIOS:
            reports[scenario] = await agent.generate_recommendations(
                "ignite-oak-brook", scenario=scenario
            )

        # Collect title sets for scenarios that produce deficit-driven recommendations
        deficit_scenarios = [
            s for s in SCENARIOS if s not in ("baseline", "high_census_strain")
        ]
        title_sets = {
            s: set(_get_titles(r.verified_recommendations_summary))
            for s, r in reports.items()
            if s in deficit_scenarios
        }

        # Every pair of deficit scenarios must differ
        for i, s1 in enumerate(deficit_scenarios):
            for s2 in deficit_scenarios[i + 1 :]:
                assert title_sets[s1] != title_sets[s2], (
                    f"Scenarios '{s1}' and '{s2}' produced identical recommendation titles — "
                    f"indicating hard-coded output (INV-001, FR-008)."
                )

        # Each deficit scenario must also differ from baseline
        baseline_titles = set(
            _get_titles(reports["baseline"].verified_recommendations_summary)
        )
        for s in deficit_scenarios:
            assert title_sets[s] != baseline_titles, (
                f"Scenario '{s}' produced identical recommendations to baseline — "
                f"indicating the deficit did not change output (INV-001, FR-008)."
            )

    @pytest.mark.asyncio
    async def test_scenario_specific_domains_appear_in_recommendations(self) -> None:
        """AC-4.1.1: Each stressed scenario surfaces its primary domain in recommendations."""
        agent = FacilityRecommendationAgent()

        # Staffing stress → staffing domain
        staff_report = await agent.generate_recommendations(
            "ignite-oak-brook", scenario="staffing_stress"
        )
        assert "staffing" in _get_domain_set(
            staff_report.verified_recommendations_summary
        ), "staffing_stress must surface staffing recommendations"

        # Auth cliff → payer_auth domain
        auth_report = await agent.generate_recommendations(
            "ignite-oak-brook", scenario="auth_cliff"
        )
        assert "payer_auth" in _get_domain_set(
            auth_report.verified_recommendations_summary
        ), "auth_cliff must surface payer_auth recommendations"

        # Transfer spike → hospital_transfers domain
        transfer_report = await agent.generate_recommendations(
            "ignite-oak-brook", scenario="hospital_transfer_spike"
        )
        assert "hospital_transfers" in _get_domain_set(
            transfer_report.verified_recommendations_summary
        ), "hospital_transfer_spike must surface hospital_transfers recommendations"

        # Therapy disruption → therapy domain
        therapy_report = await agent.generate_recommendations(
            "ignite-oak-brook", scenario="therapy_disruption"
        )
        assert "therapy" in _get_domain_set(
            therapy_report.verified_recommendations_summary
        ), "therapy_disruption must surface therapy recommendations"

    @pytest.mark.asyncio
    async def test_priority_distribution_reflects_scenario_severity(self) -> None:
        """AC-4.1.1: Stressed scenarios produce more HIGH priority recs than baseline."""
        agent = FacilityRecommendationAgent()

        baseline_report = await agent.generate_recommendations(
            "ignite-oak-brook", scenario="baseline"
        )
        staffing_report = await agent.generate_recommendations(
            "ignite-oak-brook", scenario="staffing_stress"
        )

        baseline_high = (
            baseline_report.verified_recommendations_summary.high_priority_count
        )
        staffing_high = (
            staffing_report.verified_recommendations_summary.high_priority_count
        )

        assert staffing_high > baseline_high, (
            f"staffing_stress ({staffing_high} HIGH) should produce more HIGH recs "
            f"than baseline ({baseline_high} HIGH)"
        )

    def test_deterministic_engine_paired_snapshot_comparison(self) -> None:
        """AC-4.1.1: Directly compare deterministic output for healthy vs deficit snapshots."""
        healthy = _build_healthy_snapshot()
        deficit = _build_staffing_deficit_snapshot()

        healthy_summary = generate_deterministic_recommendations(
            healthy, scenario="baseline"
        )
        deficit_summary = generate_deterministic_recommendations(
            deficit, scenario="staffing_stress"
        )

        # Deficit snapshot must produce more recommendations
        assert (
            deficit_summary.total_recommendations_count
            > healthy_summary.total_recommendations_count
        ), (
            f"Staffing deficit snapshot produced {deficit_summary.total_recommendations_count} recs, "
            f"expected more than healthy snapshot ({healthy_summary.total_recommendations_count})"
        )

        # Deficit snapshot must have HIGH priority recs
        assert deficit_summary.high_priority_count > 0, (
            "Staffing deficit snapshot must produce at least one HIGH priority recommendation"
        )

        # Deficit snapshot must include staffing domain
        deficit_domains = _get_domain_set(deficit_summary)
        assert "staffing" in deficit_domains, (
            "Staffing deficit snapshot must surface staffing domain recommendations"
        )

    def test_auth_deficit_produces_auth_recommendations(self) -> None:
        """AC-4.1.1: Authorization cliff snapshot produces payer_auth recommendations."""
        healthy = _build_healthy_snapshot()
        auth_deficit = _build_auth_cliff_snapshot()

        healthy_summary = generate_deterministic_recommendations(
            healthy, scenario="baseline"
        )
        auth_summary = generate_deterministic_recommendations(
            auth_deficit, scenario="auth_cliff"
        )

        assert "payer_auth" in _get_domain_set(auth_summary), (
            "Auth cliff snapshot must surface payer_auth domain"
        )
        assert "payer_auth" not in _get_domain_set(healthy_summary), (
            "Healthy snapshot should not surface payer_auth domain"
        )

    def test_transfer_spike_produces_transfer_recommendations(self) -> None:
        """AC-4.1.1: Transfer spike snapshot produces hospital_transfers recommendations."""
        healthy = _build_healthy_snapshot()
        transfer_deficit = _build_transfer_spike_snapshot()

        healthy_summary = generate_deterministic_recommendations(
            healthy, scenario="baseline"
        )
        transfer_summary = generate_deterministic_recommendations(
            transfer_deficit, scenario="hospital_transfer_spike"
        )

        assert "hospital_transfers" in _get_domain_set(transfer_summary), (
            "Transfer spike snapshot must surface hospital_transfers domain"
        )
        assert "hospital_transfers" not in _get_domain_set(healthy_summary), (
            "Healthy snapshot should not surface hospital_transfers domain"
        )


# ---------------------------------------------------------------------------
# AC-4.1.2: No predetermined recommendations when evidence removed/changed
# ---------------------------------------------------------------------------


class TestAC412_NoPredeterminedRecommendationsWhenEvidenceChanged:
    """Verify that removing or altering evidence withdraws or changes the corresponding recommendation."""

    @pytest.mark.asyncio
    async def test_removing_staffing_deficit_withdraws_staffing_high_recs(self) -> None:
        """AC-4.1.2: Fixing the staffing deficit removes HIGH staffing recommendations."""
        agent = FacilityRecommendationAgent()

        # Get recommendations for staffing_stress (known HIGH staffing recs)
        stress_report = await agent.generate_recommendations(
            "ignite-oak-brook", scenario="staffing_stress"
        )
        stress_domains = _get_high_priority_domains(
            stress_report.verified_recommendations_summary
        )
        assert "staffing" in stress_domains, (
            "staffing_stress must have HIGH staffing recs (test prerequisite)"
        )

        # Get recommendations for baseline (no staffing deficit)
        baseline_report = await agent.generate_recommendations(
            "ignite-oak-brook", scenario="baseline"
        )
        baseline_domains = _get_high_priority_domains(
            baseline_report.verified_recommendations_summary
        )
        assert "staffing" not in baseline_domains, (
            "baseline should not have HIGH staffing recs when deficit is absent"
        )

    def test_healthy_snapshot_produces_no_high_priority_deficit_recs(self) -> None:
        """AC-4.1.2: A fully healthy snapshot produces zero HIGH priority deficit recommendations."""
        healthy = _build_healthy_snapshot()
        summary = generate_deterministic_recommendations(healthy, scenario="baseline")

        # Healthy snapshot should have 0 HIGH recs (only LOW proactive)
        assert summary.high_priority_count == 0, (
            f"Healthy snapshot produced {summary.high_priority_count} HIGH recs — "
            f"expected 0 (no deficits present)"
        )

    def test_injecting_deficit_creates_corresponding_recommendation(self) -> None:
        """AC-4.1.2: Adding a staffing deficit to a healthy snapshot creates staffing recommendations."""
        healthy = _build_healthy_snapshot()

        # Verify healthy baseline has no staffing recs
        healthy_summary = generate_deterministic_recommendations(
            healthy, scenario="baseline"
        )
        assert "staffing" not in _get_domain_set(healthy_summary), (
            "Healthy snapshot should not have staffing recs (test prerequisite)"
        )

        # Inject staffing deficit
        deficit = _build_healthy_snapshot()
        deficit.staffing = StaffingData(
            hppd_actual=3.62,
            hppd_budgeted_target=4.20,
            rn_hours_actual=140.0,
            lpn_hours_actual=180.0,
            cna_hours_actual=280.0,
            call_in_absences_count=6,
            open_shifts_count=5,
            overtime_hours=36.5,
            agency_staff_pct=18.5,
        )
        deficit_summary = generate_deterministic_recommendations(
            deficit, scenario="staffing_stress"
        )

        # Now staffing domain must appear with HIGH priority
        assert "staffing" in _get_domain_set(deficit_summary), (
            "Injecting staffing deficit must produce staffing recommendations"
        )
        staffing_high = [
            r
            for r in deficit_summary.recommendations
            if r.domain == "staffing" and r.priority == "HIGH"
        ]
        assert len(staffing_high) > 0, (
            "Injecting staffing deficit must produce at least one HIGH staffing recommendation"
        )

    def test_fixing_transfer_spike_withdraws_transfer_recommendations(self) -> None:
        """AC-4.1.2: Removing the acute transfer spike withdraws hospital_transfers recommendations."""
        spike = _build_transfer_spike_snapshot()
        spike_summary = generate_deterministic_recommendations(
            spike, scenario="hospital_transfer_spike"
        )
        assert "hospital_transfers" in _get_domain_set(spike_summary), (
            "Transfer spike must produce hospital_transfers recs (test prerequisite)"
        )

        # Fix the spike — reduce transfers to healthy levels
        fixed = _build_transfer_spike_snapshot()
        fixed.hospital_transfers = HospitalTransferData(
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
        )
        fixed_summary = generate_deterministic_recommendations(
            fixed, scenario="baseline"
        )

        assert "hospital_transfers" not in _get_domain_set(fixed_summary), (
            "Fixing transfer spike must withdraw hospital_transfers recommendations"
        )

    def test_fixing_auth_cliff_withdraws_auth_recommendations(self) -> None:
        """AC-4.1.2: Removing the authorization cliff withdraws payer_auth recommendations."""
        cliff = _build_auth_cliff_snapshot()
        cliff_summary = generate_deterministic_recommendations(
            cliff, scenario="auth_cliff"
        )
        assert "payer_auth" in _get_domain_set(cliff_summary), (
            "Auth cliff must produce payer_auth recs (test prerequisite)"
        )

        # Fix the cliff — reduce expiring authorizations
        fixed = _build_auth_cliff_snapshot()
        fixed.payer_auth = PayerAuthData(
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
        )
        fixed_summary = generate_deterministic_recommendations(
            fixed, scenario="baseline"
        )

        assert "payer_auth" not in _get_domain_set(fixed_summary), (
            "Fixing auth cliff must withdraw payer_auth recommendations"
        )

    @pytest.mark.asyncio
    async def test_baseline_scenario_does_not_produce_stressed_recommendations(
        self,
    ) -> None:
        """AC-4.1.2: Baseline scenario does not produce domain-specific recs from stressed scenarios."""
        agent = FacilityRecommendationAgent()

        baseline_report = await agent.generate_recommendations(
            "ignite-oak-brook", scenario="baseline"
        )
        baseline_domains = _get_domain_set(
            baseline_report.verified_recommendations_summary
        )

        # Baseline should not surface stress-specific domains
        stress_domains = {"staffing", "payer_auth", "hospital_transfers", "therapy"}
        unexpected = baseline_domains & stress_domains
        assert not unexpected, (
            f"Baseline scenario unexpectedly produced recs in stress domains: {unexpected}"
        )

    def test_incremental_deficit_addition_gradually_adds_recommendations(self) -> None:
        """AC-4.1.2: Adding deficits one at a time incrementally increases recommendation count."""
        base = _build_healthy_snapshot()
        base_summary = generate_deterministic_recommendations(base, scenario="baseline")
        base_count = base_summary.total_recommendations_count

        # Add staffing deficit
        with_staffing = _build_healthy_snapshot()
        with_staffing.staffing = StaffingData(
            hppd_actual=3.62,
            hppd_budgeted_target=4.20,
            rn_hours_actual=140.0,
            lpn_hours_actual=180.0,
            cna_hours_actual=280.0,
            call_in_absences_count=6,
            open_shifts_count=5,
            overtime_hours=36.5,
            agency_staff_pct=18.5,
        )
        staffing_summary = generate_deterministic_recommendations(
            with_staffing, scenario="staffing_stress"
        )

        assert staffing_summary.total_recommendations_count > base_count, (
            f"Adding staffing deficit should increase rec count from {base_count} "
            f"to more, got {staffing_summary.total_recommendations_count}"
        )

        # Add auth deficit on top
        with_both = _build_healthy_snapshot()
        with_both.staffing = with_staffing.staffing
        with_both.payer_auth = PayerAuthData(
            payer_mix_pct={
                "Medicare A": 38.0,
                "Managed Care": 30.0,
                "Medicaid": 18.0,
                "Commercial": 10.0,
                "VA": 4.0,
            },
            expiring_authorizations_48h=9,
            expiring_authorizations_72h=16,
            pending_reauthorizations_count=12,
            auth_denials_pending_appeal_count=4,
        )
        both_summary = generate_deterministic_recommendations(
            with_both, scenario="staffing_stress"
        )

        assert (
            both_summary.total_recommendations_count
            > staffing_summary.total_recommendations_count
        ), (
            f"Adding auth deficit should further increase rec count from "
            f"{staffing_summary.total_recommendations_count}, got {both_summary.total_recommendations_count}"
        )
