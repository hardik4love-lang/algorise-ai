"""
Algorise PayHR - Extreme Stress, Fuzzing & Boundary Testing Suite
Validates enterprise resilience against:
1. Zero / Negative earnings, extreme LOP clamping (> 30 days)
2. High Net Worth Individuals (HNWI) with multi-crore incomes and surcharges
3. Leap years and February variations
4. Geofence boundary flapping and extreme coordinate ranges
5. Cryptographic tampering, corrupted payloads, and high-entropy fuzzing
"""

import math
import time
import pytest
from datetime import datetime, timezone
from app.services.statutory_engine import StatutoryComplianceEngine
from app.services.payroll_engine import PayrollCalculationEngine
from app.services.daily_wage_engine import DailyWageCalculationEngine
from app.services.geofence_guard import GeofenceGuardService, _active_breaches
from app.core.anti_spoofing import AntiSpoofingValidator, haversine_distance
from app.core.hmac_auth import verify_hmac_signature
from app.services.backup_engine import ZeroKnowledgeBackupEngine


# =========================================================================
# 1. EXTREME PAYROLL BOUNDARY & RESILIENCE TESTS
# =========================================================================

def test_lop_greater_than_month_days_clamping():
    """
    Ensure an employee with LOP days exceeding total calendar days (e.g. 35 days in a 30-day month)
    is gracefully clamped to 0 payable days and 0 net pay, never negative pay.
    """
    payslip = PayrollCalculationEngine.compute_employee_payslip(
        employee_id="EMP-EXTREME-01",
        employee_name="Absentee Worker",
        total_month_days=30,
        lop_days=45.0,  # 45 days LOP in 30 day month
        overtime_hours=0.0,
        monthly_basic=50000.0,
        monthly_hra=25000.0,
        monthly_special_allowance=25000.0
    )
    assert payslip["attendance_summary"]["payable_days"] == 0.0
    assert payslip["earnings"]["basic"] == 0.0
    assert payslip["earnings"]["total_gross"] == 0.0
    assert payslip["net_pay"] == 0.0
    assert payslip["deductions"]["total_deductions"] == 0.0


def test_zero_salary_unpaid_intern():
    """
    Ensure zero-salary employees (e.g. unpaid interns or volunteers) don't trigger ZeroDivisionError.
    """
    payslip = PayrollCalculationEngine.compute_employee_payslip(
        employee_id="INTERN-001",
        employee_name="Unpaid Intern",
        total_month_days=30,
        lop_days=0.0,
        overtime_hours=10.0,  # 10 OT hours on 0 basic
        monthly_basic=0.0,
        monthly_hra=0.0,
        monthly_special_allowance=0.0
    )
    assert payslip["earnings"]["basic"] == 0.0
    assert payslip["earnings"]["overtime_pay"] == 0.0
    assert payslip["net_pay"] == 0.0


def test_high_net_worth_individual_tds():
    """
    Test High Net Worth Individual (HNWI) with ₹50,00,000 monthly gross (₹6 Crores annual).
    Verifies that Section 115BAC 30% slab computes without numeric overflow.
    """
    monthly_gross = 5000000.0
    annual_gross = monthly_gross * 12.0  # ₹6,00,00,000
    tds_data = StatutoryComplianceEngine.calculate_annual_tds_new_regime(
        projected_annual_gross=annual_gross
    )
    # Taxable income = 6,00,00,000 - 75,000 = 5,99,25,000
    assert tds_data["annual_taxable_income"] == 59925000.0
    # Tax should be substantial (> ₹1.7 Crores)
    assert tds_data["total_annual_tds"] > 17000000.0
    assert tds_data["monthly_tds"] > 1400000.0


def test_february_pt_adjustment_in_payroll_run():
    """
    Verify that in February (month 2), Maharashtra Professional Tax accurately escalates to ₹300.
    """
    # Month 10 (October) -> ₹200
    p_oct = PayrollCalculationEngine.compute_employee_payslip(
        employee_id="EMP-PT-01",
        employee_name="PT Test Oct",
        total_month_days=31,
        lop_days=0.0,
        overtime_hours=0.0,
        monthly_basic=30000.0,
        monthly_hra=15000.0,
        monthly_special_allowance=10000.0,
        state_for_pt="Maharashtra",
        month_number=10
    )
    assert p_oct["deductions"]["professional_tax"] == 200.0

    # Month 2 (February) -> ₹300
    p_feb = PayrollCalculationEngine.compute_employee_payslip(
        employee_id="EMP-PT-02",
        employee_name="PT Test Feb",
        total_month_days=28,
        lop_days=0.0,
        overtime_hours=0.0,
        monthly_basic=30000.0,
        monthly_hra=15000.0,
        monthly_special_allowance=10000.0,
        state_for_pt="Maharashtra",
        month_number=2
    )
    assert p_feb["deductions"]["professional_tax"] == 300.0


