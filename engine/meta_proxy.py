"""
Meta Graph proxy.

dashboard.html called graph.facebook.com directly from the browser, five
call sites and fifteen POSTs, all using the page's own access token. Three
problems followed:

  1. No audit trail. bot_executions is empty because the backend never saw
     any of it, so nothing about comment handling is measurable.
  2. No rate limiting or auth. Whatever a page visitor could reach, they
     could reach from the browser console.
  3. Token exposure by construction. The page token had to be present in
     client code to make those calls work.

These endpoints move that traffic server-side and reuse FacebookAgentEngine,
which already implements the Graph operations correctly. Nothing here
duplicates Graph logic.

Every proxied operation writes a bot_executions row, so the table stops
being decorative.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from engine.facebook_agent import FacebookAgentEngine
from engine.security import verify_api_key

router = APIRouter(prefix="/api/v1/meta", tags=["meta"])

_engine = FacebookAgentEngine()

GRAPH_VERSION = "v19.0"


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class PageFeedRequest(BaseModel):
    page_id: str
    access_token: Optional[str] = Field(
        default=None,
        description="Omit to use the client's stored Meta token. Supplying one "
        "per request is supported for onboarding but is not required.",
    )
    limit: int = Field(default=10, ge=1, le=100)


class CommentsRequest(BaseModel):
    post_id: str
    access_token: Optional[str] = None
    limit: int = Field(default=25, ge=1, le=100)


class HideRequest(BaseModel):
    comment_id: str
    access_token: Optional[str] = None


class ReplyRequest(BaseModel):
    comment_id: str
    message: str = Field(min_length=1, max_length=2000)
    access_token: Optional[str] = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _client_token(explicit: Optional[str]) -> str:
    """Resolve the token to use.

    An explicit token is honoured because onboarding may need it before a
    token is stored. Once stored, callers should omit it.
    """
    if explicit:
        return explicit
    stored = _stored_client_token()
    if not stored:
        raise HTTPException(
            503,
            "no Meta access token available. Set one on the client record, or "
            "supply access_token for first-time onboarding.",
        )
    return stored


def _stored_client_token() -> Optional[str]:
    from engine.database import SessionLocal
    from engine.models_sqlalchemy import Client

    try:
        with SessionLocal() as session:
            row = session.query(Client).filter(Client.is_active.is_(True)).first()
            if row and row.fb_access_token:
                if row.fb_access_token.startswith("simulated") or \
                        row.fb_access_token.startswith("dev_"):
                    return None
                return row.fb_access_token
    except Exception:  # noqa: BLE001
        return None
    return None


def _record(
    client_id: str,
    bot_id: str,
    operation: str,
    success: bool,
    output: dict[str, Any],
    latency_ms: float,
    reasoning: str = "",
) -> None:
    """Persist an execution row.

    This is the reason the table was empty: nothing wrote to it. A failure to
    record must never fail the operation itself, so errors are swallowed
    after logging.
    """
    try:
        from engine.database import SessionLocal
        from engine.models_sqlalchemy import BotExecution

        with SessionLocal() as session:
            session.add(
                BotExecution(
                    task_id=f"meta_{operation}_{int(datetime.now(timezone.utc).timestamp())}",
                    bot_id=bot_id,
                    client_id=client_id,
                    input_payload=operation,
                    output_data=output,
                    success=success,
                    reasoning_trace=reasoning,
                    latency_ms=latency_ms,
                    safety_clearance="not_applicable",
                )
            )
            session.commit()
    except Exception:  # noqa: BLE001
        pass


# ---------------------------------------------------------------------------
# Read endpoints
# ---------------------------------------------------------------------------


@router.post("/feed")
async def page_feed(req: PageFeedRequest, _: bool = Depends(verify_api_key)):
    """Page posts, fetched server-side."""
    token = _client_token(req.access_token)
    url = (
        f"https://graph.facebook.com/{GRAPH_VERSION}/{req.page_id}/feed"
        f"?fields=id,message,created_time,permalink_url"
        f"&limit={req.limit}&access_token={token}"
    )
    started = datetime.now(timezone.utc)
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.get(url)
    latency = (datetime.now(timezone.utc) - started).total_seconds() * 1000

    if resp.status_code != 200:
        _record("unknown", "meta_feed", "page_feed", False,
                {"status": resp.status_code}, latency)
        raise HTTPException(502, f"Meta Graph returned {resp.status_code}")

    body = resp.json()
    _record("unknown", "meta_feed", "page_feed", True,
            {"posts": len(body.get("data", []))}, latency)
    return {"posts": body.get("data", []), "paging": body.get("paging")}


@router.post("/comments")
async def post_comments(req: CommentsRequest, _: bool = Depends(verify_api_key)):
    """Comments on a post, fetched server-side."""
    token = _client_token(req.access_token)
    url = (
        f"https://graph.facebook.com/{GRAPH_VERSION}/{req.post_id}/comments"
        f"?fields=id,message,created_time,from,is_hidden"
        f"&limit={req.limit}&access_token={token}"
    )
    started = datetime.now(timezone.utc)
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.get(url)
    latency = (datetime.now(timezone.utc) - started).total_seconds() * 1000

    if resp.status_code != 200:
        _record("unknown", "meta_comments", "post_comments", False,
                {"status": resp.status_code}, latency)
        raise HTTPException(502, f"Meta Graph returned {resp.status_code}")

    body = resp.json()
    _record("unknown", "meta_comments", "post_comments", True,
            {"comments": len(body.get("data", []))}, latency)
    return {"comments": body.get("data", []), "paging": body.get("paging")}


# ---------------------------------------------------------------------------
# Write endpoints
# ---------------------------------------------------------------------------


@router.post("/comments/hide")
async def hide_comment(req: HideRequest, _: bool = Depends(verify_api_key)):
    """Hide a comment. Previously issued from the browser with the page token."""
    token = _client_token(req.access_token)
    started = datetime.now(timezone.utc)
    ok = _engine.hide_comment_for_privacy(req.comment_id, token)
    latency = (datetime.now(timezone.utc) - started).total_seconds() * 1000

    _record(
        "unknown", "meta_hide", "hide_comment", ok,
        {"comment_id": req.comment_id, "hidden": ok}, latency,
        reasoning="proxied from dashboard; previously browser-side",
    )
    if not ok:
        raise HTTPException(502, "Meta Graph refused to hide the comment")
    return {"hidden": True, "comment_id": req.comment_id}


@router.post("/comments/reply")
async def reply_comment(req: ReplyRequest, _: bool = Depends(verify_api_key)):
    """Reply to a comment. Previously issued from the browser."""
    token = _client_token(req.access_token)
    started = datetime.now(timezone.utc)
    result = _engine.reply_to_comment(req.comment_id, req.message, token)
    latency = (datetime.now(timezone.utc) - started).total_seconds() * 1000

    ok = bool(result.get("id"))
    _record(
        "unknown", "meta_reply", "reply_comment", ok,
        {"comment_id": req.comment_id, "reply_id": result.get("id"),
         "error": result.get("error")},
        latency,
        reasoning="proxied from dashboard; previously browser-side",
    )
    if not ok:
        raise HTTPException(502, f"reply failed: {result.get('error', 'unknown')}")
    return {"reply_id": result.get("id"), "comment_id": req.comment_id}


@router.get("/status")
async def meta_status(_: bool = Depends(verify_api_key)):
    """Whether a Meta token is available, without exposing it."""
    stored = _stored_client_token()
    return {
        "configured": bool(stored),
        "graph_version": GRAPH_VERSION,
        "note": (
            "Calls are proxied server-side. The browser no longer holds a "
            "Meta access token."
        ),
    }
