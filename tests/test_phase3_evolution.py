"""
Unit and Integration Tests for Phase 3 Evolution Milestones:
- TECH-301: Enterprise Control Plane & Role-Based Access Control (RBAC)
- TECH-302: Distributed Autonomous Healing Mesh (TraceRoot AI <-> ModernizeAI <-> ContextPR)
"""

import os
import tempfile
import pytest
from fastapi.testclient import TestClient

from devex.api import app, TENANT_REGISTRY
from trace_root_ai.mesh import AutonomousHealingMesh
from trace_root_ai.models import IncidentPayload

client = TestClient(app)
ADMIN_KEY = "alg_live_test_key_9981"
DEV_KEY = "alg_demo_client_key_001"
VIEWER_KEY = "alg_readonly_key_002"


# ===========================================================================
# 1. TECH-301: Role-Based Access Control (RBAC) Tests
# ===========================================================================

def test_rbac_admin_full_access():
    headers = {"X-Algorise-API-Key": ADMIN_KEY}
    resp = client.get("/v1/usage", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["role"] == "admin"


def test_rbac_viewer_allowed_read():
    headers = {"X-Algorise-API-Key": VIEWER_KEY}
    # Viewer has quarantine:read
    resp = client.get("/v1/quarantine", headers=headers)
    assert resp.status_code == 200


def test_rbac_viewer_forbidden_write():
    headers = {"X-Algorise-API-Key": VIEWER_KEY}
    # Viewer does NOT have quarantine:write
    payload = {
        "test_id": "tests/test_dummy.py::test_fail",
        "file_path": "tests/test_dummy.py",
        "flakiness_score": 0.9,
        "root_cause": "TIMING_RACE",
        "failure_rate": 0.5,
    }
    resp = client.post("/v1/quarantine", json=payload, headers=headers)
    assert resp.status_code == 403
    assert "Forbidden" in resp.json()["detail"]
    assert "quarantine:write" in resp.json()["detail"]


def test_rbac_developer_forbidden_incident_heal():
    headers = {"X-Algorise-API-Key": DEV_KEY}
    # Developer key does not have incident:heal scope
    payload = {
        "incident_id": "INC-TEST-01",
        "service_name": "billing-service",
        "error_type": "KeyError",
        "error_message": "'missing_token'",
        "stack_trace": "File \"dummy.py\", line 10, in execute\n    token = payload['missing_token']",
    }
    resp = client.post("/v1/incidents/heal", json=payload, headers=headers)
    assert resp.status_code == 403
    assert "incident:heal" in resp.json()["detail"]


# ===========================================================================
# 2. TECH-302: Autonomous Healing Mesh Tests
# ===========================================================================

def test_autonomous_healing_mesh_end_to_end():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a sample python file with a KeyError bug
        code_file = os.path.join(tmpdir, "processor.py")
        code_content = """def process_request(data):
    token = data["auth_token"]
    return token
"""
        with open(code_file, "w", encoding="utf-8") as f:
            f.write(code_content)

        traceback_str = f"""Traceback (most recent call last):
  File "{code_file}", line 2, in process_request
    token = data["auth_token"]
KeyError: 'auth_token'
"""
        incident = IncidentPayload(
            incident_id="INC-MESH-101",
            service_name="auth-service",
            error_type="KeyError",
            error_message="'auth_token'",
            raw_stack_trace=traceback_str,
        )

        mesh = AutonomousHealingMesh(root_dir=tmpdir)
        result = mesh.process_incident(incident=incident, auto_stage=False)

        assert result.hotfix_synthesized is True
        assert result.culprit_file == "processor.py"
        assert result.culprit_line == 2
        assert result.hotfix_plan is not None
        assert ".get(\"auth_token\", None)" in result.hotfix_plan["patch_diff"]
        assert result.blast_radius_risk in ["LOW", "MEDIUM"]
        assert result.verification_passed is True


def test_api_incident_heal_endpoint():
    with tempfile.TemporaryDirectory() as tmpdir:
        code_file = os.path.join(tmpdir, "calc.py")
        with open(code_file, "w", encoding="utf-8") as f:
            f.write("def calculate_ratio(a, b):\n    return a / b\n")

        traceback_str = f"""Traceback (most recent call last):
  File "{code_file}", line 2, in calculate_ratio
    return a / b
ZeroDivisionError: division by zero
"""
        headers = {"X-Algorise-API-Key": ADMIN_KEY}
        payload = {
            "incident_id": "INC-DIV-99",
            "service_name": "calc-service",
            "error_type": "ZeroDivisionError",
            "error_message": "division by zero",
            "stack_trace": traceback_str,
            "root_dir": tmpdir,
            "auto_stage": False,
        }

        resp = client.post("/v1/incidents/heal", json=payload, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["incident_id"] == "INC-DIV-99"
        assert data["hotfix_synthesized"] is True
        assert data["culprit_file"] == "calc.py"
        assert data["verification_passed"] is True
        assert "ZeroDivisionError" in data["remediation_summary"]
