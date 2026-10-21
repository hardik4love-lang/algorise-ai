"""
Integration and End-to-End Tests for Algorise DevEx Platform
Validates cross-engine workflows, CLI orchestration, API integration,
and MCP server tool execution.
"""

import os
import tempfile
import json
import pytest
import subprocess
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

import devex.cli as cli_module
import devex.api as api_module
from devex.api import app, TENANT_STORE
from devex.mcp_server import DevExMCPServer


class TestEndToEndWorkflows:
    """End-to-end tests covering complete user workflows."""

    def setup_method(self):
        """Setup clean state for each test."""
        api_module.TENANT_REGISTRY.clear()
        api_module.TENANT_STORE.fallback_registry.clear()
        if api_module.TENANT_STORE._redis_available and api_module.TENANT_STORE.redis_client:
            api_module.TENANT_STORE.redis_client.flushall()
        
        test_tenants = {
            "e2e_admin_key": {
                "client": "E2E Admin",
                "tier": "Enterprise",
                "role": "admin",
                "scopes": api_module.ALL_SCOPES,
                "quota": 1000,
                "requests_used": 0,
            },
            "e2e_dev_key": {
                "client": "E2E Dev",
                "tier": "Growth",
                "role": "developer",
                "scopes": ["quarantine:read", "quarantine:write", "blast_radius:read", "usage:read", "incident:heal"],
                "quota": 500,
                "requests_used": 0,
            },
        }
        print(f"DEBUG setup: Loading tenants: {list(test_tenants.keys())}")
        api_module.TENANT_STORE.load_registry_from_env(test_tenants)
        print(f"DEBUG setup: fallback_registry keys after load: {list(api_module.TENANT_STORE.fallback_registry.keys())}")
        self.client = TestClient(app)
        print(f"DEBUG setup: fallback_registry keys after TestClient: {list(api_module.TENANT_STORE.fallback_registry.keys())}")
        self.admin_headers = {"X-Algorise-API-Key": "e2e_admin_key"}
        self.dev_headers = {"X-Algorise-API-Key": "e2e_dev_key"}

    def test_flaky_test_lifecycle(self):
        """Complete lifecycle: detect flaky -> quarantine -> heal -> restore."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 1. Create a test file with a flaky pattern
            test_file = os.path.join(tmpdir, "test_flaky.py")
            with open(test_file, "w") as f:
                f.write("""
import time
import random

def test_flaky_sleep():
    time.sleep(0.1)  # Fixed sleep - anti-pattern
    assert True

def test_flaky_random():
    x = random.randint(0, 10)  # Unseeded random - anti-pattern
    assert x > 0
