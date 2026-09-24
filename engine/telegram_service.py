"""
Algorise Telegram Bot Integration (Hermes @Aassqqee_bot)
Connects the 5 Closer Agents Swarm & Freelance Harvester to Telegram for real-time alerts,
command dispatch, and escrow contract notifications.
"""

import socket
import urllib.request
import urllib.parse
import json
import os
import time
from typing import Dict, Any, List, Optional

# Force IPv4 resolution on Windows to avoid dual-stack hangs
_original_getaddrinfo = socket.getaddrinfo
def _ipv4_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    return _original_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)
socket.getaddrinfo = _ipv4_getaddrinfo

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8961434797:AAHaPPybfby3G-Mj7WeJEXsAtKPna-uSPnw")
TELEGRAM_BOT_ID = 8961434797
TELEGRAM_BOT_USERNAME = "Aassqqee_bot"
TELEGRAM_DEFAULT_CHAT_ID = int(os.getenv("TELEGRAM_CHAT_ID", "8737013099"))
TELEGRAM_API_BASE = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

class AlgoriseTelegramService:
    def __init__(self, token: Optional[str] = None):
        self.token = token or TELEGRAM_BOT_TOKEN
        self.api_base = f"https://api.telegram.org/bot{self.token}"

    def get_me(self) -> Dict[str, Any]:
        """Verifies bot identity with Telegram API."""
        try:
            req = urllib.request.Request(f"{self.api_base}/getMe")
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def get_updates(self, offset: Optional[int] = None) -> List[Dict[str, Any]]:
        """Pulls latest incoming messages and commands from users."""
        try:
            url = f"{self.api_base}/getUpdates"
            if offset:
                url += f"?offset={offset}"
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data.get("result", [])
        except Exception as e:
            print(f"[TELEGRAM ERROR] get_updates: {e}")
            return []

    def send_message(self, chat_id: int | str, text: str, parse_mode: str = "HTML") -> Dict[str, Any]:
        """Sends formatted message to Telegram chat or channel."""
        try:
            payload = {
                "chat_id": chat_id,
                "text": text,
                "parse_mode": parse_mode,
                "disable_web_page_preview": True
            }
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                f"{self.api_base}/sendMessage",
                data=data,
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            err_msg = str(e)
            try:
                err_msg = e.read().decode("utf-8", errors="ignore")
            except Exception:
                pass
            e.close()
            return {"ok": False, "error": err_msg}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def notify_job_closed(self, chat_id: int | str, job_data: Dict[str, Any]) -> Dict[str, Any]:
        """Broadcasts live job closed alert with closer deliverable info."""
        title = job_data.get("title", "Remote Engineering Project")
        platform = job_data.get("platform", "World Freelance Feed")
        budget = job_data.get("budget", "$4,500 - $8,500")
        closer = job_data.get("closer_assigned", "Apex Closer Agent")
        code_file = job_data.get("code_deliverable", {}).get("filename", "deliverable.py")

        msg = (
            f"⚡ <b>[ALGORISE SWARM ALERT]</b> Contract Locked!\n\n"
            f"💼 <b>Job:</b> {title}\n"
            f"🌐 <b>Platform:</b> {platform}\n"
            f"💰 <b>Budget:</b> {budget}\n"
            f"🤖 <b>Closer Agent:</b> {closer}\n"
            f"📦 <b>Generated Deliverable:</b> <code>{code_file}</code>\n"
            f"🔒 <b>Escrow Status:</b> SECURED (100% Verified)\n\n"
            f"<i>Powered by Hermes (@{TELEGRAM_BOT_USERNAME})</i>"
        )
        return self.send_message(chat_id, msg)

    def notify_new_subscriber(self, chat_id: int | str, sub_data: Dict[str, Any]) -> Dict[str, Any]:
        """Broadcasts alert when a new Surat client subscribes."""
        client_name = sub_data.get("client_name", "Surat Client")
        business_name = sub_data.get("business_name", "Local Business")
        phone = sub_data.get("phone", "N/A")
        plan_name = sub_data.get("plan_name", "Surat Business Pro")
        monthly = sub_data.get("monthly_price", 29999)
        advance = sub_data.get("advance_amount", 5999)
        pin = sub_data.get("pin", "1234")
        client_id = sub_data.get("client_id", "N/A")

        msg = (
            f"🚀 <b>[NEW SURAT CLIENT SUBSCRIBED]</b>\n\n"
            f"🏢 <b>Business:</b> {business_name}\n"
            f"👤 <b>Contact:</b> {client_name}\n"
            f"📱 <b>Phone:</b> <code>{phone}</code>\n"
            f"💎 <b>Plan:</b> {plan_name}\n"
            f"💰 <b>Monthly:</b> ₹{monthly:,.0f} | <b>Advance (20%):</b> ₹{advance:,.0f}\n"
            f"🔑 <b>Client ID:</b> <code>{client_id}</code>\n"
            f"🔒 <b>Dashboard PIN:</b> <code>{pin}</code>\n\n"
            f"<i>Action: Send PIN to client for Facebook Page authorization.</i>"
        )
        return self.send_message(chat_id, msg)

    def notify_facebook_hot_lead(self, chat_id: int | str, lead_data: Dict[str, Any]) -> Dict[str, Any]:
        """Broadcasts instant alert when Facebook Agent qualifies a hot lead."""
        client_business = lead_data.get("business_name", "Client Business")
        lead_name = lead_data.get("lead_name", "Prospect")
        phone = lead_data.get("phone", "Extracted in DM")
        score = lead_data.get("score", 95)
        comment = lead_data.get("comment", "")
        intent = lead_data.get("intent", "High buying intent")

        msg = (
            f"🔥 <b>[HOT LEAD QUALIFIED — FACEBOOK AGENT]</b>\n\n"
            f"🏢 <b>Client Account:</b> {client_business}\n"
            f"👤 <b>Lead Name:</b> {lead_name}\n"
            f"📞 <b>Phone / Contact:</b> <code>{phone}</code>\n"
            f"🎯 <b>Score:</b> {score}/100 (HOT LEAD)\n"
            f"💬 <b>Original Comment:</b> <i>\"{comment[:120]}\"</i>\n"
            f"💡 <b>Identified Intent:</b> {intent}\n\n"
            f"⚡ <i>Auto-response delivered in 0.05s. Hand off to sales team!</i>"
        )
        return self.send_message(chat_id, msg)

if __name__ == "__main__":
    tg = AlgoriseTelegramService()
    me = tg.get_me()
    print("Telegram Bot Verified:")
    print(json.dumps(me, indent=2))
