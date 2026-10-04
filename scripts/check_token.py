"""Test the new user token: derive a Page token and check capabilities."""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from engine.facebook_token import (  # noqa: E402
    capability_report, find_page, list_pages,
)

TOKEN = os.getenv("SHRUHI_USER_TOKEN", "")
if not TOKEN:
    raise SystemExit("  set SHRUHI_USER_TOKEN")

pages = list_pages(TOKEN)
print(f"  pages this token reaches: {len(pages)}")
for p in pages:
    print(f"    {p.page_id}  {p.name}")

page = find_page(TOKEN, name_hint="shruhi collections")
if not page:
    raise SystemExit("  could not resolve the Shruhi page")

print()
print(f"  resolved: {page.page_id}  {page.name}")

cap = capability_report(page.page_token)
print(f"  scopes: {len(cap['scopes'])}")
print(f"  can_read_comments : {cap['can_read_comments']}")
print(f"  can_send_dm       : {cap['can_send_dm']}")
print(f"  can_post          : {cap['can_post']}")
print(f"  can_hide_comments : {cap['can_hide_comments']}")
