"""Tests for 'Try New Facility Data' database mutation and unified analysis flow."""

import time
import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select

from src.api.main import app
from src.data.mutator import mutate_facility_data
from src.db.database import _get_session_factory, init_db
from src.db.models import DailySnapshotRecord
from src.agent.llm_client import LLMClient, LLMExecutionReceipt
from src.models.facility import DailyFacilitySnapshot


from src.api.routes import mcp_server, unified_agent
from src.db.seed import reset_facility_data


@pytest.fixture(autouse=True)
def setup_and_teardown_db():
    init_db()
    reset_facility_data("ignite-oak-brook")
    reset_facility_data("ignite-mokena")
    mcp_server.data_loader.clear_cache()
    unified_agent.clear_cache()
    yield
    reset_facility_data("ignite-oak-brook")
    reset_facility_data("ignite-mokena")
    mcp_server.data_loader.clear_cache()
    unified_agent.clear_cache()


@pytest.mark.asyncio
async def test_try_new_facility_data_endpoint_success():
    """Verify POST /api/facilities/{facility_id}/try-new-data succeeds and returns modified fields."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        res = await ac.post("/api/facilities/ignite-oak-brook/try-new-data?scenario=baseline")
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert data["facility_id"] == "ignite-oak-brook"
        assert data["scenario"] == "baseline"
        assert "modified_fields" in data
        assert "staffing_hppd_actual" in data["modified_fields"]
        assert "census_current" in data["modified_fields"]


@pytest.mark.asyncio
async def test_database_record_actually_mutated():
    """Verify that the database records in daily_facility_snapshots are actually mutated in-place."""
    with _get_session_factory()() as session:
        # Retrieve snapshot record before
        rec_before = session.scalar(
            select(DailySnapshotRecord)
            .where(
                DailySnapshotRecord.facility_id == "ignite-oak-brook",
                DailySnapshotRecord.scenario_name == "baseline",
            )
            .order_by(DailySnapshotRecord.snapshot_date.desc())
        )
        if rec_before:
            data_before = dict(rec_before.data_json)
            hppd_before = data_before["staffing"]["hppd_actual"]
        else:
            hppd_before = None

    # Perform mutation
    result = mutate_facility_data(facility_id="ignite-oak-brook", scenario="baseline")
    assert result["success"] is True

    # Retrieve snapshot record after from fresh DB session
    with _get_session_factory()() as session:
        rec_after = session.scalar(
            select(DailySnapshotRecord)
            .where(
                DailySnapshotRecord.facility_id == "ignite-oak-brook",
                DailySnapshotRecord.scenario_name == "baseline",
            )
            .order_by(DailySnapshotRecord.snapshot_date.desc())
        )
        assert rec_after is not None
        data_after = dict(rec_after.data_json)
        hppd_after = data_after["staffing"]["hppd_actual"]

        # Ensure database row data has actually changed
        if hppd_before is not None:
            assert hppd_after != hppd_before or data_after != data_before
        assert hppd_after == result["modified_fields"]["staffing_hppd_actual"]


@pytest.mark.asyncio
async def test_mutation_modifies_only_target_facility():
    """Verify that mutating ignite-oak-brook does NOT modify other facilities like ignite-mokena."""
    mutate_facility_data(facility_id="ignite-mokena", scenario="baseline")

    with _get_session_factory()() as session:
        mokena_rec_before = session.scalar(
            select(DailySnapshotRecord)
            .where(
                DailySnapshotRecord.facility_id == "ignite-mokena",
                DailySnapshotRecord.scenario_name == "baseline",
            )
            .order_by(DailySnapshotRecord.snapshot_date.desc())
        )
        mokena_data_before = dict(mokena_rec_before.data_json)

    # Mutate ONLY ignite-oak-brook
    mutate_facility_data(facility_id="ignite-oak-brook", scenario="baseline")

    with _get_session_factory()() as session:
        mokena_rec_after = session.scalar(
            select(DailySnapshotRecord)
            .where(
                DailySnapshotRecord.facility_id == "ignite-mokena",
                DailySnapshotRecord.scenario_name == "baseline",
            )
            .order_by(DailySnapshotRecord.snapshot_date.desc())
        )
        mokena_data_after = dict(mokena_rec_after.data_json)

        # Verify mokena was untouched
        assert mokena_data_after == mokena_data_before


@pytest.mark.asyncio
async def test_unknown_facility_fails_safely():
    """Verify that an invalid facility returns HTTP 404."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        res = await ac.post("/api/facilities/invalid-facility-999/try-new-data")
        assert res.status_code == 404
        assert "not recognized" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_unified_analysis_pipeline_consumes_mutated_data():
    """Verify the normal /api/agent/facility-analysis endpoint reflects updated DB data with 1 LLM call."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        # 1. Mutate data via endpoint
        mutate_res = await ac.post("/api/facilities/ignite-oak-brook/try-new-data?scenario=baseline")
        assert mutate_res.status_code == 200
        mod_fields = mutate_res.json()["modified_fields"]

        # 2. Call unified analysis
        analysis_res = await ac.get(
            "/api/agent/facility-analysis?facility_id=ignite-oak-brook&scenario=baseline&force_refresh=true"
        )
        assert analysis_res.status_code == 200
        analysis = analysis_res.json()

        # Check that vitals in analysis reflect the mutated DB data
        vitals_map = {v["label"]: v["formatted_value"] for v in analysis["vitals"]}
        assert "Direct Care HPPD" in vitals_map
        assert f"{mod_fields['staffing_hppd_actual']:.2f}" in vitals_map["Direct Care HPPD"]
        assert "Occupancy Rate" in vitals_map
        assert f"{mod_fields['occupancy_rate_pct']:.1f}%" in vitals_map["Occupancy Rate"]
        assert "Therapy Completion" in vitals_map
        assert f"{mod_fields['therapy_completion_rate_pct']:.1f}%" in vitals_map["Therapy Completion"]


@pytest.mark.asyncio
async def test_exactly_one_llm_call_during_refresh():
    """Verify that calling the unified facility analysis after mutation executes exactly ONE LLM call."""
    mock_receipt = LLMExecutionReceipt(
        receipt_id="REC-TEST-TRY-NEW-DATA",
        provider="mock",
        model="google/gemini-2.5-flash-lite",
        latency_ms=120.0,
        is_live_call=True,
        prompt_chars=1000,
        completion_chars=500,
    )
    mock_llm_response = {
        "executive_summary": "Facility operations reflect updated staffing coverage and dynamic admission shifts.",
        "findings_interpretations": [],
        "positive_interpretations": [],
        "suggested_questions": [
            {
                "question_text": "What is driving the recent staffing variation?",
                "related_domain": "staffing",
                "context_summary": "Staffing metrics adjusted in synthetic data.",
                "priority": "HIGH",
            }
        ],
    }

    with patch.object(
        LLMClient,
        "generate_structured_analysis",
        new_callable=AsyncMock,
        return_value=(mock_llm_response, mock_receipt),
    ) as mock_gen:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            # 1. Mutate (must NOT call LLM)
            mutate_res = await ac.post("/api/facilities/ignite-oak-brook/try-new-data?scenario=baseline")
            assert mutate_res.status_code == 200
            assert mock_gen.call_count == 0  # Zero LLM calls for mutation

            # 2. Unified analysis (must call LLM exactly ONCE)
            analysis_res = await ac.get(
                "/api/agent/facility-analysis?facility_id=ignite-oak-brook&scenario=baseline&force_refresh=true"
            )
            assert analysis_res.status_code == 200
            assert mock_gen.call_count == 1  # Exactly ONE LLM call


@pytest.mark.asyncio
async def test_latency_benchmarks():
    """Benchmark the execution speed of mutation, data loading, and Python analytics."""
    # 1. Mutation speed
    t0 = time.perf_counter()
    result = mutate_facility_data(facility_id="ignite-oak-brook", scenario="baseline")
    mutation_ms = (time.perf_counter() - t0) * 1000.0
    assert result["success"] is True
    # DB mutation should complete in well under 100ms (typically < 15ms)
    assert mutation_ms < 200.0

    # 2. Fast API endpoint roundtrip (excluding live LLM network)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        t1 = time.perf_counter()
        res = await ac.post("/api/facilities/ignite-oak-brook/try-new-data?scenario=baseline")
        endpoint_ms = (time.perf_counter() - t1) * 1000.0
        assert res.status_code == 200
        assert endpoint_ms < 200.0
