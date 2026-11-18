"""
Algorise PayHR - Anti-Spoofing & Geofence Verification Engine
Prevents GPS Mocking, Virtual Location injection, and impossible teleportation.
"""

import math
from datetime import datetime
from typing import Optional, Tuple, Dict, Any


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Computes great-circle distance between two GPS coordinates in meters using Haversine formula.
    """
    R = 6371000.0  # Earth radius in meters

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (math.sin(delta_phi / 2.0) ** 2 +
         math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2)
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))

    return R * c


class AntiSpoofingValidator:
    """
    Validates mobile punch veracity and rejects spoofed locations.
    """

    @staticmethod
    def validate_punch_authenticity(
        current_lat: float,
        current_lon: float,
        accuracy_meters: float,
        is_mock_provider: bool,
        office_lat: float,
        office_lon: float,
        allowed_radius_meters: float,
        last_punch_lat: Optional[float] = None,
        last_punch_lon: Optional[float] = None,
        last_punch_time: Optional[datetime] = None,
        current_punch_time: Optional[datetime] = None,
        reported_wifi_bssid: Optional[str] = None,
        authorized_wifi_bssids: Optional[list] = None
    ) -> Dict[str, Any]:
        """
        Runs comprehensive anti-spoofing checks:
        1. Mock Location Detector: Android/iOS OS mock flags
        2. Coarse Accuracy Filter: Reject high uncertainty GPS fixes
        3. Distance Verification: Must be within geofence perimeter
        4. Teleportation / Velocity Check: Rejects impossible travel speeds
        5. Secondary Wi-Fi Match: Validates local router hardware MAC
        """
        reasons = []

        # 1. OS-Level Mock Location Detection
        if is_mock_provider:
            return {
                "is_valid": False,
                "error_code": "MOCK_LOCATION_DETECTED",
                "message": "Fraudulent GPS detected. Mock location applications are prohibited."
            }

        # 2. GPS Precision Check (reject coarse towers if > 80m uncertainty)
        if accuracy_meters > 80.0:
            return {
                "is_valid": False,
                "error_code": "POOR_GPS_ACCURACY",
                "message": f"GPS accuracy ({accuracy_meters:.1f}m) too low. Move near a window or turn on Wi-Fi."
            }

        # 3. Distance from Office Geofence Center
        dist_to_office = haversine_distance(current_lat, current_lon, office_lat, office_lon)
        is_inside_geofence = dist_to_office <= allowed_radius_meters

        # 4. Secondary Wi-Fi Check (Dual-factor)
        wifi_verified = False
        if reported_wifi_bssid and authorized_wifi_bssids:
            clean_bssid = reported_wifi_bssid.strip().lower()
            auth_bssids = [b.strip().lower() for b in authorized_wifi_bssids]
            if clean_bssid in auth_bssids:
                wifi_verified = True

        # If outside GPS geofence AND not on verified Wi-Fi -> Reject
        if not is_inside_geofence and not wifi_verified:
            return {
                "is_valid": False,
                "error_code": "OUTSIDE_GEOFENCE",
                "message": f"You are {dist_to_office:.1f}m away from the office. Allowed limit is {allowed_radius_meters}m.",
                "distance_meters": dist_to_office
            }

        # 5. Impossible Travel / Velocity Check (Anti-Teleportation)
        if (last_punch_lat is not None and last_punch_lon is not None and
                last_punch_time is not None and current_punch_time is not None):
            delta_seconds = abs((current_punch_time - last_punch_time).total_seconds())
            if delta_seconds > 0:
                dist_moved = haversine_distance(last_punch_lat, last_punch_lon, current_lat, current_lon)
                speed_kmh = (dist_moved / 1000.0) / (delta_seconds / 3600.0)
                if speed_kmh > 150.0:  # Faster than 150 km/h indicates location spoofing or jumping
                    return {
                        "is_valid": False,
                        "error_code": "IMPOSSIBLE_VELOCITY",
                        "message": f"Velocity anomaly detected ({speed_kmh:.1f} km/h). Teleportation check failed."
                    }

        return {
            "is_valid": True,
            "distance_meters": dist_to_office,
            "wifi_verified": wifi_verified,
            "status": "VERIFIED"
        }
