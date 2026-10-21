"""
Algorise DevEx Platform: Model Context Protocol (MCP) Server
Exposes the 5 autonomous DevEx engines as MCP tools for AI agent integration.

Tools exposed:
- autotest_sentinel.quarantine_status: Get flaky test quarantine registry
- autotest_sentinel.quarantine_test: Quarantine a flaky test
- context_pr.blast_radius: Compute AST blast radius for changed files
- context_pr.review_pr: Generate semantic PR review with invariant checks
- modernize_ai.transform: Apply AST codemods for dependency upgrades
- modernize_ai.check_upgrade: Check available upgrade paths
- trace_root_ai.heal_incident: Synthesize defensive hotfix for production incidents
- trace_root_ai.analyze_telemetry: Ingest and analyze incident telemetry
- revenue_engine.scan_opportunities: Scan and evaluate bounty opportunities
- revenue_engine.get_ledger: Retrieve audit ledger of evaluated opportunities
"""

from __future__ import annotations

import json
import time
import os
from typing import Any, Dict, List, Optional

from autotest_sentinel.quarantine import QuarantineManager
from autotest_sentinel.classifier import FlakeClassifier
from autotest_sentinel.models import FlakinessReport, FlakeCategory, RootCauseHypothesis
from context_pr.blast_radius import BlastRadiusAnalyzer
from context_pr.invariants import InvariantExtractor
from context_pr.reviewer import PRReviewer
from modernize_ai.rule_engine import CodemodRuleEngine
from modernize_ai.transformer import ASTCodeTransformer
from trace_root_ai.healer import IncidentHealer
from trace_root_ai.ingestor import TelemetryIngestor
from trace_root_ai.mesh import AutonomousHealingMesh
from trace_root_ai.models import IncidentPayload, BlameContext
from revenue_engine.scanner import OpportunityScanner
from revenue_engine.reporter import RevenueReporter
from revenue_engine.models import BountyOpportunity as Opportunity


