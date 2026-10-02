"""Inventory: API base URLs, hardcoded endpoints, and agent wiring per surface.

Answers three questions that determine whether unification is even possible:
  1. Do the surfaces agree on where the API lives?
  2. Which surfaces call Meta directly from the browser?
  3. Which surfaces reference credentials or chat IDs in client code?
"""
import re
from collections import Counter, defaultdict
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

URL_RE = re.compile(r"https?://[A-Za-z0-9._~:/?#\[\]@!$&'()*+,;=%-]+")
API_RE = re.compile(r"(local_api|cloud_api|api_base|apiBase|API_URL|API_BASE|BASE_URL)\s*[=:]\s*['\"]([^'\"]+)['\"]", re.I)

print("=" * 96)
print("API ENDPOINTS DECLARED PER SURFACE")
print("=" * 96)
endpoints = defaultdict(set)
for rel in SURFACES:
    p = ROOT / rel
    if not p.exists():
        continue
    text = p.read_text(encoding="utf-8", errors="replace")
    found = {m.group(2) for m in API_RE.finditer(text)}
    endpoints[rel] = found
    status = ", ".join(sorted(found)) if found else "-- none declared --"
    print(f"{rel:<44} {status}")

all_eps = Counter()
for v in endpoints.values():
    all_eps.update(v)
print()
print("distinct declared endpoints:")
for ep, n in all_eps.most_common():
    print(f"  {n:>2}x  {ep}")

print()
print("=" * 96)
print("BROWSER-SIDE EXTERNAL CALLS (must be proxied, not called from a page)")
print("=" * 96)
EXTERNAL = ("graph.facebook.com", "api.telegram.org", "api.whatsapp.com",
            "graph.facebook.net", "text.pollinations.ai")
for rel in SURFACES:
    p = ROOT / rel
    if not p.exists():
        continue
    text = p.read_text(encoding="utf-8", errors="replace")
    hits = [e for e in EXTERNAL if e in text]
    if hits:
        n = sum(text.count(e) for e in hits)
        print(f"  {rel:<44} {n:>3}x  {', '.join(hits)}")

print()
print("=" * 96)
print("HARDCODE CREDENTIALS / IDENTIFIERS IN CLIENT CODE")
print("=" * 96)
PATTERNS = {
    "telegram bot token": r"\b\d{8,10}:[A-Za-z0-9_-]{30,}",
    "telegram chat id":   r"\b(?:chat_id|TELEGRAM_CHAT_ID)['\"]?\s*[:=]\s*['\"]?\d{8,}",
    "facebook page id":   r"\b6\d{12}\b",
    "phone number":       r"\+91[\s-]?\d{4,5}[\s-]?\d{5}",
    "wa.me deep link":    r"wa\.me/\d{10,}",
}
for rel in SURFACES:
    p = ROOT / rel
    if not p.exists():
        continue
    text = p.read_text(encoding="utf-8", errors="replace")
    findings = []
    for label, pat in PATTERNS.items():
        n = len(re.findall(pat, text))
        if n:
            findings.append(f"{label} x{n}")
    if findings:
        print(f"  {rel:<44} {', '.join(findings)}")

print()
print("=" * 96)
print("DUPLICATION: source tree vs dist/ mirror")
print("=" * 96)
diffs = same = 0
for rel in SURFACES:
    src = ROOT / rel
    d = ROOT / "dist" / rel
    if not (src.exists() and d.exists()):
        continue
    if src.read_bytes() == d.read_bytes():
        same += 1
    else:
        diffs += 1
        print(f"  DIVERGED: {rel}")
print(f"  identical: {same}   diverged: {diffs}")
print("  A diverged mirror means the served page and the source differ.")