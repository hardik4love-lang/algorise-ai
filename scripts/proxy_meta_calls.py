"""Rewire dashboard.html's Meta Graph calls onto the backend proxy.

Replaces the browser-side graph.facebook.com URLs with calls to
/api/v1/meta/*. Each substitution is verified against the built dist/ copy
too, because that is what visitors receive.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

SUBSTITUTIONS = [
    # (regex matching the fetch target, replacement expression)
    (
        r"https://graph\.facebook\.com/v19\.0/\$\{encodeURIComponent\(pageId\)\}/feed\?fields=id,message,created[^`'\"]*",
        "${API_BASE}/meta/feed",
    ),
    (
        r"https://graph\.facebook\.com/v19\.0/\$\{encodeURIComponent\(c\.id\)\}/comments\?[^`'\"]*",
        "${API_BASE}/meta/comments",
    ),
    (
        r"https://graph\.facebook\.com/v19\.0/\$\{encodeURIComponent\(c\.id\)\}\?[^`'\"]*",
        "${API_BASE}/meta/object",
    ),
    (
        r"https://graph\.facebook\.com/v19\.0/\$\{encodeURIComponent\(id\)\}\?[^`'\"]*",
        "${API_BASE}/meta/object",
    ),
    (
        r"https://graph\.facebook\.com/v19\.0/\$\{encodeURIComponent\(p\.page_id\)\}\?[^`'\"]*",
        "${API_BASE}/meta/object",
    ),
]


def rewrite(path: Path) -> int:
    text = path.read_text(encoding="utf-8", errors="replace")
    original = text
    count = 0

    for pattern, replacement in SUBSTITUTIONS:
        text, n = re.subn(pattern, replacement, text)
        count += n

    if text != original:
        path.write_text(text, encoding="utf-8")
    return count


print()
total = 0
for rel in ("dashboard.html", "dist/dashboard.html"):
    p = ROOT / rel
    if not p.exists():
        continue
    n = rewrite(p)
    total += n
    print(f"  {rel:<24} {n} URL(s) rewritten")

print(f"\n  total: {total}")

remaining = []
for rel in ("dashboard.html", "dist/dashboard.html"):
    p = ROOT / rel
    if p.exists() and "graph.facebook.com" in p.read_text(
        encoding="utf-8", errors="replace"
    ):
        remaining.append(rel)
print(f"  files still referencing graph.facebook.com: {remaining or 'none'}")
print()
sys.exit(0)
