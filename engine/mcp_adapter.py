"""
Algorise Model Context Protocol (MCP) Native Adapter
Provides standardized MCP (2024-11-05 spec) tool discovery and execution endpoints
for enterprise AI integration (Claude Desktop, Cursor, custom AI orchestrators).
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from engine.graph_rag import graph_rag
from engine.guardrails import safety_gate


class AlgoriseMCPAdapter:
    """Enterprise-grade Native Model Context Protocol (MCP) server and tool provider."""

    def __init__(self, bot_registry: Optional[Dict[str, Any]] = None):
        self.bot_registry = bot_registry or {}
        self.protocol_version = "2024-11-05"
        self.server_info = {
            "name": "algorise-ai-mcp",
            "version": "1.0.0",
        }

    def list_tools(self) -> List[Dict[str, Any]]:
        """Returns standard MCP tool declarations for all Algorise capabilities and registered bots."""
        tools: List[Dict[str, Any]] = [
            {
                "name": "algorise_graphrag_query",
                "description": "Query the Algorise Hybrid GraphRAG context layer to retrieve multi-hop verified product, inventory, and commerce knowledge.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Customer inquiry or entity search prompt (e.g. 'plus size silk suit under 3000')"},
                        "top_k": {"type": "integer", "description": "Number of grounded entities to retrieve", "default": 5},
                    },
                    "required": ["query"],
                },
            },
            {
                "name": "algorise_causal_safety_audit",
                "description": "Pre-flight audit a proposed action or response against deterministic Algorise Causal Safety Gates (SQL injection, shell execution, PII leakage, financial caps).",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "action_type": {"type": "string", "description": "Category of action (e.g. 'order_discount', 'meta_reply', 'database_query')"},
                        "proposed_payload": {"type": "object", "description": "The exact action or message payload to be validated"},
                    },
                    "required": ["action_type", "proposed_payload"],
                },
            },
            {
                "name": "algorise_catalog_search",
                "description": "Search verified high-converting 4K ethnic and festive catalog inventory by size (S to 6XL), fabric, price, and occasion.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "keyword": {"type": "string", "description": "Search term (e.g. 'bandhani', 'tejal', 'curvy plus')"},
                        "max_price": {"type": "number", "description": "Maximum budget in INR (₹)"},
                        "size": {"type": "string", "description": "Specific size requirement (e.g. '3XL', 'M')"},
                    },
                },
            },
            {
                "name": "algorise_classify_lead",
                "description": "Classify a prospective buyer comment or message for commercial buying intent and hotness score (0-99).",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "comment_text": {"type": "string", "description": "Inbound buyer comment or message text"},
                    },
                    "required": ["comment_text"],
                },
            },
            {
                "name": "algorise_attribution_funnel",
                "description": "Retrieve real-time closed-loop attribution metrics (comment -> reply -> WhatsApp DM -> order).",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "client_id": {"type": "string", "description": "Client ID (defaults to active client)", "default": "client_srt_shruhi"},
                    },
                },
            },
        ]

        # Register all bot algorithms from registry
        for bot_id, bot in self.bot_registry.items():
            if isinstance(bot, tuple):
                desc = bot[3] if len(bot) > 3 else f"Algorise algorithmic solver for {bot_id}"
            else:
                desc = getattr(bot, "description", f"Algorise algorithmic solver for {bot_id}")
            tools.append({
                "name": f"algorise_bot_{bot_id}",
                "description": desc,
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Instruction or input problem vector"},
                        "parameters": {"type": "object", "description": "Domain-specific input parameters"},
                    },
                    "required": ["query"],
                },
            })

        return tools

    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Executes a tool call according to the Model Context Protocol specification with Causal Safety gating."""
        started = time.perf_counter()

        # Deterministic Safety Gate Pre-Flight Audit
        safety_res = safety_gate.audit_detailed(
            bot_name=tool_name,
            proposed_action=arguments,
        )
        if not safety_res.is_approved:
            elapsed_ms = (time.perf_counter() - started) * 1000
            return {
                "isError": True,
                "content": [
                    {
                        "type": "text",
                        "text": f"Blocked by Algorise Causal Safety Gate: {safety_res.status_code}. Flags: {', '.join(safety_res.audit_flags)}",
                    }
                ],
                "meta": {
                    "latency_ms": elapsed_ms,
                    "safety_gate": "BLOCKED",
                    "risk_score": safety_res.risk_score,
                },
            }

        # 1. Specialized Algorise Core Tools
        if tool_name == "algorise_graphrag_query":
            q = arguments.get("query", "")
            top_k = int(arguments.get("top_k", 5))
            result = graph_rag.query_context_sync(q, top_k=top_k)
            elapsed_ms = (time.perf_counter() - started) * 1000
            return {
                "isError": False,
                "content": [
                    {"type": "text", "text": result["grounded_context"]},
                    {"type": "json", "data": result},
                ],
                "meta": {"latency_ms": elapsed_ms, "confidence": result["confidence_score"]},
            }

        if tool_name == "algorise_causal_safety_audit":
            act_type = arguments.get("action_type", "general")
            payload = arguments.get("proposed_payload", {})
            audit = safety_gate.audit_detailed(act_type, payload)
            elapsed_ms = (time.perf_counter() - started) * 1000
            return {
                "isError": not audit.is_approved,
                "content": [
                    {"type": "text", "text": f"Status: {audit.status_code} | Risk Score: {audit.risk_score}"},
                    {"type": "json", "data": {"flags": audit.audit_flags, "approved": audit.is_approved}},
                ],
                "meta": {"latency_ms": elapsed_ms, "status": audit.status_code},
            }

        if tool_name == "algorise_catalog_search":
            from engine.facebook_agent import SHRUHI_CATALOG
            kw = (arguments.get("keyword") or "").lower()
            max_p = arguments.get("max_price")
            sz = (arguments.get("size") or "").lower()

            matches = []
            for item in SHRUHI_CATALOG:
                text_blob = f"{item['name']} {item['price']} {item['sizes']} {' '.join(item.get('keys', []))}".lower()
                if kw and kw not in text_blob:
                    continue
                if sz and sz not in item["sizes"].lower():
                    continue
                matches.append(item)

            elapsed_ms = (time.perf_counter() - started) * 1000
            return {
                "isError": False,
                "content": [
                    {"type": "text", "text": f"Found {len(matches)} catalog items matching criteria."},
                    {"type": "json", "data": matches},
                ],
                "meta": {"latency_ms": elapsed_ms, "count": len(matches)},
            }

        if tool_name == "algorise_classify_lead":
            from engine.facebook_agent import FacebookAgentEngine
            agent = FacebookAgentEngine()
            c_text = arguments.get("comment_text", "")
            score, status, intent = agent.classify_lead_intent(c_text)
            elapsed_ms = (time.perf_counter() - started) * 1000
            return {
                "isError": False,
                "content": [
                    {"type": "text", "text": f"Lead Status: {status.upper()} (Score: {score}/99). Intent: {intent}"},
                ],
                "meta": {"latency_ms": elapsed_ms, "score": score, "status": status},
            }

        if tool_name == "algorise_attribution_funnel":
            from engine.attribution import build_funnel
            from engine.database import sync_session
            cid = arguments.get("client_id", "client_srt_shruhi")
            session = sync_session()
            try:
                funnel = build_funnel(session, client_id=cid)
            finally:
                session.close()
            elapsed_ms = (time.perf_counter() - started) * 1000
            return {
                "isError": False,
                "content": [
                    {"type": "json", "data": funnel},
                ],
                "meta": {"latency_ms": elapsed_ms},
            }

        # 2. Hero Bot execution
        clean_name = tool_name.replace("algorise_bot_", "").replace("algorise_", "")
        from engine.hero_registry import HERO_BOT_IDS_SET, HeroBotRunner
        if clean_name in HERO_BOT_IDS_SET:
            runner = HeroBotRunner()
            result = runner.execute_hero_bot(clean_name, arguments)
            elapsed_ms = (time.perf_counter() - started) * 1000
            return {
                "isError": not result.success,
                "content": [
                    {"type": "text", "text": str(result.data)},
                    {"type": "json", "data": {"reasoning_trace": result.reasoning_trace, "data": result.data}},
                ],
                "meta": {
                    "latency_ms": result.latency_ms or elapsed_ms,
                    "bot": result.bot_name,
                    "success": result.success,
                },
            }

        elapsed_ms = (time.perf_counter() - started) * 1000
        return {
            "isError": True,
            "content": [{"type": "text", "text": f"Tool or Bot '{tool_name}' not found."}],
            "meta": {"latency_ms": elapsed_ms},
        }

    def handle_jsonrpc(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handles standard JSON-RPC 2.0 messages from MCP clients."""
        req_id = request.get("id")
        method = request.get("method")
        params = request.get("params", {})

        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": self.protocol_version,
                    "serverInfo": self.server_info,
                    "capabilities": {
                        "tools": {"listChanged": False},
                    },
                },
            }

        if method == "ping":
            return {"jsonrpc": "2.0", "id": req_id, "result": {}}

        if method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"tools": self.list_tools()},
            }

        if method == "tools/call":
            tool_name = params.get("name", "")
            args = params.get("arguments", {})
            result = self.call_tool(tool_name, args)
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": result,
            }

        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32601, "message": f"Method '{method}' not found"},
        }
