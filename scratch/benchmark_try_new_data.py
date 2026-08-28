"""End-to-end benchmark measuring exact latencies for the 'Try New Facility Data' flow."""

import asyncio
import time
from httpx import AsyncClient, ASGITransport
from src.api.main import app
from src.data.mutator import mutate_facility_data
from src.mcp.client import MockDomoMCPClient
from src.analytics.calculations import calculate_facility_metrics
from src.analytics.trends import calculate_historical_trends
from src.analytics.attention_areas import evaluate_attention_areas
from src.analytics.recommendations import generate_deterministic_recommendations
from src.analytics.positive_highlights import evaluate_positive_highlights
from src.db.seed import reset_facility_data


async def run_benchmark():
    print("=" * 60)
    print("BENCHMARK: 'Try New Facility Data' Latency Breakdown")
    print("=" * 60)

    # 1. Measure raw database mutation latency
    t0 = time.perf_counter()
    mutate_result = mutate_facility_data(facility_id="ignite-oak-brook", scenario="baseline")
    t_mutate_ms = (time.perf_counter() - t0) * 1000.0
    print(f"1. Database Mutation (SQL update + commit): {t_mutate_ms:.2f} ms")

    # 2. Measure data retrieval via Mock Domo MCP from DB
    mcp_client = MockDomoMCPClient()
    t1 = time.perf_counter()
    snapshot = mcp_client.get_facility_snapshot(facility_id="ignite-oak-brook", scenario="baseline")
    history = mcp_client.get_facility_history(facility_id="ignite-oak-brook", days_history=30, scenario="baseline")
    t_retrieval_ms = (time.perf_counter() - t1) * 1000.0
    print(f"2. MCP Data Retrieval from DB: {t_retrieval_ms:.2f} ms")

    # 3. Measure deterministic Python calculations across all 8 domains
    t2 = time.perf_counter()
    calcs = calculate_facility_metrics(snapshot, history, scenario="baseline")
    trends = calculate_historical_trends(snapshot, history, scenario="baseline")
    attention_summary = evaluate_attention_areas(snapshot, history, scenario="baseline", calculations=calcs, trends=trends)
    rec_summary = generate_deterministic_recommendations(snapshot, history, scenario="baseline", calculations=calcs, trends=trends, attention_summary=attention_summary)
    pos_summary = evaluate_positive_highlights(snapshot, history, scenario="baseline", trends=trends)
    t_py_calcs_ms = (time.perf_counter() - t2) * 1000.0
    print(f"3. Deterministic Python Analytics (all 8 domains): {t_py_calcs_ms:.2f} ms")

    # 4. Measure HTTP POST mutation endpoint via FastAPI
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        t3 = time.perf_counter()
        post_res = await ac.post("/api/facilities/ignite-oak-brook/try-new-data?scenario=baseline")
        t_http_post_ms = (time.perf_counter() - t3) * 1000.0
        assert post_res.status_code == 200
        print(f"4. HTTP POST /api/facilities/ignite-oak-brook/try-new-data: {t_http_post_ms:.2f} ms")

        # 5. Measure HTTP GET unified analysis endpoint (deterministic offline fallback mode)
        t4 = time.perf_counter()
        get_res = await ac.get("/api/agent/facility-analysis?facility_id=ignite-oak-brook&scenario=baseline&force_refresh=true")
        t_http_get_ms = (time.perf_counter() - t4) * 1000.0
        assert get_res.status_code == 200
        analysis_data = get_res.json()
        print(f"5. HTTP GET /api/agent/facility-analysis (with reconciliation): {t_http_get_ms:.2f} ms")

        total_flow_ms = t_http_post_ms + t_http_get_ms
        print("-" * 60)
        print(f"TOTAL User-Visible Cycle (POST mutate + GET analysis): {total_flow_ms:.2f} ms ({total_flow_ms / 1000:.3f} s)")
        print(f"Analysis State: {analysis_data.get('analysis_state')}")
        print(f"Overall Status: {analysis_data.get('overall_status')} ({analysis_data.get('status_label')})")
        print("Vitals Generated:")
        for v in analysis_data.get("vitals", []):
            print(f"   - {v['label']}: {v['formatted_value']} ({v['subtitle']})")
        print("=" * 60)

    # Cleanup DB back to clean seed
    reset_facility_data("ignite-oak-brook")


if __name__ == "__main__":
    asyncio.run(run_benchmark())
