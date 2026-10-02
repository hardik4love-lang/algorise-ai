"""Insert the config.js script tag into every interactive surface.

The tag must load before any inline script that reads window.ALGORISE_CONFIG,
so it is placed immediately before the first inline <script> that is not a
CDN/library import.

Idempotent: running twice does not add a second tag.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

SURFACES = [
    "index.html",
    "dashboard.html",
    "creator_studio.html",
    "admin.html",
    "realtor_sales_console.html",
]

TAG = '<script src="/config.js"></script>'
MARKER = "ALGORISE_CONFIG"

results = []

for rel in SURFACES:
    p = ROOT / rel
    if not p.exists():
        results.append((rel, "missing", 0))
        continue

    text = p.read_text(encoding="utf-8")
    if TAG in text:
        results.append((rel, "already present", 0))
        continue

    # Place before the first inline script that reads the config.
    marker_at = text.find(MARKER)
    if marker_at == -1:
        results.append((rel, "no config reference; skipped", 0))
        continue

    # Walk back to the opening <script> of the block containing the marker.
    open_at = text.rfind("<script", 0, marker_at)
    if open_at == -1:
        results.append((rel, "could not locate enclosing script", 0))
        continue

    indent = " " * (len(text[:open_at].split("\n")[-1]))
    text = text[:open_at] + f"{indent}{TAG}\n" + text[open_at:]
    p.write_text(text, encoding="utf-8")
    results.append((rel, "tag inserted", open_at))

print()
for rel, status, pos in results:
    print(f"  {rel:<34} {status}")
print()