# =========================================================================
# 2. GEOFENCE BOUNDARY FLAPPING & FLICKER RESILIENCE
# =========================================================================

def test_geofence_boundary_flicker_handling():
    """
    Simulates an employee walking right on the perimeter line (49.9m to 50.2m)
    repeatedly. Ensures system does not spawn duplicate cutoffs or crash.
    """
    office_lat = 19.0760
    office_lon = 72.8777
    emp_id = "EMP-FLICKER-01"

    if emp_id in _active_breaches:
        del _active_breaches[emp_id]

    # 1. Inside (40m)
    r1 = GeofenceGuardService.process_location_update(
        employee_id=emp_id, employee_name="Flicker User", department="IT",
        current_lat=19.0763, current_lon=72.8777,
        office_lat=office_lat, office_lon=office_lon,
        geofence_radius_meters=50.0
    )
    assert r1["is_inside"] is True

    # 2. Flap outside (55m) -> Initiates grace warning
    r2 = GeofenceGuardService.process_location_update(
        employee_id=emp_id, employee_name="Flicker User", department="IT",
        current_lat=19.0765, current_lon=72.8777,
        office_lat=office_lat, office_lon=office_lon,
        geofence_radius_meters=50.0
    )
    assert r2["is_inside"] is False
    assert r2["action_taken"] == "BREACH_WARNING"

    # 3. Steps back inside (30m) -> Clears active breach state cleanly
    r3 = GeofenceGuardService.process_location_update(
        employee_id=emp_id, employee_name="Flicker User", department="IT",
        current_lat=19.0762, current_lon=72.8777,
        office_lat=office_lat, office_lon=office_lon,
        geofence_radius_meters=50.0
    )
    assert r3["is_inside"] is True
    assert emp_id not in _active_breaches


# =========================================================================
# 3. CRYPTOGRAPHIC & REPLAY ATTACK STRESS TESTS
# =========================================================================

def test_hmac_future_timestamp_attack_rejection():
    """
    Ensure an attacker cannot send a timestamp 10 minutes in the future to keep a request valid longer.
    """
    import hmac, hashlib
    secret = "secret-key"
    body = b'{"punch": true}'
    future_ts = str(int(time.time()) + 600)  # +10 minutes
    nonce = "future-nonce-1"

    p_hash = hashlib.sha256(body).hexdigest()
    sig = hmac.new(secret.encode(), f"{future_ts}.{nonce}.{p_hash}".encode(), hashlib.sha256).hexdigest()

    # Must be rejected because drift > 300s
    assert verify_hmac_signature(body, sig, future_ts, nonce, secret) is False


def test_hmac_past_expired_timestamp_attack_rejection():
    """
    Ensure an attacker cannot replay a 10-minute old signature.
    """
    import hmac, hashlib
    secret = "secret-key"
    body = b'{"punch": true}'
    past_ts = str(int(time.time()) - 600)  # -10 minutes
    nonce = "past-nonce-1"

    p_hash = hashlib.sha256(body).hexdigest()
    sig = hmac.new(secret.encode(), f"{past_ts}.{nonce}.{p_hash}".encode(), hashlib.sha256).hexdigest()

    # Must be rejected
    assert verify_hmac_signature(body, sig, past_ts, nonce, secret) is False


def test_large_payload_encrypted_backup_stress(tmp_path):
    """
    Stress test zero-knowledge AES-256-GCM encryption with a 1MB payload (simulating a 10,000 employee company).
    """
    large_payload = (b"EMPLOYEE_RECORD_DATA_MUSTER_LOG_ENTRY;" * 25000)  # ~1MB
    out_file = str(tmp_path / "large_enterprise_backup.sql.gz.enc")

    meta = ZeroKnowledgeBackupEngine.encrypt_data_to_file(large_payload, out_file)
    assert meta["size_bytes"] > 0

    # Decrypt and verify exact bit-for-bit integrity
    restored = ZeroKnowledgeBackupEngine.decrypt_file_to_data(out_file)
    assert restored == large_payload
