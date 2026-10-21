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
        active_client_configs = []
        async with db_manager.session() as session:
            query = select(Client).where(Client.is_active == True)
            result = await session.execute(query)
            clients = result.scalars().all()
            for c in clients:
                active_client_configs.append({
                    "id": c.id,
                    "name": c.name,
                    "fb_page_id": c.fb_page_id,
                    "fb_access_token": c.fb_access_token,
                    "settings": c.settings,
                })

        loop = asyncio.get_running_loop()
        client_semaphore = asyncio.Semaphore(10)

        async def _process_client(c_cfg: dict) -> None:
            async with client_semaphore:
                client_id = c_cfg["id"]
                client_name = c_cfg["name"]
                page_id = c_cfg["fb_page_id"] or "61586357894191"
                token = _safe_decrypt(c_cfg["fb_access_token"])
                is_shruhi = client_id == "client_srt_shruhi" or "61586357894191" in str(page_id)

                if not is_shruhi and (not token or not token.startswith("EAA")):
                    return

                # Dynamic sector lookup
                sector = "textile"
                c_settings = c_cfg.get("settings")
                if c_settings and isinstance(c_settings, dict):
                    sector = c_settings.get("sector") or c_settings.get("agent_rules", {}).get("sector", "textile")

                try:
                    if token and token.startswith("EAA"):
                        run_res = await loop.run_in_executor(
                            None,
                            lambda cid=client_id, cname=client_name, pid=page_id, tok=token, sec=sector: fb_engine.process_client_agent_run(
                                client_id=cid,
                                client_name=cname,
                                business_name=cname.split("(")[0].strip(),
                                page_id=pid,
                                access_token=tok,
                                sector=sec,
                                force_simulation=False
                            )
                        )
                    else:
                        run_res = {
                            "status": "not_configured",
                            "reason": "no Meta access token on this client",
                            "comments_scanned": 0,
                            "replies_sent": 0,
                            "leads_detected": 0,
                            "leads": [],
                        }

                    if run_res.get("status") == "token_required" and not is_shruhi:
                        return

                    # Dedicated isolated database transaction per client
                    async with db_manager.session() as client_session:
                        for lead_info in run_res.get("leads", []):
                            lead = Lead(
                                client_id=client_id,
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
                            client_session.add(lead)

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
                            client_id=client_id,
                            job_type="scheduled_cron_sweep",
                            status=_status,
                            comments_scanned=_scanned,
                            replies_sent=_replied,
                            leads_detected=_leads_found,
                            log_summary=job_log,
                            run_at=datetime.now(timezone.utc)
                        )
                        client_session.add(job)

                except Exception as client_err:
                    logger.error("Error processing client sweep", client_id=client_id, error=str(client_err))

        await asyncio.gather(*(_process_client(cfg) for cfg in active_client_configs), return_exceptions=True)
        logger.info(
            "Facebook Agent autonomous sweep cycle completed successfully",
            total_clients=len(active_client_configs),
        )

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