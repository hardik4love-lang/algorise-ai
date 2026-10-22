"""Test that a reply is built from the client record, not a fixed merchant.

The auto-reply used to carry one merchant's name, domain and WhatsApp
number in the template. A second client then received a reply pointing
at the first merchant, and onboarding required editing the reply code.

These tests pin the behaviour that fixed: every merchant-specific value
in a reply comes from the client record, and a client without a number
never receives another merchant's contact details.
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from engine.merchant_context import (  # noqa: E402
    MerchantContext,
    load_merchant_context,
)
from engine.facebook_agent import FacebookAgentEngine  # noqa: E402


class FakeClient:
    """A stand-in for the Client model."""

    def __init__(self, id_, name, phone, settings=None):
        self.id = id_
        self.name = name
        self.phone = phone
        self.settings = settings or {}


@pytest.fixture
def engine():
    return FacebookAgentEngine(api_version="v20.0")


def test_context_uses_client_record():
    client = FakeClient(
        "client_a",
        "Alpha Textiles (Ravi Patel)",
        "+91 98765 43210",
        {"domain": "https://alpha.example", "agent_rules": {"sector": "textile"}},
    )
    ctx = load_merchant_context(client)

    assert ctx.client_id == "client_a"
    # The contact person's name is not part of the trading name.
    assert ctx.business_name == "Alpha Textiles"
    assert ctx.whatsapp_number == "+91 98765 43210"
    assert ctx.domain == "https://alpha.example"
    assert ctx.sector == "textile"


def test_reply_uses_the_clients_identity(engine):
    ctx = load_merchant_context(
        FakeClient(
            "client_a",
            "Alpha Textiles (Ravi Patel)",
            "+91 98765 43210",
            {"domain": "https://alpha.example", "agent_rules": {"sector": "textile"}},
        )
    )
    reply = engine.select_auto_reply("ભાવ શું છે?", sector="textile", merchant=ctx)

    assert "Alpha Textiles" in reply
    assert "alpha.example" in reply
    assert "9876543210" in reply
    # No other merchant's details.
    assert "Shruhi" not in reply
    assert "63552" not in reply


def test_two_clients_get_different_replies(engine):
    alpha = load_merchant_context(
        FakeClient("a", "Alpha Textiles (Ravi)", "+91 98765 43210",
                   {"domain": "https://alpha.example"})
    )
    beta = load_merchant_context(
        FakeClient("b", "Beta Diamonds (Neha)", "+91 91234 56789",
                   {"domain": "https://beta.example"})
    )

    alpha_reply = engine.select_auto_reply("price?", merchant=alpha)
    beta_reply = engine.select_auto_reply("price?", merchant=beta)

    assert "Alpha Textiles" in alpha_reply
    assert "9876543210" in alpha_reply
    assert "Beta Diamonds" in beta_reply
    assert "9123456789" in beta_reply

    # Neither reply mentions the other merchant.
    assert "Beta" not in alpha_reply
    assert "Alpha" not in beta_reply
    assert "9876543210" not in beta_reply
    assert "9123456789" not in alpha_reply


def test_client_without_a_number_never_borrows_one(engine):
    """A client with no WhatsApp number must not receive someone else's."""
    ctx = load_merchant_context(
        FakeClient("c", "Gamma Apparel (Kim)", None, {"domain": "https://gamma.example"})
    )
    reply = engine.select_auto_reply("ભાવ?", merchant=ctx)

    assert "Gamma Apparel" in reply
    # No number at all, and specifically not the first merchant's.
    assert "63552" not in reply
    assert "wa.me/" not in reply


def test_private_dm_uses_the_clients_link(engine):
    ctx = load_merchant_context(
        FakeClient("d", "Delta Sarees (Rhea)", "+91 99887 76655",
                   {"domain": "https://delta.example"})
    )
    dm = engine.build_private_dm("કિંમત?", merchant=ctx)

    assert "Delta Sarees" in dm
    assert "wa.me/9988776655" in dm
    assert "63552" not in dm


def test_whatsapp_link_normalises_the_country_code():
    ctx = MerchantContext(whatsapp_number="+91 98765 43210")
    assert ctx.whatsapp_link == "https://wa.me/9876543210"

    ctx = MerchantContext(whatsapp_number="9876543210")
    assert ctx.whatsapp_link == "https://wa.me/9876543210"

    ctx = MerchantContext(whatsapp_number="")
    assert ctx.whatsapp_link == ""


def test_catalogue_claim_comes_from_the_client_record():
    ctx = MerchantContext(catalogue_count=12, catalogue_range="₹100 – ₹900")
    assert "12+ Verified Designs" in ctx.catalogue_claim
    assert "₹100 – ₹900" in ctx.catalogue_claim

    # A client with no catalogue makes no catalogue claim.
    empty = MerchantContext()
    assert empty.catalogue_claim == ""


def test_source_has_no_fixed_merchant_phone():
    """The reply code must not carry a merchant number any more."""
    source = (
        ROOT / "engine" / "facebook_agent.py"
    ).read_text(encoding="utf-8")
    for literal in ("63552 85433", "916355285433"):
        assert literal not in source, (
            f"facebook_agent.py still hardcodes the merchant number {literal}"
        )
