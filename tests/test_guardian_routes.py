"""Tests for Guardian Angel Cloud Sentinel routes (/api/v1/guardian/*)."""

import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


@pytest.fixture
def guardian_client(tmp_path, monkeypatch):
    """TestClient with isolated SQLite DB and cleared caches/env."""
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("MIGRATE_ON_START", "false")
    monkeypatch.setenv("REDIS_REQUIRED", "false")
    monkeypatch.setenv("ENABLE_EMBEDDED_SCHEDULER", "false")
    monkeypatch.delenv("STRIPE_SECRET_KEY", raising=False)
    monkeypatch.delenv("FOUNDER_UPI_VPA", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)

    import engine.guardian_routes as gr

    test_db = tmp_path / "guardian_test.db"
    monkeypatch.setattr(gr, "TELEMETRY_DB_PATH", test_db)
    gr.TRIAGE_CACHE.clear()
    gr._init_guardian_db()

    from engine.main import app

    with TestClient(app) as client:
        yield client


def test_guardian_health_endpoint(guardian_client):
    resp = guardian_client.get("/api/v1/guardian/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "HEALTHY"
    assert data["version"] == "3.2.0"
    assert data["stripe_configured"] is False
    assert data["upi_configured"] is False


def test_triage_blocks_bare_spoofed_and_disposable_links(guardian_client):
    r1 = guardian_client.post(
        "/api/v1/guardian/triage",
        json={
            "channel": "URL",
            "content": "https://irs.gov.verify-tax.top/claim",
            "region": "US",
        },
    )
    assert r1.status_code == 200
    d1 = r1.json()
    assert d1["threat_score"] >= 70
    assert d1["category"] == "CRITICAL_FRAUD"
    assert d1["senior_safe"] is False
    assert d1["extracted_urls"][0]["verdict"] == "MALICIOUS"

    r2 = guardian_client.post(
        "/api/v1/guardian/triage",
        json={
            "channel": "TEXT",
            "content": "USPS missed your parcel at track-usps-alert.top",
            "region": "US",
        },
    )
    assert r2.status_code == 200
    d2 = r2.json()
    assert d2["threat_score"] >= 70
    assert d2["senior_safe"] is False


def test_triage_verifies_official_domains_and_healthcare_lifelines(guardian_client):
    official = guardian_client.post(
        "/api/v1/guardian/triage",
        json={
            "channel": "URL",
            "content": "Official check: https://www.irs.gov/refunds",
            "region": "US",
        },
    )
    assert official.status_code == 200
    do = official.json()
    assert do["threat_score"] < 35
    assert do["senior_safe"] is True
    assert do["extracted_urls"][0]["verdict"] == "SAFE_OFFICIAL"

    clinic = guardian_client.post(
        "/api/v1/guardian/triage",
        json={
            "channel": "TEXT",
            "content": "NHS clinic appointment scheduled with Dr. Brown at St Mary's Hospital.",
            "region": "UK",
        },
    )
    assert clinic.status_code == 200
    dc = clinic.json()
    assert dc["threat_score"] == 0
    assert dc["category"] == "SAFE_HEALTHCARE"
    assert dc["senior_safe"] is True


def test_orders_concierge_and_upi_modes_no_fake_stripe_redirect(guardian_client, monkeypatch):
    us_resp = guardian_client.post(
        "/api/v1/guardian/orders",
        json={
            "plan_tier": "family",
            "region": "US",
            "customer_name": "Alice Smith",
            "customer_email": "alice@example.com",
            "senior_name": "Margaret",
            "payment_method": "auto",
        },
    )
    assert us_resp.status_code == 200
    us_data = us_resp.json()
    assert us_data["payment_mode"] == "concierge_invoice"
    assert us_data["checkout_url"] is None
    assert us_data["amount"] == 19.99
    assert us_data["currency"] == "USD"
    assert "t.me/Aassqqee_bot" in us_data["telegram_activation_url"]

    monkeypatch.setenv("FOUNDER_UPI_VPA", "algorise@okicici")
    in_resp = guardian_client.post(
        "/api/v1/guardian/orders",
        json={
            "plan_tier": "family",
            "region": "IN",
            "customer_name": "Rohan Patel",
            "customer_email": "rohan@example.com",
            "payment_method": "upi",
        },
    )
    assert in_resp.status_code == 200
    in_data = in_resp.json()
    assert in_data["payment_mode"] == "upi_direct"
    assert in_data["upi_uri"].startswith("upi://pay?")
    assert "algorise%40okicici" in in_data["upi_uri"]
    assert in_data["currency"] == "INR"

    bad_resp = guardian_client.post(
        "/api/v1/guardian/orders",
        json={
            "plan_tier": "nonexistent_plan",
            "customer_name": "Test",
            "customer_email": "test@example.com",
        },
    )
    assert bad_resp.status_code == 400


def test_clips_alert_family_and_telemetry_stats(guardian_client):
    clips = guardian_client.get("/api/v1/guardian/clips").json()
    assert clips["total_clips"] == 3
    assert all(c["video_url"].startswith("/assets/reels/") for c in clips["clips"])

    alert = guardian_client.post(
        "/api/v1/guardian/alert-family",
        json={
            "protected_name": "Margaret <script>",
            "channel": "CALL",
            "scam_type": "IRS Gift Card Demand",
            "threat_score": 95,
            "threat_snippet": "Buy Target cards now",
            "region": "US",
        },
    )
    assert alert.status_code == 200
    assert alert.json()["protected_name"] == "Margaret <script>"

    # Trigger 1 scam scan + 1 telemetry event + 1 order and verify live counts
    guardian_client.post(
        "/api/v1/guardian/triage",
        json={"channel": "CALL", "content": "IRS arrest warrant buy $2500 Target gift card", "region": "US"},
    )
    guardian_client.post(
        "/api/v1/guardian/telemetry",
        json={"event_name": "download_extension", "surface": "index", "meta": {"v": "3.2.0"}},
    )
    guardian_client.post(
        "/api/v1/guardian/orders",
        json={"plan_tier": "individual", "customer_name": "Bob", "customer_email": "bob@example.com"},
    )

    stats = guardian_client.get("/api/v1/guardian/stats").json()
    assert stats["scans_processed"] == 1
    assert stats["scams_blocked"] == 1
    assert stats["orders_created"] == 1
    assert stats["events_recorded"] == 1
