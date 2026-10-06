"""
Tests verifying that the Algorise Marketing Claims are now fully functional realities:
1. Native Model Context Protocol (MCP) tool discovery & execution.
2. Enterprise Hybrid GraphRAG Context Layer (Knowledge Graph + Semantic Vectors).
3. Deterministic Causal Safety Release Gates.
4. Live Empirical Tuning & Benchmark Telemetry.
5. Hardened Authentication on all router surfaces.
"""

import pytest
from fastapi.testclient import TestClient

from engine.graph_rag import graph_rag
from engine.guardrails import safety_gate
from engine.mcp_adapter import AlgoriseMCPAdapter
from engine.main import app
from engine.hero_registry import HERO_BOT_REGISTRY_MAP


@pytest.fixture
def client():
    return TestClient(app)


# ============================================================================
# 1. MODEL CONTEXT PROTOCOL (MCP) TESTS
# ============================================================================

def test_mcp_list_tools():
    adapter = AlgoriseMCPAdapter(bot_registry=HERO_BOT_REGISTRY_MAP)
    tools = adapter.list_tools()
    assert len(tools) >= 5
    tool_names = [t["name"] for t in tools]
    assert "algorise_graphrag_query" in tool_names
    assert "algorise_causal_safety_audit" in tool_names
    assert "algorise_catalog_search" in tool_names
    assert "algorise_classify_lead" in tool_names
    assert "algorise_attribution_funnel" in tool_names

    # Check JSON Schema structure
    for t in tools:
        assert "inputSchema" in t
        assert t["inputSchema"]["type"] == "object"


def test_mcp_call_tool_catalog_search():
    adapter = AlgoriseMCPAdapter(bot_registry=HERO_BOT_REGISTRY_MAP)
    res = adapter.call_tool("algorise_catalog_search", {"keyword": "tejal", "size": "M"})
    assert not res["isError"]
    assert "content" in res
    assert res["meta"]["latency_ms"] < 50.0


def test_mcp_call_tool_graphrag():
    adapter = AlgoriseMCPAdapter(bot_registry=HERO_BOT_REGISTRY_MAP)
    res = adapter.call_tool("algorise_graphrag_query", {"query": "plus size curvy silk suit"})
    assert not res["isError"]
    assert len(res["content"]) >= 2
    assert "grounded_context" in res["content"][1]["data"]


def test_mcp_blocked_by_safety_gate():
    adapter = AlgoriseMCPAdapter(bot_registry=HERO_BOT_REGISTRY_MAP)
    res = adapter.call_tool("algorise_catalog_search", {"keyword": "drop table clients; --"})
    assert res["isError"]
    assert "Blocked by Algorise Causal Safety Gate" in res["content"][0]["text"]
    assert res["meta"]["safety_gate"] == "BLOCKED"


def test_mcp_jsonrpc_protocol():
    adapter = AlgoriseMCPAdapter(bot_registry=HERO_BOT_REGISTRY_MAP)

    # Initialize
    init_res = adapter.handle_jsonrpc({"id": "req-1", "method": "initialize", "params": {}})
    assert init_res["result"]["serverInfo"]["name"] == "algorise-ai-mcp"
    assert init_res["result"]["protocolVersion"] == "2024-11-05"

    # Tools/list
    tools_res = adapter.handle_jsonrpc({"id": "req-2", "method": "tools/list", "params": {}})
    assert len(tools_res["result"]["tools"]) >= 5

    # Tools/call
    call_res = adapter.handle_jsonrpc({
        "id": "req-3",
        "method": "tools/call",
        "params": {
            "name": "algorise_classify_lead",
            "arguments": {"comment_text": "Need 50 pieces wholesale georgette saree, send rate on 9825012345"},
        },
    })
    assert "result" in call_res
    assert not call_res["result"]["isError"]