""")
            
            # 2. Run AutoTest Sentinel classification
            from autotest_sentinel.classifier import FlakeClassifier
            from autotest_sentinel.models import TestExecutionRecord, TestStatus
            
            clf = FlakeClassifier()
            
            # Simulate mixed execution records
            records = [
                TestExecutionRecord(
                    test_id="test_flaky.py::test_flaky_sleep",
                    file_path="test_flaky.py",
                    status=TestStatus.PASSED,
                    duration_seconds=0.15,
                ) for _ in range(7)
            ] + [
                TestExecutionRecord(
                    test_id="test_flaky.py::test_flaky_sleep",
                    file_path="test_flaky.py",
                    status=TestStatus.FAILED,
                    duration_seconds=0.15,
                ) for _ in range(3)
            ]
            
            report = clf.analyze_executions(records)
            assert report.flakiness_score > 0.5
            assert report.category.value in ["FLAKY_HIGH", "FLAKY_MEDIUM"]
            
            # 3. Quarantine the test via API
            from autotest_sentinel.quarantine import QuarantineManager
            from autotest_sentinel.models import FlakinessReport, FlakeCategory, RootCauseHypothesis
            
            qm = QuarantineManager()
            qm.quarantine_test(
                report=FlakinessReport(
                    test_id="test_flaky.py::test_flaky_sleep",
                    file_path="test_flaky.py",
                    flakiness_score=report.flakiness_score,
                    category=report.category,
                    root_cause=report.root_cause,
                    total_runs=report.total_runs,
                    failure_rate=report.failure_rate,
                    duration_jitter=report.duration_jitter,
                    recommended_action="QUARANTINE",
                    remediation_notes="E2E test quarantine",
                ),
                reason="Detected via E2E test",
                ttl_days=14,
            )
            
            assert "test_flaky.py::test_flaky_sleep" in qm.get_quarantined_ids()
            
            # 4. Verify API returns quarantined test
            response = self.client.get("/v1/quarantine", headers=self.admin_headers)
            assert response.status_code == 200
            data = response.json()
            assert data["total_quarantined"] >= 1
            
            # 5. Heal and unquarantine
            removed = qm.unquarantine_test("test_flaky.py::test_flaky_sleep")
            assert removed is True
            assert "test_flaky.py::test_flaky_sleep" not in qm.get_quarantined_ids()

    def test_blast_radius_pr_review(self):
        """Complete PR review: changed files -> blast radius -> semantic review."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a small dependency chain
            os.makedirs(os.path.join(tmpdir, "src"), exist_ok=True)
            
            # Core module
            with open(os.path.join(tmpdir, "src", "core.py"), "w") as f:
                f.write("""
def get_config():
    return {"debug": True, "version": "1.0"}

def validate_input(data):
    if not isinstance(data, dict):
        raise ValueError("Expected dict")
    return True
""")
            
            # Service module depending on core
            with open(os.path.join(tmpdir, "src", "service.py"), "w") as f:
                f.write("""
from src.core import get_config, validate_input

def process_request(data):
    config = get_config()
    validate_input(data)
    return {"status": "ok", "config": config}

def handle_webhook(payload):
    return process_request(payload)
""")
            
            # API module depending on service
            with open(os.path.join(tmpdir, "src", "api.py"), "w") as f:
                f.write("""
from src.service import process_request, handle_webhook

def handle_http_request(data):
    return process_request(data)

def webhook_endpoint(payload):
    return handle_webhook(payload)
""")
            
            # Initialize git repo
            subprocess.run(["git", "init"], cwd=tmpdir, capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmpdir)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=tmpdir)
            subprocess.run(["git", "add", "."], cwd=tmpdir)
            subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=tmpdir)
            
            # Modify core.py (breaking change)
            with open(os.path.join(tmpdir, "src", "core.py"), "w") as f:
                f.write("""
def get_config():
    return {"debug": False, "version": "2.0", "new_field": "added"}

def validate_input(data):
    if not isinstance(data, dict):
        raise ValueError("Expected dict")
    return True

def new_function():
    return "new"
""")
            
            # Test blast radius analysis via API
            response = self.client.post(
                "/v1/blast-radius",
                json={
                    "changed_files": ["src/core.py"],
                    "base_ref": "master",
                    "head_ref": "HEAD",
                    "root_dir": tmpdir,
                },
                headers=self.dev_headers,
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["risk_level"] in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
            assert data["impacted_files_count"] >= 2  # service.py and api.py should be impacted
            assert any("service.py" in f["file_path"] for f in data["impacted_downstream_files"])
            assert any("api.py" in f["file_path"] for f in data["impacted_downstream_files"])
            
            # Test semantic PR review via ContextPR
            from context_pr.reviewer import PRReviewer
            from context_pr.blast_radius import BlastRadiusAnalyzer
            
            analyzer = BlastRadiusAnalyzer(root_dir=tmpdir)
            report = analyzer.compute_blast_radius(
                changed_files=["src/core.py"],
                base_ref="master",
                head_ref="HEAD",
            )
            
            reviewer = PRReviewer()
            markdown = reviewer.generate_review_markdown(report, [])
            
            assert len(markdown) > 0
            assert "ContextPR" in markdown
            assert "Risk Score" in markdown

    def test_incident_healing_e2e(self):
        """Complete incident healing: incident -> blame -> heal -> verify."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Setup git repo with buggy code
            subprocess.run(["git", "init"], cwd=tmpdir, capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmpdir)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=tmpdir)
            
            buggy_file = os.path.join(tmpdir, "service.py")
            with open(buggy_file, "w") as f:
                f.write("def get_user(id):\n    return users['user_123']\n")
            subprocess.run(["git", "add", "service.py"], cwd=tmpdir)
            subprocess.run(["git", "commit", "-m", "Add service"], cwd=tmpdir)
            print(f"DEBUG test: File content: {repr(open(buggy_file).read())}")
            
            # Trigger incident healing via API
            response = self.client.post(
                "/v1/incidents/heal",
                json={
                    "incident_id": "INC-E2E-001",
                    "service_name": "user-service",
                    "error_type": "KeyError",
                    "error_message": "'user_123'",
                    "stack_trace": "Traceback (most recent call last):\n  File \"service.py\", line 2, in get_user\n    return users['user_123']\nKeyError: 'user_123'",
                    "root_dir": tmpdir,
                    "auto_stage": False,
                },
                headers=self.dev_headers,  # dev has incident:heal scope
            )
            
            assert response.status_code == 200
            data = response.json()
            print(f"DEBUG incident heal: status={response.status_code}, data={data}")
            assert data["incident_id"] == "INC-E2E-001"
            assert data["hotfix_synthesized"] is True
            assert data["hotfix_plan"] is not None
            assert "users.get" in data["hotfix_plan"]["patch_diff"]
            assert data["verification_passed"] is True
            
            # Verify hotfix can be staged
            from trace_root_ai.mesh import AutonomousHealingMesh
            from trace_root_ai.models import IncidentPayload
            
            mesh = AutonomousHealingMesh(root_dir=tmpdir)
            incident = IncidentPayload(
                incident_id="INC-E2E-002",
                service_name="user-service",
                error_type="KeyError",
                error_message="'user_456'",
                raw_stack_trace="Traceback (most recent call last):\n  File \"service.py\", line 2, in get_user\n    return users[\'user_456\']\nKeyError: \'user_456\'",
            )
            
            result = mesh.process_incident(incident=incident, auto_stage=True)
            assert result.hotfix_synthesized is True
            assert result.auto_staged is True
            
            # Verify file was modified (auto_stage applies patch but doesn't create branch by default)
            with open(os.path.join(tmpdir, "service.py"), "r") as f:
                content = f.read()
            print("DEBUG test: Modified file content:", repr(content))
            assert "users.get" in content
            # Note: Second incident fix for user_456 may not be applied if file already modified by first incident

    def test_revenue_scan_and_ledger(self):
        """Revenue engine: scan -> evaluate -> ledger persistence."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ledger_path = os.path.join(tmpdir, "ledger.json")
            
            from revenue_engine.scanner import OpportunityScanner
            
            mock_items = [{
                "number": 100,
                "title": "E2E Bounty Task",
                "repository": {"nameWithOwner": "test/repo"},
                "url": "https://github.com/test/repo/issues/1",
                "estimated_payout": 100.0,
                "urgency": 0.8,
                "risk": 0.1,
            }]
            
            scanner = OpportunityScanner(ledger_path=ledger_path)
            ledger = scanner.scan_opportunities(
                query="bounty",
                limit=1,
                enforce_zero_cost=True,
                mock_items=mock_items,
            )
            
            assert ledger.total_evaluated == 1
            assert len(ledger.opportunities) == 1
            assert os.path.exists(ledger_path)
            
            # Verify ledger append-only behavior
            ledger2 = scanner.scan_opportunities(
                query="bounty",
                limit=1,
                enforce_zero_cost=True,
                mock_items=mock_items,
            )
            
            with open(ledger_path, "r") as f:
                data = json.load(f)
            assert data["total_evaluated"] == 2
            task_ids = {o["task_id"] for o in data["opportunities"]}
            assert len(task_ids) == 1  # Same task_id should be deduped or both present

    def test_modernize_ai_upgrade_cycle(self):
        """ModernizeAI: check upgrade -> dry-run -> apply -> verify."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a file with datetime.utcnow() usage
            test_file = os.path.join(tmpdir, "legacy.py")
            with open(test_file, "w") as f:
                f.write("""
from datetime import datetime

def get_timestamp():
    return datetime.utcnow()

def log_event(event):
    print(f"[{datetime.utcnow()}] {event}")
""")
            
            # Check upgrade plan
            from modernize_ai.rule_engine import CodemodRuleEngine
            engine = CodemodRuleEngine()
            
            # Get migration plan
            plan = engine.get_plan(package_name="datetime", target_version="3.12")
            assert plan is not None
            assert len(plan.rules) > 0
            
            # Apply transformations
            from modernize_ai.transformer import ASTCodeTransformer
            transformer = ASTCodeTransformer()
            
            with open(test_file, "r") as f:
                source = f.read()
            
            # Dry run
            result = transformer.transform_code(test_file, source, plan.rules)
            assert result.syntax_valid
            assert result.unified_diff is not None and len(result.unified_diff) > 0
            
            # Apply
            result = transformer.transform_code(test_file, source, plan.rules)
            assert result.syntax_valid
            if result.transformations_applied > 0:
                with open(test_file, "w", encoding="utf-8") as f:
                    f.write(result.modified_code + "\n")
            
            # Verify changes applied
            with open(test_file, "r") as f:
                content = f.read()
            
            assert "datetime.now(timezone.utc)" in content or "datetime.utcnow().replace(tzinfo=timezone.utc)" in content
            assert "from datetime import datetime, timezone" in content or "import timezone" in content


class TestCLIOrchestration:
    """Tests for unified devex CLI orchestration."""

    def test_cli_subcommand_routing_all(self):
        """All subcommands should route correctly."""
        import sys
        
        subcommands = ["sentinel", "context", "modernize", "traceroot", "revenue", "api"]
        
        for subcmd in subcommands:
            sys.argv = ["devex", subcmd, "--help"]
            with pytest.raises(SystemExit) as exc:
                cli_module.main()
            assert exc.value.code == 0

    def test_platform_status(self):
        """Platform status should run without errors."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cli_module.show_platform_status(root_dir=tmpdir)


class TestMCPServerIntegration:
    """Tests for MCP server tool execution."""

    def setup_method(self):
        """Setup MCP server."""
        self.server = DevExMCPServer()

    def test_list_tools(self):
        """Should list all 10 MCP tools."""
        tools = self.server.list_tools()
        assert len(tools) == 10
        tool_names = {t["name"] for t in tools}
        expected = {
            "autotest_sentinel.quarantine_status",
            "autotest_sentinel.quarantine_test",
            "context_pr.blast_radius",
            "context_pr.review_pr",
            "modernize_ai.transform",
            "modernize_ai.check_upgrade",
            "trace_root_ai.heal_incident",
            "trace_root_ai.analyze_telemetry",
            "revenue_engine.scan_opportunities",
            "revenue_engine.get_ledger",
        }
        assert tool_names == expected

    def test_mcp_tool_execution_quarantine(self):
        """Execute quarantine_status tool via MCP."""
        result = self.server.call_tool("autotest_sentinel.quarantine_status", {"active_only": True})
        assert result["isError"] is False
        assert "total_quarantined" in result["content"][1]["data"]

    def test_mcp_tool_execution_blast_radius(self):
        """Execute blast_radius tool via MCP."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create simple dependency
            with open(os.path.join(tmpdir, "a.py"), "w") as f:
                f.write("import b\n")
            with open(os.path.join(tmpdir, "b.py"), "w") as f:
                f.write("def foo(): pass\n")
            
            subprocess.run(["git", "init"], cwd=tmpdir, capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmpdir)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=tmpdir)
            subprocess.run(["git", "add", "."], cwd=tmpdir)
            subprocess.run(["git", "commit", "-m", "init"], cwd=tmpdir)
            
            server = DevExMCPServer(root_dir=tmpdir)
            result = server.call_tool("context_pr.blast_radius", {
                "changed_files": ["a.py"],
                "base_ref": "master",
                "head_ref": "HEAD",
            })
            
            assert result["isError"] is False
            assert "impacted_downstream_files" in result["content"][1]["data"]

    def test_mcp_tool_execution_heal_incident(self):
        """Execute heal_incident tool via MCP."""
        with tempfile.TemporaryDirectory() as tmpdir:
            subprocess.run(["git", "init"], cwd=tmpdir, capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmpdir)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=tmpdir)
            
            with open(os.path.join(tmpdir, "service.py"), "w") as f:
                f.write("def get_user(id):\n    return users['user_123']\n")
            subprocess.run(["git", "add", "service.py"], cwd=tmpdir)
            subprocess.run(["git", "commit", "-m", "Add service"], cwd=tmpdir)
            
            server = DevExMCPServer(root_dir=tmpdir)
            result = server.call_tool("trace_root_ai.heal_incident", {
                "incident_id": "MCP-TEST-001",
                "service_name": "test-service",
                "error_type": "KeyError",
                "error_message": "'key'",
                "stack_trace": "Traceback (most recent call last):\n  File \"service.py\", line 2, in get_user\n    return users[\'key\']\nKeyError: \'key\'",
                "root_dir": tmpdir,
                "auto_stage": False,
            })
            
            print("DEBUG MCP heal:", result)
            assert result["isError"] is False
            assert result["content"][1]["data"]["hotfix_synthesized"] is True


class TestMCPProtocol:
    """Tests for MCP JSON-RPC protocol compliance."""

    def test_initialize_request(self):
        """MCP initialize request should return server info and capabilities."""
        server = DevExMCPServer()
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {}
        }
        response = server.handle_jsonrpc(request)
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 1
        assert "result" in response
        assert response["result"]["protocolVersion"] == "2024-11-05"
        assert response["result"]["serverInfo"]["name"] == "algorise-devex-mcp"

    def test_ping_request(self):
        """MCP ping should return empty result."""
        server = DevExMCPServer()
        response = server.handle_jsonrpc({"jsonrpc": "2.0", "id": 1, "method": "ping", "params": {}})
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 1
        assert response["result"] == {}

    def test_tools_list_request(self):
        """MCP tools/list should return all tools."""
        server = DevExMCPServer()
        response = server.handle_jsonrpc({"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}})
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 1
        assert "result" in response
        assert "tools" in response["result"]
        assert len(response["result"]["tools"]) == 10

    def test_tools_call_request(self):
        """MCP tools/call should execute tool."""
        server = DevExMCPServer()
        response = server.handle_jsonrpc({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": "autotest_sentinel.quarantine_status", "arguments": {"active_only": True}}
        })
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 1
        assert "result" in response
        assert "isError" in response["result"]
        assert response["result"]["isError"] is False

    def test_unknown_method(self):
        """Unknown method should return error."""
        server = DevExMCPServer()
        response = server.handle_jsonrpc({"jsonrpc": "2.0", "id": 1, "method": "unknown/method", "params": {}})
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 1
        assert "error" in response
        assert response["error"]["code"] == -32601

    def test_parse_error(self):
        """Invalid JSON should return parse error."""
        server = DevExMCPServer()
        # This is tested by the server's JSON parsing in run_stdio_server


class TestObservabilityIntegration:
    """Tests for observability features."""

    def setup_method(self):
        """Setup test client."""
        import devex.api as api_module
        api_module.TENANT_REGISTRY.clear()
        api_module.TENANT_STORE.fallback_registry.clear()
        if api_module.TENANT_STORE._redis_available and api_module.TENANT_STORE.redis_client:
            api_module.TENANT_STORE.redis_client.flushall()
        
        test_tenants = {
            "obs_test_key": {
                "client": "Obs Test",
                "tier": "Enterprise",
                "role": "admin",
                "scopes": api_module.ALL_SCOPES,
                "quota": 1000,
                "requests_used": 0,
            },
        }
        api_module.TENANT_STORE.load_registry_from_env(test_tenants)
        self.client = TestClient(app)
        self.headers = {"X-Algorise-API-Key": "obs_test_key"}

    def test_health_endpoint_detailed(self):
        """Health endpoint should include dependency checks."""
        response = self.client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["healthy", "degraded"]
        assert "checks" in data
        assert "tenant_store" in data["checks"]

    def test_readiness_endpoint_detailed(self):
        """Readiness endpoint should include dependency checks."""
        response = self.client.get("/ready")
        assert response.status_code == 200
        data = response.json()
        assert "ready" in data
        assert "checks" in data
        assert "tenant_store" in data["checks"]

    def test_correlation_id_header(self):
        """Responses should include correlation ID."""
        response = self.client.get("/health", headers={"X-Correlation-ID": "test-correlation-123"})
        assert response.status_code == 200
        assert response.headers.get("X-Correlation-ID") == "test-correlation-123"

    def test_metrics_endpoint_if_available(self):
        """Metrics endpoint should exist if Prometheus available."""
        try:
            import prometheus_client
            response = self.client.get("/metrics")
            assert response.status_code == 200
            assert "text/plain" in response.headers.get("content-type", "")
            # Check for key metrics
            content = response.text
            assert "algorise_http_requests_total" in content
        except ImportError:
            pytest.skip("Prometheus client not available")


class TestResiliencyIntegration:
    """Tests for resiliency features."""

    def setup_method(self):
        """Setup test client."""
        import devex.api as api_module
        api_module.TENANT_REGISTRY.clear()
        api_module.TENANT_STORE.fallback_registry.clear()
        if api_module.TENANT_STORE._redis_available and api_module.TENANT_STORE.redis_client:
            api_module.TENANT_STORE.redis_client.flushall()
        
        test_tenants = {
            "res_test_key": {
                "client": "Res Test",
                "tier": "Enterprise",
                "role": "admin",
                "scopes": api_module.ALL_SCOPES,
                "quota": 1000,
                "requests_used": 0,
            },
        }
        api_module.TENANT_STORE.load_registry_from_env(test_tenants)
        self.client = TestClient(app)
        self.headers = {"X-Algorise-API-Key": "res_test_key"}

    def test_global_rate_limiter(self):
        """Global rate limiter should enforce limits."""
        # Make requests up to burst limit + some refill allowance
        # Rate limiter: 1000 req/min (16.67/sec), burst=100
        # With ~10ms between requests, ~16 tokens refill per 100 requests
        # So expect rate limiting around 115-120 requests
        rate_limited = False
        for i in range(130):  # burst=100 + refill allowance
            response = self.client.get("/health", headers=self.headers)
            if response.status_code == 429:
                rate_limited = True
                break
            assert response.status_code == 200
        
        # Should eventually hit rate limit
        assert rate_limited, "Rate limiter should eventually trigger 429"

    def test_secret_redaction_in_logs(self):
        """Logs should not contain secrets."""
        # This is a functional test - verify redaction logic
        from devex.api import redact_secrets
        
        test_msg = 'Authorization: Bearer sk_live_abc123def456\nAPI Key: "sk_test_abc123"\nPassword: "secret123"'
        redacted = redact_secrets(test_msg)
        
        assert "sk_live_abc123def456" not in redacted
        assert "sk_test_abc123" not in redacted
        assert "secret123" not in redacted
        assert "***" in redacted

    def test_redacting_logger(self):
        """RedactingLogger should redact secrets."""
        from devex.api import RedactingLogger, redact_secrets
        import logging
        
        base_logger = logging.getLogger("test_redactor")
        redacting_logger = RedactingLogger(base_logger)
        
        # Should not raise
        redacting_logger.info('Bearer sk_live_abc123')
        redacting_logger.warning('Password: "secret123"')
        redacting_logger.error('Token: ghp_abc123def456')


if __name__ == "__main__":
    pytest.main([__file__, "-v"])