"""
WhatsApp inbound webhook tests.

Two properties matter more than the happy path:

  1. A wrong verify token must not echo the challenge, or anyone could claim
     the endpoint.
  2. Meta retries a delivery until it gets a 2xx. Without dedupe a retry
     creates a second Lead for one enquiry and inflates the funnel.
"""

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from engine.database import sync_session  # noqa: E402
from engine.models_sqlalchemy import Lead  # noqa: E402
from engine.whatsapp_webhook import (  # noqa: E402
    InboundMessage, parse_payload,
)

TOKEN = "test-verify-token"


@pytest.fixture
def client(monkeypatch):
    from fastapi.testclient import TestClient

    import engine.whatsapp_webhook as wh

    monkeypatch.setattr(wh, "_verify_token", lambda: TOKEN)
    return TestClient(wh.router and _app_for(wh))


def _app_for(wh):
    """Mount only the webhook router, so tests do not pull in the whole app."""
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(wh.router)
    return app


@pytest.fixture
def session():
    s = sync_session()
    InboundMessage.__table__.create(bind=s.get_bind(), checkfirst=True)
    for model in (InboundMessage, Lead):
        s.query(model).delete()
    s.commit()
    yield s
    s.close()


def _payload(msg_id="wamid.123", phone="919876543210", body="Do you have 5XL?"):
    return {
        "object": "whatsapp_business_account",
        "entry": [{
            "id": "0", "changes": [{
                "field": "messages",
                "value": {
                    "messaging_product": "whatsapp",
                    "contacts": [{
                        "profile": {"name": "Priya"},
                        "wa_id": phone,
                    }],
                    "messages": [{
                        "id": msg_id,
                        "from": phone,
                        "type": "text",
                        "timestamp": "1767225600",
                        "text": {"body": body},
                    }],
                },
            }],
        }],
    }


# ---------------------------------------------------------------------------
# Verification handshake
# ---------------------------------------------------------------------------


def test_correct_token_returns_challenge(client):
    r = client.get("/api/v1/whatsapp/webhook", params={
        "hub.mode": "subscribe",
        "hub.verify_token": TOKEN,
        "hub.challenge": "3141592",
    })
    assert r.status_code == 200
    assert r.text == "3141592"


def test_wrong_token_is_refused_and_challenge_not_echoed(client):
    r = client.get("/api/v1/whatsapp/webhook", params={
        "hub.mode": "subscribe",
        "hub.verify_token": "not-the-token",
        "hub.challenge": "3141592",
    })
    assert r.status_code == 403
    assert "3141592" not in r.text


def test_wrong_mode_is_refused(client):
    r = client.get("/api/v1/whatsapp/webhook", params={
        "hub.mode": "unsubscribe",
        "hub.verify_token": TOKEN,
        "hub.challenge": "3141592",
    })
    assert r.status_code == 403


def test_unconfigured_verification_refuses_rather_than_accepting(client):
    from fastapi.testclient import TestClient

    import engine.whatsapp_webhook as wh

    original = wh._verify_token
    wh._verify_token = lambda: ""
    try:
        r = TestClient(_app_for(wh)).get("/api/v1/whatsapp/webhook", params={
            "hub.mode": "subscribe",
            "hub.verify_token": "",
            "hub.challenge": "3141592",
        })
        # Without a configured token the endpoint must not verify anyone.
        assert r.status_code == 503
        assert "3141592" not in r.text
    finally:
        wh._verify_token = original


# ---------------------------------------------------------------------------
# Payload parsing
# ---------------------------------------------------------------------------


def test_parse_flattens_meta_envelope():
    msgs = parse_payload(_payload())
    assert len(msgs) == 1
    assert msgs[0]["from_phone"] == "919876543210"
    assert msgs[0]["body"] == "Do you have 5XL?"
    assert msgs[0]["profile_name"] == "Priya"
    assert msgs[0]["message_type"] == "text"


def test_status_callbacks_are_ignored():
    """A status update is not a conversation and must not become a lead."""
    payload = {"entry": [{"changes": [{
        "field": "messages",
        "value": {"statuses": [{"id": "x", "status": "delivered"}]},
    }]}]}
    assert parse_payload(payload) == []


def test_empty_payload_is_tolerated():
    assert parse_payload({}) == []
    assert parse_payload({"entry": []}) == []
    assert parse_payload({"entry": [{"changes": []}]}) == []


def test_messages_without_an_id_are_dropped():
    payload = _payload()
    payload["entry"][0]["changes"][0]["value"]["messages"][0].pop("id")
    assert parse_payload(payload) == []


def test_multiple_messages_are_all_returned():
    payload = _payload()
    msgs = payload["entry"][0]["changes"][0]["value"]["messages"]
    second = dict(msgs[0])
    second["id"] = "wamid.456"
    second["from"] = "919111111111"
    payload["entry"][0]["changes"][0]["value"]["messages"] = [msgs[0], second]
    parsed = parse_payload(payload)
    assert len(parsed) == 2
    assert {m["from_phone"] for m in parsed} == {"919876543210", "919111111111"}


# ---------------------------------------------------------------------------
# Ingestion and dedupe
# ---------------------------------------------------------------------------


def test_inbound_message_creates_a_lead(client, session):
    r = client.post("/api/v1/whatsapp/webhook", json=_payload())
    assert r.status_code == 200
    assert r.json()["stored"] == 1
    session.expire_all()

    lead = session.query(Lead).filter(
        Lead.phone == "919876543210"
    ).first()
    assert lead is not None, "the enquiry did not become a lead"
    assert lead.source == "whatsapp_inbound"
    assert lead.name == "Priya"


def test_duplicate_delivery_does_not_create_a_second_lead(client, session):
    """Meta retries until it gets a 2xx. A retry must be a no-op."""
    client.post("/api/v1/whatsapp/webhook", json=_payload())
    r2 = client.post("/api/v1/whatsapp/webhook", json=_payload())
    session.expire_all()

    assert r2.json()["duplicates"] == 1
    assert r2.json()["stored"] == 0
    assert session.query(Lead).filter(
        Lead.phone == "919876543210"
    ).count() == 1


def test_repeat_from_same_number_reuses_the_lead(client, session):
    """A second message from the same number updates rather than duplicates."""
    client.post("/api/v1/whatsapp/webhook", json=_payload(
        msg_id="wamid.1", body="First enquiry"))
    client.post("/api/v1/whatsapp/webhook", json=_payload(
        msg_id="wamid.2", body="Second enquiry"))
    session.expire_all()

    assert session.query(Lead).filter(
        Lead.phone == "919876543210"
    ).count() == 1
    assert session.query(InboundMessage).count() == 2


def test_status_callback_post_is_acknowledged_not_stored(client, session):
    payload = {"entry": [{"changes": [{
        "field": "messages",
        "value": {"statuses": [{"id": "x", "status": "read"}]},
    }]}]}
    r = client.post("/api/v1/whatsapp/webhook", json=payload)
    assert r.status_code == 200
    assert r.json()["received"] == 0
    session.expire_all()
    assert session.query(InboundMessage).count() == 0


def test_malformed_json_is_rejected(client):
    r = client.post(
        "/api/v1/whatsapp/webhook",
        content=b"not json",
        headers={"Content-Type": "application/json"},
    )
    assert r.status_code == 400


def test_recent_endpoint_lists_stored_messages(client, session):
    client.post("/api/v1/whatsapp/webhook", json=_payload())
    r = client.get("/api/v1/whatsapp/inbound/recent")
    assert r.status_code == 200
    body = r.json()
    assert body["count"] == 1
    assert body["messages"][0]["from_phone"] == "919876543210"
