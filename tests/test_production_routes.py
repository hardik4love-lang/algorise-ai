"""Test that the client routes work in production.

The seeder raises in production by design, because a client record must
be created through the onboarding flow. Several request handlers called
the seeder directly, which turned every one of those routes into a 403
in production. The live API returned
"Automatic client seeding is disabled in production" for the Meta token
route, so the onboarding step that provisions a token could not be
completed at all.

These tests run the routes with ENVIRONMENT=production and assert they
are not blocked by the seeder.
"""
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


@pytest.fixture(scope="module")
def production_client():
    """A test client with the production environment configured."""
    previous = dict(os.environ)
    os.environ["ENVIRONMENT"] = "production"
    os.environ["MIGRATE_ON_START"] = "false"
    os.environ["REDIS_REQUIRED"] = "false"
    os.environ["ENABLE_EMBEDDED_SCHEDULER"] = "false"
    os.environ.setdefault("SECRET_KEY", "test-not-a-real-secret")
    os.environ.setdefault("ADMIN_SECRET", "test-not-a-real-secret")
    os.environ.setdefault("FB_APP_SECRET", "test-not-a-real-secret")

    from fastapi.testclient import TestClient
    from engine.main import app

    with TestClient(app) as client:
        yield client

    os.environ.clear()
    os.environ.update(previous)


def _is_seeder_blocked(response):
    """True when the response was blocked by the client seeder."""
    if response.status_code != 403:
        return False
    try:
        body = response.json()
    except Exception:
        return False
    detail = str(body.get("detail", "")).lower()
    return "seeding" in detail or "seeding is disabled" in detail


def test_the_token_route_is_not_blocked_by_the_seeder(production_client):
    """The Meta token route has to work in production."""
    response = production_client.post(
        "/api/v1/auth/facebook/manual-token",
        json={
            "client_id": "client_srt_shruhi",
            "pin": "2026",
            "page_id": "61586357894191",
            "page_name": "Route Check",
            "access_token": "EAA_ROUTE_CHECK_TOKEN_1234567890",
        },
    )
    assert not _is_seeder_blocked(response), (
        "the token route is blocked by the seeder in production"
    )


def test_the_client_login_route_is_not_blocked(production_client):
    response = production_client.post(
        "/api/v1/auth/client-login",
        json={"client_id": "client_srt_shruhi", "pin": "2026"},
    )
    assert not _is_seeder_blocked(response)


def test_the_dashboard_route_is_not_blocked(production_client):
    response = production_client.get(
        "/api/v1/client/client_srt_shruhi/dashboard?pin=2026"
    )
    assert not _is_seeder_blocked(response)


def test_the_rules_route_is_not_blocked(production_client):
    response = production_client.get(
        "/api/v1/client/client_srt_shruhi/rules?pin=2026"
    )
    assert not _is_seeder_blocked(response)


def test_the_meta_pages_route_is_not_blocked(production_client):
    response = production_client.get(
        "/api/v1/client/client_srt_shruhi/meta-pages?pin=2026"
    )
    assert not _is_seeder_blocked(response)


def test_no_handler_calls_the_seeder_directly():
    """The seeder must only be reached through the safe wrapper."""
    source = (ROOT / "engine" / "subscription_routes.py").read_text(
        encoding="utf-8"
    )
    lines = source.splitlines()
    direct = []
    for number, line in enumerate(lines, start=1):
        if "ensure_shruhi_surat_pro_client()" not in line:
            continue
        # The definition of the wrapper and its single call inside the
        # wrapper are allowed.
        if "async def " in line:
            continue
        if "await ensure_shruhi_surat_pro_client()" in line:
            continue
        direct.append((number, line.strip()))

    assert not direct, (
        "the seeder is called directly: "
        + "; ".join(f"line {n}: {t}" for n, t in direct)
    )


def test_roi_defense_calculator_route(production_client):
    """Asserts that the ROI defense calculator calculates protected metrics accurately."""
    resp = production_client.get(
        "/api/v1/roi-defense/calculate",
        params={
            "ad_spend": 100000,
            "inbound_comments": 1000,
            "average_order_value": 50000,
            "tier_cost": 29999,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    metrics = data["metrics"]
    assert metrics["shielded_poaching_leads"] == 180
    assert metrics["estimated_reclaimed_orders"] == 25
    assert metrics["monthly_reclaimed_revenue"] == 1250000.0
    assert metrics["roi_multiplier"] == 41.7
    assert metrics["average_reaction_latency_seconds"] == 0.048
