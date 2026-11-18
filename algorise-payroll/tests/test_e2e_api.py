"""
End-to-End API Integration Tests for Algorise PayHR
Tests FastAPI HTTP endpoints with real payloads, HMAC verification, and Geofence alerts.
"""

import time
import hmac
import hashlib
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings
from app.services.geofence_guard import _active_breaches

client = TestClient(app)


def test_health_check_endpoint():
    """Verify health check returns 200 and correct status"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "HEALTHY"
    assert data["system"] == settings.PROJECT_NAME


def test_statutory_rates_endpoint():
    """Verify statutory metadata endpoint returns verified Indian rates"""
    response = client.get("/api/v1/payroll/statutory-rates")
    assert response.status_code == 200
    data = response.json()
    assert data["epf"]["wage_ceiling"] == 15000.0
    assert data["esic"]["wage_ceiling"] == 21000.0
    assert data["tds_new_regime_sec_115bac"]["standard_deduction"] == 75000.0


def test_payslip_calculation_endpoint():
    """Verify itemized gross-to-net payslip calculation via HTTP POST"""
    payload = {
        "employee_id": "EMP-001",
        "employee_name": "Priya Patel",
        "total_month_days": 30,
        "lop_days": 2.0,  # 2 days LOP
        "overtime_hours": 5.0,  # 5 hours OT
        "monthly_basic": 40000.0,
        "monthly_hra": 20000.0,
        "monthly_special_allowance": 15000.0,
        "state_for_pt": "Maharashtra",
        "month_number": 10,
        "gender": "FEMALE",
        "tax_regime": "NEW"
    }
    response = client.post("/api/v1/payroll/calculate-payslip", json=payload)
    assert response.status_code == 200
    data = response.json()
    
    # Payable days = 30 - 2 = 28 days
    assert data["attendance_summary"]["payable_days"] == 28.0
    # Prorated basic = 40,000 * (28/30) = 37,333.33
    assert abs(data["earnings"]["basic"] - 37333.33) < 1.0
    # Overtime pay should be non-zero
    assert data["earnings"]["overtime_pay"] > 0
    # Net pay should be computed
    assert data["net_pay"] > 0
    # Female in Maharashtra earning > 25,000 pays PT ₹200
    assert data["deductions"]["professional_tax"] == 200.0


def test_device_push_with_valid_hmac():
    """Verify biometric device push with valid HMAC signature succeeds"""
    body_dict = {
        "device_sn": "ZK-CAMERA-01",
        "records": [
            {
                "pin": "EMP-042",
                "time": "2026-10-26T09:30:00Z",
                "verify_mode": 15
            }
        ]
    }
    import json
    body_bytes = json.dumps(body_dict).encode("utf-8")
    ts = str(int(time.time()))
    nonce = f"test-nonce-{int(time.time()*1000)}"

    payload_hash = hashlib.sha256(body_bytes).hexdigest()
    signing_input = f"{ts}.{nonce}.{payload_hash}".encode("utf-8")
    sig = hmac.new(
        settings.DEVICE_HMAC_SECRET.encode("utf-8"),
        signing_input,
        hashlib.sha256
    ).hexdigest()

    headers = {
        "X-Algorise-Signature": sig,
        "X-Algorise-Timestamp": ts,
        "X-Algorise-Nonce": nonce,
        "Content-Type": "application/json"
    }

    response = client.post(
        "/api/v1/attendance/device/push",
        content=body_bytes,
        headers=headers
    )
    assert response.status_code == 200
    assert response.json()["status"] == "SUCCESS"


def test_device_push_with_tampered_signature_fails():
    """Verify device push with invalid signature returns 401 Unauthorized"""
    headers = {
        "X-Algorise-Signature": "invalid_tampered_signature_hex",
        "X-Algorise-Timestamp": str(int(time.time())),
        "X-Algorise-Nonce": "fake-nonce",
        "Content-Type": "application/json"
    }
    response = client.post(
        "/api/v1/attendance/device/push",
        json={"device_sn": "FAKE", "records": []},
        headers=headers
    )
    assert response.status_code == 401


def test_geofence_sentinel_endpoint():
    """Verify geofence sentinel detects outside boundary and cut-off"""
    # Clean test state
    if "EMP-E2E-01" in _active_breaches:
        del _active_breaches["EMP-E2E-01"]

    headers = {
        "X-Employee-ID": "EMP-E2E-01",
        "X-Employee-Name": "Anand Verma",
        "X-Department": "Operations"
    }
    # 600 meters away from office
    breach_payload = {
        "latitude": 19.0820,
        "longitude": 72.8830,
        "is_wifi_connected": False
    }

    # First heartbeat -> WARNING
    res1 = client.post("/api/v1/attendance/geofence/heartbeat", json=breach_payload, headers=headers)
    assert res1.status_code == 200
    assert res1.json()["is_inside"] is False
    assert res1.json()["action_taken"] == "BREACH_WARNING"

    # Fast forward breach timer beyond grace period
    _active_breaches["EMP-E2E-01"]["first_breach_timestamp"] -= 200

    # Second heartbeat -> CUTOFF_EXECUTED
    res2 = client.post("/api/v1/attendance/geofence/heartbeat", json=breach_payload, headers=headers)
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["is_inside"] is False
    assert data2["action_taken"] == "CUTOFF_EXECUTED"
    assert data2["auto_punch_out_applied"] is True
    assert data2["alert_dispatched"]["severity"] == "HIGH"
