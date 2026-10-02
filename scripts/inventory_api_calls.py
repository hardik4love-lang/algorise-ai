"""How each surface actually reaches the API, and whether it can work at all."""
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

SURFACES = [
    "index.html", "dashboard.html", "creator_studio.html",
    "realtor_sales_console.html", "admin.html", "cocopeat.html",
    "field_pitch.html",
    "compare/manychat-alternative.html", "compare/wati-alternative.html",
    "industry/diamond-cvd-sales-agent.html",
    "industry/textile-saree-wholesale-ai-agent.html",
]

FETCH_RE = re.compile(
    r"""fetch\(\s*(?P<q>['"`])(?P<url>[^'"`]{0,120})(?P=q)""", re.I | re.S
)
TEMPLATE_FETCH_RE = re.compile(r"fetch\(\s*`(?P<url>[^`]{0,160})`", re.I | re.S)

ROUTES = Counter()

for rel in SURFACES:
    p = ROOT / rel
    if not p.exists():
        continue
    text = p.read_text(encoding="utf-8", errors="replace")

    urls = [m.group("url") for m in FETCH_RE.finditer(text)]
    urls += [m.group("url") for m in TEMPLATE_FETCH_RE.finditer(text)]

    kinds = Counter()
    for u in urls:
        if u.startswith("/api/") or u.startswith("api/"):
            kinds["relative /api (needs same origin)"] += 1
        elif "localhost" in u or "127.0.0.1" in u:
            kinds["absolute localhost (dev only)"] += 1
        elif "onrender.com" in u or u.startswith("https://algorise"):
            kinds["absolute production"] += 1
        elif u.startswith("http"):
            host = u.split("/")[2]
            kinds[f"absolute third-party ({host})"] += 1
        else:
            kinds["other/relative"] += 1
        ROUTES[u.split("?")[0][:70]] += 1

    print(f"{rel}")
    print(f"   fetch() calls: {len(urls)}")
    for k, n in kinds.most_common():
        print(f"      {n:>3}x  {k}")
    if not urls:
        print("      (no fetch calls — static page)")
    print()

print("=" * 90)
print("MOST-CALLED URL PREFIXES ACROSS ALL SURFACES")
print("=" * 90)
for u, n in ROUTES.most_common(18):
    print(f"  {n:>3}x  {u}")