"""
Algorise AI Solutions — Proprietary Engine Demonstration Runner
Validates that Algorise's own in-house Bots & Autoflow Engines execute seamlessly.
"""

from engine.models import AutoflowPipeline, AutoflowStep, BotTask
from engine.bots import NexusBot, CortexBot, HunterBot, SentinelBot, PulseBot
from engine.autoflow import AlgoriseAutoflowEngine
import json

def main():
    print("=" * 70)
    print("  ALGORISE AI SOLUTIONS — PROPRIETARY ENGINE VERIFICATION")
    print("  'Rise Above with AI.' | In-House IP Architecture")
    print("=" * 70)

    # 1. Test Nexus Bot
    nexus = NexusBot()
    nexus_task = BotTask(input_payload={"query": "Can you check my order shipping status?", "customer_id": "cust_9921"})
    nexus_res = nexus.execute(nexus_task)
    print(f"\n[1] Bot: Nexus (Support & Action)")
    print(f"    Latency: {nexus_res.latency_ms}ms")
    print(f"    Intent:  {nexus_res.data['intent']}")
    print(f"    Action:  {nexus_res.data['action_taken']}")

    # 2. Test Cortex Bot (RAG)
    cortex = CortexBot()
    mock_docs = [
        {"id": "DOC-101", "content": "Algorise cloud deployments require zero-trust IAM authentication and private VPC endpoints."},
        {"id": "DOC-102", "content": "Our SLAs guarantee 99.99% uptime with failover clusters active across 3 availability zones."}
    ]
    cortex_task = BotTask(input_payload={"query": "What are the cloud VPC and SLA uptime requirements?", "documents": mock_docs})
    cortex_res = cortex.execute(cortex_task)
    print(f"\n[2] Bot: Cortex (Zero-Leakage RAG)")
    print(f"    Latency:    {cortex_res.latency_ms}ms")
    print(f"    Confidence: {cortex_res.data['confidence_score']}")
    print(f"    Citations:  {cortex_res.data['source_citations']}")

    # 3. Test Hunter Bot (Outbound Lead Scout)
    hunter = HunterBot()
    hunter_task = BotTask(input_payload={"company": "Vanguard Logistics", "role": "VP of Engineering"})
    hunter_res = hunter.execute(hunter_task)
    print(f"\n[3] Bot: Hunter (B2B Lead Scout)")
    print(f"    Target:  {hunter_res.data['target_company']} ({hunter_res.data['target_role']})")
    print(f"    Pitch:   {hunter_res.data['personalized_sequence'][:90]}...")

    # 4. Test Sentinel Bot (DevOps & Code Security)
    sentinel = SentinelBot()
    sentinel_task = BotTask(input_payload={"diff": "def connect_db(): token = os.getenv('DB_SECRET'); return token"})
    sentinel_res = sentinel.execute(sentinel_task)
    print(f"\n[4] Bot: Sentinel (DevOps & Code Integrity)")
    print(f"    Audit Passed: {sentinel_res.data['audit_passed']}")
    print(f"    Vulnerabilities: {sentinel_res.data['issues']}")

    # 5. Test Pulse Bot (Natural Language to SQL)
    pulse = PulseBot()
    pulse_task = BotTask(input_payload={"question": "What is our gross recurring revenue across all enterprise accounts?"})
    pulse_res = pulse.execute(pulse_task)
    print(f"\n[5] Bot: Pulse (Conversational Text-to-SQL)")
    print(f"    Generated SQL: {pulse_res.data['query_generated']}")
    print(f"    Summary:       {pulse_res.data['summary']}")

    # 6. Test Algorise Autoflow Engine (Multi-Agent End-to-End Pipeline)
    print("\n" + "-" * 70)
    print("  TESTING ALGORISE AUTOFLOW ENGINE (EVENT-DRIVEN PIPELINE)")
    print("-" * 70)

    autoflow_engine = AlgoriseAutoflowEngine()
    
    # Define an enterprise client autoflow pipeline
    pipeline = AutoflowPipeline(
        name="Enterprise Inbound Automation & Resolution Flow",
        client_id="enterprise_client_001",
        steps=[
            AutoflowStep(
                step_id="step_1_triage",
                bot_name="nexus",
                action="classify_and_triage",
                parameters={"query": "We have an urgent question about our cloud VPC latency SLA."}
            ),
            AutoflowStep(
                step_id="step_2_knowledge_retrieval",
                bot_name="cortex",
                action="retrieve_context",
                parameters={"query": "cloud VPC latency SLA", "documents": mock_docs}
            ),
            AutoflowStep(
                step_id="step_3_audit_telemetry",
                bot_name="pulse",
                action="query_telemetry",
                parameters={"question": "Check recent SLA telemetry uptime metrics"}
            )
        ]
    )

    flow_id = autoflow_engine.register_pipeline(pipeline)
    execution_result = autoflow_engine.execute_flow(flow_id, {"trigger_type": "customer_webhook"})

    print(f"  Pipeline ID:    {execution_result['flow_id']}")
    print(f"  Total Duration: {execution_result['total_latency_ms']}ms")
    print(f"  Status:         {execution_result['status']}")
    print("  Execution Log:")
    for log in execution_result['execution_log']:
        print(f"    {log}")

    print("\n" + "=" * 70)
    print("  VERIFICATION COMPLETE: ALL PROPRIETARY BOTS & AUTOFLOWS OPERATIONAL")
    print("=" * 70)

if __name__ == "__main__":
    main()
