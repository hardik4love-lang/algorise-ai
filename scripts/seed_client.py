"""Restore the Shruhi client record into algorise_prod.db."""
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from engine.subscription_routes import ensure_shruhi_surat_pro_client  # noqa: E402


async def main():
    r = await ensure_shruhi_surat_pro_client()
    print("  seed result:", r)

    from engine.database import sync_session
    from engine.models_sqlalchemy import Client

    s = sync_session()
    for c in s.query(Client).all():
        print(f"  id={c.id}  name={c.name}  page={c.fb_page_id}  tier={c.tier}")
    s.close()


asyncio.run(main())