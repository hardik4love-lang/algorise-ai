"""
Algorise PayHR - Geofence Guard & Auto Cut-Off Service
Monitors perimeter breaches in real time, executes auto punch-out, and dispatches admin alerts.
"""

import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from app.core.config import settings
from app.core.anti_spoofing import haversine_distance

# In-memory breach tracking (In production, backed by Redis with TTL)
# Key: employee_id -> Dict of initial breach timestamp, coordinates, and alert state
_active_breaches: Dict[str, Dict[str, Any]] = {}


class GeofenceGuardService:
    """
    Real-time perimeter sentinel.
    Detects when an employee leaves the office radius, counts down grace period,
    cuts off active work session, and notifies administrators.
    """

    @classmethod
    def process_location_update(
        cls,
        employee_id: str,
        employee_name: str,
        department: str,
        current_lat: float,
        current_lon: float,
        office_lat: float,
        office_lon: float,
        geofence_radius_meters: float = settings.DEFAULT_GEOFENCE_RADIUS_METERS,
        is_wifi_connected: bool = False,
        grace_period_seconds: int = settings.GEOFENCE_BREACH_BUFFER_SECONDS
    ) -> Dict[str, Any]:
        """
        Evaluates a continuous heartbeat or boundary event from the mobile agent.
        Returns:
            - is_inside: bool
            - action_taken: 'NONE' | 'BREACH_WARNING' | 'CUTOFF_EXECUTED'
            - details: Dict
        """
        now = time.time()
        distance = haversine_distance(current_lat, current_lon, office_lat, office_lon)
        is_inside = (distance <= geofence_radius_meters) or is_wifi_connected

        # Case 1: Employee is inside safe zone
        if is_inside:
            # If there was an active breach tracking, clear it (they returned within grace)
            if employee_id in _active_breaches:
                del _active_breaches[employee_id]
            return {
                "is_inside": True,
                "distance_meters": round(distance, 1),
                "action_taken": "NONE",
                "message": "Within authorized boundary."
            }

        # Case 2: Employee is outside perimeter
        if employee_id not in _active_breaches:
            # First detection outside boundary -> start countdown
            _active_breaches[employee_id] = {
                "first_breach_timestamp": now,
                "lat": current_lat,
                "lon": current_lon,
                "distance": distance,
                "cutoff_executed": False
            }
            return {
                "is_inside": False,
                "distance_meters": round(distance, 1),
                "action_taken": "BREACH_WARNING",
                "seconds_remaining_in_grace": grace_period_seconds,
                "message": f"Outside office boundary ({distance:.1f}m). Return within {grace_period_seconds}s to avoid auto-cutoff."
            }

        breach_record = _active_breaches[employee_id]
        breach_duration = now - breach_record["first_breach_timestamp"]

        # Case 3: Still within grace period
        if breach_duration < grace_period_seconds:
            remaining = int(grace_period_seconds - breach_duration)
            return {
                "is_inside": False,
                "distance_meters": round(distance, 1),
                "action_taken": "BREACH_WARNING",
                "seconds_remaining_in_grace": remaining,
                "message": f"Outside boundary for {int(breach_duration)}s. {remaining}s left before auto cut-off."
            }

        # Case 4: Grace period expired -> Execute Auto Cut-Off
        if not breach_record["cutoff_executed"]:
            breach_record["cutoff_executed"] = True

            # Generate admin alert payload
            alert = cls._generate_admin_alert(
                employee_id=employee_id,
                employee_name=employee_name,
                department=department,
                breach_duration_seconds=int(breach_duration),
                distance_meters=round(distance, 1),
                lat=current_lat,
                lon=current_lon
            )

            return {
                "is_inside": False,
                "distance_meters": round(distance, 1),
                "action_taken": "CUTOFF_EXECUTED",
                "auto_punch_out_applied": True,
                "alert_dispatched": alert,
                "message": "Grace period expired. Session auto-terminated and admin notified."
            }

        # Already cutoff
        return {
            "is_inside": False,
            "distance_meters": round(distance, 1),
            "action_taken": "ALREADY_CUTOFF",
            "message": "Employee already punched out due to unauthorized departure."
        }

    @staticmethod
    def _generate_admin_alert(
        employee_id: str,
        employee_name: str,
        department: str,
        breach_duration_seconds: int,
        distance_meters: float,
        lat: float,
        lon: float
    ) -> Dict[str, Any]:
        """
        Dispatches high-priority alert payload for HR / Admin.
        In production, sends via WebSocket push, Firebase, or WhatsApp Business API.
        """
        return {
            "alert_id": f"ALT-BREACH-{int(time.time())}",
            "severity": "HIGH",
            "event": "GEOFENCE_BREACH_AUTO_CUTOFF",
            "employee": {
                "id": employee_id,
                "name": employee_name,
                "department": department
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "details": {
                "distance_from_office_meters": distance_meters,
                "latitude": lat,
                "longitude": lon,
                "unauthorized_duration_seconds": breach_duration_seconds,
                "system_action": "AUTOMATIC_PUNCH_OUT_RECORDED"
            }
        }
