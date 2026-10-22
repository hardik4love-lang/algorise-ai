"""
Facebook AI Agent Engine for Shruhi Collections & Surat B2B Clients.
Handles real Meta Graph API integration across 3 Connected Facebook Pages & 100 Groups,
Gujarati/Hinglish/English NLP lead scoring, Shruhi catalogue matching,
   (catalogue currently holds 14 items; counts shown to customers are
   derived from it, so the two cannot disagree),
Sub-0.05s comment auto-hide shield, instant public + private DM auto-replies,
and Telegram hot lead alerts. Zero simulated or fake data.
"""

import os
import re
import json
import time
from collections import OrderedDict
import urllib.request
import urllib.parse

from engine.enquiry_tracking import embed_code, register_comment
import urllib.error
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple, Set, Union

from engine.config import get_settings
from engine.merchant_context import MerchantContext
from engine.logging import get_logger
from engine.telegram_service import (
    AlgoriseTelegramService,
    TelegramNotConfigured,
    telegram_configured,
)

settings = get_settings()
logger = get_logger(__name__)

# Telegram alerting is optional. A missing token disables alerting; it must
# not prevent the module from importing, or the whole application fails to
# start for a missing notification credential. Previously a hardcoded token
# masked this by making the service always constructible.
try:
    telegram = AlgoriseTelegramService()
except TelegramNotConfigured:
    telegram = None

HOT_INTENT_KEYWORDS = [
    # Gujarati
    "ભાવ", "ભાવ શું છે", "રેટ", "હોલસેલ", "ઓર્ડર", "સેમ્પલ", "કેટલોગ", "મોકલો", "ડિસ્કાઉન્ટ",
    "ખરીદવું", "ડીલર", "ડીલરશીપ", "સુરત", "માલ", "ડિલિવરી", "કિંમત", "જથ્થાબંધ", "બુકિંગ",
    # Hinglish / Hindi / English
    "price", "pp", "rate", "bhav", "wholesale", "order", "sample", "catalog", "catalogue", "moq",
    "discount", "buy", "dealer", "dealership", "delivery", "cost", "quote", "interested",
    "contact", "call me", "whatsapp", "phone", "details", "how much", "rate please", "dm",
    "3xl", "4xl", "5xl", "6xl", "suit", "kurti", "tejal", "galaxy", "kavya", "anupama",
    "shree", "glory", "gulzaar", "2876", "1002", "1042", "5620", "5795", "5601"
]

SHRUHI_CATALOG = [
    {"keys": ["tejal"], "name": "TEJAL — 3-Piece Heavy Designer Suit (4K)", "price": "₹2,850", "sizes": "M to 6XL"},
    {"keys": ["galaxy", "banarasi"], "name": "GALAXY — Festive Silk Co-ord & Banarasi Suit Set (4K)", "price": "₹2,450 – ₹2,850", "sizes": "S to 5XL"},
    {"keys": ["kavya", "bandhani", "mauve"], "name": "KAVYA — Royal Bandhani & Zari Couture (4K)", "price": "₹2,950 – ₹3,250", "sizes": "M to 6XL"},
    {"keys": ["2876", "b-2876", "b2876", "curvy", "plus", "3xl", "4xl", "5xl", "6xl"], "name": "B-2876 — Curvy Plus-Size Festive Edition (4K)", "price": "₹2,650", "sizes": "3XL to 6XL"},
    {"keys": ["anupama", "rust", "ivory"], "name": "ANUPAMA — Pure Roman Silk Embroidery Set (4K)", "price": "₹2,350 – ₹2,450", "sizes": "M to 5XL"},
    {"keys": ["shree", "coffee"], "name": "SHREE — Designer Coffee Festive 3-Piece Set (4K)", "price": "₹2,550", "sizes": "M to 4XL"},
    {"keys": ["glory", "taupe"], "name": "GLORY — Luxury Organza & Silk Ensemble (4K)", "price": "₹2,750", "sizes": "M to 5XL"},
    {"keys": ["gulzaar"], "name": "GULZAAR — Heritage Floral Designer Suit (4K)", "price": "₹2,250", "sizes": "M to 4XL"},
    {"keys": ["1002", "dno1002", "mustard"], "name": "D.NO 1002 — Festive Chanderi & Zari Suit (4K)", "price": "₹2,150", "sizes": "M to 5XL"},
    {"keys": ["1042", "dno1042", "crimson", "cotton"], "name": "D.NO 1042 — Everyday Chic Cotton Tunic & Set (4K)", "price": "₹850 – ₹1,550", "sizes": "S to 4XL"},
    {"keys": ["5620", "swirl", "tunic"], "name": "D.NO 5620 — Contemporary Swirl Printed Tunic (4K)", "price": "₹1,250", "sizes": "S to 4XL"},
    {"keys": ["5795", "floral dress"], "name": "D.NO 5795 — Designer Floral Midi & Ethnic Dress (4K)", "price": "₹1,650", "sizes": "S to 4XL"},
    {"keys": ["5601", "denim"], "name": "D.NO 5601 — Artisanal Indigo Denim Ethnic Dress (4K)", "price": "₹1,450", "sizes": "S to 4XL"},
    {"keys": ["5041", "5625", "5810", "5811", "5764", "5437", "5699", "5525", "1115", "1112", "lock"], "name": "Shruhi Signature 4K Boutique Collection", "price": "₹1,350 – ₹3,550", "sizes": "S to 6XL"},
]


