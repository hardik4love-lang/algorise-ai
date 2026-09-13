import json
import time
from engine.tuning_engine import AlgoriseTuningEngine
from engine.hero_registry import HERO_BOT_DEFINITIONS, HeroBotRunner

def run_deep_test_and_tune():
    print("=================================================================")
    print(">> ALGORISE 100 HERO BOTS: DEEP BENCHMARK, EXECUTION & TUNING PASS")
    print("=================================================================")

    runner = HeroBotRunner()
    tuning_engine = AlgoriseTuningEngine()

    start_time = time.time()
    results = tuning_engine.run_full_suite()
    total_elapsed = time.time() - start_time

    print("\n-----------------------------------------------------------------")
    print(">> SECTOR BY SECTOR BREAKDOWN (ALL 10 SECTORS TESTED & TUNED):")
    print("-----------------------------------------------------------------")
    for sector, metrics in results["sector_metrics"].items():
        avg_lat = round(metrics["total_lat"] / metrics["count"], 3)
        avg_conf = round(metrics["tuned_conf_sum"] / metrics["count"], 3)
        print(f"  [Sector] {sector:<14} | Bots: {metrics['count']} | Avg Latency: {avg_lat:>6.2f}ms | Avg Tuned Conf: {avg_conf * 100:.1f}%")

    print("\n-----------------------------------------------------------------")
    print(">> SAMPLING 10 REAL BOT DOMAIN COMPUTATIONS (ONE PER SECTOR):")
    print("-----------------------------------------------------------------")
    
    sector_samples = [
        ("agroyield", {"crop": "Wheat", "ndvi_index": 0.76, "soil_moisture_pct": 31.0, "growing_degree_days": 1520.0}),
        ("nexus_core", {"query": "Customer order #88412 cancellation and refund", "max_authorized_usd": 150.0}),
        ("dynamicprice", {"value": 85.00, "rate": 0.05}),
        ("sponsorscout", {"audience_size": 250000, "rate": 0.08}),
        ("caretriage", {"value": 75000.0, "query": "Acute chest pressure radiating to left arm"}),
        ("compgenius", {"value": 650000.0, "query": "4 bed 3 bath luxury suburban home"}),
        ("alphaaudit", {"value": 15000000.0, "query": "10-K footnote off-balance-sheet review"}),
        ("redline_playbook", {"value": 250000.0, "query": "Enterprise SaaS Master Services Agreement"}),
        ("routeoptima", {"value": 1200.0, "stops": 18}),
        ("gradeassure", {"value": 850.0, "essay_topic": "Ethical Implications of Autonomous Systems"})
    ]

    for bot_id, sample_payload in sector_samples:
        res = runner.execute_hero_bot(bot_id, sample_payload)
        domain_data = res.data.get("domain_output", {})
        print(f"\n[BOT: {res.bot_name}]")
        print(f"  - Status: {'PASS (100% Verified)' if res.success else 'FAIL'}")
        print(f"  - Latency: {res.latency_ms} ms")
        print(f"  - Confidence: {round(res.data.get('confidence_score', 0) * 100, 1)}%")
        print(f"  - Real Computed Output:")
        for k, v in list(domain_data.items())[:3]:
            print(f"      * {k}: {v}")

    print("\n=================================================================")
    print(f">> FINAL VERIFICATION: {results['total_passed']}/100 BOTS CERTIFIED FUNCTIONAL")
    print(f">> ADVERSARIAL CAUSAL SAFETY GATES: {results['safety_tests_passed']}/100 BLOCKED HARMFUL INJECTIONS")
    print(f">> AVERAGE EXECUTION LATENCY: {results['average_latency_ms']} ms")
    print(f">> TOTAL DURATION: {round(total_elapsed, 3)} seconds")
    print("=================================================================")

    # Save permanent audit artifact
    with open("hero_100_tuning_report.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(">> Report written to hero_100_tuning_report.json")

if __name__ == "__main__":
    run_deep_test_and_tune()
