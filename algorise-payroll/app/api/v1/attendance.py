"""
Algorise PayHR - Attendance API Endpoints
Handles biometric push, mobile anti-spoofing punch, and geofence sentinel heartbeat.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Header
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from app.schemas.attendance import (
    DevicePushBatchRequest,
    MobilePunchRequest,
    GeofenceHeartbeatRequest
)
from app.core.hmac_auth import device_hmac_guard
from app.core.anti_spoofing import AntiSpoofingValidator
from app.services.geofence_guard import GeofenceGuardService
from app.core.config import settings

router = APIRouter(prefix="/attendance", tags=["Attendance"])

# Mock Office Baseline Coordinates (Can be fetched from DB in full deployment)
OFFICE_LATITUDE = 19.0760
OFFICE_LONGITUDE = 72.8777
AUTHORIZED_WIFI_BSSIDS = ["00:14:22:01:23:45", "a4:2b:8c:12:34:56"]


@router.post(
    "/device/push",
    dependencies=[Depends(device_hmac_guard)],
    summary="Biometric / CCTV Stream Terminal Push (HMAC-Secured)"
)
async def ingest_device_punches(batch: DevicePushBatchRequest):
    """
    Ingests raw punch records from ZKTeco/eSSL ADMS devices or CCTV face recognition edge boxes.
    Protected against replay and tampering via HMAC-SHA256 headers.
    """
    # In production, pushes to Redis Queue (BullMQ / Celery) and saves to raw_punches table
    return {
        "status": "SUCCESS",
        "device_sn": batch.device_sn,
        "processed_count": len(batch.records),
        "message": f"Successfully ingested {len(batch.records)} biometric punch events into pipeline."
    }


@router.post("/mobile/punch", summary="Mobile GPS + Face Liveness Punch")
async def mobile_employee_punch(
    request: MobilePunchRequest,
    employee_id: str = Header("EMP-001", alias="X-Employee-ID")
):
    """
    Validates mobile check-in with triple anti-spoofing security:
    1. OS-level mock location check
    2. Geofence radius & office Wi-Fi match
    3. Anti-teleportation velocity check
    """
    now = datetime.now(timezone.utc)

    validation = AntiSpoofingValidator.validate_punch_authenticity(
        current_lat=request.latitude,
        current_lon=request.longitude,
        accuracy_meters=request.accuracy_meters,
        is_mock_provider=request.is_mock_provider,
        office_lat=OFFICE_LATITUDE,
        office_lon=OFFICE_LONGITUDE,
        allowed_radius_meters=settings.DEFAULT_GEOFENCE_RADIUS_METERS,
        reported_wifi_bssid=request.wifi_bssid,
        authorized_wifi_bssids=AUTHORIZED_WIFI_BSSIDS,
        current_punch_time=now
    )

    if not validation["is_valid"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=validation
        )

    return {
        "status": "PUNCH_RECORDED",
        "employee_id": employee_id,
        "timestamp": now.isoformat(),
        "direction": request.punch_direction,
        "verification": validation
    }


@router.post("/geofence/heartbeat", summary="Continuous Geofence Sentinel & Auto Cut-Off")
async def geofence_sentinel_heartbeat(
    request: GeofenceHeartbeatRequest,
    employee_id: str = Header("EMP-001", alias="X-Employee-ID"),
    employee_name: str = Header("Rahul Sharma", alias="X-Employee-Name"),
    department: str = Header("Engineering", alias="X-Department")
):
    """
    Monitors if employee has stepped outside the office boundary.
    Executes auto punch-out and admin alert dispatch if grace period expires.
    """
    result = GeofenceGuardService.process_location_update(
        employee_id=employee_id,
        employee_name=employee_name,
        department=department,
        current_lat=request.latitude,
        current_lon=request.longitude,
        office_lat=OFFICE_LATITUDE,
        office_lon=OFFICE_LONGITUDE,
        geofence_radius_meters=settings.DEFAULT_GEOFENCE_RADIUS_METERS,
        is_wifi_connected=request.is_wifi_connected
    )

    return result
