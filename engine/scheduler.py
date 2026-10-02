"""
Background Autonomous Scheduler for Facebook AI Agent.
Runs scheduled sweeps across all active client Facebook pages,
classifies comments, auto-replies, and alerts via Telegram.
"""

import asyncio
import os
from datetime import datetime, timezone
from typing import Optional

from engine.config import get_settings
from engine.database import db_manager
from engine.facebook_agent import FacebookAgentEngine
from engine.models_sqlalchemy import Client, FacebookAgentJob, Lead
from engine.telegram_service import AlgoriseTelegramService
from engine.logging import get_logger
from sqlalchemy import select

logger = get_logger(__name__)
settings = get_settings()
telegram = AlgoriseTelegramService()
fb_engine = FacebookAgentEngine(api_version=settings.fb_graph_api_version)


def _safe_decrypt(token: Optional[str]) -> str:
    if not token or token == "simulated_token":
        return ""
    try:
        from engine.security import encryption_manager
        return encryption_manager.decrypt(token)
    except Exception:
        return token


async def run_facebook_agent_sweep():
    """Performs one autonomous sweep across all active subscribers who have a real Meta Page Access Token."""
    try:
        async with db_manager.session() as session:
            query = select(Client).where(Client.is_active == True)
            result = await session.execute(query)
            clients = result.scalars().all()

            loop = asyncio.get_running_loop()

            for client in clients:
                page_id = client.fb_page_id or "61586357894191"
                token = _safe_decrypt(client.fb_access_token)
                is_shruhi = client.id == "client_srt_shruhi" or "61586357894191" in str(page_id)

                if not is_shruhi and (not token or not token.startswith("EAA")):
                    continue

                # Dynamic sector lookup
                sector = "textile"
                if client.settings and isinstance(client.settings, dict):
                    sector = client.settings.get("sector") or client.settings.get("agent_rules", {}).get("sector", "textile")

                if token and token.startswith("EAA"):
                    run_res = await loop.run_in_executor(
                        None,
                        lambda c=client, pid=page_id, tok=token, sec=sector: fb_engine.process_client_agent_run(
                            client_id=c.id,
                            client_name=c.name,
                            business_name=c.name.split("(")[0].strip(),
                            page_id=pid,
                            access_token=tok,
                            sector=sec,
                            force_simulation=False
                        )
                    )
                else:
                    # NO Meta token: record that nothing ran.
                    #
                    # This branch previously fabricated a successful run
                    # claiming comments_scanned=31 and "3-Page Auto-Update
                    # Active" without calling the Meta API, writing roughly
                    # 1,440 rows per day of synthetic activity that the
                    # client dashboard displayed as evidence of work. An
                    # honest "not configured" is more useful than a fake
                    # success, because a client paying for comment handling
                    # can see exactly what is and is not running.
                    run_res = {
                        "status": "not_configured",
                        "reason": "no Meta access token on this client",
                        "comments_scanned": 0,
                        "replies_sent": 0,
                        "leads_detected": 0,
                        "leads": [],
                    }

                if run_res.get("status") == "token_required" and not is_shruhi:
                    continue

                # Persist discovered leads
                for lead_info in run_res.get("leads", []):
                    lead = Lead(
                        client_id=client.id,
                        name=lead_info["name"],
                        phone=lead_info["phone"],
                        fb_user_id=lead_info.get("fb_user_id"),
                        fb_comment_id=lead_info.get("fb_comment_id"),
                        source="facebook_comment",
                        status=lead_info["status"],
                        qualification_score=lead_info["score"],
                        intent_summary=lead_info["intent"],
                        original_message=lead_info.get("comment"),
                        created_at=datetime.now(timezone.utc)
                    )
                    session.add(lead)

                # Persist an honest record. The `31` default and the hardcoded
                # "3-Page Auto-Update Active ... Viral Reel synced" summary
                # asserted work that had not happened. A run row now states
                # what actually occurred, and a client without a token gets
                # a not_configured row rather than a fake success.
                _scanned = run_res.get("comments_scanned", 0)
                _replied = run_res.get("replies_sent", 0)
                _leads_found = run_res.get("leads_detected", 0)
                _status = run_res.get("status", "completed")

                if _status == "not_configured":
                    job_log = (
                        "No Meta access token configured; no sweep was "
                        "performed and no comments were read."
                    )
                elif is_shruhi:
                    job_log = (
                        f"Sweep completed on the configured pages: scanned "
                        f"{_scanned}, replies {_replied}, leads {_leads_found}."
                    )
                else:
                    job_log = (
                        f"Automated sweep on Page {page_id}: scanned {_scanned}, "
                        f"replies {_replied}, leads {_leads_found}."
                    )

                job = FacebookAgentJob(
                    client_id=client.id,
                    job_type="scheduled_cron_sweep",
                    status=_status,
                    comments_scanned=_scanned,
                    replies_sent=_replied,
                    leads_detected=_leads_found,
                    log_summary=job_log,
                    run_at=datetime.now(timezone.utc)
                )
                session.add(job)

        logger.info("Facebook Agent autonomous sweep cycle completed successfully")

    except Exception as e:
        logger.error("Facebook Agent sweep failed", error=str(e))


async def start_background_scheduler_loop(interval_seconds: int = 900):
    """Asynchronous loop running agent sweeps periodically."""
    logger.info("Facebook Agent background daemon active", interval_seconds=interval_seconds)
    while True:
        try:
            await run_facebook_agent_sweep()
        except Exception as e:
            logger.error("Facebook Agent scheduler loop exception", error=str(e))
        await asyncio.sleep(interval_seconds)


if __name__ == "__main__":
    asyncio.run(start_background_scheduler_loop(interval_seconds=60))