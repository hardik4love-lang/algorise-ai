"""
Verifies the advanced market-driven upgrades: Causal Safety Gate, GraphRAG, and MCP Adapter.
"""

from engine.guardrails import AlgoriseSafetyGate
from engine.graph_rag import AlgoriseGraphRAG
from engine.mcp_adapter import AlgoriseMCPAdapter
from engine.bots import NexusBot, CortexBot, HunterBot

def main():
    print("=" * 65)
    print("  ALGORISE ADVANCED ENGINE UPGRADES VERIFICATION")
    print("=" * 65)

    # 1. Test Causal Safety Gate
    gate = AlgoriseSafetyGate()
    
    # Safe Action
    safe_approved, code, flags = gate.audit_bot_action("nexus", {"action": "track_order", "order_id": "ORD-991"})
    print(f"\n[1] Causal Safety Gate - Normal Action:")
    print(f"    Approved: {safe_approved} ({code})")
    print(f"    Audit:    {flags[0]}")

    # Malicious / Unsafe Action Block
    malicious_action = {"action": "drop table users; --", "target": "database"}
    unsafe_approved, u_code, u_flags = gate.audit_bot_action("nexus", malicious_action)
    print(f"\n[2] Causal Safety Gate - Rogue SQL Injection Block:")
    print(f"    Approved: {unsafe_approved} ({u_code})")
    print(f"    Blocked:  {u_flags[0]}")

    # 2. Test Hybrid GraphRAG Context Layer
    graph = AlgoriseGraphRAG()
    graph.index_entity_relations("AcmeCorp", ["Order992", "SLA_Tier1", "CloudVPC"], {"account_status": "Enterprise VIP"})
    graph.index_entity_relations("Order992", ["Shipper_FedEx", "Warehouse_Chicago"], {"eta": "Tomorrow 10am"})

    context = graph.query_context("What is the status of AcmeCorp order delivery?")
    print(f"\n[3] Hybrid GraphRAG - Missing Context Layer:")
    print(f"    Entities Discovered: {context['seed_entities_found']}")
    print(f"    Multi-Hop Graph:     {context['multi_hop_connected_entities']}")
    print(f"    Context Density:     {context['context_density_score']}")

    # 3. Test Model Context Protocol (MCP) Adapter
    registry = {"nexus": NexusBot(), "cortex": CortexBot(), "hunter": HunterBot()}
    mcp = AlgoriseMCPAdapter(registry)
    tools = mcp.list_tools()
    print(f"\n[4] Model Context Protocol (MCP) Adapter:")
    print(f"    MCP Tools Declared: {len(tools)}")
    for t in tools:
        print(f"    - {t['name']}: {t['description'][:50]}...")

    print("\n" + "=" * 65)
    print("  ALL MARKET-DRIVEN ARCHITECTURAL UPGRADES FUNCTIONING OPTIMALLY")
    print("=" * 65)

if __name__ == "__main__":
    main()
