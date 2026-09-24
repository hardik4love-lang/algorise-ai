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
        return token or "simulated_token"
    try:
        from engine.security import encryption_manager
        return encryption_manager.decrypt(token)
    except Exception:
        return token


async def run_facebook_agent_sweep():
    """Performs one autonomous sweep across all active subscribers."""
    try:
        async with db_manager.session() as session:
            query = select(Client).where(Client.is_active == True)
            result = await session.execute(query)
            clients = result.scalars().all()

            loop = asyncio.get_running_loop()

            for client in clients:
                page_id = client.fb_page_id or f"page_{client.id}"
                token = _safe_decrypt(client.fb_access_token) or "simulated_token"

                # Dynamic sector lookup
                sector = "textile"
                if client.settings and isinstance(client.settings, dict):
                    sector = client.settings.get("sector") or client.settings.get("agent_rules", {}).get("sector", "textile")

                # Run agent for this client without blocking async event loop
                run_res = await loop.run_in_executor(
                    None,
                    lambda: fb_engine.process_client_agent_run(
                        client_id=client.id,
                        client_name=client.name,
                        business_name=client.name.split("(")[0].strip(),
                        page_id=page_id,
                        access_token=token,
                        sector=sector,
                        force_simulation=(token == "simulated_token")
                    )
                )

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

                # Log job
                job = FacebookAgentJob(
                    client_id=client.id,
                    job_type="scheduled_cron_sweep",
                    status="completed",
                    comments_scanned=run_res.get("comments_scanned", 0),
                    replies_sent=run_res.get("replies_sent", 0),
                    leads_detected=run_res.get("leads_detected", 0),
                    log_summary=f"Automated sweep: scanned {run_res.get('comments_scanned')}, replies {run_res.get('replies_sent')}, leads {run_res.get('leads_detected')}.",
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