"""Tests for the pending-outcome queue and the outcome-recording contract."""

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from engine.database import sync_session  # noqa: E402
from engine.enquiry_tracking import EnquiryTracking, ensure_table  # noqa: E402
from engine.models_sqlalchemy import Lead  # noqa: E402
from engine.whatsapp_webhook import InboundMessage, ensure_inbound_table  # noqa: E402


@pytest.fixture
def client():
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    import engine.attribution_routes as ar

    s = sync_session()
    ensure_table(s)
    ensure_inbound_table(s)
    for model in (EnquiryTracking, InboundMessage, Lead, ar.CommentOutcome):
        s.query(model).delete()
    s.commit()
    s.close()

    app = FastAPI()
    app.include_router(ar.router)
    return TestClient(app)


def _inbound(s, msg_id, phone="919876543210", comment_id=None):
    s.add(InboundMessage(
        wa_message_id=msg_id, from_phone=phone, body="Do you have 5XL?",
        profile_name="Priya", lead_id=None, tracked_comment_id=comment_id,
    ))
    s.commit()


def test_pending_lists_enquiries_with_no_outcome(client):
    from engine.database import sync_session

    s = sync_session()
    _inbound(s, "wamid-1")
    _inbound(s, "wamid-2")
    s.close()

    body = client.get("/api/v1/attribution/pending").json()
    assert body["count"] == 2
    assert {e["wa_message_id"] for e in body["enquiries"]} == {"wamid-1", "wamid-2"}


def test_recording_an_outcome_removes_it_from_pending(client):
    from engine.database import sync_session

    s = sync_session()
    _inbound(s, "wamid-1")
    s.close()

    client.post("/api/v1/attribution/outcome", json={
        "comment_id": "wamid-1", "outcome": "converted",
    })
    body = client.get("/api/v1/attribution/pending").json()
    assert body["count"] == 0, "a decided enquiry is still queued for triage"


def test_attributed_enquiries_are_labelled(client):
    from engine.database import sync_session

    s = sync_session()
    _inbound(s, "wamid-attributed", comment_id="cmt-99")
    _inbound(s, "wamid-orphan")
    s.close()

    body = client.get("/api/v1/attribution/pending").json()
    by_id = {e["wa_message_id"]: e for e in body["enquiries"]}
    assert by_id["wamid-attributed"]["tracked_comment_id"] == "cmt-99"
    assert by_id["wamid-orphan"]["tracked_comment_id"] is None


def test_pending_explains_that_conversion_is_human_recorded(client):
    body = client.get("/api/v1/attribution/pending").json()
    assert "never inferred" in body["note"]


def test_outcome_is_idempotent_per_enquiry(client):
    from engine.database import sync_session

    s = sync_session()
    _inbound(s, "wamid-1")
    s.close()

    client.post("/api/v1/attribution/outcome", json={
        "comment_id": "wamid-1", "outcome": "lost",
    })
    client.post("/api/v1/attribution/outcome", json={
        "comment_id": "wamid-1", "outcome": "converted",
        "outcome_value_inr": 5000.0,
    })

    s = sync_session()
    import engine.attribution_routes as ar

    rows = s.query(ar.CommentOutcome).filter(
        ar.CommentOutcome.comment_id == "wamid-1"
    ).all()
    assert len(rows) == 1, "recording twice double-counted the enquiry"
    assert rows[0].outcome == "converted", "the later record should win"
    assert rows[0].outcome_value_inr == 5000.0
    s.close()


def test_invalid_outcome_is_rejected(client):
    r = client.post("/api/v1/attribution/outcome", json={
        "comment_id": "wamid-1", "outcome": "definitely_won",
    })
    assert r.status_code == 422


def test_pending_does_not_count_pending_as_lost_or_converted(client):
    """A pending enquiry is undecided, and must not inflate either side."""
    from engine.database import sync_session

    s = sync_session()
    _inbound(s, "wamid-1")
    _inbound(s, "wamid-2")
    s.close()

    client.post("/api/v1/attribution/outcome", json={
        "comment_id": "wamid-1", "outcome": "converted",
        "outcome_value_inr": 1000.0,
    })
    client.post("/api/v1/attribution/outcome", json={
        "comment_id": "wamid-2", "outcome": "pending",
    })

    funnel = client.get("/api/v1/attribution/funnel").json()
    assert funnel["funnel"]["converted"] == 1
    assert funnel["funnel"]["lost"] == 0
    assert funnel["rates"]["conversion_rate"] == pytest.approx(1.0), (
        "pending must be excluded from the denominator, not counted as lost"
    )
