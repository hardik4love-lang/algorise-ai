"""
Official Meta WhatsApp Cloud API Direct Dispatcher & 24/7 Shruhi Collections AI Receiver.
Supports "Until I Jump In" Human Takeover (!takeover / !ai) + 29-Product Shruhi Catalog
on Official WhatsApp +91 63552 85433 (916355285433).
"""

import os
import re
import json
import urllib.request
import urllib.parse
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta

from engine.config import get_settings
from engine.facebook_agent import SHRUHI_29_CATALOG

settings = get_settings()

WHATSAPP_API_VERSION = "v19.0"
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "108920194829102")
WHATSAPP_TOKEN = os.getenv("WHATSAPP_CLOUD_TOKEN", "dev_whatsapp_cloud_token_simulated")
WHATSAPP_VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "algorise_surat_wa_verify_9921")
OFFICIAL_SHRUHI_WHATSAPP = "+91 63552 85433"
HUMAN_TAKEOVER_PAUSE_HOURS = 12


class WhatsAppCloudAPIService:
    """Direct client & 24/7 AI Concierge for Meta WhatsApp Cloud API (+91 63552 85433)."""

    def __init__(
        self,
        phone_number_id: Optional[str] = None,
        access_token: Optional[str] = None
    ):
        self.phone_number_id = phone_number_id or WHATSAPP_PHONE_NUMBER_ID
        self.access_token = access_token or WHATSAPP_TOKEN
        self.base_url = f"https://graph.facebook.com/{WHATSAPP_API_VERSION}/{self.phone_number_id}/messages"
        # Maps customer phone -> datetime until which AI is paused ("Until I Jump In")
        self.human_takeover_until: Dict[str, datetime] = {}

    def format_phone_number(self, phone: str) -> str:
        """Cleans and standardizes Indian phone numbers to 91XXXXXXXXXX."""
        clean = "".join(filter(str.isdigit, phone or ""))
        if len(clean) == 10:
            return f"91{clean}"
        if len(clean) == 12 and clean.startswith("91"):
            return clean
        return clean

    def activate_human_takeover(self, customer_phone: str) -> None:
        norm = self.format_phone_number(customer_phone)
        self.human_takeover_until[norm] = datetime.now(timezone.utc) + timedelta(hours=HUMAN_TAKEOVER_PAUSE_HOURS)

    def resume_ai_mode(self, customer_phone: str) -> None:
        norm = self.format_phone_number(customer_phone)
        self.human_takeover_until.pop(norm, None)

    def is_human_takeover_active(self, customer_phone: str) -> bool:
        norm = self.format_phone_number(customer_phone)
        until = self.human_takeover_until.get(norm)
        if not until:
            return False
        if datetime.now(timezone.utc) >= until:
            self.human_takeover_until.pop(norm, None)
            return False
        return True

    def generate_shruhi_whatsapp_ai_reply(self, customer_phone: str, incoming_text: str, is_from_owner: bool = False) -> Optional[str]:
        """
        Generates 24/7 Shruhi Collections AI response for WhatsApp (+91 63552 85433)
        unless owner has jumped in ("Until I Jump In").
        """
        text = (incoming_text or "").strip()
        lower = text.lower()

        if is_from_owner or lower in ("!takeover", "/takeover"):
            self.activate_human_takeover(customer_phone)
            return None

        if lower in ("!ai", "/ai"):
            self.resume_ai_mode(customer_phone)
            return "🤖 *Shruhi Collections 24/7 AI Concierge Resumed!* How may we assist you with our 29+ 4K Ethnic & Curvy Couture designs today?"

        if self.is_human_takeover_active(customer_phone):
            return None

        # Match specific product from 29-outfit catalog
        for item in SHRUHI_29_CATALOG:
            if any(k in lower for k in item["keys"]):
                return (
                    f"Namaste! 🙏 Welcome to *Shruhi Collections* (Official Online Store: www.shruhicollections.in)\n\n"
                    f"✨ *{item['name']}*\n"
                    f"• *Boutique Price:* {item['price']}\n"
                    f"• *Sizes Ready to Ship:* {item['sizes']} (Full S to 6XL Range)\n"
                    f"• *Dispatch:* 100% Online Store • Pan-India & Worldwide Express Delivery\n\n"
                    f"Please reply with your *Size (S to 6XL)* and *Delivery Pincode* to confirm your order, or our team will jump in shortly! 🛍️"
                )

        if any(w in lower for w in ["3xl", "4xl", "5xl", "6xl", "plus", "curvy", "size"]):
            return (
                "Namaste! 🙏 *Shruhi Collections — Curvy & Plus-Size Haute Couture (S to 6XL)*\n\n"
                "We specialize in true-fit Indian Festive & Designer Suits up to *6XL*:\n"
                "• *TEJAL 3-Piece Heavy Suit:* ₹2,850 (M to 6XL)\n"
                "• *KAVYA Royal Bandhani Couture:* ₹3,250 (M to 6XL)\n"
                "• *B-2876 Curvy Festive Edition:* ₹2,650 (3XL to 6XL)\n"
                "• *GALAXY Silk Co-ord & Suit:* ₹2,450 (S to 5XL)\n\n"
                "🛍️ Browse all 29+ 4K outfits at: https://shruhicollections.in\n"
                "Reply with your preferred design code or size to book immediately!"
            )

        return (
            "નમસ્તે / Namaste! 🙏 Welcome to *Shruhi Collections* (Official WhatsApp: *+91 63552 85433*)\n\n"
            "✨ *29+ Verified 4K Designer Ethnic, Festive & Curvy Couture Outfits*\n"
            "• *Sizes:* S, M, L, XL, 2XL, 3XL, 4XL, 5XL & 6XL\n"
            "• *Boutique Price Range:* ₹850 – ₹3,550\n"
            "• *Storefront:* 100% Online Store • Pan-India & Worldwide Express Delivery\n\n"
            "🛍️ *View Full 4K Catalog & Viral Runway Reel:*\n"
            "https://shruhicollections.in/\n\n"
            "Reply with any outfit name (e.g., *TEJAL*, *KAVYA*, *GALAXY*, *B-2876*, *ANUPAMA*, *1042*) or your size (*S–6XL*) for instant pricing & booking!"
        )

    def send_text_message(self, recipient_phone: str, message_body: str) -> Dict[str, Any]:
        """Sends a standard text message within the 24-hour service window."""
        formatted_phone = self.format_phone_number(recipient_phone)

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": formatted_phone,
            "type": "text",
            "text": {"preview_url": True, "body": message_body}
        }

        return self._execute_request(payload)

    def send_template_message(
        self,
        recipient_phone: str,
        template_name: str = "surat_b2b_instant_welcome",
        language_code: str = "gu",
        parameters: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Sends an approved WhatsApp template message to initiate conversations
        outside the 24-hour service window.
        """
        formatted_phone = self.format_phone_number(recipient_phone)

        components = []
        if parameters:
            components.append({
                "type": "body",
                "parameters": [{"type": "text", "text": str(p)} for p in parameters]
            })

        payload = {
            "messaging_product": "whatsapp",
            "to": formatted_phone,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": language_code},
                "components": components
            }
        }

        return self._execute_request(payload)

    def send_catalog_document(
        self,
        recipient_phone: str,
        document_url: str,
        filename: str = "Shruhi_Collections_4K_Catalog.pdf",
        caption: Optional[str] = None
    ) -> Dict[str, Any]:
        """Sends PDF catalog or invoice directly to prospect."""
        formatted_phone = self.format_phone_number(recipient_phone)

        payload = {
            "messaging_product": "whatsapp",
            "to": formatted_phone,
            "type": "document",
            "document": {
                "link": document_url,
                "filename": filename,
                "caption": caption or "Shruhi Collections: 29+ 4K Designer Outfits (Sizes S to 6XL) • www.shruhicollections.in"
            }
        }

        return self._execute_request(payload)

    def _execute_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatches HTTP POST to Meta Graph API or returns mock in test environment."""
        if not self.access_token or self.access_token.startswith("dev_"):
            return {
                "messaging_product": "whatsapp",
                "contacts": [{"input": payload.get("to"), "wa_id": payload.get("to")}],
                "messages": [{"id": f"wamid.HBgL{int(datetime.now().timestamp())}SIM"}],
                "simulated": True,
                "delivered_at": datetime.now(timezone.utc).isoformat()
            }

        try:
            req = urllib.request.Request(
                self.base_url,
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {self.access_token}",
                    "Content-Type": "application/json"
                }
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            return {"error": str(e), "success": False}