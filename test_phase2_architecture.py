"""
Unit and regression tests for Phase 2 Architectural Refactoring:
- REC-2.1: Bounded context domain services (client_billing, client_auth, client_agent_ops)
- REC-2.3: Unified bot polymorphism (BaseAlgoriseBot, HeroBotRunner, BotTask)
"""

import pytest
from fastapi import HTTPException

from engine.client_billing import PLAN_PRICING, resolve_plan_tier, get_tier_pricing
from engine.client_auth import hash_pin, verify_pin, verify_client_pin, verify_admin_key
from engine.client_agent_ops import (
    load_100_facebook_groups,
    evaluate_nlp_shield,
)
from engine.bots import BaseAlgoriseBot
from engine.hero_registry import HeroBotRunner
from engine.models import BotTask, BotResult


# ============================================================================
# 1. CLIENT BILLING DOMAIN SERVICE TESTS
# ============================================================================

def test_resolve_plan_tier():
    assert resolve_plan_tier("starter") == "starter"
    assert resolve_plan_tier("PRO") == "pro"
    assert resolve_plan_tier("Enterprise ") == "enterprise"
    assert resolve_plan_tier(None) == "pro"
    assert resolve_plan_tier("nonexistent_tier") == "pro"


def test_get_tier_pricing_calculations():
    pro_pricing = get_tier_pricing("pro")
    assert pro_pricing["tier_key"] == "pro"
    assert pro_pricing["monthly_price"] == 29999.0
    assert pro_pricing["setup_fee"] == 29999.0
    assert pro_pricing["advance_amount"] == pytest.approx(5999.8, rel=1e-3)
    assert pro_pricing["advance_pct"] == 0.20

    starter_pricing = get_tier_pricing("starter")
    assert starter_pricing["monthly_price"] == 12499.0
    assert starter_pricing["advance_amount"] == pytest.approx(2499.8, rel=1e-3)

    enterprise_pricing = get_tier_pricing("enterprise")
    assert enterprise_pricing["monthly_price"] == 64999.0
    assert enterprise_pricing["advance_amount"] == pytest.approx(12999.8, rel=1e-3)


# ============================================================================
# 2. CLIENT AUTH DOMAIN SERVICE TESTS
# ============================================================================

def test_hash_pin_and_verify():
    pin = "2026"
    hashed = hash_pin(pin)
    assert isinstance(hashed, str)
    assert len(hashed) == 64  # SHA-256 hex string

    assert verify_pin(hashed, "2026") is True
    assert verify_pin(hashed, "1234") is False
    assert verify_pin(None, "anything") is True


def test_verify_client_pin_enforcement():
    hashed = hash_pin("2026")

    # Should pass without exception when correct
    verify_client_pin(hashed, "2026", is_production=False)
    verify_client_pin(hashed, "2026", is_production=True)

    # Should raise 401 when incorrect
    with pytest.raises(HTTPException) as exc_info:
        verify_client_pin(hashed, "9999", is_production=False)
    assert exc_info.value.status_code == 401

    # Should raise 401 when pin missing in production
    with pytest.raises(HTTPException) as exc_info:
        verify_client_pin(hashed, None, is_production=True)
    assert exc_info.value.status_code == 401
    assert "Valid 4-digit PIN required" in exc_info.value.detail


def test_verify_admin_key():
    secret = "test_admin_secret_9981"

    # Should pass with valid secret
    verify_admin_key(secret, secret)

    # Should raise 403 on invalid key
    with pytest.raises(HTTPException) as exc_info:
        verify_admin_key("wrong_key", secret)
    assert exc_info.value.status_code == 403

    with pytest.raises(HTTPException) as exc_info:
        verify_admin_key(None, secret)
    assert exc_info.value.status_code == 403


# ============================================================================
# 3. CLIENT AGENT OPERATIONS TESTS
# ============================================================================

def test_load_100_facebook_groups():
    data = load_100_facebook_groups()
    assert isinstance(data, dict)
    assert "groups" in data
    assert len(data["groups"]) >= 100


