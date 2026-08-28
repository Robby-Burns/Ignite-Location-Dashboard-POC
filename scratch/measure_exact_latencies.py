"""Measure precise latencies of all components in local test mode and report metrics."""

import asyncio
import os
import time

os.environ["TESTING"] = "1"

from httpx import AsyncClient, ASGITransport
from src.api.main import app
from src.data.mutator import mutate_facility_data
from src.mcp.client import MockDomoMCPClient
from src.analytics.calculations import calculate_facility_metrics
from src.analytics.trends import calculate_historical_trends
from src.analytics.attention_areas import evaluate_attention_areas
from src.analytics.recommendations import generate_deterministic_recommendations
from src.analytics.positive_highlights import evaluate_positive_highlights
from src.agent.llm_client import LLMClient, LLMExecutionReceipt
from src.agent.unified_agent import FacilityUnifiedAnalysisAgent
from src.db.seed import reset_facility_data


async def measure():
    print("=" * 65)
    print("IGNITE DECISION AGENT — 'TRY NEW FACILITY DATA' LATENCY AUDIT")
    print("=" * 65)

    # 1. Measure DB mutation
    t0 = time.perf_counter()
    res = mutate_facility_data("ignite-oak-brook", "baseline")
    t_mutate = (time.perf_counter() - t0) * 1000.0
    print(f"1. Database Mutation (SQL update + commit):        {t_mutate:6.2f} ms")

    # 2. Measure MCP data retrieval
    mcp = MockDomoMCPClient()
    t1 = time.perf_counter()
    snap = mcp.get_facility_snapshot("ignite-oak-brook", "baseline")
    hist = mcp.get_facility_history("ignite-oak-brook", 30, "baseline")
    t_mcp = (time.perf_counter() - t1) * 1000.0
    print(f"2. MCP Data Retrieval (from SQLite DB):           {t_mcp:6.2f} ms")

    # 3. Measure Python Calculations
    t2 = time.perf_counter()
    calcs = calculate_facility_metrics(snap, hist, "baseline")
    trends = calculate_historical_trends(snap, hist, "baseline")
    att = evaluate_attention_areas(snap, hist, "baseline", calcs, trends)
    recs = generate_deterministic_recommendations(snap, hist, "baseline", calcs, trends, att)
    pos = evaluate_positive_highlights(snap, hist, "baseline", trends=trends)
    t_calc = (time.perf_counter() - t2) * 1000.0
    print(f"3. Python Analytics Engine (all 8 domains):       {t_calc:6.2f} ms")

    # 4. FastAPI POST endpoint
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        t3 = time.perf_counter()
        post_resp = await ac.post("/api/facilities/ignite-oak-brook/try-new-data?scenario=baseline")
        t_post = (time.perf_counter() - t3) * 1000.0
        print(f"4. HTTP POST /api/facilities/try-new-data:        {t_post:6.2f} ms")

        # 5. FastAPI GET unified analysis endpoint
        t4 = time.perf_counter()
        get_resp = await ac.get("/api/agent/facility-analysis?facility_id=ignite-oak-brook&scenario=baseline&force_refresh=true")
        t_get = (time.perf_counter() - t4) * 1000.0
        print(f"5. HTTP GET /api/agent/facility-analysis:         {t_get:6.2f} ms")

        total = t_post + t_get
        print("-" * 65)
        print(f"TOTAL User-Visible Cycle (POST + GET):            {total:6.2f} ms ({total/1000:.3f} s)")
        print("=" * 65)

    reset_facility_data("ignite-oak-brook")


if __name__ == "__main__":
    asyncio.run(measure())
