#!/usr/bin/env python3
"""
================================================================================
ARIA — EXECUTIVE PERSONAL ASSISTANT: EMAIL & TELEGRAM DISPATCH ENGINE
================================================================================
Monitors user inbox (Gmail/IMAP), extracts actionable priorities, generates
intelligent next-step recommendations, and pushes them directly to Telegram.
================================================================================
"""

import os
import sys
import json
import time
import email
import imaplib
import urllib.request
import urllib.parse
from email.header import decode_header
from datetime import datetime, timezone

# Ensure UTF-8 output
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_DIR = os.path.join(ROOT_DIR, "config")
CONFIG_PATH = os.path.join(CONFIG_DIR, "aria_assistant_config.json")
STATE_PATH = os.path.join(CONFIG_DIR, "aria_inbox_state.json")

os.makedirs(CONFIG_DIR, exist_ok=True)

DEFAULT_CONFIG = {
    "user_name": "Hardik",
    "email_account": "shruhicollections@gmail.com",
    "imap_server": "imap.gmail.com",
    "imap_port": 993,
    "email_app_password": "",  # 16-character Google App Password
    "telegram_bot_token": "",   # Telegram Bot Token from @BotFather
    "telegram_chat_id": "8737013099",
    "poll_interval_seconds": 120,
    "auto_suggest": True
}


def load_config() -> dict:
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                merged = {**DEFAULT_CONFIG, **cfg}
                return merged
        except Exception as e:
            print(f"[WARN] Error loading config: {e}")
    return DEFAULT_CONFIG.copy()


def save_config(cfg: dict):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)


def load_state() -> dict:
    if os.path.exists(STATE_PATH):
        try:
            with open(STATE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"processed_email_ids": [], "last_check": None}


def save_state(state: dict):
    # Keep last 500 processed IDs
    state["processed_email_ids"] = state.get("processed_email_ids", [])[-500:]
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


def decode_str(header_val) -> str:
    """Decodes email header text safely."""
    if not header_val:
        return ""
    decoded_fragments = []
    for fragment, charset in decode_header(header_val):
        if isinstance(fragment, bytes):
            try:
                decoded_fragments.append(fragment.decode(charset or "utf-8", errors="replace"))
            except Exception:
                decoded_fragments.append(fragment.decode("latin1", errors="replace"))
        else:
            decoded_fragments.append(str(fragment))
    return "".join(decoded_fragments)


def send_telegram_alert(bot_token: str, chat_id: str, message: str) -> bool:
    """Delivers formatted markdown alert to the user's Telegram."""
    if not bot_token or not chat_id:
        print("[TELEGRAM] Missing bot token or chat ID. Alert not sent.")
        return False

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True
    }
    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=12) as response:
            res = json.loads(response.read().decode())
            return res.get("ok", False)
    except Exception as e:
        print(f"[TELEGRAM ERROR] {e}")
        return False


def analyze_email_and_suggest(sender: str, subject: str, snippet: str) -> dict:
    """Analyzes email intent and formulates high-priority action recommendations."""
    full_text = f"{sender} {subject} {snippet}".lower()
    
    category = "GENERAL"
    suggestion = "Review and archive if not urgent."
    priority = "NORMAL"

    if "github" in full_text or "pull request" in full_text or "merged" in full_text or "issue" in full_text:
        category = "GITHUB & DEV"
        priority = "HIGH"
        if "merged" in full_text:
            suggestion = "Pull request has been merged. Update bounty ledger and pull latest changes to local workspace."
        elif "approved" in full_text:
            suggestion = "Maintainer approved changes. Awaiting final merge by repository owner."
        else:
            suggestion = "New comment or review received. Verify requested edits."

    elif "order" in full_text or "razorpay" in full_text or "payment" in full_text or "upi" in full_text:
        category = "PAYMENTS & ORDERS"
        priority = "URGENT"
        suggestion = "Confirm payment settlement in merchant ledger and dispatch order to warehouse concierge."

    elif "wholesale" in full_text or "inquiry" in full_text or "catalogue" in full_text or "price" in full_text:
        category = "B2B WHOLESALE INQUIRY"
        priority = "HIGH"
        suggestion = "Prospective buyer inquiry detected. Route to primary WhatsApp line (+91 90542 41725) with 59-item 4K lookbook."

    elif "security" in full_text or "alert" in full_text or "password" in full_text or "login" in full_text:
        category = "SECURITY"
        priority = "CRITICAL"
        suggestion = "Security verification needed. Confirm whether this login attempt was initiated by you."

    return {
        "category": category,
        "priority": priority,
        "suggestion": suggestion
    }


