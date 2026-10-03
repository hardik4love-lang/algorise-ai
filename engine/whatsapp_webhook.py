"""
WhatsApp Cloud API inbound webhook.

The service could send but never receive. Two consequences:

  1. An enquiry arriving on WhatsApp was invisible to the system. Only a
     browser polling could notice, so every enquiry required a portal to be
     open.
  2. The attribution funnel had no final hop. comment -> reply -> lead
     stopped at lead, because the enquiry that actually converted never
     entered the record.

This is the hop that turns a comment into a measurable outcome, so inbound
messages become Leads and OutreachMessages rather than being logged and
forgotten.

Meta's protocol is honoured exactly:
  GET  verify  -> hub.mode=subscribe, hub.verify_token, hub.challenge
  POST receive -> entry[].changes[].value.messages[]

The verify token is compared with a constant-time comparison, and the
challenge is only echoed for an exact token match.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from loguru import logger

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text

from engine.enquiry_tracking import attach_lead, extract_code, resolve
from engine.models_sqlalchemy import Base

router = APIRouter(prefix="/api/v1/whatsapp", tags=["whatsapp"])


# --- inbound dedupe ---------------------------------------------------------

class InboundMessage(Base):
    """A message received from WhatsApp, stored so a Meta retry is a no-op.

    Meta retries a webhook until it gets a 2xx. Without dedupe, a redelivery
    creates a second Lead for one real enquiry and inflates every count
    downstream.
    """

    __tablename__ = "whatsapp_inbound_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    wa_message_id = Column(String(128), unique=True, index=True, nullable=False)
    client_id = Column(String(64), index=True)
    from_phone = Column(String(32), index=True)
    profile_name = Column(String(200))
    body = Column(Text)
    message_type = Column(String(32))
    timestamp = Column(DateTime(timezone=True))
    lead_id = Column(Integer, index=True)
    # Opaque code from the prefilled WhatsApp link, and the comment it
    # resolved to. Null when the buyer removed the reference line or came
    # without one, which is a missing attribution rather than an error.
    tracked_code = Column(String(12), index=True)
    tracked_comment_id = Column(String(128), index=True)
    received_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


def ensure_inbound_table(session) -> None:
    """Create the inbound table, adding columns an older table lacks.

    create(checkfirst=True) does nothing when the table already exists, so a
    deployment that received a message before this table gained
    tracked_code/tracked_comment_id would fail every insert with "no column
    named tracked_code" — and the handler swallows that error and returns
    200, so enquiries would vanish without trace.

    SQLite cannot drop or retype columns, so adding the ones we introduced
    is the whole migration. A real Alembic revision is the long-term answer.
    """
    from sqlalchemy import inspect, text

    InboundMessage.__table__.create(bind=session.get_bind(), checkfirst=True)

    existing = {
        c["name"] for c in inspect(session.get_bind()).get_columns(
            InboundMessage.__tablename__
        )
    }
    added = []
    for col in InboundMessage.__table__.columns:
        if col.name in existing:
            continue
        ddl = (
            f"ALTER TABLE {InboundMessage.__tablename__} "
            f"ADD COLUMN {col.name} {col.type.compile(session.get_bind().dialect)}"
        )
        session.execute(text(ddl))
        added.append(col.name)
    if added:
        session.commit()
        logger.info("whatsapp inbound table migrated: added {}", str(added))


# --- verification -----------------------------------------------------------

def _verify_token() -> str:
    return os.getenv("WHATSAPP_VERIFY_TOKEN", "")


def _constant_time_equals(a: str, b: str) -> bool:
    return hmac.compare_digest(
        (a or "").encode("utf-8"), (b or "").encode("utf-8")
    )


@router.get("/webhook")
async def verify_webhook(request: Request) -> Any:
    """Meta's subscription handshake.

    Query parameters are read from the raw request rather than declared as
    FastAPI parameters. Meta sends the literal keys ``hub.mode``,
    ``hub.verify_token`` and ``hub.challenge``, which Python identifiers
    cannot express, so declaring them would bind the wrong names and the
    endpoint could never verify a real subscription.

    A wrong token yields 403 rather than echoing the challenge. Echoing it
    unconditionally would let anyone claim the endpoint.
    """
    expected = _verify_token()
    if not expected:
        logger.error(
            "WHATSAPP_VERIFY_TOKEN is not set; the webhook cannot verify"
        )
        return PlainTextResponse("verification not configured", status_code=503)

    params = request.query_params
    mode = params.get("hub.mode", "")
    supplied = params.get("hub.verify_token", "")
    challenge = params.get("hub.challenge", "")

    if mode == "subscribe" and _constant_time_equals(supplied, expected):
        return PlainTextResponse(challenge)

    logger.warning(
        f"webhook verification failed: mode={mode} "
        f"token_match={_constant_time_equals(supplied, expected)}"
    )
    return PlainTextResponse("forbidden", status_code=403)


# --- ingestion --------------------------------------------------------------

def parse_payload(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Flatten Meta's nested envelope into a list of messages.

    Returns only message entries. Status callbacks and template updates are
    deliberately ignored rather than misread as conversations.
    """
    out: list[dict[str, Any]] = []
    for entry in payload.get("entry", []) or []:
        for change in entry.get("changes", []) or []:
            value = change.get("value") or {}
            contacts = {
                c.get("wa_id"): c
                for c in value.get("contacts", []) or []
            }
            for msg in value.get("messages", []) or []:
                sender = msg.get("from", "")
                out.append({
                    "wa_message_id": msg.get("id", ""),
                    "from_phone": sender,
                    "profile_name": (
                        contacts.get(sender, {}).get("profile", {}).get("name")
                    ),
                    "body": (msg.get("text") or {}).get("body"),
                    "message_type": msg.get("type"),
                    "timestamp": msg.get("timestamp"),
                })
    return [m for m in out if m["wa_message_id"]]


