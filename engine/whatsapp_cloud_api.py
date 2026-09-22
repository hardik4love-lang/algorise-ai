"""
Official Meta WhatsApp Cloud API Direct Dispatcher & Receiver.
Bypasses third-party BSP markups to send sub-2s WhatsApp template messages,
product catalogs, and 2-way conversation replies.
"""

import os
import json
import urllib.request
import urllib.parse
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from engine.config import get_settings

settings = get_settings()

WHATSAPP_API_VERSION = "v19.0"
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "108920194829102")
WHATSAPP_TOKEN = os.getenv("WHATSAPP_CLOUD_TOKEN", "dev_whatsapp_cloud_token_simulated")
WHATSAPP_VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "algorise_surat_wa_verify_9921")


class WhatsAppCloudAPIService:
    """Direct client for Meta WhatsApp Cloud API."""

    def __init__(
        self,
        phone_number_id: Optional[str] = None,
        access_token: Optional[str] = None
    ):
        self.phone_number_id = phone_number_id or WHATSAPP_PHONE_NUMBER_ID
        self.access_token = access_token or WHATSAPP_TOKEN
        self.base_url = f"https://graph.facebook.com/{WHATSAPP_API_VERSION}/{self.phone_number_id}/messages"

    def format_phone_number(self, phone: str) -> str:
        """Cleans and standardizes Indian phone numbers to 91XXXXXXXXXX."""
        clean = "".join(filter(str.isdigit, phone))
        if len(clean) == 10:
            return f"91{clean}"
        if len(clean) == 12 and clean.startswith("91"):
            return clean
        return clean

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
        filename: str = "Surat_Wholesale_Catalog.pdf",
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
                "caption": caption or "Algorise AI: Ex-Factory Surat Wholesale Catalog"
            }
        }

        return self._execute_request(payload)

    def _execute_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatches HTTP POST to Meta Graph API or returns mock in test environment."""
        if not self.access_token or self.access_token.startswith("dev_"):
            # Sandbox / Simulation mode for development and automated tests
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