"""Adopt the newer dist/ mirrors into source.

compare_mirrors.py found that the four diverged mirrors are NEWER than their
source counterparts: the mirror copy carries a domain migration
(algorise-ai.surge.sh -> algorise-ai.com) in canonical tags, og:url,
og:image and JSON-LD, which source never received.

Syncing source into dist without this would have silently reverted that
migration on four SEO pages, breaking canonical tags and the structured data
that drives rich results.

Only files the comparison judged "MIRROR NEWER" are adopted. Where source is
newer, source wins. Nothing is overwritten blindly.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from compare_mirrors import SURFACES, classify  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent

print()
adopted = []
skipped = []

for rel in SURFACES:
    src_p, mir_p = ROOT / rel, ROOT / "dist" / rel
    if not (src_p.exists() and mir_p.exists()):
        continue

    src = src_p.read_text(encoding="utf-8", errors="replace")
    mir = mir_p.read_text(encoding="utf-8", errors="replace")

    if src == mir:
        continue

    verdict, in_mir, in_src = classify(src, mir)

    if not verdict.startswith("MIRROR NEWER"):
        skipped.append((rel, verdict))
        print(f"  KEEP SOURCE  {rel}  ({verdict})")
        continue

    # Record what is being taken, so the change is reviewable.
    domains_src = set(re.findall(r"https?://([a-z0-9.-]+)", src))
    domains_mir = set(re.findall(r"https?://([a-z0-9.-]+)", mir))
    gained = sorted(domains_mir - domains_src)

    src_p.write_text(mir, encoding="utf-8")
    adopted.append((rel, gained))
    print(f"  ADOPTED MIRROR  {rel}")
    if gained:
        print(f"                   introduces: {', '.join(gained)}")

print()
print(f"  adopted {len(adopted)}, kept source for {len(skipped)}")
print()
print("  Verify with: python scripts/compare_mirrors.py")
print()