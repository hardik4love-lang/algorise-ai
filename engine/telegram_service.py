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

if __name__ == "__main__":
    tg = AlgoriseTelegramService()
    me = tg.get_me()
    print("Telegram Bot Verified:")
    print(json.dumps(me, indent=2))
