"""
Unit and Integration Tests for Phase 2 Optimization Milestones:
- TECH-201: Cloud-Native Quarantine Storage & Remote Sync
- TECH-202: Incremental AST Hash Caching in BlastRadiusAnalyzer
- TECH-203: Commercial Metering Gateway API (FastAPI)
"""

import json
import os
import shutil
import tempfile
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from autotest_sentinel.models import (
    FlakeCategory,
    FlakinessReport,
    QuarantineManifest,
    RootCauseHypothesis,
)
from autotest_sentinel.quarantine import QuarantineManager
from context_pr.blast_radius import BlastRadiusAnalyzer
from devex.api import app, TENANT_REGISTRY


# ===========================================================================
# 1. TECH-201: Quarantine Remote Cloud Storage & Sync Tests
# ===========================================================================

def test_quarantine_remote_sync_fetch():
    with tempfile.TemporaryDirectory() as tmpdir:
        local_manifest = os.path.join(tmpdir, "quarantine.json")
        remote_data = {
            "version": "1.0.0",
            "updated_at": "2026-10-15T00:00:00Z",
            "quarantined_tests": {
                "tests/test_remote.py::test_cloud_flaky": {
                    "test_id": "tests/test_remote.py::test_cloud_flaky",
                    "file_path": "tests/test_remote.py",
                    "flakiness_score": 0.95,
                    "root_cause": "TIMING_RACE",
                    "failure_rate": 0.5,
                    "reason": "Cloud sync test",
                    "quarantined_at": "2026-10-15T00:00:00Z",
                    "expires_at": "2026-10-29T00:00:00Z"
                }
            }
        }

        # Mock httpx.Client to return remote_data on GET
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = remote_data

        with patch("httpx.Client.get", return_value=mock_response):
            qm = QuarantineManager(
                manifest_path=local_manifest,
                remote_url="https://api.algorise.ai/v1/quarantine",
                api_token="alg_test_token_123"
            )
            assert "tests/test_remote.py::test_cloud_flaky" in qm.manifest.quarantined_tests
            # Verify cached to local file
            assert os.path.exists(local_manifest)


def test_quarantine_remote_save_sync():
    with tempfile.TemporaryDirectory() as tmpdir:
        local_manifest = os.path.join(tmpdir, "quarantine.json")
        mock_put = MagicMock()

        with patch("httpx.Client.get", side_effect=Exception("Connection refused")), \
             patch("httpx.Client.put", mock_put):
            qm = QuarantineManager(
                manifest_path=local_manifest,
                remote_url="https://api.algorise.ai/v1/quarantine",
                api_token="alg_test_token_123"
            )
            report = FlakinessReport(
                test_id="tests/test_db.py::test_lock_contention",
                file_path="tests/test_db.py",
                flakiness_score=0.88,
                category=FlakeCategory.FLAKY_HIGH,
                root_cause=RootCauseHypothesis.TIMING_RACE,
                total_runs=20,
                failure_rate=0.4,
                duration_jitter=0.08,
                recommended_action="Quarantine",
            )
            is_new = qm.quarantine_test(report, reason="High lock contention")
            assert is_new is True
            assert mock_put.called
            # Verify payload contains new test
            put_payload = mock_put.call_args[1]["json"]
            assert "tests/test_db.py::test_lock_contention" in put_payload["quarantined_tests"]


# ===========================================================================
# 2. TECH-202: Incremental AST Hash Caching Tests
# ===========================================================================

def test_blast_radius_ast_cache_hit_and_invalidation():
    with tempfile.TemporaryDirectory() as tmpdir:
        cache_file = os.path.join(tmpdir, "ast_cache.json")
        module_a = os.path.join(tmpdir, "module_a.py")
        module_b = os.path.join(tmpdir, "module_b.py")

        with open(module_a, "w", encoding="utf-8") as f:
            f.write("def helper():\n    return 42\n")

        with open(module_b, "w", encoding="utf-8") as f:
            f.write("from module_a import helper\n\ndef main():\n    return helper()\n")

        # First run: cache misses
        analyzer1 = BlastRadiusAnalyzer(root_dir=tmpdir, cache_path=cache_file)
        assert analyzer1.cache_misses >= 2
        assert analyzer1.cache_hits == 0
        assert os.path.exists(cache_file)

        # Second run: cache hits
        analyzer2 = BlastRadiusAnalyzer(root_dir=tmpdir, cache_path=cache_file)
        assert analyzer2.cache_hits >= 2
        assert analyzer2.cache_misses == 0

        # Modify module_a: should miss 1, hit 1
        with open(module_a, "w", encoding="utf-8") as f:
            f.write("def helper():\n    return 999  # Modified\n")

        analyzer3 = BlastRadiusAnalyzer(root_dir=tmpdir, cache_path=cache_file)
        assert analyzer3.cache_hits >= 1
        assert analyzer3.cache_misses >= 1