def test_evaluate_nlp_shield_trilingual_and_sub_005s():
    # Test Gujarati detection & phone shielding
    res_gu = evaluate_nlp_shield(
        comment_text="નમસ્તે, કુરતી ભાવ શું છે? મારો નંબર 9825411209 છે",
        buyer_name="Anjali Patel",
        dispatch_telegram=False,
    )
    assert res_gu["shield_triggered"] is True
    assert res_gu["extracted_phone"] == "9825411209"
    assert "Gujarati" in res_gu["detected_language"]
    assert res_gu["latency_seconds"] < 0.05
    assert "પ્રાઈવસી" in res_gu["public_comment_reply"]

    # Test Hindi detection
    res_hi = evaluate_nlp_shield(
        comment_text="नमस्ते Tejal suit का क्या rate है? WhatsApp करो 9820194822",
        buyer_name="Sunita Sharma",
        dispatch_telegram=False,
    )
    assert res_hi["shield_triggered"] is True
    assert res_hi["extracted_phone"] == "9820194822"
    assert "Hindi" in res_hi["detected_language"]
    assert "TEJAL" in res_hi["matched_outfit"]
    assert res_hi["latency_seconds"] < 0.05

    # Test English without phone
    res_en = evaluate_nlp_shield(
        comment_text="Hi, what is the price for Kavya suit?",
        buyer_name="Pooja Rao",
        dispatch_telegram=False,
    )
    assert res_en["shield_triggered"] is False
    assert res_en["extracted_phone"] is None
    assert res_en["detected_language"] == "English"
    assert "KAVYA" in res_en["matched_outfit"]


# ============================================================================
# 4. UNIFIED BOT POLYMORPHISM TESTS (REC-2.3)
# ============================================================================

def test_hero_bot_runner_is_subclass_of_base_bot():
    assert issubclass(HeroBotRunner, BaseAlgoriseBot)


def test_hero_bot_runner_executes_via_bot_task():
    runner = HeroBotRunner()
    task = BotTask(
        bot_name="agroyield",
        input_payload={"query": "predict yield", "ndvi_index": 0.81},
    )
    result = runner.execute(task)

    assert isinstance(result, BotResult)
    assert result.success is True
    assert result.bot_name == "Algorise AgroYield AI"
    assert result.data["confidence_score"] > 0.9
    assert result.latency_ms >= 0


def test_base_algorise_bot_run_helper():
    from engine.bots import NexusBot
    nexus = NexusBot()
    res_nexus = nexus.run(input_payload={"query": "order status for item", "customer_id": "cust_123"})
    assert isinstance(res_nexus, BotResult)
    assert res_nexus.success is True
    assert res_nexus.bot_name == "nexus"
    assert res_nexus.data["intent"] == "ORDER_TRACKING"

    runner = HeroBotRunner()
    result = runner.run(
        input_payload={"query": "precision irrigation", "soil_moisture": 42},
        bot_name="hydrosense",
    )
    assert isinstance(result, BotResult)
    assert result.success is True
    assert result.bot_name == "Algorise HydroSense Closed-Loop"


# ============================================================================
# 5. IDEMPOTENCY KEY ENFORCEMENT TESTS (REC-3.2)
# ============================================================================

def test_idempotent_subscription_replay():
    from fastapi.testclient import TestClient
    from engine.main import app

    client = TestClient(app)
    idem_key = "test_idem_sub_key_9981"
    sub_payload = {
        "business_name": "Idempotent Surat Textiles",
        "full_name": "Ramesh Patel",
        "phone": "+91 99999 11111",
        "plan_tier": "starter",
    }

    # 1. First invocation: creates new subscription
    res1 = client.post("/api/v1/subscribe", json=sub_payload, headers={"X-Idempotency-Key": idem_key})
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["success"] is True
    client_id1 = data1["client_id"]
    assert "idempotent_replay" not in data1 or not data1["idempotent_replay"]

    # 2. Second invocation with exact same key & payload: returns cached replay
    res2 = client.post("/api/v1/subscribe", json=sub_payload, headers={"X-Idempotency-Key": idem_key})
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["client_id"] == client_id1  # Must return identical client_id, not create a new one!
    assert data2.get("idempotent_replay") is True

    # 3. Third invocation with same key but differing payload: returns 422 Unprocessable Entity
    altered_payload = dict(sub_payload)
    altered_payload["plan_tier"] = "enterprise"
    res3 = client.post("/api/v1/subscribe", json=altered_payload, headers={"X-Idempotency-Key": idem_key})
    assert res3.status_code == 422

