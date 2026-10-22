"""Merchant identity resolved from the client record.

The auto-reply used to hardcode one merchant's name, domain and
WhatsApp number. Onboarding a second client then required editing the
reply code, which is the tell that the product is not multi-tenant.

This module resolves that identity from the client record so a reply is
built from the database, and a new client needs no code change.
"""
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

# A reply always needs somewhere to send the buyer. When the client has
# no number configured the reply says so rather than pointing at another
# merchant's.
UNKNOWN_PHONE_DISPLAY = "our WhatsApp"


@dataclass
class MerchantContext:
    """The identity used inside an auto-reply."""

    client_id: str = ""
    business_name: str = "our store"
    domain: str = ""
    whatsapp_number: str = ""
    sector: str = "default"
    catalogue_count: int = 0
    catalogue_range: str = ""
    custom_greeting: str = ""

    @property
    def whatsapp_display(self) -> str:
        if not self.whatsapp_number:
            return UNKNOWN_PHONE_DISPLAY
        return self.whatsapp_number

    @property
    def whatsapp_link(self) -> str:
        """The wa.me link, or an empty string when no number is set."""
        if not self.whatsapp_number:
            return ""
        digits = "".join(ch for ch in self.whatsapp_number if ch.isdigit())
        if not digits:
            return ""
        # wa.me expects the number without a country code prefix of 91
        # duplicated, and without the leading plus.
        if digits.startswith("91") and len(digits) > 10:
            digits = digits[2:]
        return f"https://wa.me/{digits}"

    @property
    def catalogue_claim(self) -> str:
        """The catalogue summary, or an empty string when there is none."""
        if not self.catalogue_count:
            return ""
        summary = f"{self.catalogue_count}+ Verified Designs"
        if self.catalogue_range:
            summary += f" • {self.catalogue_range}"
        return summary

    def from_settings(self, settings: Optional[Dict[str, Any]]) -> "MerchantContext":
        """Fill the context from a client settings mapping."""
        if not isinstance(settings, dict):
            return self

        rules = settings.get("agent_rules")
        if not isinstance(rules, dict):
            rules = {}

        self.domain = settings.get("domain") or self.domain
        self.sector = (rules.get("sector") or settings.get("sector") or self.sector)
        self.custom_greeting = rules.get("custom_greeting") or self.custom_greeting
        self.catalogue_count = int(rules.get("catalogue_count") or 0)
        self.catalogue_range = rules.get("catalogue_range") or ""

        # The WhatsApp number may live in settings, in agent rules, or on
        # the client record itself.
        for candidate in (
            rules.get("whatsapp"),
            settings.get("whatsapp"),
            settings.get("whatsapp_number"),
            rules.get("whatsapp_number"),
        ):
            if candidate and not self.whatsapp_number:
                self.whatsapp_number = str(candidate)

        return self

    def contact_line(self) -> str:
        """The order-contact sentence for this merchant."""
        link = self.whatsapp_link
        if not link:
            return f"📲 Order on WhatsApp: {self.whatsapp_display}"
        return f"📲 Order on WhatsApp: {self.whatsapp_display} ({link})"


def _business_name_from(client_name: str) -> str:
    """Derive the trading name from a client record name.

    Client names are stored as "Business (Contact Person)". Only the
    business part belongs in a reply.
    """
    if not client_name:
        return ""
    if "(" in client_name:
        return client_name.split("(")[0].strip()
    return client_name.strip()


def load_merchant_context(client) -> MerchantContext:
    """Build the merchant context from a Client record.

    The WhatsApp number comes from the client record when it is set.
    It is never inherited from another merchant: a client without a
    number gets a reply that asks the buyer to respond instead of
    pointing them at someone else.
    """
    if client is None:
        return MerchantContext()

    settings = client.settings if isinstance(client.settings, dict) else {}

    ctx = MerchantContext(
        client_id=getattr(client, "id", "") or "",
        business_name=_business_name_from(getattr(client, "name", "") or ""),
        sector="default",
    )

    # The client record holds the canonical phone number.
    phone = getattr(client, "phone", None)
    if phone:
        ctx.whatsapp_number = str(phone)

    ctx.from_settings(settings)
    return ctx
