"""
Client Billing & Subscription Tier Domain Service for Algorise AI Solutions.
Handles commercial tier pricing, plan resolution, and billing calculations.
"""

from typing import Dict, Any, Optional

# Commercial tier definitions
PLAN_PRICING: Dict[str, Dict[str, Any]] = {
    "starter": {
        "name": "Starter Merchant",
        "monthly": 12499.0,
        "setup": 12499.0,
        "advance_pct": 0.20,
    },
    "pro": {
        "name": "Surat Business Pro",
        "monthly": 29999.0,
        "setup": 29999.0,
        "advance_pct": 0.20,
    },
    "enterprise": {
        "name": "Enterprise / Agency",
        "monthly": 64999.0,
        "setup": 64999.0,
        "advance_pct": 0.20,
    },
}


def resolve_plan_tier(tier_raw: Optional[str]) -> str:
    """
    Normalizes and resolves the plan tier key.
    Defaults to 'pro' (Surat Business Pro) if missing or unrecognised.
    """
    if not tier_raw:
        return "pro"
    tier_key = str(tier_raw).lower().strip()
    return tier_key if tier_key in PLAN_PRICING else "pro"


def get_tier_pricing(tier_raw: Optional[str]) -> Dict[str, Any]:
    """
    Calculates commercial pricing, setup fee, and 20% advance for a plan tier.
    """
    tier_key = resolve_plan_tier(tier_raw)
    tier_info = PLAN_PRICING[tier_key]
    monthly_price = tier_info["monthly"]
    setup_fee = tier_info["setup"]
    advance_amount = setup_fee * tier_info["advance_pct"]

    return {
        "tier_key": tier_key,
        "tier_name": tier_info["name"],
        "monthly_price": monthly_price,
        "setup_fee": setup_fee,
        "advance_amount": advance_amount,
        "advance_pct": tier_info["advance_pct"],
    }