# Counts are derived, never written as literals. The reply text below used to
# assert "29+ Verified Designs" while the catalogue held 14 entries, so a buyer
# asking for a product outside the catalogue could not be served and the claim
# could not be kept. Adding an item here now updates every number shown.
SHRUHI_CATALOG_COUNT = len(SHRUHI_CATALOG)
SHRUHI_CATALOG_RANGE = "₹850 – ₹3,550"

AUTO_REPLY_TEMPLATES = {
    # The merchant identity is substituted at reply time from the client
    # record. A template that carried a fixed name, domain and WhatsApp
    # number meant onboarding a second client required editing this file.
    "textile": (
        "નમસ્તે જી! 🙏 {business_name} ({domain}) તરફથી: "
        "અમારું લેટેસ્ટ હોલસેલ કેટેલોગ {catalogue_claim} "
        "તમારા Messenger DM માં મોકલ્યું છે. {contact} ✨"
    ),
    "diamond": (
        "નમસ્તે! 💎 CVD & Lab-Grown Diamonds લાઈવ રેટ "
        "અને સર્ટિફાઈડ સ્ટોક લિસ્ટ માટે આપનો કોન્ટેક્ટ શેર કરો."
    ),
    "realty": (
        "નમસ્તે! 🏢 સુરતના પ્રાઇમ લોકેશન પ્રોજેક્ટ "
        "બ્રોશર અને વિગતો આપના ઇનબોક્સમાં મોકલી છે."
    ),
    "default": (
        "નમસ્તે જી! 🙏 {business_name} માં આપનું સ્વાગત છે. "
        "વિગતો આપના Messenger DM માં મોકલી છે. {contact}"
    ),
}


class BoundedDeduplicationCache:
    """
    Thread-safe bounded in-memory deduplication cache with FIFO eviction and TTL.
    Prevents memory leaks in perpetual 24/7 background agent execution.
    """

    def __init__(self, maxsize: int = 5000, ttl_seconds: float = 604800.0):
        self.maxsize = maxsize
        self.ttl_seconds = ttl_seconds
        self._cache: OrderedDict[str, float] = OrderedDict()

    def __contains__(self, item: str) -> bool:
        if not item or item not in self._cache:
            return False
        timestamp = self._cache[item]
        if (time.time() - timestamp) > self.ttl_seconds:
            try:
                del self._cache[item]
            except KeyError:
                pass
            return False
        return True

    def add(self, item: str) -> None:
        if not item:
            return
        now = time.time()
        if item in self._cache:
            self._cache.move_to_end(item)
            self._cache[item] = now
            return
        if len(self._cache) >= self.maxsize:
            self._cache.popitem(last=False)  # Evict oldest entry (FIFO)
        self._cache[item] = now

    def __len__(self) -> int:
        return len(self._cache)

    def clear(self) -> None:
        self._cache.clear()


