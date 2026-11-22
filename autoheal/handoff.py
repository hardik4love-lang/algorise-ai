"""
Algorise AutoHeal™ — Seamless Human-Handoff Protocol
Compiles executable on-site runbooks for the founder when physical intervention
is mathematically proven to be necessary.
"""
from __future__ import annotations

import sys
import json
import urllib.request
import urllib.parse
from typing import Dict, Any, List

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

class HumanHandoffProtocol:
    def __init__(self, telegram_token: str = "", telegram_chat_id: str = "", founder_phone: str = "9227095624"):
        self.telegram_token = telegram_token
        self.telegram_chat_id = telegram_chat_id
        self.founder_phone = founder_phone

    def compile_tactical_runbook(
        self,
        incident_id: str,
        client_name: str,
        market_location: str,
        visiting_deposit_status: str,
        hardware_symptoms: str,
        step_by_step_runbook: List[str]
    ) -> str:
        """Compiles an exact, concise, mobile-friendly tactical dispatch runbook."""
        steps_formatted = "\n".join([f"{i+1}. {step}" for i, step in enumerate(step_by_step_runbook)])
        runbook = (
            f"🚨 <b>ALGORISE AUTOHEAL™ — PHYSICAL SRE ESCALATION</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"<b>Incident ID:</b> <code>{incident_id}</code>\n"
            f"<b>Client:</b> {client_name}\n"
            f"<b>Location:</b> 📍 {market_location}\n"
            f"<b>Visiting Deposit:</b> {visiting_deposit_status}\n\n"
            f"<b>Hardware Root Cause:</b>\n"
            f"⚠️ {hardware_symptoms}\n\n"
            f"<b>🛠️ Step-by-Step Tactical Runbook:</b>\n"
            f"{steps_formatted}\n\n"
            f"<b>1-Click Verification Command (Run on Phone after fix):</b>\n"
            f"<code>curl -X POST https://webhook.algorise-ai.com/v1/verify-heal?id={incident_id}</code>"
        )
        return runbook

    def dispatch_alert(self, runbook_html: str) -> bool:
        """Sends runbook directly to Founder's Telegram."""
        if not self.telegram_token or not self.telegram_chat_id:
            print("[AUTOHEAL HANDOFF ALERT]\n" + runbook_html)
            return True
        url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
        data = urllib.parse.urlencode({
            "chat_id": self.telegram_chat_id,
            "text": runbook_html,
            "parse_mode": "HTML"
        }).encode("utf-8")
        req = urllib.request.Request(url, data=data)
        try:
            with urllib.request.urlopen(req, timeout=5.0) as resp:
                res = json.loads(resp.read().decode())
                return res.get("ok", False)
        except Exception:
            return False
