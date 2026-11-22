import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ops_path = ROOT / "engine" / "client_agent_ops.py"
content = ops_path.read_text(encoding="utf-8")

support_func = '''
async def ensure_algorise_support_client() -> Dict[str, Any]:
    """Idempotently ensures Algorise Support client exists from client_algorise_support.json."""
    from datetime import datetime, timezone, timedelta
    from sqlalchemy import select
    from engine.client_auth import hash_pin
    from engine.database import db_manager
    from engine.models_sqlalchemy import Client, Subscription

    client_id = "client_algorise_support"
    client_config = load_client_config(client_id)
    client_settings = client_config.get("settings", {})
    sub_config = client_config.get("subscription", {})

    async with db_manager.session() as session:
        existing = (await session.execute(select(Client).where(Client.id == client_id))).scalar_one_or_none()
        if existing:
            existing.fb_page_id = client_config.get("fb_page_id", "algorise_tech_services")
            existing.fb_page_name = client_config.get("fb_page_name", "AlgoRise Tech Support")
            existing.city = client_config.get("city", "Surat")
            existing.tier = client_config.get("tier", "Tier 3: Omnichannel Pro")
        else:
            support_client = Client(
                id=client_id,
                name=client_config.get("name", "AlgoRise Tech Support & Onsite Engineering"),
                tier=client_config.get("tier", "Tier 3: Omnichannel Pro"),
                api_key_hash="",
                phone=client_config.get("phone", "+91 92270 95624"),
                email=client_config.get("email", "support@algorise-ai.com"),
                city=client_config.get("city", "Surat, Gujarat"),
                pin_hash=hash_pin("2026"),
                fb_page_id=client_config.get("fb_page_id", "algorise_tech_services"),
                fb_page_name=client_config.get("fb_page_name", "AlgoRise Tech Support & Hardware Engineering"),
                fb_access_token=None,
                is_active=True,
                settings=client_settings,
            )
            session.add(support_client)
            await session.flush()

            now = datetime.now(timezone.utc)
            sub = Subscription(
                client_id=client_id,
                plan_tier="omnichannel_pro",
                plan_name="TIER 3: OMNICHANNEL LEADSHIELD PRO (OWN PRODUCT INTERNAL SUITE)",
                monthly_price=30000.0,
                setup_fee=0.0,
                advance_amount=0.0,
                status="active",
                started_at=now,
                next_billing_at=now + timedelta(days=365),
                notes="Internal Pro Suite for Algorise Tech Support & Surat Onsite Engineering",
            )
            session.add(sub)

    return {
        "client_id": client_id,
        "pin": "2026",
        "name": client_config.get("name"),
        "tier": "Tier 3: Omnichannel Pro",
        "phone": "+91 92270 95624",
        "upi": "9227095624@upi"
    }
'''

if "def ensure_algorise_support_client" not in content:
    content += support_func
    ops_path.write_text(content, encoding="utf-8")
    print("SUCCESS: Added ensure_algorise_support_client to engine/client_agent_ops.py")
else:
    print("ALREADY EXISTS")
