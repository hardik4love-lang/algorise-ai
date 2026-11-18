"""
Unit Tests for Geofence Guard & Sentinel Service
"""

import time
import pytest
from app.services.geofence_guard import GeofenceGuardService, _active_breaches


def test_geofence_inside_radius():
    """
    Employee within 50m of office should be marked safe with no action taken.
    """
    office_lat = 19.0760
    office_lon = 72.8777
    # 10 meters away
    emp_lat = 19.07608
    emp_lon = 72.87772

    result = GeofenceGuardService.process_location_update(
        employee_id="EMP-TEST-01",
        employee_name="Test User",
        department="IT",
        current_lat=emp_lat,
        current_lon=emp_lon,
        office_lat=office_lat,
        office_lon=office_lon,
        geofence_radius_meters=50.0
    )

    assert result["is_inside"] is True
    assert result["action_taken"] == "NONE"


def test_geofence_breach_and_auto_cutoff():
    """
    Employee leaving perimeter triggers warning, and after grace period executes auto cut-off.
    """
    office_lat = 19.0760
    office_lon = 72.8777
    # 500 meters away
    emp_lat = 19.0805
    emp_lon = 72.8800

    # Clean any residual test state
    if "EMP-TEST-02" in _active_breaches:
        del _active_breaches["EMP-TEST-02"]

    # Step 1: Initial breach -> Warning state
    res1 = GeofenceGuardService.process_location_update(
        employee_id="EMP-TEST-02",
        employee_name="Test User 2",
        department="Sales",
        current_lat=emp_lat,
        current_lon=emp_lon,
        office_lat=office_lat,
        office_lon=office_lon,
        geofence_radius_meters=50.0,
        grace_period_seconds=2  # Fast 2-second grace for test
    )
    assert res1["is_inside"] is False
    assert res1["action_taken"] == "BREACH_WARNING"

    # Step 2: Simulate time passage beyond grace period
    _active_breaches["EMP-TEST-02"]["first_breach_timestamp"] -= 5

    res2 = GeofenceGuardService.process_location_update(
        employee_id="EMP-TEST-02",
        employee_name="Test User 2",
        department="Sales",
        current_lat=emp_lat,
        current_lon=emp_lon,
        office_lat=office_lat,
        office_lon=office_lon,
        geofence_radius_meters=50.0,
        grace_period_seconds=2
    )
    assert res2["is_inside"] is False
    assert res2["action_taken"] == "CUTOFF_EXECUTED"
    assert res2["auto_punch_out_applied"] is True
    assert "alert_dispatched" in res2
