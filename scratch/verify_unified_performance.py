"""Comprehensive Performance and Verification Benchmark for Unified Facility Analysis Architecture."""

import asyncio
import json
import os
import time
from dotenv import load_dotenv

load_dotenv()

from src.agent.unified_agent import FacilityUnifiedAnalysisAgent
from src.mcp.client import MockDomoMCPClient
from src.agent.llm_client import LLMClient


async def run_benchmark():
    mcp_client = MockDomoMCPClient()
    llm_client = LLMClient()
    agent = FacilityUnifiedAnalysisAgent(mcp_client=mcp_client, llm_client=llm_client)

    print("=" * 70)
    print("IGNITE OPERATIONAL DECISION AGENT - UNIFIED ARCHITECTURE BENCHMARK")
    print(f"Active Provider: {llm_client.effective_provider}")
    print(f"Active Model:    {llm_client.model}")
    print("=" * 70)

    scenarios = [
        "staffing_stress",
        "auth_cliff",
        "high_census_strain",
        "hospital_transfer_spike",
        "therapy_disruption",
        "baseline",
    ]

    results = []

    for sc in scenarios:
        print(f"\n--- Testing Scenario: {sc} ---")
        t0 = time.perf_counter()

        # Step 1: Measure MCP data retrieval
        t_mcp0 = time.perf_counter()
        snapshot = mcp_client.get_facility_snapshot("ignite-oak-brook", scenario=sc)
        history = mcp_client.get_facility_history("ignite-oak-brook", days_history=30, scenario=sc)
        t_mcp = (time.perf_counter() - t_mcp0) * 1000

        # Step 2: Measure Python calculation time
        from src.analytics.calculations import calculate_facility_metrics
        from src.analytics.trends import calculate_historical_trends
        from src.analytics.attention_areas import evaluate_attention_areas
        from src.analytics.recommendations import generate_deterministic_recommendations
        from src.analytics.positive_highlights import evaluate_positive_highlights

        t_py0 = time.perf_counter()
        calcs = calculate_facility_metrics(snapshot, history, scenario=sc)
        trends = calculate_historical_trends(snapshot, history, scenario=sc)
        att = evaluate_attention_areas(snapshot, history, sc, calcs, trends)
        recs = generate_deterministic_recommendations(snapshot, history, sc, calcs, trends, att)
        pos = evaluate_positive_highlights(snapshot, history, sc, trends)
        t_py = (time.perf_counter() - t_py0) * 1000

        # Step 3: Run complete analyze_facility (measures total wall-clock time)
        t_call0 = time.perf_counter()
        res = await agent.analyze_facility(
            facility_id="ignite-oak-brook",
            scenario=sc,
        )
        total_wall_ms = (time.perf_counter() - t_call0) * 1000

        receipt = res.audit_receipt
        llm_ms = receipt.latency_ms

        print(f"Status: {res.overall_status} ({res.status_label})")
        print(f"Analysis State: {res.analysis_state}")
        print(f"Data Retrieval Latency: {t_mcp:.2f} ms")
        print(f"Python Calc Latency:    {t_py:.2f} ms")
        print(f"LLM Latency:            {llm_ms:.2f} ms ({llm_ms/1000:.2f}s)")
        print(f"Total Wall-Clock:       {total_wall_ms:.2f} ms ({total_wall_ms/1000:.2f}s)")
        print(f"Findings Count:         {len(res.findings)}")
        print(f"Positive Count:         {len(res.positive_highlights)}")
        print(f"Questions Count:        {len(res.suggested_questions)}")
        print(f"Prompt Chars / Compl:   {receipt.prompt_chars} / {receipt.completion_chars}")
        print(f"Live LLM Call:          {receipt.is_live_call}")
        print(f"Executive Summary:      {res.executive_summary[:120]}...")

        if res.findings:
            f0 = res.findings[0]
            print(f"  [Finding 1]: {f0.title}")
            print(f"    - What's Happening: {f0.whatsHappening[:100]}...")
            print(f"    - Why It Matters:   {f0.whyItMatters[:100]}...")
            if f0.recommendation:
                print(f"    - Consider:         {f0.recommendation.consider[:100]}...")
                print(f"    - Why Suggested:    {f0.recommendation.whySuggested[:100]}...")

        if res.suggested_questions:
            print(f"  [Suggested Q1]: {res.suggested_questions[0].question_text}")

        results.append({
            "scenario": sc,
            "mcp_ms": t_mcp,
            "py_ms": t_py,
            "llm_ms": llm_ms,
            "total_ms": total_wall_ms,
            "live_call": receipt.is_live_call,
            "prompt_chars": receipt.prompt_chars,
            "completion_chars": receipt.completion_chars,
            "q1": res.suggested_questions[0].question_text if res.suggested_questions else "",
        })

    print("\n" + "=" * 70)
    print("FINAL BENCHMARK SUMMARY ACROSS ALL SCENARIOS")
    print("=" * 70)
    print(f"{'Scenario':<25} | {'MCP (ms)':<9} | {'Py (ms)':<8} | {'LLM (s)':<8} | {'Total (s)':<9} | {'Prompt':<7} | {'Compl':<6}")
    print("-" * 80)
    for r in results:
        print(f"{r['scenario']:<25} | {r['mcp_ms']:<9.2f} | {r['py_ms']:<8.2f} | {r['llm_ms']/1000:<8.2f} | {r['total_ms']/1000:<9.2f} | {r['prompt_chars']:<7} | {r['completion_chars']:<6}")

    print("\nDynamic Suggested Questions by Scenario:")
    for r in results:
        print(f"  * {r['scenario']}: {r['q1']}")

if __name__ == "__main__":
    asyncio.run(run_benchmark())