# ===========================================================================
# 3. TECH-203: Commercial Metering Gateway API Tests
# ===========================================================================

client = TestClient(app)
VALID_KEY = "alg_live_test_key_9981"


def test_api_health():
    response = client.get("/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "algorise-devex-gateway"
    assert "autotest_sentinel" in data["engines"]


def test_api_auth_unauthorized():
    # Missing API key
    response = client.get("/v1/quarantine")
    assert response.status_code == 401
    assert "Unauthorized" in response.json()["detail"]

    # Invalid API key
    response = client.get(
        "/v1/quarantine",
        headers={"X-Algorise-API-Key": "invalid_key_9999"}
    )
    assert response.status_code == 401


def test_api_usage_metering():
    headers = {"X-Algorise-API-Key": VALID_KEY}
    response = client.get("/v1/usage", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["client"] == "Acme Corp"
    assert data["tier"] == "Enterprise Tier"
    assert data["requests_used"] >= 1
    assert response.headers["X-Algorise-Tenant"] == "Acme Corp"


def test_api_quarantine_crud():
    with tempfile.TemporaryDirectory() as tmpdir:
        test_manifest = os.path.join(tmpdir, "quarantine.json")
        headers = {"X-Algorise-API-Key": VALID_KEY}

        # 1. Add to quarantine
        payload = {
            "test_id": "tests/test_payment.py::test_stripe_webhook",
            "file_path": "tests/test_payment.py",
            "flakiness_score": 0.92,
            "root_cause": "NETWORK_IO",
            "failure_rate": 0.45,
            "reason": "Intermittent HTTP 504 in stripe mock",
            "ttl_days": 7
        }
        resp = client.post(
            f"/v1/quarantine?manifest_path={test_manifest}",
            json=payload,
            headers=headers
        )
        assert resp.status_code == 201
        res_data = resp.json()
        assert res_data["success"] is True
        assert res_data["is_new"] is True
        assert res_data["test_id"] == "tests/test_payment.py::test_stripe_webhook"

        # 2. List quarantine
        list_resp = client.get(
            f"/v1/quarantine?manifest_path={test_manifest}",
            headers=headers
        )
        assert list_resp.status_code == 200
        ldata = list_resp.json()
        assert ldata["total_quarantined"] == 1
        assert "tests/test_payment.py::test_stripe_webhook" in ldata["quarantined_tests"]
        assert any("tests/test_payment.py::test_stripe_webhook" in arg for arg in ldata["pytest_deselect_args"])

        # 3. Remove from quarantine
        del_resp = client.delete(
            f"/v1/quarantine/tests/test_payment.py::test_stripe_webhook?manifest_path={test_manifest}",
            headers=headers
        )
        assert del_resp.status_code == 200
        assert del_resp.json()["success"] is True
        assert del_resp.json()["remaining_quarantined"] == 0


def test_api_blast_radius():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create minimal python project
        core_file = os.path.join(tmpdir, "core.py")
        service_file = os.path.join(tmpdir, "service.py")

        with open(core_file, "w", encoding="utf-8") as f:
            f.write("def calculate_total():\n    return 100\n")

        with open(service_file, "w", encoding="utf-8") as f:
            f.write("from core import calculate_total\n\ndef run():\n    return calculate_total()\n")

        headers = {"X-Algorise-API-Key": VALID_KEY}
        payload = {
            "changed_files": ["core.py"],
            "root_dir": tmpdir
        }
        resp = client.post("/v1/blast-radius", json=payload, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_files_changed"] == 1
        assert "risk_score" in data
        assert "risk_level" in data
        assert "cache_telemetry" in data
        assert data["cache_telemetry"]["cache_misses"] >= 2
