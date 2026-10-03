"""
Attribution: the comment-to-revenue chain.

The three tables that hold the data were never joined:

  BotExecution     one row per Meta operation, output_data carries comment_id
  Lead             keyed by fb_comment_id
  OutreachMessage  keyed by lead_id

Without the join the product can only report activity, because it cannot say
which comments produced conversations. That is the whole reason it competes
with EveryChat and WATI on features rather than on results.

This module adds the missing end of the chain. Nothing here reports a
conversion unless a human records one in CommentOutcome, so the funnel is
built from evidence rather than from inference.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import declarative_base

from engine.models_sqlalchemy import Base  # noqa: F401  (same metadata)


# ---------------------------------------------------------------------------
# The missing table
# ---------------------------------------------------------------------------


class CommentOutcome(Base):
    """A recorded business outcome for a comment-derived lead.

    Added because nothing previously captured it. Every conversion metric is
    downstream of this table, and it is written only when a merchant confirms
    what happened. That constraint is deliberate: an inferred conversion
    would make the accuracy dashboard a second source of invented numbers.
    """

    __tablename__ = "comment_outcomes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    comment_id = Column(
        String(128), index=True, nullable=False,
        comment="Meta comment id, joins to Lead.fb_comment_id and to "
                "BotExecution.output_data.comment_id",
    )
    client_id = Column(String(64), index=True, nullable=False)
    outcome = Column(String(32), nullable=False)  # converted, lost, pending
    outcome_value_inr = Column(Float, nullable=True)
    recorded_by = Column(String(128), nullable=True)
    recorded_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    notes = Column(Text, nullable=True)

    def to_json(self) -> dict[str, Any]:
        return {
            "comment_id": self.comment_id,
            "outcome": self.outcome,
            "outcome_value_inr": self.outcome_value_inr,
            "recorded_by": self.recorded_by,
            "recorded_at": self.recorded_at.isoformat()
            if self.recorded_at else None,
            "notes": self.notes,
        }


# ---------------------------------------------------------------------------
# Funnel
# ---------------------------------------------------------------------------


def _loads(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except (TypeError, ValueError):
            return {}
    return {}


def comment_ids_from_executions(
    session, client_id: Optional[str] = None
) -> dict[str, dict[str, Any]]:
    """Map comment_id -> the executions recorded against it.

    BotExecution stores its payload as JSON rather than a column, so the
    comment id is extracted from output_data. Executions that carry no
    comment id (health checks, tuning runs) are ignored.

    Two rules that a naive version got wrong:

      * FAILED operations do not count toward the funnel. A reply that Meta
        rejected is not a reply, and counting it would inflate every stage
        that follows.
      * The client filter applies to the executions too. Filtering only the
        leads made a per-client funnel return every client's replies.
    """
    from engine.models_sqlalchemy import BotExecution

    out: dict[str, dict[str, Any]] = {}
    q = session.query(BotExecution)
    if client_id:
        q = q.filter(BotExecution.client_id == client_id)

    for row in q.all():
        data = _loads(row.output_data)
        cid = data.get("comment_id")
        if not cid:
            continue
        entry = out.setdefault(
            cid,
            {"replies": 0, "hides": 0, "success": 0, "failure": 0},
        )
        entry["success" if row.success else "failure"] += 1
        if not row.success:
            continue
        op = row.input_payload or ""
        if "reply" in op:
            entry["replies"] += 1
        if "hide" in op:
            entry["hides"] += 1
    return out


def build_funnel(session, client_id: Optional[str] = None) -> dict[str, Any]:
    """Compute the comment-to-revenue funnel.

    Every stage is counted from stored rows. A stage with no evidence is
    reported as zero with a note, never estimated.
    """
    from engine.models_sqlalchemy import Lead, OutreachMessage

    execs = comment_ids_from_executions(session, client_id)
    replied = {cid: e for cid, e in execs.items() if e["replies"] > 0}

    q_leads = session.query(Lead)
    if client_id:
        q_leads = q_leads.filter(Lead.client_id == client_id)
    leads = q_leads.all()

    leads_with_comment = [l for l in leads if l.fb_comment_id]
    lead_by_comment = {
        l.fb_comment_id: l for l in leads_with_comment
    }

    q_msgs = session.query(OutreachMessage)
    if client_id:
        lead_ids = [l.id for l in leads]
        q_msgs = q_msgs.filter(OutreachMessage.lead_id.in_(lead_ids))
    messages = q_msgs.all()
    msgs_by_lead: dict[int, list] = {}
    for m in messages:
        msgs_by_lead.setdefault(m.lead_id, []).append(m)

    delivered = sum(
        1 for m in messages if (m.status or "").lower() in
        ("delivered", "sent", "read")
    )

    outcomes = session.query(CommentOutcome)
    if client_id:
        outcomes = outcomes.filter(CommentOutcome.client_id == client_id)
    outcome_rows = outcomes.all()

    converted = [o for o in outcome_rows if o.outcome == "converted"]
    lost = [o for o in outcome_rows if o.outcome == "lost"]
    value = sum(o.outcome_value_inr or 0.0 for o in converted)

    # Only report rates where the denominator is real.
    replied_n = len(replied)
    leads_n = len(leads_with_comment)
    delivered_n = delivered
    decided_n = len(converted) + len(lost)

    return {
        "client_id": client_id,
        "funnel": {
            "comments_replied": replied_n,
            "leads_captured": leads_n,
            "messages_delivered": delivered_n,
            "outcomes_recorded": decided_n,
            "converted": len(converted),
            "lost": len(lost),
        },
        "rates": {
            "reply_to_lead": (leads_n / replied_n) if replied_n else None,
            "lead_to_delivered": (delivered_n / leads_n) if leads_n else None,
            "delivered_to_outcome": (decided_n / delivered_n) if delivered_n else None,
            "conversion_rate": (len(converted) / decided_n) if decided_n else None,
        },
        "value": {
            "recorded_revenue_inr": value,
            "average_deal_inr": (value / len(converted)) if converted else None,
        },
        "coverage": {
            "executions_with_comment_id": len(execs),
            "leads_missing_outcome": leads_n - sum(
                1 for c in converted + lost
                if c.comment_id in lead_by_comment
            ),
        },
        "notes": [
            "Rates are null where the denominator is zero. No rate is "
            "estimated from a partial sample.",
            "Conversion counts only outcomes a merchant recorded. Unrecorded "
            "leads are excluded from the conversion rate rather than "
            "counted as failures.",
            "Every prediction-window KPI depends on this table being "
            "populated. Until it is, coverage cannot be computed honestly.",
        ],
    }