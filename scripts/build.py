"""Deterministic build: source surfaces into dist/, then generate config.

One command produces the deployable tree. Previously dist/ was maintained
by hand, which is how five surfaces ended up serving a different document
than the repository contained.

    python scripts/build.py            # build
    python scripts/build.py --check    # fail if dist/ is stale or missing
    python scripts/build.py --check-all   # also report working-tree drift

The check mode is what CI runs, so a stale dist/ fails the pipeline instead
of being discovered by a visitor.
"""

from __future__ import annotations

import argparse
import filecmp
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Windows ships npx as a .cmd shim, which subprocess cannot resolve.
_NPX = 'npx.cmd' if os.name == 'nt' else 'npx'
DIST = ROOT / "dist"

# Copied verbatim from source.
SURFACES = [
    "index.html", "dashboard.html", "creator_studio.html",
    "realtor_sales_console.html", "admin.html", "cocopeat.html",
    "field_pitch.html",
    "compare/manychat-alternative.html", "compare/wati-alternative.html",
    "industry/diamond-cvd-sales-agent.html",
    "industry/textile-saree-wholesale-ai-agent.html",
]

# Copied verbatim from source (assets and static root files).
STATIC_FILES = ["CNAME", "robots.txt", "sitemap.xml", "brand.js"]
STATIC_DIRS = ["assets"]


# Generated from source rather than maintained by hand.
#   200.html           - SPA fallback for static hosts that use it
#   cocopeat/index.html - clean-URL variant of cocopeat.html
GENERATED = {"200.html": "index.html", "cocopeat/index.html": "cocopeat.html"}


def sync(verbose: bool = True) -> list[str]:
    """Copy source into dist. Returns the list of copied paths."""
    copied: list[str] = []
    DIST.mkdir(parents=True, exist_ok=True)

    for rel in SURFACES + STATIC_FILES:
        src = ROOT / rel
        if not src.exists():
            continue
        dest = DIST / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        copied.append(rel)

    for rel in STATIC_DIRS:
        src = ROOT / rel
        if not src.is_dir():
            continue
        dest = DIST / rel
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(src, dest, ignore=shutil.ignore_patterns("*.pyc", "__pycache__"))
        copied.append(f"{rel}/")

    for dest_rel, source_rel in GENERATED.items():
        src = ROOT / source_rel
        if not src.exists():
            continue
        dest = DIST / dest_rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        copied.append(f"{dest_rel} (from {source_rel})")

    # Compile Tailwind at build time. The pages used to load the Play CDN,
    # which shipped ~407 KB of compiler and generated the stylesheet in the
    # browser; on a slow connection the page rendered unstyled for seconds.
    r = subprocess.run(
        [_NPX, 'tailwindcss', '-i', 'app.css', '-o', str(DIST / 'app.css'),
         '--minify'],
        cwd=ROOT, capture_output=True, text=True,
    )
    if r.returncode != 0:
        print(f'  WARNING: tailwind build failed:\n{(r.stdout + r.stderr)[-500:]}')
    else:
        size = (DIST / 'app.css').stat().st_size
        copied.append(f'app.css ({size // 1024} KB compiled)')

    # config.js is generated, never copied.
    cfg = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "gen_config.py")],
        cwd=ROOT, capture_output=True, text=True,
    )
    if cfg.returncode != 0:
        print(f"  gen_config failed:\n{cfg.stderr}")
        raise SystemExit(1)
    copied.append("config.js")

    if verbose:
        print(f"  built {len(copied)} entries into dist/")
    return copied


def is_stale() -> list[str]:
    """Files where dist/ does not match source, or dist/ is missing."""
    stale: list[str] = []
    for rel in SURFACES + STATIC_FILES:
        src, dest = ROOT / rel, DIST / rel
        if not src.exists():
            continue
        if not dest.exists():
            stale.append(f"{rel} (missing from dist/)")
        elif not filecmp.cmp(src, dest, shallow=False):
            stale.append(f"{rel} (differs from source)")

    if not (DIST / "config.js").exists():
        stale.append("config.js (missing; run gen_config.py)")
    return stale


def untracked_in_dist() -> list[str]:
    """Files in dist/ with no counterpart in source.

    These are leftovers from the hand-maintained era. After a build they
    should not exist, because dist/ is fully derived.
    """
    expected = (
        set(SURFACES) | set(STATIC_FILES) | {"config.js"} | set(STATIC_DIRS)
        | set(GENERATED)
    )
    found = []
    for p in DIST.rglob("*"):
        if p.is_dir():
            continue
        rel = str(p.relative_to(DIST)).replace("\\", "/")
        top = rel.split("/")[0]
        if rel in expected or top in STATIC_DIRS:
            continue
        found.append(rel)
    return found


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true",
                        help="report staleness without rebuilding")
    parser.add_argument("--check-all", action="store_true",
                        help="also list untracked files in dist/")
    args = parser.parse_args()

    if args.check or args.check_all:
        stale = is_stale()
        print("\n  BUILD CHECK\n  " + "-" * 52)
        if stale:
            print(f"  {len(stale)} stale item(s):")
            for s in stale:
                print(f"    {s}")
            print("\n  Fix with: python scripts/build.py\n")
            return 1
        print("  dist/ matches source.")

        if args.check_all:
            extra = untracked_in_dist()
            if extra:
                print(f"\n  {len(extra)} untracked file(s) in dist/:")
                for e in extra[:15]:
                    print(f"    {e}")
                print()
            else:
                print("  no untracked files in dist/.")
        print()
        return 0

    sync()
    stale = is_stale()
    if stale:
        print("  WARNING: build completed but these still differ:")
        for s in stale:
            print(f"    {s}")
        return 1
    print("  dist/ is current.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())