def _default_client_id() -> str:
    """Which client an inbound message belongs to.

    Meta's webhook carries the business account, not the Algorise client, so
    with a single WhatsApp number the mapping is one-to-one. Overridable
    because a multi-tenant deployment will need a per-number mapping table.
    """
    return os.getenv("WHATSAPP_DEFAULT_CLIENT_ID", "unassigned")


def _upsert_lead(session, phone: str, name: str | None, body: str) -> int:
    """Create a Lead for an unknown number, or return the existing one."""
    from engine.models_sqlalchemy import Lead

    existing = (
        session.query(Lead)
        .filter(Lead.phone == phone)
        .first()
    )
    if existing is not None:
        return existing.id

    lead = Lead(
        # client_id is NOT NULL. Omitting it raised an IntegrityError that
        # the broad handler below swallowed, so the enquiry was acknowledged
        # and silently discarded.
        client_id=_default_client_id(),
        name=name or f"WhatsApp {phone[-4:]}",
        phone=phone,
        source="whatsapp_inbound",
        status="new",
        original_message=body[:2000] if body else None,
        qualification_score=0,
    )
    session.add(lead)
    session.flush()
    return lead.id


@router.post("/webhook")
async def receive_webhook(request: Request) -> Any:
    """Receive an inbound WhatsApp message and record it as a lead.

    Always returns 200 for a well-formed Meta delivery, even when the message
    cannot be stored. A 5xx makes Meta retry, and a message we already
    recorded would be duplicated on the retry unless dedupe holds.
    """
    try:
        payload = await request.json()
    except (json.JSONDecodeError, UnicodeDecodeError):
        logger.warning("webhook received a non-JSON body")
        return PlainTextResponse("bad request", status_code=400)

    messages = parse_payload(payload)
    if not messages:
        # Status callbacks and other non-message events. Acknowledge them.
        return JSONResponse({"received": 0, "stored": 0})

    from engine.database import sync_session

    session = sync_session()
    ensure_inbound_table(session)

    stored = 0
    duplicates = 0
    try:
        for msg in messages:
            already = (
                session.query(InboundMessage)
                .filter(
                    InboundMessage.wa_message_id == msg["wa_message_id"]
                )
                .first()
            )
            if already is not None:
                duplicates += 1
                continue

            phone = msg["from_phone"]
            lead_id = None
            if phone:
                try:
                    lead_id = _upsert_lead(
                        session, phone, msg.get("profile_name"),
                        msg.get("body") or "",
                    )
                except Exception as exc:  # noqa: BLE001
                    logger.error("could not create lead for {}: {}", str(phone), str(exc))
                    lead_id = None

            # Resolve the tracking code so the enquiry is tied to the comment
            # that produced it, not merely present in the database. This is
            # the join that makes the funnel honest.
            code = extract_code(msg.get("body"))
            tracked_comment = None
            if code:
                # Same session: opening a second connection here would
                # deadlock against the write this handler is mid-way through.
                tracked = resolve(code, session=session)
                if tracked:
                    tracked_comment = tracked["comment_id"]
                    if lead_id:
                        attach_lead(code, lead_id, session=session)
                else:
                    logger.info(
                        f"inbound enquiry carried an unknown code: {code}"
                    )

            ts = None
            if msg.get("timestamp"):
                try:
                    ts = datetime.fromtimestamp(
                        int(msg["timestamp"]), tz=timezone.utc
                    )
                except (ValueError, TypeError, OSError):
                    ts = None

            session.add(
                InboundMessage(
                    wa_message_id=msg["wa_message_id"],
                    client_id=None,
                    from_phone=phone,
                    profile_name=msg.get("profile_name"),
                    body=msg.get("body"),
                    message_type=msg.get("message_type"),
                    timestamp=ts,
                    lead_id=lead_id,
                    tracked_code=code,
                    tracked_comment_id=tracked_comment,
                )
            )
            stored += 1

        session.commit()
    except Exception as exc:  # noqa: BLE001
        session.rollback()
        logger.error("webhook store failed: {}: {}", str(type(exc).__name__), str(exc))
        # Still 200: the message is logged, and Meta retrying would not help.
    finally:
        session.close()

    logger.info(
        "whatsapp webhook: %d received, %d stored, %d duplicate",
        len(messages), stored, duplicates,
    )
    return JSONResponse({
        "received": len(messages),
        "stored": stored,
        "duplicates": duplicates,
    })


@router.get("/inbound/recent")
async def recent_inbound(limit: int = 50) -> Any:
    """Recent inbound messages, newest first."""
    from engine.database import sync_session

    session = sync_session()
    try:
        ensure_inbound_table(session)
        rows = (
            session.query(InboundMessage)
            .order_by(InboundMessage.id.desc())
            .limit(min(limit, 200))
            .all()
        )
        return {
            "count": len(rows),
            "messages": [
                {
                    "wa_message_id": r.wa_message_id,
                    "from_phone": r.from_phone,
                    "profile_name": r.profile_name,
                    "body": r.body,
                    "message_type": r.message_type,
                    "timestamp": r.timestamp.isoformat() if r.timestamp else None,
                    "lead_id": r.lead_id,
                    "received_at": r.received_at.isoformat()
                    if r.received_at else None,
                }
                for r in rows
            ],
        }
    finally:
        session.close()