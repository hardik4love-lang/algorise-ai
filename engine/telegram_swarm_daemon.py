"""
Algorise 24/7 Autonomous Telegram Swarm Daemon (Hermes @Aassqqee_bot)
Continuously processes scraped world freelance jobs, generates live code deliverables
and tailored pitches via the 5 Closer Agents, and streams interactive approval cards to Telegram.
"""

import socket
import urllib.request
import urllib.parse
import json
import time
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Enforce IPv4 on Windows to eliminate dual-stack routing latency
_orig_getaddrinfo = socket.getaddrinfo
def _ipv4_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    return _orig_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)
socket.getaddrinfo = _ipv4_getaddrinfo

from engine.freelance_harvester import AlgoriseFreelanceHarvester
from engine.telegram_service import AlgoriseTelegramService, TELEGRAM_DEFAULT_CHAT_ID
from engine.freelancer_bidder import freelancer_bidder, HARDIK_PROFILE

class TelegramSwarmDaemon:
    def __init__(self, chat_id: int = TELEGRAM_DEFAULT_CHAT_ID, interval_sec: float = 25.0):
        self.chat_id = chat_id
        self.interval_sec = interval_sec
        self.harvester = AlgoriseFreelanceHarvester()
        self.tg = AlgoriseTelegramService()
        self.is_paused = False
        self.last_update_id = 0
        self.closed_count = 0
        self.total_escrow = 0
        self.pending_jobs = {}

    def check_incoming_commands(self):
        """Polls for Telegram commands and interactive button approvals."""
        updates = self.tg.get_updates(offset=self.last_update_id + 1)
        for u in updates:
            self.last_update_id = u.get("update_id", self.last_update_id)

            # 1. Interactive Button Approval / Skip Handling
            if "callback_query" in u:
                cq = u["callback_query"]
                cq_id = cq.get("id")
                sender_id = cq.get("from", {}).get("id")
                if sender_id != self.chat_id:
                    continue

                data = cq.get("data", "")
                msg = cq.get("message", {})
                msg_id = msg.get("message_id")

                if data.startswith("bid:"):
                    job_id = data.split(":", 1)[1]
                    p_job = self.pending_jobs.get(job_id, {})
                    self.tg.answer_callback_query(cq_id, f"? Submitting bid for {job_id}...")

                    # Extract project ID
                    proj_num_str = "".join(filter(str.isdigit, job_id))
                    proj_num = int(proj_num_str) if proj_num_str else 0
                    quote_str = p_job.get("quote_amount", "150")
                    num_amount = float("".join(filter(str.isdigit, quote_str.split("-")[-1])) or "150")

                    bid_res = freelancer_bidder.submit_bid(
                        project_id=proj_num,
                        amount=num_amount,
                        period_days=2,
                        proposal_text=p_job.get("pitch_sent", "")
                    )

                    if bid_res.get("success"):
                        confirm_text = (
                            f"?? <b>[BID SUBMITTED VIA FREELANCER API!]</b>\n\n"
                            f"? <b>Project:</b> {p_job.get('title')}\n"
                            f"? <b>Bid ID:</b> #{bid_res.get('bid_id')}\n"
                            f"? <b>Amount:</b> ${num_amount:,.0f} USD\n"
                            f"? <b>Bidder:</b> {HARDIK_PROFILE['username']} (ID: {HARDIK_PROFILE['user_id']})\n\n"
                            f"<i>The client has been notified on Freelancer.com!</i>"
                        )
                        self.tg.send_message(self.chat_id, confirm_text)
                    else:
                        pitch_full = p_job.get("pitch_sent", "")
                        quote_val = p_job.get("quote_amount", "$150")
                        deliv = p_job.get("code_deliverable", {})
                        code_full = deliv.get("code", "")[:400]
                        filename = deliv.get("filename", "deliverable.py")

                        confirm_text = (
                            f"✅ <b>[BID APPROVED • 1-TAP SUBMISSION READY]</b>\n\n"
                            f"💼 <b>{p_job.get('title')}</b>\n"
                            f"💰 <b>Your Quote:</b> <code>{quote_val}</code> (in 2 days)\n"
                            f"🔗 <b>Project:</b> {p_job.get('live_url')}\n\n"
                            f"📋 <b>Tap proposal below to COPY to clipboard:</b>\n"
                            f"<pre>{pitch_full}</pre>\n\n"
                            f"📦 <b>Deliverable Code:</b> <code>{filename}</code>\n"
                            f"<pre>{code_full}\n# ... [Full Code Ready]</pre>\n\n"
                            f"👉 <i>Click the Project link, paste proposal, and hit Submit! Zero API required.</i>"
                        )
                        self.tg.send_message(self.chat_id, confirm_text)

                    # Update original card status
                    self.tg.edit_message_text(
                        self.chat_id,
                        msg_id,
                        f"? <b>[APPROVED BY HARDIK ? READY TO CLOSE]</b>\n\n"
                        f"?? <b>{p_job.get('title')}</b>\n"
                        f"?? <b>Budget:</b> {p_job.get('budget')}\n"
                        f"?? <b>Link:</b> {p_job.get('live_url')}\n"
                        f"?? <b>Deliverable:</b> <code>{p_job.get('code_deliverable', {}).get('filename', 'deliverable.py')}</code>"
                    )

                elif data.startswith("skip:"):
                    job_id = data.split(":", 1)[1]
                    p_job = self.pending_jobs.get(job_id, {})
                    self.tg.answer_callback_query(cq_id, "? Gig Skipped")
                    self.tg.edit_message_text(
                        self.chat_id,
                        msg_id,
                        f"? <b>[SKIPPED BY OPERATOR]</b>\n\n"
                        f"?? {p_job.get('title', 'Freelance Gig')}\n"
                        f"<i>Archived. Continuing stream...</i>"
                    )

            # 2. Text Commands
            elif "message" in u:
                msg = u.get("message", {})
                text = (msg.get("text") or "").strip().lower()
                sender_id = msg.get("from", {}).get("id")

                if sender_id != self.chat_id:
                    continue

                if text == "/pause":
                    self.is_paused = True
                    self.tg.send_message(self.chat_id, "? <b>24/7 Closer Swarm PAUSED.</b>\nSend <code>/resume</code> to continue.")
                elif text == "/resume":
                    self.is_paused = False
                    self.tg.send_message(self.chat_id, "? <b>24/7 Closer Swarm RESUMED.</b>\nProcessing live world jobs...")
                elif text == "/status":
                    status_text = (
                        f"?? <b>Algorise Swarm Status Report:</b>\n\n"
                        f"? <b>Status:</b> {'PAUSED ?' if self.is_paused else 'RUNNING 24/7 ?'}\n"
                        f"? <b>Bidding Mode:</b> Semi-Autonomous (Approval-Gated)\n"
                        f"? <b>Operator Account:</b> {HARDIK_PROFILE['username']} (ID: {HARDIK_PROFILE['user_id']})\n"
                        f"? <b>World Jobs Closed:</b> {self.closed_count} / {len(self.harvester.jobs)}\n"
                        f"? <b>Escrow Pipeline:</b> ${self.total_escrow:,.0f}\n"
                        f"? <b>Active Closers:</b> 5 Specialized Agents"
                    )
                    self.tg.send_message(self.chat_id, status_text)

    def run(self):
        print(f">> Starting Algorise 24/7 Closer Swarm for Chat ID: {self.chat_id}")
        print(f">> Linked to Freelancer Profile: {HARDIK_PROFILE['username']} (ID: {HARDIK_PROFILE['user_id']})")
        print(f">> Loaded {len(self.harvester.jobs)} scraped world jobs from global web feeds.")

        profile_url = HARDIK_PROFILE["profile_url"]
        profile_name = HARDIK_PROFILE["username"]
        start_msg = (
            f"🚀 <b>24/7 APPROVAL-GATED CLOSER SWARM ONLINE!</b>\n\n"
            f"• <b>Account Linked:</b> <a href=\"{profile_url}\">{profile_name}</a>\n"
            f"• <b>Mode:</b> Semi-Autonomous (Auto-synthesize -> Wait for Your Approval)\n"
            f"• <b>Closer Squad:</b> Apex-01 to Apex-05 Online\n"
            f"• <b>Interval:</b> ~{self.interval_sec:.0f}s per gig match\n\n"
            f"<i>Tap <b>[✅ APPROVE & BID]</b> on any gig below to execute the bid instantly!</i>"
        )
        self.tg.send_message(self.chat_id, start_msg)

        job_idx = 0
        while True:
            try:
                # 1. Check for incoming control commands and button clicks
                self.check_incoming_commands()

                if self.is_paused:
                    time.sleep(3)
                    continue

                if job_idx >= len(self.harvester.jobs):
                    # Refresh jobs from live API
                    self.harvester = AlgoriseFreelanceHarvester()
                    job_idx = 0
                    self.tg.send_message(self.chat_id, "?? <b>Swarm refreshed feed. Scanning newest live gigs...</b>")

                job = self.harvester.jobs[job_idx]
                job_idx += 1

                # 2. Execute live code generation and proposal synthesis
                close_res = self.harvester.execute_job_close(job.job_id)
                self.closed_count += 1

                # Save to pending jobs for approval execution
                self.pending_jobs[job.job_id] = {
                    "job_id": job.job_id,
                    "title": close_res.get("title", job.title),
                    "budget": job.budget,
                    "quote_amount": close_res.get("quote_amount", job.quote_amount),
                    "live_url": job.live_url,
                    "pitch_sent": close_res.get("pitch_sent", ""),
                    "solution_blueprint": close_res.get("solution_blueprint", ""),
                    "code_deliverable": close_res.get("code_deliverable", {})
                }

                # Compute escrow amount
                num = 4500
                digits = "".join(c for c in (job.budget or "") if c.isdigit())
                if digits:
                    val = int(digits[-4:]) if len(digits) >= 4 else int(digits)
                    num = val if val > 500 else val * 1000
                self.total_escrow += num

                # 3. Deliver interactive approval card to Telegram
                title = close_res.get("title", "Remote Contract Gig")
                platform = job.platform
                budget = job.budget
                live_url = job.live_url or "https://www.freelancer.com/projects"
                closer = close_res.get("closer_assigned", "Apex Closer Agent")
                pitch_text = (close_res.get("pitch_sent") or "")[:240].strip()
                code_deliverable = close_res.get("code_deliverable", {})
                filename = code_deliverable.get("filename", "deliverable.py")
                lang = code_deliverable.get("language", "python")
                code_snippet = "\n".join(code_deliverable.get("code", "").splitlines()[:10])

                alert_text = (
                    f"? <b>[NEW GIG ? AWAITING YOUR APPROVAL]</b>\n\n"
                    f"?? <b>{title}</b>\n"
                    f"?? <b>Platform:</b> {platform}\n"
                    f"?? <b>Budget:</b> {budget}\n"
                    f"?? <b>Closer Agent:</b> {closer}\n\n"
                    f"?? <b>Generated Pitch:</b>\n"
                    f"<i>\"{pitch_text}...\"</i>\n\n"
                    f"?? <b>Working Deliverable:</b> <code>{filename}</code> ({lang})\n"
                    f"<pre>{code_snippet}\n# ... [Full module ready to ship]</pre>\n\n"
                    f"<i>Tap below to approve and dispatch bid under <b>{HARDIK_PROFILE['username']}</b>:</i>"
                )

                reply_markup = {
                    "inline_keyboard": [
                        [
                            {"text": "? APPROVE & BID", "callback_data": f"bid:{job.job_id}"},
                            {"text": "? SKIP", "callback_data": f"skip:{job.job_id}"}
                        ],
                        [
                            {"text": "?? VIEW PROJECT ON FREELANCER", "url": live_url}
                        ]
                    ]
                }

                self.tg.send_message(self.chat_id, alert_text, reply_markup=reply_markup)
                print(f"[SWARM DISPATCH] Awaiting approval for {job.job_id} ({filename}) -> Card sent to Telegram.")

                # 4. Wait for interval while checking commands in smaller slices
                slice_count = int(self.interval_sec / 2)
                for _ in range(slice_count):
                    self.check_incoming_commands()
                    time.sleep(2)

            except Exception as e:
                print(f"[SWARM ERROR] {e}")
                time.sleep(5)

if __name__ == "__main__":
    interval = float(sys.argv[1]) if len(sys.argv) > 1 else 25.0
    daemon = TelegramSwarmDaemon(interval_sec=interval)
    daemon.run()