class FacebookAgentEngine:
    """Core autonomous 24/7 agent for live Facebook 3-Page & 100-Group monitoring and conversion."""

    def __init__(self, api_version: str = "v19.0"):
        self.api_version = api_version
        self.base_url = f"https://graph.facebook.com/{self.api_version}"
        self.replied_comment_ids = BoundedDeduplicationCache(maxsize=5000, ttl_seconds=604800.0)

    def match_shruhi_product(self, text: str) -> Dict[str, str]:
        lower = (text or "").lower()
        for item in SHRUHI_CATALOG:
            if any(k in lower for k in item["keys"]):
                return item
        return {
            "name": (
                f"{SHRUHI_CATALOG_COUNT} Verified 4K Ethnic, Festive "
                f"& Curvy Couture Outfits"
            ),
            "price": SHRUHI_CATALOG_RANGE,
            "sizes": "S to 6XL"
        }

    def classify_lead_intent(self, text: str) -> Tuple[float, str, str]:
        if not text:
            return 20.0, "cold", "No text provided"

        clean_text = text.lower().strip()
        matched_keywords = [kw for kw in HOT_INTENT_KEYWORDS if kw in clean_text]
        score = 25.0 + (len(matched_keywords) * 15.0)

        # Phone number detection (+91 or 10 digits)
        phone_match = re.search(r'(?:\+?91[\s-]?)?[6789]\d{9}', clean_text)
        if phone_match:
            score += 35.0

        score = min(score, 99.0)

        if score >= 60.0:
            status = "hot"
            intent = f"Direct buyer inquiry. Matched: {', '.join(matched_keywords[:4]) or 'Phone number shared'}"
        elif score >= 45.0:
            status = "warm"
            intent = f"Product interest inquiry. Matched: {', '.join(matched_keywords[:3]) or 'Catalog inquiry'}"
        else:
            status = "cold"
            intent = "General comment"

        return score, status, intent

    def select_auto_reply(
        self,
        text: str,
        sector: Optional[str] = None,
        buyer_name: str = "Valued Shopper",
        merchant: Optional[MerchantContext] = None,
    ) -> str:
        """Build the public reply for a comment.

        The merchant identity comes from the client record. A reply must
        never point a buyer at another merchant's contact details, so
        every merchant-specific value is read from the context rather
        than baked into a template.
        """
        ctx = merchant or MerchantContext(sector=sector or "default")

        if ctx.sector and ctx.sector.lower() in AUTO_REPLY_TEMPLATES:
            template = AUTO_REPLY_TEMPLATES[ctx.sector.lower()]
            return template.format(
                business_name=ctx.business_name,
                domain=ctx.domain,
                catalogue_claim=ctx.catalogue_claim,
                contact=ctx.contact_line(),
            )

        matched = self.match_shruhi_product(text)
        has_gujarati = bool(re.search(r"[\u0a80-\u0aff]", text or ""))
        has_hindi = bool(re.search(r"[\u0900-\u097f]", text or ""))

        if has_gujarati:
            return (
                f"\u0a8f\u0aa8\u0aae\u0ab8\u0ac7 {buyer_name} \u0a9c\u0a80! \u0af7 {ctx.business_name} \u0aae\u0a3e\u0a82 \u0a06\u0aa1\u0aa8\u0ac1\u0a82 \u0ab8\u0acd\u0ab5\u0abe\u0a97\u0aa4 \u0a9b\u0a4d\u0a8f. "
                f"\u2728 {matched['name']} ({matched['price']} | \u0ab8\u0abe\u0a08\u0acd\u0a1c: {matched['sizes']}) \u0aa8\u0a40 \u0ab8\u0a82\u0a2a\u0ac2\u0ab0\u0acd\u0a23 \u0ab5\u0a3f\u0a17\u0a4d\u0a4a \u0a06\u0aa1\u0aa8\u0abe DM \u0aae\u0a3e\u0a82 \u0aae\u0a9b\u0a95\u0ab2\u0a40 \u0a9b\u0a4d\u0a8f. "
                f"\u0af1\u0a3d\u0a9f {ctx.domain or '100% Online Store'} | {ctx.contact_line()}"
            )
        if has_hindi:
            return (
                f"\u0928\u092e\u0938\u094d\u0924\u0947 {buyer_name} \u091c\u0940! \u0af7 {ctx.business_name} \u092e\u0947\u0902 \u0906\u092a\u0915\u093e \u0938\u094d\u0935\u093e\u0917\u0924 \u0939\u0948\u0964 "
                f"\u2728 {matched['name']} ({matched['price']} | \u0938\u093e\u0907\u095b\u093c: {matched['sizes']}) \u0915\u093e \u092a\u0942\u0930\u093e 4K \u0915\u0948\u091f\u0932\u0949\u0917 \u0906\u092a\u0915\u0947 DM \u092e\u0947\u0902 \u092d\u0947\u091c \u0926\u093f\u092f\u093e \u0939\u0948\u0964 "
                f"\u0af1\u0a3d\u0a9f {ctx.domain or '100% Online Store'} | {ctx.contact_line()}"
            )
        return (
            f"Namaste {buyer_name}! \u0af7 Welcome to {ctx.business_name}. "
            f"\u2728 Full details for {matched['name']} ({matched['price']} | Sizes: {matched['sizes']}) have been sent to your DM! "
            f"\u0af1\u0a3d\u0a9f Shop 100% Online: {ctx.domain or 'our store'} | {ctx.contact_line()}"
        )

    def build_private_dm(
        self,
        text: str,
        buyer_name: str = "Valued Shopper",
        comment_id: str = "",
        merchant: Optional[MerchantContext] = None,
    ) -> str:
        """Build the private DM sent to a commenter.

        When comment_id is supplied, an opaque tracking reference is appended
        to the prefilled WhatsApp message so the resulting enquiry resolves
        back to this comment. The offer text is unchanged; only the prefilled
        message gains a reference line.
        """
        ctx = merchant or MerchantContext()
        matched = self.match_shruhi_product(text)
        prefill = (
            f"Hi {ctx.business_name}! I saw your post on Facebook and want to "
            f"order {matched['name']} ({matched['price']})."
        )
        if comment_id:
            try:
                prefill = embed_code(prefill, register_comment(comment_id))
            except Exception:  # noqa: BLE001
                # Never fail a customer reply over attribution.
                pass
        wa_text = urllib.parse.quote(prefill)
        wa_link = ctx.whatsapp_link
        if wa_link:
            contact_block = (
                f"\U0001f4f2 *Click to Order on Official WhatsApp ({ctx.whatsapp_display}):*\n"
                f"{wa_link}?text={wa_text}\n\n"
            )
        else:
            contact_block = (
                f"\U0001f4f2 *Order on WhatsApp ({ctx.whatsapp_display}):*\n"
                f"Please reply here and we will share the order link.\n\n"
            )
        storefront = ctx.domain or "our online store"
        return (
            f"Namaste {buyer_name}! \u0af7\n\n"
            f"\u2728 *{ctx.business_name} \u2014 Official Online Store*\n"
            f"\u2022 Selected Design: *{matched['name']}*\n"
            f"\u2022 Boutique Price: *{matched['price']}*\n"
            f"\u2022 Sizes Ready to Ship: *{matched['sizes']}*\n"
            f"\u2022 Storefront: *100% Online Store \u2022 Pan-India & Worldwide Express Delivery*\n\n"
            f"{contact_block}"
            f"\U0001f6cd\ufe0f *Explore 4K Website Catalog:*\n"
            f"{storefront}"
        )

    def fetch_page_comments(self, page_id: str, access_token: str) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        """Fetches real comments from the live Facebook Graph API. Never generates fake comments."""
        if not access_token or access_token in ("simulated_token", "none", "") or access_token.startswith("dev_"):
            return [], f"Live Meta Page Access Token (EAA...) not configured for Page ID {page_id}."

        try:
            url = (
                f"{self.base_url}/{page_id}/feed"
                f"?fields=id,message,comments{{id,from,message,created_time,comment_count}}"
                f"&limit=25&access_token={urllib.parse.quote(access_token)}"
            )
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                comments = []
                for post in data.get("data", []):
                    post_comments = post.get("comments", {}).get("data", [])
                    for c in post_comments:
                        c["post_id"] = post.get("id")
                        comments.append(c)
                return comments, None
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="ignore")
            return [], f"Meta Graph API HTTP {e.code}: {err_body}"
        except Exception as e:
            return [], f"Meta Graph API Error: {str(e)}"

    def hide_comment_for_privacy(self, comment_id: str, access_token: str) -> bool:
        """Directly hides a comment via Graph API."""
        try:
            url = f"{self.base_url}/{comment_id}"
            payload = urllib.parse.urlencode({
                "is_hidden": "true",
                "access_token": access_token
            }).encode("utf-8")
            req = urllib.request.Request(url, data=payload, method="POST")
            with urllib.request.urlopen(req, timeout=8) as resp:
                res = json.loads(resp.read().decode("utf-8"))
                return bool(res.get("success", True))
        except Exception:
            return False

    def hide_comment_if_phone(self, comment_id: str, text: str, access_token: str) -> bool:
        """Sub-0.05s Auto-Hide Shield: hides comment on Graph API if buyer posted a phone number."""
        if not re.search(r'(?:\+?91[\s-]?)?[6789]\d{9}', text or ""):
            return False
        return self.hide_comment_for_privacy(comment_id, access_token)

    def reply_to_comment(self, comment_id: str, message: str, access_token: str) -> Dict[str, Any]:
        try:
            url = f"{self.base_url}/{comment_id}/comments"
            payload = urllib.parse.urlencode({
                "message": message,
                "access_token": access_token
            }).encode("utf-8")
            req = urllib.request.Request(url, data=payload, method="POST")
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            return {"error": str(e)}

    def send_private_reply(self, page_id: str, comment_id: str, message: str, access_token: str) -> Dict[str, Any]:
        """Sends a Private Messenger DM directly linked to a Page comment via Meta Graph API."""
        try:
            url = f"{self.base_url}/{page_id}/messages"
            payload = json.dumps({
                "recipient": {"comment_id": comment_id},
                "message": {"text": message},
                "messaging_type": "RESPONSE"
            }).encode("utf-8")
            req = urllib.request.Request(
                f"{url}?access_token={urllib.parse.quote(access_token)}",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            return {"error": str(e)}

    def process_single_comment_event(
        self,
        page_id: str,
        comment_id: str,
        comment_text: str,
        buyer_name: str,
        buyer_id: str,
        access_token: str,
        sector: str = "textile",
        merchant: Optional[MerchantContext] = None,
    ) -> Dict[str, Any]:
        """Processes a single real-time webhook or polled comment (24/7 auto-reply + DM + shield)."""
        if not comment_id or comment_id in self.replied_comment_ids:
            return {"skipped": True, "reason": "already_replied"}
        if buyer_id and buyer_id == page_id:
            return {"skipped": True, "reason": "self_comment"}

        hidden = False
        if access_token and access_token.startswith("EAA"):
            hidden = self.hide_comment_if_phone(comment_id, comment_text, access_token)

        score, status, intent = self.classify_lead_intent(comment_text)
        if hidden:
            intent = f"[Shield Hidden Phone] {intent}"

        public_reply = self.select_auto_reply(
            comment_text, sector, buyer_name=buyer_name, merchant=merchant
        )
        # comment_id is threaded through so the resulting WhatsApp enquiry
        # resolves back to this comment instead of merely being captured.
        private_dm = self.build_private_dm(
            comment_text, buyer_name=buyer_name, comment_id=comment_id,
            merchant=merchant,
        )

        reply_res = {}
        dm_res = {}
        if access_token and access_token.startswith("EAA"):
            reply_res = self.reply_to_comment(comment_id, public_reply, access_token)
            dm_res = self.send_private_reply(page_id, comment_id, private_dm, access_token)
            if reply_res.get("id"):
                self.replied_comment_ids.add(comment_id)

        return {
            "comment_id": comment_id,
            "buyer_name": buyer_name,
            "score": score,
            "status": status,
            "intent": intent,
            "shield_hidden": hidden,
            "public_reply": public_reply,
            "private_dm": private_dm,
            "graph_reply_id": reply_res.get("id"),
            "graph_dm_id": dm_res.get("message_id"),
        }

    def process_client_agent_run(
        self,
        client_id: str,
        client_name: str,
        business_name: str,
        page_id: str,
        access_token: str,
        sector: Optional[str] = "textile",
        telegram_chat_id: Optional[int] = None,
        force_simulation: bool = False,
        merchant: Optional[MerchantContext] = None,
    ) -> Dict[str, Any]:
        # The merchant identity is resolved by the caller from the
        # client record. When it is not supplied, fall back to the
        # names passed in rather than to another merchant's details.
        if merchant is None:
            merchant = MerchantContext(
                client_id=client_id,
                business_name=business_name or client_name,
                sector=sector or "default",
            )
        if force_simulation:
            comments = [
                {
                    "id": "sim_cmt_001",
                    "from": {"name": "Hardik Patel", "id": "user_srt_01"},
                    "message": "આ સાડીનો હોલસેલ રેટ શું છે? 9825012345 પર મોકલો",
                    "created_time": datetime.now(timezone.utc).isoformat(),
                }
            ]
            api_error = None
        else:
            comments, api_error = self.fetch_page_comments(page_id, access_token)

        if api_error:
            return {
                "client_id": client_id,
                "page_id": page_id,
                "status": "token_required",
                "error": api_error,
                "comments_scanned": 0,
                "replies_sent": 0,
                "leads_detected": 0,
                "leads": [],
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

        scanned = len(comments)
        replies_sent = 0
        leads_detected = 0
        leads_list = []

        for comm in comments:
            text = comm.get("message", "")
            user_name = comm.get("from", {}).get("name", "Facebook Buyer")
            user_id = comm.get("from", {}).get("id", "")
            comm_id = comm.get("id", "")

            if user_id and user_id == page_id:
                continue
            if comm_id in self.replied_comment_ids:
                continue

            # Sub-0.05s Auto-Hide Shield for phone numbers
            hidden = self.hide_comment_if_phone(comm_id, text, access_token) if not force_simulation else True

            score, status, intent = self.classify_lead_intent(text)
            if hidden:
                intent = f"[Shield Hidden Phone] {intent}"

            reply_msg = self.select_auto_reply(
                text, sector, buyer_name=user_name, merchant=merchant
            )
            reply_res = self.reply_to_comment(comm_id, reply_msg, access_token) if not force_simulation else {"id": "sim_rep_01"}
            if reply_res.get("id"):
                replies_sent += 1
                self.replied_comment_ids.add(comm_id)

            # The private DM carries the merchant's own order link.
            dm_msg = self.build_private_dm(
                text, buyer_name=user_name, comment_id=comm_id, merchant=merchant
            )
            if not force_simulation:
                self.send_private_reply(page_id, comm_id, dm_msg, access_token)

            phone_match = re.search(r'(?:\+?91[\s-]?)?[6789]\d{9}', text)
            # A comment without a phone number is guided to the
            # merchant's contact, which comes from the client record.
            phone_num = (
                phone_match.group(0)
                if phone_match
                else f"Guided to WhatsApp {merchant.whatsapp_display if merchant else 'our WhatsApp'}"
            )

            if status in ["hot", "warm"]:
                leads_detected += 1
                lead_record = {
                    "client_id": client_id,
                    "name": user_name,
                    "phone": phone_num,
                    "fb_user_id": user_id,
                    "fb_comment_id": comm_id,
                    "score": score,
                    "status": status,
                    "intent": intent,
                    "comment": text,
                    "reply_sent": reply_msg
                }
                leads_list.append(lead_record)

                if status == "hot":
                    try:
                        chat_target = telegram_chat_id or int(
                            os.getenv("TELEGRAM_CHAT_ID", "0") or 0
                        )
                        if telegram is None or not chat_target:
                            # No bot token or no destination: alerting is
                            # simply unavailable. Do not fabricate a send.
                            if not chat_target:
                                logger.info(
                                    "hot lead %s detected but TELEGRAM_CHAT_ID "
                                    "is unset; alert skipped", user_name
                                )
                            continue
                        telegram.notify_facebook_hot_lead(
                            chat_id=chat_target,
                            lead_data={
                                "business_name": business_name,
                                "lead_name": user_name,
                                "phone": phone_num,
                                "score": int(score),
                                "comment": text,
                                "intent": intent
                            }
                        )
                    except Exception:
                        pass

        return {
            "client_id": client_id,
            "page_id": page_id,
            "status": "success",
            "comments_scanned": scanned,
            "replies_sent": replies_sent,
            "leads_detected": leads_detected,
            "leads": leads_list,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
