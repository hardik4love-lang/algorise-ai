"""
Enquiry tracking tests.

The round-trip test is the one that matters: a comment produces a code, the
buyer's reply carries it, the inbound message resolves it back to the
originating comment. Without that join the funnel stops at "a lead exists"
and cannot say which comment produced revenue.
"""

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from engine.database import sync_session  # noqa: E402
from engine.enquiry_tracking import (  # noqa: E402
    EnquiryTracking,
    attach_lead,
    embed_code,
    ensure_table,
    extract_code,
    make_code,
    register_comment,
    resolve,
)
from engine.models_sqlalchemy import Lead  # noqa: E402
from engine.whatsapp_webhook import InboundMessage  # noqa: E402


@pytest.fixture
def session():
    """Clean state, then close.

    Deliberately does not yield an open session: the tracking helpers open
    their own per call, and holding a second connection open across those
    calls deadlocks SQLite. Tests re-open with sync_session() when they need
    to assert.
    """
    s = sync_session()
    ensure_table(s)
    InboundMessage.__table__.create(bind=s.get_bind(), checkfirst=True)
    for model in (EnquiryTracking, InboundMessage, Lead):
        s.query(model).delete()
    s.commit()
    s.close()

    yield sync_session()

    # Nothing to close; the module owns its own sessions.


def _fresh():
    return sync_session()


# ---------------------------------------------------------------------------
# Code generation
# ---------------------------------------------------------------------------


def test_code_is_deterministic():
    """A retried reply must not create a second tracking row."""
    assert make_code("123_456", "page1") == make_code("123_456", "page1")


def test_code_differs_per_comment_and_page():
    assert make_code("123_456", "p1") != make_code("123_457", "p1")
    assert make_code("123_456", "p1") != make_code("123_456", "p2")


def test_code_is_opaque_and_short():
    """The code travels in a message a buyer reads."""
    c = make_code("1234567890_9876543210", "page")
    assert 6 <= len(c) <= 12
    assert c.isalnum()


def test_code_does_not_leak_the_comment_id():
    c = make_code("1234567890_9876543210", "page")
    assert "1234" not in c
    assert "9876" not in c


# ---------------------------------------------------------------------------
# Embed and extract
# ---------------------------------------------------------------------------


def test_embed_preserves_the_offer_text():
    offer = "Hi! I saw your post and want to order the B-2876 (₹1,450)."
    out = embed_code(offer, "AG1A2B3C4D")
    assert out.startswith(offer)
    assert "AG1A2B3C4D" in out


def test_round_trip_through_embed_and_extract():
    offer = "Do you have 5XL?"
    code = make_code("999_888", "page")
    assert extract_code(embed_code(offer, code)) == code


def test_extract_handles_missing_and_malformed_input():
    assert extract_code(None) is None
    assert extract_code("") is None
    assert extract_code("no reference here at all") is None
    assert extract_code("Ref #SHORT") is None


def test_extract_survives_line_wrapping():
    """WhatsApp wraps long messages; a naive parser would miss the code."""
    assert extract_code("Namaste ji,\n\nRef #AG1A2B3C4D\n\nThank you") == "AG1A2B3C4D"


def test_extract_is_case_insensitive():
    assert extract_code("ref #ag1a2b3c4d") == "AG1A2B3C4D"


def test_extract_ignores_other_hashtags():
    """A buyer writing '#fashion' must not be parsed as a code."""
    assert extract_code("I love this #fashion #sale") is None


# ---------------------------------------------------------------------------
# Persistence and the round trip
# ---------------------------------------------------------------------------


def test_register_then_resolve(session):
    code = register_comment("cmt-555", page_id="pg-1", client_id="c1")
    found = resolve(code)
    assert found is not None
    assert found["comment_id"] == "cmt-555"
    assert found["page_id"] == "pg-1"
    assert found["client_id"] == "c1"


def test_register_is_idempotent_per_comment(session):
    a = register_comment("cmt-666", page_id="pg-1")
    b = register_comment("cmt-666", page_id="pg-1")
    assert a == b
    chk = _fresh()
    try:
        assert chk.query(EnquiryTracking).count() == 1
    finally:
        chk.close()


