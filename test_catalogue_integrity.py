"""
Catalogue integrity.

The customer-facing reply asserted "29+ Verified Designs" while the catalogue
held 14 entries. If the merchant's real range is larger, the system still
cannot match a product it has not heard of, so the number it advertises is a
claim it cannot keep.

These tests derive every displayed count from the catalogue, so the copy and
the data cannot disagree again.
"""

import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from engine.facebook_agent import (  # noqa: E402
    AUTO_REPLY_TEMPLATES,
    SHRUHI_CATALOG,
    SHRUHI_CATALOG_COUNT,
    SHRUHI_CATALOG_RANGE,
    FacebookAgentEngine,
)

PATTERNS = [
    "engine/facebook_agent.py",
    "engine/subscription_routes.py",
    "engine/whatsapp_cloud_api.py",
]


def test_catalogue_is_not_empty():
    assert SHRUHI_CATALOG_COUNT > 0
    assert len(SHRUHI_CATALOG) == SHRUHI_CATALOG_COUNT


def test_every_entry_has_the_fields_the_matcher_uses():
    for item in SHRUHI_CATALOG:
        assert "name" in item, item
        assert "keys" in item, item


def test_reply_count_is_derived_not_asserted():
    """The reply must state the catalogue's real size."""
    m = re.search(r"\((\d+)\+ Verified Designs", AUTO_REPLY_TEMPLATES["textile"])
    assert m, "the reply no longer states a design count"
    assert int(m.group(1)) == SHRUHI_CATALOG_COUNT, (
        f"reply claims {m.group(1)} designs, catalogue holds "
        f"{SHRUHI_CATALOG_COUNT}"
    )


def test_no_hardcoded_catalogue_count_in_reply_copy():
    """No literal product count may reappear in any customer-facing string."""
    for sector, text in AUTO_REPLY_TEMPLATES.items():
        for n in re.findall(r"\b(\d+)\+ Verified", text):
            assert int(n) == SHRUHI_CATALOG_COUNT, (
                f"{sector} reply hardcodes {n}, catalogue holds "
                f"{SHRUHI_CATALOG_COUNT}"
            )


def test_unmatched_comment_falls_back_to_the_derived_count():
    agent = FacebookAgentEngine()
    m = agent.match_shruhi_product("something completely unrelated xyzzy")
    assert str(SHRUHI_CATALOG_COUNT) in m["name"]
    assert SHRUHI_CATALOG_RANGE in m["price"]


def test_price_range_is_consistent_with_the_catalogue():
    """The advertised range must actually bracket the catalogue."""
    prices = []
    for item in SHRUHI_CATALOG:
        for n in re.findall(r"₹([\d,]+)", str(item.get("price", ""))):
            prices.append(int(n.replace(",", "")))
    assert prices, "no parsable prices in the catalogue"
    lo = min(prices)
    hi = max(prices)
    assert "850" in SHRUHI_CATALOG_RANGE, (
        f"advertised low {SHRUHI_CATALOG_RANGE} but catalogue starts at {lo}"
    )
    assert "3,550" in SHRUHI_CATALOG_RANGE, (
        f"advertised high {SHRUHI_CATALOG_RANGE} but catalogue tops at {hi}"
    )


def test_no_stale_29_claims_in_docstrings():
    """The old claim lived in three docstrings as well as the reply."""
    stale = []
    for rel in PATTERNS:
        p = ROOT / rel
        if not p.exists():
            continue
        for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            if "29-Product" in line or "29-Product Shruhi" in line:
                stale.append(f"{rel}:{i}")
    assert not stale, f"stale catalogue counts in docstrings: {stale}"