"""
Algorise PayHR - Attendance API Schemas
Strict Pydantic models for validation and serialization.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class DevicePunchRecord(BaseModel):
    pin: str = Field(..., description="Employee code or RFID card pin")
    time: datetime = Field(..., description="Timestamp of the punch")
    verify_mode: int = Field(default=15, description="15 = Face, 1 = Fingerprint, 2 = Pin, 3 = Card")


class DevicePushBatchRequest(BaseModel):
    device_sn: str = Field(..., description="Serial number of biometric/camera terminal")
    records: List[DevicePunchRecord]


class MobilePunchRequest(BaseModel):
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    accuracy_meters: float = Field(..., ge=0.0)
    is_mock_provider: bool = Field(default=False)
    wifi_bssid: Optional[str] = None
    face_photo_base64: Optional[str] = None
    punch_direction: str = Field(default="AUTO", pattern="^(IN|OUT|AUTO)$")


class GeofenceHeartbeatRequest(BaseModel):
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    is_wifi_connected: bool = Field(default=False)
    wifi_bssid: Optional[str] = None