def test_resolve_unknown_code_returns_none(session):
    assert resolve("AGZZZZZZZZ") is None
    assert resolve(None) is None


def test_attach_lead_links_the_enquiry(session):
    code = register_comment("cmt-777", page_id="pg-1")
    s = _fresh()
    lead = Lead(client_id="c1", name="Buyer", phone="919876543210",
                source="whatsapp_inbound", status="new",
                qualification_score=0)
    s.add(lead)
    s.commit()
    lead_id = lead.id
    s.close()

    assert attach_lead(code, lead_id) is True
    found = resolve(code)
    assert found["lead_id"] == lead_id
    assert found["converted_at"] is not None, "the link time must be recorded"


def test_attach_unknown_code_fails_without_raising(session):
    assert attach_lead("AGNOSUCH", 1) is False


def test_end_to_end_comment_to_enquiry(session):
    """comment -> reply link -> buyer clicks -> enquiry resolves back.

    This is the join that lets the funnel attribute revenue to a comment.
    """
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    import engine.whatsapp_webhook as wh

    code = register_comment("cmt-e2e", page_id="pg-1", client_id="c1")
    offer = "I want the B-2876 in 5XL."

    app = FastAPI()
    app.include_router(wh.router)
    client = TestClient(app)

    payload = {
        "entry": [{"changes": [{
            "field": "messages",
            "value": {
                "contacts": [{"profile": {"name": "Priya"},
                              "wa_id": "919876543210"}],
                "messages": [{
                    "id": "wamid.e2e",
                    "from": "919876543210",
                    "type": "text",
                    "timestamp": "1767225600",
                    "text": {"body": embed_code(offer, code)},
                }],
            },
        }]}]
    }

    r = client.post("/api/v1/whatsapp/webhook", json=payload)
    assert r.json()["stored"] == 1

    msg = _fresh().query(InboundMessage).first()
    assert msg is not None
    assert msg.tracked_code == code
    assert msg.tracked_comment_id == "cmt-e2e", (
        "the enquiry was not tied back to the comment that produced it"
    )
    assert msg.lead_id is not None

    # And the tracking row now points at the lead.
    found = resolve(code)
    assert found["lead_id"] == msg.lead_id


def test_enquiry_without_a_code_is_still_captured(session):
    """A buyer who deletes the reference line is a missing attribution, not a
    lost enquiry."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    import engine.whatsapp_webhook as wh

    app = FastAPI()
    app.include_router(wh.router)
    client = TestClient(app)

    payload = {
        "entry": [{"changes": [{
            "field": "messages",
            "value": {
                "contacts": [{"profile": {"name": "Anon"},
                              "wa_id": "919000000001"}],
                "messages": [{
                    "id": "wamid.nocode",
                    "from": "919000000001",
                    "type": "text",
                    "timestamp": "1767225600",
                    "text": {"body": "What is the price?"},
                }],
            },
        }]}]
    }

    r = client.post("/api/v1/whatsapp/webhook", json=payload)
    assert r.json()["stored"] == 1

    msg = _fresh().query(InboundMessage).first()
    assert msg is not None
    assert msg.tracked_code is None
    assert msg.tracked_comment_id is None
    assert msg.lead_id is not None, "the lead must still be created"


def test_unknown_code_does_not_break_ingestion(session):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    import engine.whatsapp_webhook as wh

    app = FastAPI()
    app.include_router(wh.router)
    client = TestClient(app)

    payload = {
        "entry": [{"changes": [{
            "field": "messages",
            "value": {
                "messages": [{
                    "id": "wamid.bad",
                    "from": "919000000002",
                    "type": "text",
                    "timestamp": "1767225600",
                    "text": {"body": "Hello, ref #AGZZZZZZZZ"},
                }],
            },
        }]}]
    }

    r = client.post("/api/v1/whatsapp/webhook", json=payload)
    assert r.json()["stored"] == 1
    msg = _fresh().query(InboundMessage).first()
    assert msg.tracked_comment_id is None
    assert msg.lead_id is not None
