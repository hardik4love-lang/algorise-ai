"""
Enquiry-to-comment tracking.

The webhook captures an inbound enquiry as a Lead, but without a link back
to the comment that produced it. Attribution therefore relied on the phone
number matching, which fails whenever a buyer clicks a link and messages
from a different number, or simply does not comment first.

WhatsApp Business deep links accept only `?text=`, so a tracking code has to
travel inside the prefilled message. A short opaque code is appended to it,
and the inbound webhook parses the code back out.

Why an opaque code rather than the raw Meta comment id:
  * Meta's comment id embeds the post id and is long enough to make the
    prefilled message unreadable for a buyer.
  * It would expose Meta's internal identifiers to every recipient.
  * A code can be revoked independently if a link is ever shared publicly.
"""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
)

from engine.models_sqlalchemy import Base

# Buyers retype the reference, often in lowercase, so the prefix is matched
# case-insensitively while the body stays hex-only. The earlier version was
# fully IGNORECASE with a generic [A-Z0-9]{6,10} body, which matched
# "#fashion" in an ordinary message; requiring the AG prefix and hex digits
# keeps ordinary hashtags from parsing as a code.
CODE_RE = re.compile(r"#\s?([Aa][Gg][0-9A-Fa-f]{4,8})\b")

CODE_PREFIX = "AG"


class EnquiryTracking(Base):
    """Maps an opaque tracking code to the comment that produced it."""

    __tablename__ = "enquiry_tracking"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(12), unique=True, index=True, nullable=False)
    comment_id = Column(String(128), index=True, nullable=False)
    client_id = Column(String(64), index=True)
    page_id = Column(String(64))
    lead_id = Column(Integer, index=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    converted_at = Column(DateTime(timezone=True))


def make_code(comment_id: str, page_id: str = "") -> str:
    """Deterministic, short, opaque code for a comment.

    Deterministic so a retried reply produces the same code rather than a
    second tracking row for the same comment.

    Uses SHA-256 rather than BLAKE2. blake2s aborts the interpreter with an
    illegal-instruction fault on hosts without SSE4.1, which would take the
    scheduler down rather than raise. Hash choice here is a portability
    constraint, not a preference.
    """
    material = f"{page_id}|{comment_id}".encode("utf-8")
    digest = hashlib.sha256(material).hexdigest().upper()
    return f"{CODE_PREFIX}{digest}"[:10]


def embed_code(prefill_text: str, code: str) -> str:
    """Append the code to a prefilled WhatsApp message.

    Kept short and at the end so a buyer reading the message sees the offer
    first. The prefix is a bare marker rather than anything resembling a
    campaign identifier.
    """
    return f"{prefill_text}\n\nRef #{code}"


def extract_code(message_body: Optional[str]) -> Optional[str]:
    """Pull a tracking code out of an inbound message.

    Returns the code upper-cased, or None. A buyer who deletes the reference
    line simply yields None; that is a missing attribution, not an error.
    """
    if not message_body:
        return None
    m = CODE_RE.search(message_body)
    return m.group(1).upper() if m else None


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------


def ensure_table(session) -> None:
    EnquiryTracking.__table__.create(bind=session.get_bind(), checkfirst=True)


def register_comment(
    comment_id: str,
    page_id: str = "",
    client_id: Optional[str] = None,
) -> str:
    """Record a comment's code. Idempotent per comment."""
    from engine.database import sync_session

    session = sync_session()
    try:
        ensure_table(session)
        existing = (
            session.query(EnquiryTracking)
            .filter(
                EnquiryTracking.comment_id == comment_id,
                EnquiryTracking.page_id == (page_id or ""),
            )
            .first()
        )
        if existing is not None:
            return existing.code

        code = make_code(comment_id, page_id)
        session.add(
            EnquiryTracking(
                code=code,
                comment_id=comment_id,
                page_id=page_id or None,
                client_id=client_id,
            )
        )
        session.commit()
        return code
    finally:
        session.close()


def resolve(code: Optional[str], session=None) -> Optional[dict]:
    """Resolve a code back to the originating comment and lead.

    Accepts an open session so a caller inside a transaction reuses it.
    Opening a second connection while the first holds a write lock produces
    "database is locked" on SQLite, which is what happened when the webhook
    resolved a code using its own session.
    """
    if not code:
        return None

    owned = session is None
    if owned:
        from engine.database import sync_session

        session = sync_session()
    try:
        ensure_table(session)
        row = (
            session.query(EnquiryTracking)
            .filter(EnquiryTracking.code == code.upper())
            .first()
        )
        if row is None:
            return None
        return {
            "code": row.code,
            "comment_id": row.comment_id,
            "page_id": row.page_id,
            "client_id": row.client_id,
            "lead_id": row.lead_id,
            "converted_at": row.converted_at.isoformat()
            if row.converted_at else None,
        }
    finally:
        if owned:
            session.close()


def attach_lead(code: str, lead_id: int, session=None) -> bool:
    """Record that an enquiry carrying this code became this lead.

    This is the join that makes the funnel honest: the enquiry is now tied
    to the comment, not merely present in the database.

    Accepts an open session so it joins the caller's transaction rather
    than deadlocking against it.
    """
    owned = session is None
    if owned:
        from engine.database import sync_session

        session = sync_session()
    try:
        ensure_table(session)
        row = (
            session.query(EnquiryTracking)
            .filter(EnquiryTracking.code == code.upper())
            .first()
        )
        if row is None:
            return False
        if row.lead_id is None:
            row.lead_id = lead_id
            row.converted_at = datetime.now(timezone.utc)
            session.commit()
        return True
    finally:
        if owned:
            session.close()
