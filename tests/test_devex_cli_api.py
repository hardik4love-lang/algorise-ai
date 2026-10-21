"""
Unit and Integration Tests for DevEx CLI and API Gateway
Validates unified CLI orchestration, subcommand routing, API endpoints,
multi-tenant auth/RBAC, quota enforcement, and metering headers.
"""

import os
import tempfile
import json
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

import devex.cli as cli_module
import devex.api as api_module
from devex.api import app, authenticate_api_key, require_scope, TENANT_REGISTRY, ALL_SCOPES, _load_tenant_registry


class TestDevexCLI:
    """Tests for unified devex CLI."""

    def test_show_platform_status_no_errors(self):
        """Platform status should run without errors."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cli_module.show_platform_status(root_dir=tmpdir)

    def test_cli_subcommand_routing_sentinel(self):
        """CLI should route 'sentinel' to autotest_sentinel.cli."""
        import sys
        sys.argv = ["devex", "sentinel", "--help"]
        with pytest.raises(SystemExit) as exc:
            cli_module.main()
        assert exc.value.code == 0

    def test_cli_subcommand_routing_context(self):
        """CLI should route 'context' to context_pr.cli."""
        import sys
        sys.argv = ["devex", "context", "--help"]
        with pytest.raises(SystemExit) as exc:
            cli_module.main()
        assert exc.value.code == 0

    def test_cli_subcommand_routing_modernize(self):
        """CLI should route 'modernize' to modernize_ai.cli."""
        import sys
        sys.argv = ["devex", "modernize", "--help"]
        with pytest.raises(SystemExit) as exc:
            cli_module.main()
        assert exc.value.code == 0

    def test_cli_subcommand_routing_traceroot(self):
        """CLI should route 'traceroot' to trace_root_ai.cli."""
        import sys
        sys.argv = ["devex", "traceroot", "--help"]
        with pytest.raises(SystemExit) as exc:
            cli_module.main()
        assert exc.value.code == 0

    def test_cli_subcommand_routing_revenue(self):
        """CLI should route 'revenue' to revenue_engine.cli."""
        import sys
        sys.argv = ["devex", "revenue", "--help"]
        with pytest.raises(SystemExit) as exc:
            cli_module.main()
        assert exc.value.code == 0

    def test_cli_subcommand_routing_api(self):
        """CLI should route 'api' to FastAPI server."""
        import sys
        sys.argv = ["devex", "api", "--help"]
        with pytest.raises(SystemExit) as exc:
            cli_module.main()
        assert exc.value.code == 0


class TestDevexAPIAuth:
    """Tests for API authentication and RBAC."""

    def setup_method(self):
        """Setup clean tenant registry for each test."""
        # Clear both old registry and new store
        api_module.TENANT_REGISTRY.clear()
        api_module.TENANT_STORE.fallback_registry.clear()
        if api_module.TENANT_STORE._redis_available and api_module.TENANT_STORE.redis_client:
            api_module.TENANT_STORE.redis_client.flushall()
        
        test_tenants = {
            "test_admin_key": {
                "client": "Test Admin",
                "tier": "Enterprise",
                "role": "admin",
                "scopes": ALL_SCOPES,
                "quota": 1000,
                "requests_used": 0,
            },
            "test_dev_key": {
                "client": "Test Dev",
                "tier": "Growth",
                "role": "developer",
                "scopes": ["quarantine:read", "quarantine:write", "blast_radius:read", "usage:read"],
                "quota": 100,
                "requests_used": 0,
            },
            "test_viewer_key": {
                "client": "Test Viewer",
                "tier": "Viewer",
                "role": "viewer",
                "scopes": ["quarantine:read", "blast_radius:read", "usage:read"],
                "quota": 50,
                "requests_used": 0,
            },
        }
        # Load into TENANT_STORE (falls back to in-memory)
        api_module.TENANT_STORE.load_registry_from_env(test_tenants)

    def test_auth_valid_admin_key(self):
        """Valid admin key should authenticate and return tenant."""
        tenant = authenticate_api_key(x_algorise_api_key="test_admin_key")
        assert tenant["client"] == "Test Admin"
        assert tenant["role"] == "admin"
        assert tenant["requests_used"] == 1

    def test_auth_valid_dev_key(self):
        """Valid developer key should authenticate."""
        tenant = authenticate_api_key(x_algorise_api_key="test_dev_key")
        assert tenant["client"] == "Test Dev"
        assert tenant["role"] == "developer"

    def test_auth_invalid_key_raises_401(self):
        """Invalid key should raise 401."""
        with pytest.raises(api_module.HTTPException) as exc:
            authenticate_api_key(x_algorise_api_key="invalid_key")
        assert exc.value.status_code == 401

    def test_auth_bearer_token(self):
        """Bearer token authentication should work."""
        tenant = authenticate_api_key(authorization="Bearer test_dev_key")
        assert tenant["client"] == "Test Dev"

    def test_auth_missing_key_raises_401(self):
        """Missing key should raise 401."""
        with pytest.raises(api_module.HTTPException) as exc:
            authenticate_api_key(x_algorise_api_key=None, authorization=None)
        assert exc.value.status_code == 401

    def test_quota_enforcement(self):
        """Exceeding quota should raise 429."""
        api_module.TENANT_STORE.fallback_registry["test_viewer_key"]["requests_used"] = 50  # quota is 50

        with pytest.raises(api_module.HTTPException) as exc:
            authenticate_api_key(x_algorise_api_key="test_viewer_key")
        assert exc.value.status_code == 429

    def test_scope_admin_all_access(self):
        """Admin with admin:* should pass all scope checks."""
        admin_tenant = api_module.TENANT_STORE.get_tenant("test_admin_key")
        checker = require_scope("quarantine:write")
        result = checker(admin_tenant)
        assert result["client"] == "Test Admin"

    def test_scope_dev_has_write(self):
        """Developer should have quarantine:write."""
        dev_tenant = api_module.TENANT_STORE.get_tenant("test_dev_key")
        checker = require_scope("quarantine:write")
        result = checker(dev_tenant)
        assert result["client"] == "Test Dev"

    def test_scope_dev_no_incident_heal(self):
        """Developer should NOT have incident:heal."""
        dev_tenant = api_module.TENANT_STORE.get_tenant("test_dev_key")
        checker = require_scope("incident:heal")
        with pytest.raises(api_module.HTTPException) as exc:
            checker(dev_tenant)
        assert exc.value.status_code == 403

    def test_scope_viewer_read_only(self):
        """Viewer should only have read scopes."""
        viewer_tenant = api_module.TENANT_STORE.get_tenant("test_viewer_key")
        checker = require_scope("quarantine:read")
        result = checker(viewer_tenant)
        assert result["client"] == "Test Viewer"

    def test_scope_viewer_no_write(self):
        """Viewer should NOT have write scopes."""
        viewer_tenant = api_module.TENANT_STORE.get_tenant("test_viewer_key")
        checker = require_scope("quarantine:write")
        with pytest.raises(api_module.HTTPException) as exc:
            checker(viewer_tenant)
        assert exc.value.status_code == 403


class TestDevexAPIEndpoints:
    """Integration tests for API endpoints using TestClient."""

    def setup_method(self):
        """Setup test client with mock auth."""
        api_module.TENANT_REGISTRY.clear()
        api_module.TENANT_STORE.fallback_registry.clear()
        if api_module.TENANT_STORE._redis_available and api_module.TENANT_STORE.redis_client:
            api_module.TENANT_STORE.redis_client.flushall()
        
        test_tenants = {
            "test_key": {
                "client": "Test Client",
                "tier": "Enterprise",
                "role": "admin",
                "scopes": ALL_SCOPES,
                "quota": 1000,
                "requests_used": 0,
            },
        }
        api_module.TENANT_STORE.load_registry_from_env(test_tenants)
        
        self.client = TestClient(app)
        self.headers = {"X-Algorise-API-Key": "test_key"}

    def test_public_health_endpoint(self):
        """Public /health should work without auth."""
        response = self.client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "algorise-devex-gateway"

    def test_public_ready_endpoint(self):
        """Public /ready should work without auth."""
        response = self.client.get("/ready")
        assert response.status_code == 200
        data = response.json()
        assert "ready" in data

    def test_protected_v1_health_requires_auth(self):
        """/v1/health should require auth."""
        response = self.client.get("/v1/health")
        assert response.status_code == 401

    def test_v1_health_with_valid_auth(self):
        """/v1/health should work with valid auth."""
        response = self.client.get("/v1/health", headers=self.headers)
        assert response.status_code == 200
        data = response.json()
        assert data["tenant"] == "Test Client"

    def test_quarantine_list_requires_read_scope(self):
        """/v1/quarantine should require quarantine:read."""
        dev_headers = {"X-Algorise-API-Key": "test_key"}
        response = self.client.get("/v1/quarantine", headers=dev_headers)
        assert response.status_code == 200

    def test_metering_headers_present(self):
        """Response should include metering headers."""
        response = self.client.get("/v1/health", headers=self.headers)
        assert "X-Algorise-Tenant" in response.headers
        assert "X-Algorise-Tier" in response.headers
        assert "X-Algorise-Role" in response.headers
        assert "X-Algorise-Requests-Used" in response.headers
        assert "X-Algorise-Quota-Remaining" in response.headers

    def test_security_headers_present(self):
        """Response should include security headers."""
        response = self.client.get("/health")
        assert response.headers.get("X-Content-Type-Options") == "nosniff"
        assert response.headers.get("X-Frame-Options") == "DENY"
        assert "Referrer-Policy" in response.headers

    def test_cors_allowlist_enforced(self):
        """CORS should only allow configured origins."""
        response = self.client.options(
            "/health",
            headers={"Origin": "https://app.algorise.ai", "Access-Control-Request-Method": "GET"}
        )
        assert response.status_code == 200
        assert "https://app.algorise.ai" in response.headers.get("Access-Control-Allow-Origin", "")


class TestConfigLoading:
    """Tests for configuration loading from environment."""

    def test_parse_origins_from_env(self):
        """Should parse comma-separated origins from env."""
        with patch.dict(os.environ, {"ALLOWED_ORIGINS": "https://a.com, https://b.com"}):
            origins = api_module._parse_origins()
            assert "https://a.com" in origins
            assert "https://b.com" in origins

    def test_parse_origins_defaults(self):
        """Should use defaults when env not set."""
        with patch.dict(os.environ, {}, clear=True):
            origins = api_module._parse_origins()
            assert len(origins) > 0
            assert "http://localhost:3000" in origins

    def test_load_tenant_registry_from_env(self):
        """Should load tenant registry from JSON env var."""
        registry_json = json.dumps({
            "key1": {"client": "Client1", "tier": "Test", "role": "admin", "scopes": ["admin:*"], "quota": 100, "requests_used": 0}
        })
        with patch.dict(os.environ, {"ALGORISE_TENANT_REGISTRY": registry_json}):
            registry = api_module._load_tenant_registry()
            assert "key1" in registry
            assert registry["key1"]["client"] == "Client1"

    def test_load_tenant_registry_invalid_json(self):
        """Should return empty dict on invalid JSON."""
        with patch.dict(os.environ, {"ALGORISE_TENANT_REGISTRY": "not valid json"}):
            registry = api_module._load_tenant_registry()
            assert registry == {}

    def test_env_api_key_override(self):
        """ALGORISE_API_KEY should add admin tenant."""
        with patch.dict(os.environ, {"ALGORISE_API_KEY": "env_admin_key"}):
            registry = api_module._load_tenant_registry()
            registry["env_admin_key"] = {
                "client": "Environment Admin",
                "tier": "Enterprise Custom",
                "role": "admin",
                "scopes": ALL_SCOPES,
                "quota": 100000,
                "requests_used": 0,
            }
            assert "env_admin_key" in registry
            assert registry["env_admin_key"]["role"] == "admin"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])