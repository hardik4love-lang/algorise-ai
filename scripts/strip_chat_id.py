"""Strip the hardcoded Telegram chat id from the dashboard.

The browser sent chat_id: '8737013099' in seven places. The backend now
defaults it from TELEGRAM_CHAT_ID, so the client no longer needs to know the
operator's notification destination.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHAT_ID = "8737013099"

for rel in ("dashboard.html", "field_pitch.html", "index.html", "admin.html",
            "creator_studio.html", "realtor_sales_console.html", "cocopeat.html",
            "compare/manychat-alternative.html", "compare/wati-alternative.html",
            "industry/diamond-cvd-sales-agent.html",
            "industry/textile-saree-wholesale-ai-agent.html"):
    p = ROOT / rel
    if not p.exists():
        continue
    t = p.read_text(encoding="utf-8")
    n = t.count(CHAT_ID)
    if not n:
        continue

    # Drop the field entirely where it is a JSON body property, so the
    # backend uses its configured default.
    t = re.sub(
        rf"\s*chat_id:\s*['\"]?{CHAT_ID}['\"]?\s*,?\s*",
        "\n      ",
        t,
    )
    # Anything left is a fallback default in a JS expression.
    t = t.replace(f"'{CHAT_ID}'", "undefined")
    t = t.replace(f'"{CHAT_ID}"', "undefined")
    t = t.replace(CHAT_ID, "")

    p.write_text(t, encoding="utf-8")
    print(f"  {rel}: {n} occurrence(s) removed")

print()
print("  Verify the endpoint still resolves a destination server-side:")
print("    POST /api/v1/telegram/send with only {\"text\": ...}")
