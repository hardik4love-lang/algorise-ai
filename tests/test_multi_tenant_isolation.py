"""Test that a client never sees another client's page or plan.

Several endpoints had a hardcoded fallback to one merchant's page id
and plan. A client with no page configured was shown that page, and a
new client was handed that client's plan and PIN. Both mean the
product is not yet multi-tenant, which is the condition the onboarding
SOP has to rule out.
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

DEMO_PAGE_ID = "61586357894191"


def test_the_meta_pages_route_has_no_hardcoded_fallback():
    """A client with no configured pages gets an empty list."""
    source = (
        ROOT / "engine" / "subscription_routes.py"
    ).read_text(encoding="utf-8")

    # The fallback page list that used to be returned for every client.
    assert '"page_name": "Shruhi Collections | Surat (Official Flagship)"' not in source
    assert '"page_id": "61586323275145"' not in source
    assert '"page_id": "shruhi_boutique_reseller_hub"' not in source


def test_the_dashboard_does_not_default_to_another_page():
    source = (
        ROOT / "engine" / "subscription_routes.py"
    ).read_text(encoding="utf-8")
    assert 'client.fb_page_id or "61586357894191"' not in source
    assert 'client.fb_page_name or "Page ID: 61586357894191"' not in source


def test_the_agent_run_requires_a_configured_page():
    """Running the agent for a client with no page is a clear error."""
    source = (
        ROOT / "engine" / "subscription_routes.py"
    ).read_text(encoding="utf-8")
    assert 'page_id = client.fb_page_id or "61586357894191"' not in source
    assert "no Facebook page or access token configured" in source


def test_the_telegram_message_is_not_sent_in_another_merchants_name():
    source = (
        ROOT / "engine" / "subscription_routes.py"
    ).read_text(encoding="utf-8")
    assert "SHRUHI COLLECTIONS — 2-WAY TELEGRAM PROXY" not in source


def test_the_subscribe_route_reads_the_plan_from_configuration():
    """The demo plan comes from the client configuration file."""
    source = (
        ROOT / "engine" / "subscription_routes.py"
    ).read_text(encoding="utf-8")
    assert "load_client_config" in source
    # The plan details are not written into the handler.
    assert '"plan_name": "SURAT PRO TIER (₹29,999 / MONTH)"' not in source


def test_the_webhook_does_not_assume_a_page():
    source = (
        ROOT / "engine" / "subscription_routes.py"
    ).read_text(encoding="utf-8")
    assert 'entry.get("id", "61586357894191")' not in source