def check_inbox(config: dict, state: dict) -> list:
    """Connects to IMAP, reads recent unread emails, and compiles intelligence briefs."""
    email_user = config.get("email_account")
    app_pw = config.get("email_app_password")

    if not email_user or not app_pw:
        print("[INBOX] Email address or Google App Password not provided.")
        return []

    processed = set(state.get("processed_email_ids", []))
    new_alerts = []

    try:
        mail = imaplib.IMAP4_SSL(config.get("imap_server", "imap.gmail.com"), config.get("imap_port", 993))
        mail.login(email_user, app_pw)
        mail.select("INBOX")

        # Search unread messages
        status, messages = mail.search(None, "UNSEEN")
        if status != "OK":
            return []

        msg_ids = messages[0].split()
        print(f"[INBOX] Found {len(msg_ids)} unread messages.")

        for msg_id in msg_ids[-10:]:  # Check up to 10 latest unread
            msg_id_str = msg_id.decode()
            if msg_id_str in processed:
                continue

            status, msg_data = mail.fetch(msg_id, "(RFC822)")
            if status != "OK":
                continue

            raw_email = msg_data[0][1]
            msg = email.message_from_bytes(raw_email)

            subject = decode_str(msg.get("Subject", "(No Subject)"))
            sender = decode_str(msg.get("From", "(Unknown Sender)"))
            date_str = msg.get("Date", "")

            # Extract body snippet
            snippet = ""
            if msg.is_multipart():
                for part in msg.walk():
                    content_type = part.get_content_type()
                    content_disp = str(part.get("Content-Disposition"))
                    if content_type == "text/plain" and "attachment" not in content_disp:
                        payload = part.get_payload(decode=True)
                        if payload:
                            snippet = payload.decode("utf-8", errors="replace")[:300]
                            break
            else:
                payload = msg.get_payload(decode=True)
                if payload:
                    snippet = payload.decode("utf-8", errors="replace")[:300]

            snippet_clean = " ".join(snippet.split())[:180]

            analysis = analyze_email_and_suggest(sender, subject, snippet_clean)

            alert_msg = (
                f"👑 *Aria — Executive Inbox Alert*\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"🏷️ *Category*: {analysis['category']} (`{analysis['priority']}`)\n"
                f"👤 *From*: `{sender}`\n"
                f"📌 *Subject*: *{subject}*\n"
                f"📝 *Summary*: {snippet_clean}...\n\n"
                f"💡 *Aria's Recommendation*:\n"
                f"_{analysis['suggestion']}_\n"
                f"━━━━━━━━━━━━━━━━━━"
            )

            new_alerts.append(alert_msg)
            processed.add(msg_id_str)

        mail.logout()
        state["processed_email_ids"] = list(processed)
        save_state(state)

    except Exception as e:
        print(f"[INBOX ERROR] {e}")

    return new_alerts


def main():
    config = load_config()
    state = load_state()

    print("=" * 60)
    print("👑 ARIA EXECUTIVE INBOX & TELEGRAM DISPATCH ENGINE")
    print(f"• Account    : {config.get('email_account')}")
    print(f"• Telegram   : Chat ID {config.get('telegram_chat_id')}")
    print(f"• App PW Set : {'YES' if config.get('email_app_password') else 'NO (Requires 16-char App Password)'}")
    print("=" * 60)

    alerts = check_inbox(config, state)
    bot_token = config.get("telegram_bot_token")
    chat_id = config.get("telegram_chat_id")

    for a in alerts:
        print(a)
        if bot_token:
            send_telegram_alert(bot_token, chat_id, a)

    print(f"[STATUS] Processed {len(alerts)} new actionable emails.")


if __name__ == "__main__":
    main()
