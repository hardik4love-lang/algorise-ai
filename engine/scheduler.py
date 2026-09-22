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
from sqlalchemy import select

settings = get_settings()
telegram = AlgoriseTelegramService()
fb_engine = FacebookAgentEngine(api_version=settings.fb_graph_api_version)


async def run_facebook_agent_sweep():
    """Performs one autonomous sweep across all active subscribers."""
    try:
        async with db_manager.session() as session:
            query = select(Client).where(Client.is_active == True)
            result = await session.execute(query)
            clients = result.scalars().all()

            for client in clients:
                page_id = client.fb_page_id or f"page_{client.id}"
                token = client.fb_access_token or "simulated_token"

                # Run agent for this client
                run_res = fb_engine.process_client_agent_run(
                    client_id=client.id,
                    client_name=client.name,
                    business_name=client.name.split("(")[0].strip(),
                    page_id=page_id,
                    access_token=token,
                    sector="textile",
                    force_simulation=(token == "simulated_token")
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

    except Exception as e:
        print(f"[SCHEDULER ERROR] Facebook Agent sweep failed: {e}")


async def start_background_scheduler_loop(interval_seconds: int = 900):
    """Asynchronous loop running agent sweeps periodically."""
    print(f"[SCHEDULER] Facebook Agent background daemon active (interval: {interval_seconds}s)")
    while True:
        try:
            await run_facebook_agent_sweep()
        except Exception as e:
            print(f"[SCHEDULER ERROR] Loop exception: {e}")
        await asyncio.sleep(interval_seconds)


if __name__ == "__main__":
    asyncio.run(start_background_scheduler_loop(interval_seconds=60))