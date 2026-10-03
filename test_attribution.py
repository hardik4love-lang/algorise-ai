"""
Attribution tests.

The behaviour that matters most is what the funnel does with NO outcome
data. A funnel that reported conversions from inferred data would be the
same defect as the fabricated scheduler telemetry, in a more valuable place.
"""

import os
import sys
from datetime import date
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from engine.attribution import CommentOutcome, build_funnel  # noqa: E402
from engine.database import sync_session  # noqa: E402
from engine.models_sqlalchemy import (  # noqa: E402
    Base, BotExecution, Client, Lead, OutreachMessage,
)


@pytest.fixture
def session():
    s = sync_session()
    CommentOutcome.__table__.create(bind=s.get_bind(), checkfirst=True)
    # Order matters: children before parents.
    for model in (CommentOutcome, BotExecution, Lead, Client):
        s.query(model).delete()
    s.commit()
    yield s
    s.close()


def _client(s, cid="c1"):
    # api_key_hash is UNIQUE, so each client needs a distinct value.
    c = Client(
        id=cid, name=f"Merchant {cid}", tier="pro",
        api_key_hash=(cid * 64)[:64],
    )
    s.add(c)
    s.commit()
    return c


def _exec(s, client_id="c1", payload="reply_comment", data=None,
          success=True, task_id="t1"):
    """Add a BotExecution. latency_ms is NOT NULL, so it is always set."""
    s.add(BotExecution(
        task_id=task_id,
        bot_id=f"meta_{payload}",
        client_id=client_id,
        input_payload=payload,
        output_data=data or {},
        success=success,
        latency_ms=1.0,
    ))
    s.commit()


def test_funnel_on_empty_database_reports_zero_not_guessed(session):
    r = build_funnel(session)
    assert r["funnel"]["comments_replied"] == 0
    assert r["funnel"]["converted"] == 0
    # Every rate must be null, not zero and not a guess.
    for name, value in r["rates"].items():
        assert value is None, f"{name} was {value} on empty data"
    assert r["value"]["recorded_revenue_inr"] == 0.0


def test_executions_without_comment_id_are_ignored(session):
    """Health checks and tuning runs must not pollute the funnel."""
    _client(session)
    _exec(session, payload="reply_comment",
          data={"error": "no comment"}, success=False)

    r = build_funnel(session)
    assert r["funnel"]["comments_replied"] == 0
    assert r["coverage"]["executions_with_comment_id"] == 0


def test_funnel_counts_replies_and_leads(session):
    _client(session)
    _exec(session, data={"comment_id": "c-100", "reply_id": "r1"})
    session.add(Lead(
        client_id="c1", name="Buyer", phone="+919999999999",
        source="facebook_comment", status="new",
        fb_comment_id="c-100", qualification_score=80,
    ))
    session.commit()

    r = build_funnel(session)
    assert r["funnel"]["comments_replied"] == 1
    assert r["funnel"]["leads_captured"] == 1
    assert r["rates"]["reply_to_lead"] == pytest.approx(1.0)


def test_conversion_requires_a_recorded_outcome(session):
    """A lead with no recorded outcome must NOT count as converted."""
    _client(session)
    session.add(Lead(
        client_id="c1", name="Buyer", phone="+91", source="facebook_comment",
        status="new", fb_comment_id="c-200", qualification_score=90,
    ))
    session.commit()

    r = build_funnel(session)
    assert r["funnel"]["outcomes_recorded"] == 0
    assert r["funnel"]["converted"] == 0
    assert r["rates"]["conversion_rate"] is None


def test_recorded_outcome_produces_a_conversion_rate(session):
    _client(session)
    for cid in ("c-300", "c-301"):
        session.add(Lead(
            client_id="c1", name="B", phone="+91", source="facebook_comment",
            status="new", fb_comment_id=cid, qualification_score=80,
        ))
    session.add(CommentOutcome(
        comment_id="c-300", client_id="c1", outcome="converted",
        outcome_value_inr=45000.0, recorded_by="test",
    ))
    session.add(CommentOutcome(
        comment_id="c-301", client_id="c1", outcome="lost", recorded_by="test",
    ))
    session.commit()

    r = build_funnel(session)
    assert r["funnel"]["converted"] == 1
    assert r["funnel"]["lost"] == 1
    assert r["funnel"]["outcomes_recorded"] == 2
    assert r["rates"]["conversion_rate"] == pytest.approx(0.5)
    assert r["value"]["recorded_revenue_inr"] == pytest.approx(45000.0)
    assert r["value"]["average_deal_inr"] == pytest.approx(45000.0)


def test_funnel_is_scoped_to_a_client(session):
    _client(session, "c1")
    _client(session, "c2")
    _exec(session, "c1", data={"comment_id": "c-1"}, task_id="t1")
    _exec(session, "c2", data={"comment_id": "c-2"}, task_id="t2")

    assert build_funnel(session, "c1")["funnel"]["comments_replied"] == 1
    assert build_funnel(session, "c2")["funnel"]["comments_replied"] == 1
    assert build_funnel(session)["funnel"]["comments_replied"] == 2


def test_failed_executions_are_counted_separately(session):
    _client(session)
    _exec(session, data={"comment_id": "c-9"}, success=False)

    r = build_funnel(session)
    # A failed reply is not a reply, so it must not inflate the funnel.
    assert r["funnel"]["comments_replied"] == 0
    assert r["coverage"]["executions_with_comment_id"] == 1


def test_funnel_always_carries_its_caveats(session):
    r = build_funnel(session)
    assert len(r["notes"]) >= 3
    joined = " ".join(r["notes"]).lower()
    assert "merchant recorded" in joined
    assert "no rate is estimated" in joined