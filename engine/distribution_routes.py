"""
Distribution API.

Exposes target import, capability probing and broadcast. The capability
endpoint is the important one: it reports what the deployment can genuinely
do, so the dashboard and the sales conversation quote verified reach rather
than an aspiration.
"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from engine.distribution import (
    broadcast,
    connect,
    import_from_directory,
    import_targets,
    probe,
)
from engine.security import verify_api_key

router = APIRouter(prefix="/api/v1/distribution", tags=["distribution"])


class TargetImport(BaseModel):
    targets: list[dict[str, Any]] = Field(default_factory=list)


class BroadcastRequest(BaseModel):
    body: str = Field(min_length=1, max_length=4000)
    platform: str = Field(default="telegram", pattern="^(telegram|facebook)$")
    media_path: Optional[str] = None
    limit: Optional[int] = Field(default=None, ge=1, le=100)
    min_interval: float = Field(
        default=20.0, ge=0.0, le=600.0,
        description="Seconds between posts. Cross-posting faster than this "
        "is how accounts get restricted.",
    )


def _session():
    return connect()


@router.get("/capabilities")
def capabilities(_: bool = Depends(verify_api_key)):
    """What this deployment can actually post to, discovered not assumed."""
    conn = _session()
    try:
        return probe(conn).to_json()
    finally:
        conn.close()


@router.post("/targets/import")
def import_targets_route(payload: TargetImport, _: bool = Depends(verify_api_key)):
    """Import real targets. Placeholder ids are rejected, not stored."""
    conn = _session()
    try:
        return import_targets(payload.targets, conn=conn)
    finally:
        conn.close()


@router.post("/targets/import-directory")
def import_directory(_: bool = Depends(verify_api_key)):
    """Import the bundled directory. Rejects its placeholder ids."""
    conn = _session()
    try:
        return import_from_directory(conn=conn)
    finally:
        conn.close()


@router.get("/targets")
def list_targets(
    platform: Optional[str] = None, _: bool = Depends(verify_api_key)
):
    conn = _session()
    try:
        if platform:
            rows = conn.execute(
                "SELECT * FROM targets WHERE platform=?", (platform,)
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM targets").fetchall()
        return {
            "count": len(rows),
            "verified": sum(1 for r in rows if r["verified"]),
            "unverified": sum(1 for r in rows if not r["verified"]),
            "targets": [dict(r) for r in rows],
        }
    finally:
        conn.close()


@router.post("/broadcast")
async def broadcast_route(payload: BroadcastRequest, _: bool = Depends(verify_api_key)):
    """Post to every VERIFIED target. Unverified targets are never counted."""
    from pathlib import Path

    conn = _session()
    try:
        media = Path(payload.media_path) if payload.media_path else None
        return await broadcast(
            body=payload.body,
            platform=payload.platform,
            media=media,
            limit=payload.limit,
            conn=conn,
            min_interval=payload.min_interval,
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(500, f"broadcast failed: {exc}") from exc
    finally:
        conn.close()


@router.get("/posts")
def recent_posts(limit: int = 50, _: bool = Depends(verify_api_key)):
    conn = _session()
    try:
        rows = conn.execute(
            "SELECT p.*, t.platform, t.external_id, t.name FROM posts p"
            " LEFT JOIN targets t ON t.id = p.target_id"
            " ORDER BY p.id DESC LIMIT ?",
            (min(limit, 200),),
        ).fetchall()
        return {"count": len(rows), "posts": [dict(r) for r in rows]}
    finally:
        conn.close()