def test_mcp_api_endpoints(client):
    headers = {"X-Algorise-Key": "alg_live_test_key_9981"}

    # List tools endpoint
    resp = client.get("/api/v1/mcp/tools", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()["tools"]) >= 5

    # Call tool endpoint
    resp = client.post(
        "/api/v1/mcp/call",
        json={"name": "algorise_catalog_search", "arguments": {"keyword": "bandhani"}},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["isError"] is False

    # JSON-RPC endpoint
    resp = client.post(
        "/api/v1/mcp",
        json={"id": "mcp-test", "method": "ping", "params": {}},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["id"] == "mcp-test"


# ============================================================================
# 2. HYBRID GRAPHRAG CONTEXT LAYER TESTS
# ============================================================================

def test_graphrag_ontology_integrity():
    assert len(graph_rag.nodes) >= 15
    assert len(graph_rag.adjacency) >= 5
    assert "prod_tejal" in graph_rag.nodes
    assert "prod_b2876" in graph_rag.nodes
    assert "merchant_shruhi" in graph_rag.nodes


def test_graphrag_multi_hop_traversal():
    scores, paths = graph_rag.multi_hop_traversal(["prod_b2876"], max_hops=2)
    assert len(scores) >= 3
    # B-2876 belongs to cat_plussize and fab_silk
    assert "cat_plussize" in scores
    assert "fab_silk" in scores


def test_graphrag_hybrid_query():
    res = graph_rag.query_context_sync("Curvy Plus Size 4XL festive suit")
    assert len(res["retrieved_context_nodes"]) > 0
    assert res["confidence_score"] >= 0.5
    assert "B-2876" in res["grounded_context"] or "Plus-Size" in res["grounded_context"]


def test_graphrag_api_endpoints(client):
    headers = {"X-Algorise-Key": "alg_live_test_key_9981"}

    # Query endpoint
    resp = client.post(
        "/api/v1/graphrag/query",
        json={"query": "Pure Roman Silk with Pan-India delivery", "top_k": 3},
        headers=headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "retrieved_context_nodes" in body
    assert "confidence_score" in body
    assert body["confidence_score"] > 0.0

    # Stats endpoint
    resp = client.get("/api/v1/graphrag/stats", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["total_nodes"] >= 15


# ============================================================================
# 3. DETERMINISTIC CAUSAL SAFETY GATE TESTS
# ============================================================================

def test_safety_gate_blocks_sql_injection():
    is_safe, code, flags = safety_gate.audit_bot_action(
        "sql_test", {"query": "SELECT * FROM users WHERE 1=1; DROP TABLE clients; --"}
    )
    assert not is_safe
    assert code in ["BLOCKED_MALICIOUS_SQL", "BLOCKED_MALICIOUS_INTENT"]
    assert len(flags) > 0


def test_safety_gate_blocks_shell_execution():
    is_safe, code, flags = safety_gate.audit_bot_action(
        "cmd_test", {"action": "rm -rf /var/data && cat /etc/passwd"}
    )
    assert not is_safe
    assert code in ["BLOCKED_COMMAND_INJECTION", "BLOCKED_MALICIOUS_INTENT"]


def test_safety_gate_blocks_financial_overflow():
    is_safe, code, flags = safety_gate.audit_bot_action(
        "finance_test", {"amount": 999999.0, "currency": "INR"}
    )
    assert not is_safe
    assert code == "REQUIRES_HUMAN_SIGN_OFF"


def test_safety_gate_blocks_excessive_discount():
    is_safe, code, flags = safety_gate.audit_bot_action(
        "discount_test", {"discount_pct": 75.0}
    )
    assert not is_safe
    assert code == "DISCOUNT_EXCEEDED_REQUIRES_APPROVAL"


def test_safety_gate_approves_safe_action():
    is_safe, code, flags = safety_gate.audit_bot_action(
        "safe_test", {"action": "catalog_lookup", "item_code": "TEJAL"}
    )
    assert is_safe
    assert code == "APPROVED_DETERMINISTIC"


def test_safety_audit_api_endpoint(client):
    headers = {"X-Algorise-Key": "alg_live_test_key_9981"}
    resp = client.post(
        "/api/v1/safety/audit",
        json={"action_type": "meta_reply", "payload": {"message": "Thank you! Check our catalog."}},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["is_approved"] is True
    assert resp.json()["latency_ms"] < 20.0


# ============================================================================
# 4. LIVE EMPIRICAL BENCHMARK & TUNING STATUS TESTS
# ============================================================================

def test_tuning_status_returns_live_empirical_metrics(client):
    headers = {"X-Algorise-Key": "alg_live_test_key_9981"}
    resp = client.get("/api/v1/tuning/status", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["live_measured"] is True
    assert data["total_evaluated"] >= 10
    assert "functional_pass_rate" in data
    assert "safety_gate_block_rate" in data
    assert data["average_latency_ms"] > 0.0


# ============================================================================
# 5. AUTHENTICATION PROTECTION ON ROUTERS
# ============================================================================

def test_invalid_api_key_rejected_with_401(client):
    bad_headers = {"X-Algorise-Key": "bad_key_12345"}
    assert client.get("/api/v1/meta/status", headers=bad_headers).status_code == 401
    assert client.get("/api/v1/attribution/funnel", headers=bad_headers).status_code == 401
    assert client.get("/api/v1/client/client_srt_shruhi/brand", headers=bad_headers).status_code == 401
    assert client.get("/api/v1/distribution/capabilities", headers=bad_headers).status_code == 401
