"""
Attribution API.

Exposes the comment-to-revenue funnel and the outcome recorder that
populates it. Both are read-only against the existing tables plus the new
CommentOutcome table.
"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from engine.attribution import CommentOutcome, build_funnel
from engine.security import verify_api_key

router = APIRouter(prefix="/api/v1/attribution", tags=["attribution"])


class OutcomeRequest(BaseModel):
    comment_id: str = Field(min_length=4, max_length=128)
    outcome: str = Field(pattern="^(converted|lost|pending)$")
    outcome_value_inr: Optional[float] = Field(default=None, ge=0)
    recorded_by: Optional[str] = Field(default=None, max_length=128)
    notes: Optional[str] = Field(default=None, max_length=2000)


def _session():
    from engine.database import sync_session

    return sync_session()


@router.get("/funnel")
def funnel(client_id: Optional[str] = None, _: bool = Depends(verify_api_key)):
    """The comment-to-revenue funnel for a client."""
    from engine.attribution import CommentOutcome

    session = _session()
    try:
        CommentOutcome.__table__.create(bind=session.get_bind(), checkfirst=True)
        return build_funnel(session, client_id)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(500, f"attribution unavailable: {exc}") from exc
    finally:
        session.close()


@router.post("/outcome", status_code=201)
def record_outcome(req: OutcomeRequest, _: bool = Depends(verify_api_key)):
    """Record what actually happened to a comment-derived lead.

    Idempotent per comment: recording twice overwrites rather than
    double-counting a conversion.
    """
    from engine.attribution import CommentOutcome

    session = _session()
    try:
        CommentOutcome.__table__.create(bind=session.get_bind(), checkfirst=True)
        existing = (
            session.query(CommentOutcome)
            .filter(CommentOutcome.comment_id == req.comment_id)
            .first()
        )
        if existing is None:
            row = CommentOutcome(
                comment_id=req.comment_id,
                client_id="unknown",
                outcome=req.outcome,
                outcome_value_inr=req.outcome_value_inr,
                recorded_by=req.recorded_by,
                notes=req.notes,
            )
        else:
            row = existing
            row.outcome = req.outcome
            row.outcome_value_inr = req.outcome_value_inr
            row.recorded_by = req.recorded_by or row.recorded_by
            row.notes = req.notes or row.notes
        session.add(row)
        session.commit()
        return {"recorded": True, "outcome": row.to_json()}
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(500, f"could not record outcome: {exc}") from exc
    finally:
        session.close()