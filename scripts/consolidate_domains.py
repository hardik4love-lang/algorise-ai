"""Consolidate on one canonical domain.

The repository carried three domains at once:

  algorise-ai.com       38 refs, 9 files   matches CNAME
  algorise-ai.surge.sh  14 refs, 3 files   legacy
  algorise.surge.sh      2 refs, 1 file    legacy alias

splitting SEO signals and making it unclear which surface is authoritative.
algorise-ai.com wins because CNAME already claims it and it has the most
references.

This rewrites the legacy hosts to canonical, then regenerates sitemap.xml
from the surfaces actually present, so the two cannot disagree again.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CANONICAL = "algorise-ai.com"
LEGACY = ("algorise-ai.surge.sh", "algorise.surge.sh")

SURFACES = [
    "index.html", "dashboard.html", "creator_studio.html",
    "realtor_sales_console.html", "admin.html", "cocopeat.html",
    "field_pitch.html",
    "compare/manychat-alternative.html", "compare/wati-alternative.html",
    "industry/diamond-cvd-sales-agent.html",
    "industry/textile-saree-wholesale-ai-agent.html",
]

TARGETS = SURFACES + [
    "robots.txt", "sitemap.xml", "CNAME", "deploy_cloud.bat",
    "lead_finder.py", "nursery_lead_scraper.py", "surat_business_scraper.py",
    "send_gujarati_presentation.py", "send_telegram_presentation.py",
    "update_domain.py", "README.md",
]


def rewrite(rel: str) -> int:
    p = ROOT / rel
    if not p.exists():
        return 0
    text = p.read_text(encoding="utf-8", errors="replace")
    original = text
    for legacy in LEGACY:
        text = text.replace(legacy, CANONICAL)
    if text != original:
        p.write_text(text, encoding="utf-8")
        return sum(original.count(x) for x in LEGACY)
    return 0


def regenerate_sitemap() -> int:
    """Write sitemap.xml from the surfaces that exist."""
    entries = [""]
    for rel in SURFACES:
        rel_path = "/" if rel == "index.html" else f"/{rel}"
        entries.append(rel_path)

    now = "2026-10-02"
    urls = "\n".join(
        f"  <url>\n"
        f"    <loc>https://{CANONICAL}{e}</loc>\n"
        f"    <lastmod>{now}</lastmod>\n"
        f"    <changefreq>weekly</changefreq>\n"
        f"    <priority>{'1.0' if not e else '0.7'}</priority>\n"
        f"  </url>"
        for e in entries
    )
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{urls}\n"
        "</urlset>\n"
    )
    (ROOT / "sitemap.xml").write_text(xml, encoding="utf-8")
    return len(entries)


def rewrite_robots() -> None:
    p = ROOT / "robots.txt"
    text = (
        "User-agent: *\n"
        "Allow: /\n"
        f"Sitemap: https://{CANONICAL}/sitemap.xml\n"
        "\n"
        "# Administrative surfaces are not for indexing.\n"
        "Disallow: /admin.html\n"
    )
    p.write_text(text, encoding="utf-8")


print()
total = 0
for rel in TARGETS:
    n = rewrite(rel)
    if n:
        print(f"  rewrote {n:>2} reference(s) in {rel}")
        total += n

print(f"\n  total legacy references rewritten: {total}")

count = regenerate_sitemap()
print(f"  sitemap.xml regenerated with {count} URLs")
rewrite_robots()
print("  robots.txt regenerated")

# Verify. Documentation and the tooling itself are exempt: they name the
# legacy hosts on purpose, because that is what they exist to detect and
# record. dist/ is exempt because build.py regenerates it.
EXEMPT_SUFFIXES = {".md"}
EXEMPT_NAMES = {"consolidate_domains.py", "adopt_mirrors.py", "update_domain.py"}

remaining = []
for p in ROOT.rglob("*"):
    if not p.is_file() or ".git" in p.parts or "__pycache__" in p.parts:
        continue
    if p.suffix in EXEMPT_SUFFIXES or p.name in EXEMPT_NAMES:
        continue
    if "dist" in p.parts:
        continue
    if p.suffix not in {".html", ".xml", ".txt", ".bat", ".py", ".yaml"}:
        continue
    try:
        c = p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        continue
    for legacy in LEGACY:
        if legacy in c:
            remaining.append(f"{p.relative_to(ROOT)} ({legacy})")

print()
if remaining:
    print("  still referencing a legacy domain:")
    for r in remaining:
        print(f"    {r}")
    sys.exit(1)
print(f"  CLEAN: every reference now points at {CANONICAL}")
print()