class DevExMCPServer:
    """MCP Server exposing Algorise DevEx Platform engines as tools."""

    PROTOCOL_VERSION = "2024-11-05"
    SERVER_INFO = {
        "name": "algorise-devex-mcp",
        "version": "1.0.0",
        "description": "Algorise DevEx Platform - 5 Autonomous Engines via MCP",
    }

    def __init__(self, root_dir: str = ".", tenant_registry: Optional[Dict[str, Any]] = None):
        self.root_dir = os.path.abspath(root_dir)
        self.tenant_registry = tenant_registry or {}

    def list_tools(self) -> List[Dict[str, Any]]:
        """Returns standard MCP tool declarations for all 5 DevEx engines."""
        return [
            # AutoTest Sentinel (2 tools)
            {
                "name": "autotest_sentinel.quarantine_status",
                "description": "Retrieve current flaky test quarantine registry with active/inactive tests, TTLs, and pytest deselection arguments.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "active_only": {"type": "boolean", "default": True, "description": "Show only active (non-expired) quarantines"},
                        "manifest_path": {"type": "string", "description": "Optional custom path to quarantine manifest JSON"},
                    },
                },
            },
            {
                "name": "autotest_sentinel.quarantine_test",
                "description": "Quarantine a flaky test by registering it in the quarantine manifest with flakiness score, root cause, and TTL.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "test_id": {"type": "string", "description": "Pytest node ID (e.g. 'tests/test_api.py::test_flaky')"},
                        "file_path": {"type": "string", "description": "Path to test file"},
                        "flakiness_score": {"type": "number", "minimum": 0.0, "maximum": 1.0, "default": 0.85},
                        "root_cause": {"type": "string", "enum": ["TIMING_RACE", "FIXTURE_LEAK", "EXTERNAL_DEPENDENCY", "NON_DETERMINISTIC_ORDER", "FIXED", "FLAKY_HIGH", "FLAKY_MEDIUM"], "default": "TIMING_RACE"},
                        "failure_rate": {"type": "number", "minimum": 0.0, "maximum": 1.0, "default": 0.3},
                        "reason": {"type": "string", "description": "Human-readable reason for quarantine"},
                        "ttl_days": {"type": "integer", "minimum": 1, "maximum": 90, "default": 14},
                    },
                    "required": ["test_id", "file_path"],
                },
            },

            # ContextPR (2 tools)
            {
                "name": "context_pr.blast_radius",
                "description": "Compute transitive downstream blast radius and risk tier for changed files using incremental AST dependency graph with caching.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "changed_files": {"type": "array", "items": {"type": "string"}, "description": "List of modified file paths"},
                        "base_ref": {"type": "string", "default": "master", "description": "Base branch reference"},
                        "head_ref": {"type": "string", "default": "HEAD", "description": "Head branch reference"},
                        "root_dir": {"type": "string", "description": "Repository root directory (defaults to current)"},
                    },
                    "required": ["changed_files"],
                },
            },
            {
                "name": "context_pr.review_pr",
                "description": "Generate semantic PR review with contract invariant checking, breaking change detection, and property test synthesis.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "changed_files": {"type": "array", "items": {"type": "string"}, "description": "List of modified file paths"},
                        "base_ref": {"type": "string", "default": "master"},
                        "head_ref": {"type": "string", "default": "HEAD"},
                        "root_dir": {"type": "string"},
                    },
                    "required": ["changed_files"],
                },
            },

            # ModernizeAI (2 tools)
            {
                "name": "modernize_ai.transform",
                "description": "Apply AST codemods for automated dependency upgrades (Pydantic v1→v2, LangChain, Python 3.12+ deprecations) with verified diffs.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "package": {"type": "string", "enum": ["pydantic", "langchain", "datetime"], "description": "Target package to upgrade"},
                        "target_version": {"type": "string", "description": "Target version (e.g. '2.0', '0.3', '3.12')"},
                        "root_dir": {"type": "string", "description": "Repository root"},
                        "write": {"type": "boolean", "default": False, "description": "Apply changes in-place (default: dry-run)"},
                    },
                    "required": ["package"],
                },
            },
            {
                "name": "modernize_ai.check_upgrade",
                "description": "Check available upgrade paths and preview transformations without applying changes.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "package": {"type": "string", "enum": ["pydantic", "langchain", "datetime"]},
                        "root_dir": {"type": "string"},
                    },
                    "required": ["package"],
                },
            },

            # TraceRoot AI (2 tools)
            {
                "name": "trace_root_ai.heal_incident",
                "description": "Synthesize defensive hotfix for production incidents (KeyError, ZeroDivisionError, AttributeError, IndexError) with AST validation and optional git branch staging.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "incident_id": {"type": "string", "description": "Unique incident identifier"},
                        "service_name": {"type": "string", "default": "unknown-service"},
                        "error_type": {"type": "string", "enum": ["KeyError", "ZeroDivisionError", "AttributeError", "IndexError"]},
                        "error_message": {"type": "string"},
                        "stack_trace": {"type": "string", "description": "Raw Python exception traceback"},
                        "root_dir": {"type": "string"},
                        "auto_stage": {"type": "boolean", "default": False, "description": "Create git hotfix branch"},
                    },
                    "required": ["incident_id", "error_type", "error_message", "stack_trace"],
                },
            },
            {
                "name": "trace_root_ai.analyze_telemetry",
                "description": "Ingest and parse incident telemetry (JSON payload or raw stderr traceback) into structured IncidentPayload.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "payload": {"type": "object", "description": "JSON incident payload"},
                        "stderr": {"type": "string", "description": "Raw stderr traceback text"},
                        "service_name": {"type": "string"},
                    },
                },
            },

            # Revenue Engine (2 tools)
            {
                "name": "revenue_engine.scan_opportunities",
                "description": "Scan and evaluate GitHub bounty opportunities through 7-gate deterministic evaluation (confidence, ENR, budget, quotas, risk, tools, idempotency).",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "default": "bounty", "description": "Search query for issues"},
                        "limit": {"type": "integer", "default": 10, "minimum": 1, "maximum": 50},
                        "enforce_zero_cost": {"type": "boolean", "default": True, "description": "Enforce $0 compute budget gate"},
                        "ledger_path": {"type": "string", "description": "Custom audit ledger path"},
                    },
                },
            },
            {
                "name": "revenue_engine.get_ledger",
                "description": "Retrieve audit ledger of evaluated opportunities with gate results, ENR, and status.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "ledger_path": {"type": "string", "description": "Path to audit ledger JSON"},
                    },
                },
            },
        ]

    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a DevEx engine tool call."""
        started = time.perf_counter()

        try:
            # AutoTest Sentinel
            if tool_name == "autotest_sentinel.quarantine_status":
                return self._sentinel_quarantine_status(arguments, started)
            if tool_name == "autotest_sentinel.quarantine_test":
                return self._sentinel_quarantine_test(arguments, started)

            # ContextPR
            if tool_name == "context_pr.blast_radius":
                return self._contextpr_blast_radius(arguments, started)
            if tool_name == "context_pr.review_pr":
                return self._contextpr_review_pr(arguments, started)

            # ModernizeAI
            if tool_name == "modernize_ai.transform":
                return self._modernize_transform(arguments, started)
            if tool_name == "modernize_ai.check_upgrade":
                return self._modernize_check_upgrade(arguments, started)

            # TraceRoot AI
            if tool_name == "trace_root_ai.heal_incident":
                return self._traceroot_heal_incident(arguments, started)
            if tool_name == "trace_root_ai.analyze_telemetry":
                return self._traceroot_analyze_telemetry(arguments, started)

            # Revenue Engine
            if tool_name == "revenue_engine.scan_opportunities":
                return self._revenue_scan_opportunities(arguments, started)
            if tool_name == "revenue_engine.get_ledger":
                return self._revenue_get_ledger(arguments, started)

            elapsed_ms = (time.perf_counter() - started) * 1000
            return {
                "isError": True,
                "content": [{"type": "text", "text": f"Unknown tool: {tool_name}"}],
                "meta": {"latency_ms": elapsed_ms},
            }

        except Exception as e:
            elapsed_ms = (time.perf_counter() - started) * 1000
            return {
                "isError": True,
                "content": [{"type": "text", "text": f"Error executing {tool_name}: {str(e)}"}],
                "meta": {"latency_ms": elapsed_ms, "error": str(e)},
            }

    # AutoTest Sentinel implementations
    def _sentinel_quarantine_status(self, args: Dict[str, Any], started: float) -> Dict[str, Any]:
        active_only = args.get("active_only", True)
        manifest_path = args.get("manifest_path")
        qm = QuarantineManager(manifest_path=manifest_path or os.path.join(self.root_dir, ".autotest", "quarantine.json"))

        if active_only:
            active_ids = qm.get_quarantined_ids()
            records = {k: v for k, v in qm.manifest.quarantined_tests.items() if k in active_ids}
        else:
            records = qm.manifest.quarantined_tests

        elapsed_ms = (time.perf_counter() - started) * 1000
        return {
            "isError": False,
            "content": [
                {"type": "text", "text": f"Quarantine Status: {len(records)} active test(s)"},
                {"type": "json", "data": {
                    "version": qm.manifest.version,
                    "updated_at": qm.manifest.updated_at,
                    "total_quarantined": len(records),
                    "quarantined_tests": records,
                    "pytest_deselect_args": qm.generate_pytest_deselection_args(),
                }},
            ],
            "meta": {"latency_ms": elapsed_ms},
        }

    def _sentinel_quarantine_test(self, args: Dict[str, Any], started: float) -> Dict[str, Any]:
        manifest_path = args.get("manifest_path")
        qm = QuarantineManager(manifest_path=manifest_path or os.path.join(self.root_dir, ".autotest", "quarantine.json"))

        try:
            cause_enum = RootCauseHypothesis(args.get("root_cause", "TIMING_RACE"))
        except ValueError:
            cause_enum = RootCauseHypothesis.TIMING_RACE

        report = FlakinessReport(
            test_id=args["test_id"],
            file_path=args["file_path"],
            flakiness_score=args.get("flakiness_score", 0.85),
            category=FlakeCategory.FLAKY_HIGH if args.get("flakiness_score", 0.85) >= 0.7 else FlakeCategory.FLAKY_MEDIUM,
            root_cause=cause_enum,
            total_runs=10,
            failure_rate=args.get("failure_rate", 0.3),
            duration_jitter=0.05,
            recommended_action="Quarantine test and notify owner",
            remediation_notes=args.get("reason", "Quarantined via MCP tool"),
        )

        is_new = qm.quarantine_test(
            report=report,
            reason=args.get("reason"),
            ttl_days=args.get("ttl_days", 14),
        )

        elapsed_ms = (time.perf_counter() - started) * 1000
        return {
            "isError": False,
            "content": [
                {"type": "text", "text": f"Test {'added' if is_new else 'updated'} in quarantine: {args['test_id']}"},
                {"type": "json", "data": {
                    "success": True,
                    "is_new": is_new,
                    "test_id": args["test_id"],
                    "quarantined_entry": qm.manifest.quarantined_tests.get(args["test_id"]),
                }},
            ],
            "meta": {"latency_ms": elapsed_ms},
        }

    # ContextPR implementations
    def _contextpr_blast_radius(self, args: Dict[str, Any], started: float) -> Dict[str, Any]:
        root_dir = args.get("root_dir") or self.root_dir
        analyzer = BlastRadiusAnalyzer(root_dir=root_dir)
        report = analyzer.compute_blast_radius(
            changed_files=args["changed_files"],
            base_ref=args.get("base_ref", "master"),
            head_ref=args.get("head_ref", "HEAD"),
        )

        impacted = [
            {
                "file_path": node.file_path,
                "direct_dependency": node.direct_dependency,
                "imported_symbols": node.imported_symbols,
                "depth": node.depth,
            }
            for node in report.impacted_downstream_files
        ]

        elapsed_ms = (time.perf_counter() - started) * 1000
        return {
            "isError": False,
            "content": [
                {"type": "text", "text": f"Blast Radius: Risk {report.risk_level.value} ({report.risk_score}/10), {len(impacted)} downstream files impacted"},
                {"type": "json", "data": {
                    "base_ref": report.base_ref,
                    "head_ref": report.head_ref,
                    "risk_level": report.risk_level.value,
                    "risk_score": report.risk_score,
                    "total_files_changed": report.total_files_changed,
                    "impacted_files_count": len(impacted),
                    "impacted_downstream_files": impacted,
                    "breaking_changes_detected": report.breaking_changes_detected,
                    "high_risk_reasons": report.high_risk_reasons,
                    "cache_telemetry": {"hits": analyzer.cache_hits, "misses": analyzer.cache_misses},
                }},
            ],
            "meta": {"latency_ms": elapsed_ms},
        }

    def _contextpr_review_pr(self, args: Dict[str, Any], started: float) -> Dict[str, Any]:
        root_dir = args.get("root_dir") or self.root_dir
        reviewer = PRReviewer(root_dir=root_dir)
        review = reviewer.review_changes(
            changed_files=args["changed_files"],
            base_ref=args.get("base_ref", "master"),
            head_ref=args.get("head_ref", "HEAD"),
        )

        elapsed_ms = (time.perf_counter() - started) * 1000
        return {
            "isError": False,
            "content": [
                {"type": "text", "text": review.markdown_summary},
                {"type": "json", "data": review.model_dump()},
            ],
            "meta": {"latency_ms": elapsed_ms},
        }

    # ModernizeAI implementations
    def _modernize_transform(self, args: Dict[str, Any], started: float) -> Dict[str, Any]:
        engine = CodemodRuleEngine()
        root_dir = args.get("root_dir") or self.root_dir

        if not os.path.exists(root_dir):
            elapsed_ms = (time.perf_counter() - started) * 1000
            return {"isError": True, "content": [{"type": "text", "text": f"Directory not found: {root_dir}"}], "meta": {"latency_ms": elapsed_ms}}

        results = engine.upgrade_package(
            package=args["package"],
            target_version=args.get("target_version", ""),
            root_dir=root_dir,
            write=args.get("write", False),
        )

        elapsed_ms = (time.perf_counter() - started) * 1000
        return {
            "isError": False,
            "content": [
                {"type": "text", "text": f"ModernizeAI {args['package']} upgrade: {len(results)} file(s) transformed"},
                {"type": "json", "data": [r.model_dump() for r in results]},
            ],
            "meta": {"latency_ms": elapsed_ms},
        }

    def _modernize_check_upgrade(self, args: Dict[str, Any], started: float) -> Dict[str, Any]:
        engine = CodemodRuleEngine()
        root_dir = args.get("root_dir") or self.root_dir

        if not os.path.exists(root_dir):
            elapsed_ms = (time.perf_counter() - started) * 1000
            return {"isError": True, "content": [{"type": "text", "text": f"Directory not found: {root_dir}"}], "meta": {"latency_ms": elapsed_ms}}

        supported = engine.list_supported_packages()
        pkg = args["package"]
        if pkg not in supported:
            return {"isError": True, "content": [{"type": "text", "text": f"Unsupported package: {pkg}"}], "meta": {"latency_ms": elapsed_ms}}

        # Dry-run preview
        results = engine.upgrade_package(
            package=pkg,
            target_version=args.get("target_version", ""),
            root_dir=root_dir,
            write=False,
        )

        elapsed_ms = (time.perf_counter() - started) * 1000
        return {
            "isError": False,
            "content": [
                {"type": "text", "text": f"Upgrade preview for {pkg}: {len(results)} file(s) would be transformed"},
                {"type": "json", "data": [r.model_dump() for r in results]},
            ],
            "meta": {"latency_ms": elapsed_ms},
        }

    # TraceRoot AI implementations
    def _traceroot_heal_incident(self, args: Dict[str, Any], started: float) -> Dict[str, Any]:
        root_dir = args.get("root_dir") or self.root_dir
        mesh = AutonomousHealingMesh(root_dir=root_dir)

        incident = IncidentPayload(
            incident_id=args["incident_id"],
            service_name=args.get("service_name", "unknown-service"),
            error_type=args["error_type"],
            error_message=args["error_message"],
            raw_stack_trace=args["stack_trace"],
        )

        result = mesh.process_incident(incident=incident, auto_stage=args.get("auto_stage", False))

        elapsed_ms = (time.perf_counter() - started) * 1000
        return {
            "isError": False,
            "content": [
                {"type": "text", "text": f"Incident {args['incident_id']}: {result.status} - {result.hotfix_plan.get('root_cause_explanation', 'No fix synthesized') if result.hotfix_plan else 'No fix synthesized'}"},
                {"type": "json", "data": result.model_dump()},
            ],
            "meta": {"latency_ms": elapsed_ms},
        }

    def _traceroot_analyze_telemetry(self, args: Dict[str, Any], started: float) -> Dict[str, Any]:
        ingestor = TelemetryIngestor()

        if "payload" in args and args["payload"]:
            incident = ingestor.ingest(args["payload"])
        elif "stderr" in args and args["stderr"]:
            incident = ingestor.ingest_stderr(args["stderr"], service_name=args.get("service_name", "unknown"))
        else:
            return {"isError": True, "content": [{"type": "text", "text": "Either 'payload' or 'stderr' required"}]}

        elapsed_ms = (time.perf_counter() - started) * 1000
        return {
            "isError": False,
            "content": [
                {"type": "text", "text": f"Parsed incident: {incident.incident_id} ({incident.error_type})"},
                {"type": "json", "data": incident.model_dump()},
            ],
            "meta": {"latency_ms": elapsed_ms},
        }

    # Revenue Engine implementations
    def _revenue_scan_opportunities(self, args: Dict[str, Any], started: float) -> Dict[str, Any]:
        ledger_path = args.get("ledger_path") or os.path.join(self.root_dir, "live_ledger", "evaluation_ledger.json")
        scanner = OpportunityScanner(ledger_path=ledger_path)

        ledger = scanner.scan_opportunities(
            query=args.get("query", "bounty"),
            limit=args.get("limit", 10),
            enforce_zero_cost=args.get("enforce_zero_cost", True),
        )

        reporter = RevenueReporter()
        report_md = reporter.generate_markdown_report(ledger)

        elapsed_ms = (time.perf_counter() - started) * 1000
        return {
            "isError": False,
            "content": [
                {"type": "text", "text": f"Revenue scan: {ledger.total_evaluated} opportunities evaluated, {sum(1 for o in ledger.opportunities if o.status == 'approved')} approved"},
                {"type": "text", "text": report_md},
                {"type": "json", "data": ledger.model_dump()},
            ],
            "meta": {"latency_ms": elapsed_ms},
        }

    def _revenue_get_ledger(self, args: Dict[str, Any], started: float) -> Dict[str, Any]:
        ledger_path = args.get("ledger_path") or os.path.join(self.root_dir, "live_ledger", "evaluation_ledger.json")

        if not os.path.exists(ledger_path):
            return {"isError": True, "content": [{"type": "text", "text": f"Ledger not found: {ledger_path}"}]}

        with open(ledger_path, "r") as f:
            data = json.load(f)

        elapsed_ms = (time.perf_counter() - started) * 1000
        return {
            "isError": False,
            "content": [
                {"type": "text", "text": f"Ledger {data['ledger_id']}: {data['total_evaluated']} opportunities"},
                {"type": "json", "data": data},
            ],
            "meta": {"latency_ms": elapsed_ms},
        }

    # MCP JSON-RPC Handler
    def handle_jsonrpc(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle standard JSON-RPC 2.0 messages from MCP clients."""
        req_id = request.get("id")
        method = request.get("method")
        params = request.get("params", {})

        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": self.PROTOCOL_VERSION,
                    "serverInfo": self.SERVER_INFO,
                    "capabilities": {"tools": {"listChanged": False}},
                },
            }

        if method == "ping":
            return {"jsonrpc": "2.0", "id": req_id, "result": {}}

        if method == "tools/list":
            return {"jsonrpc": "2.0", "id": req_id, "result": {"tools": self.list_tools()}}

        if method == "tools/call":
            tool_name = params.get("name", "")
            args = params.get("arguments", {})
            result = self.call_tool(tool_name, args)
            return {"jsonrpc": "2.0", "id": req_id, "result": result}

        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32601, "message": f"Method '{method}' not found"},
        }


# Stdio transport runner
def run_stdio_server(root_dir: str = ".") -> None:
    """Run MCP server over stdio transport (for Claude Desktop, Cursor, etc.)."""
    server = DevExMCPServer(root_dir=root_dir)
    import sys

    print(f"Algorise DevEx MCP Server starting on stdio...", file=sys.stderr)
    print(f"Root dir: {root_dir}", file=sys.stderr)
    print(f"Tools available: {len(server.list_tools())}", file=sys.stderr)

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
            response = server.handle_jsonrpc(request)
            print(json.dumps(response), flush=True)
        except json.JSONDecodeError:
            print(json.dumps({
                "jsonrpc": "2.0", "id": None,
                "error": {"code": -32700, "message": "Parse error"}
            }), flush=True)
        except Exception as e:
            print(json.dumps({
                "jsonrpc": "2.0", "id": request.get("id") if 'request' in locals() else None,
                "error": {"code": -32603, "message": f"Internal error: {str(e)}"}
            }), flush=True)


if __name__ == "__main__":
    import sys
    root = sys.argv[1] if len(sys.argv) > 1 else "."
    run_stdio_server(root)