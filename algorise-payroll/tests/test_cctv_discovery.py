"""Test suite for CCTV RTSP Discovery and Ingestion Engine."""

import pytest
from scripts.cctv_rtsp_discovery import CCTVStreamIngestEngine, CameraEndpoint


def test_camera_endpoint_rtsp_url_construction():
    """Validates vendor-specific RTSP URL formatting for Hikvision, Dahua, and CP Plus."""
    # Hikvision
    cam_hik = CameraEndpoint(
        camera_id="CAM-01",
        name="Gate 1",
        location="Front",
        brand="Hikvision",
        ip_address="192.168.1.101",
        port=554,
        username="admin",
        password="pwd",
        channel=1,
        subtype=0,
    )
    url_hik = cam_hik.construct_rtsp_url()
    assert url_hik == "rtsp://admin:pwd@192.168.1.101:554/Streaming/Channels/101"

    # Dahua
    cam_dahua = CameraEndpoint(
        camera_id="CAM-02",
        name="Floor 2",
        location="Plant",
        brand="Dahua",
        ip_address="192.168.1.102",
        port=554,
        username="admin",
        password="pwd",
        channel=2,
        subtype=1,
    )
    url_dahua = cam_dahua.construct_rtsp_url()
    assert url_dahua == "rtsp://admin:pwd@192.168.1.102:554/cam/realmonitor?channel=2&subtype=1"

    # CP Plus
    cam_cpplus = CameraEndpoint(
        camera_id="CAM-03",
        name="Bay 3",
        location="Warehouse",
        brand="CP Plus",
        ip_address="192.168.1.103",
        port=554,
        username="admin",
        password="pwd",
        channel=1,
        subtype=0,
    )
    url_cpplus = cam_cpplus.construct_rtsp_url()
    assert url_cpplus == "rtsp://admin:pwd@192.168.1.103:554/cam/realmonitor?channel=1&subtype=0"


def test_cctv_engine_registration_and_mock_scan():
    """Validates registering cameras and executing edge health scans."""
    engine = CCTVStreamIngestEngine()
    engine.register_camera(
        camera_id="CAM-TEST-01",
        name="Entrance",
        location="Gate",
        brand="Hikvision",
        ip_address="192.168.1.50",
        port=554,
        username="admin",
        password="SecretPassword",
    )

    results = engine.scan_all_cameras(force_mock=True)
    assert len(results) == 1
    r = results[0]
    assert r["camera_id"] == "CAM-TEST-01"
    assert r["status"] == "ONLINE_MOCK_VERIFIED"
    assert r["anti_spoofing_ready"] is True
    # Password must be masked in output
    assert "SecretPassword" not in r["rtsp_url"]
    assert "*****" in r["rtsp_url"]
