"""Generate config.js for the web surfaces.

One build step, one place that decides where the API lives. Previously the
answer was hardcoded in three surfaces with a fallback chain that tried
localhost first and silently retried production, so a developer testing
locally and a visitor on the deployed site could run against different
backends while both appeared to work.

Values come from the environment. Nothing is committed, so the API host is a
deployment concern rather than a source one.

    API_BASE_URL=https://algorise-ai-backend.onrender.com python scripts/gen_config.py
    python scripts/gen_config.py --check          # verify it is current
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"

DEFAULT_API = "https://algorise-ai-backend.onrender.com"
LOCAL_API = "http://localhost:8000"


def _sha() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=ROOT, capture_output=True, text=True,
        ).stdout.strip()[:12]
    except OSError:
        return "unknown"

TEMPLATE = """/* GENERATED FILE - do not edit.
 * Produced by scripts/gen_config.py at build time.
 * Source: API_BASE_URL environment variable.
 * Generated: __GENERATED__
 */
window.ALGORISE_CONFIG = __CONFIG__;
"""


def _js_config(api_base: str, api_base_dev: str) -> str:
    """Build the config object as JSON.

    Constructed programmatically rather than by formatting a template: the
    object contains braces, which collide with str.format and produce a
    KeyError on 'generated'.
    """
    import json

    return json.dumps(
        {
            "apiBase": api_base.rstrip("/"),
            "apiBaseDev": api_base_dev.rstrip("/"),
            "apiVersion": "v1",
            "buildSha": _sha(),
            "builtAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        },
        indent=2,
    )


def render(api_base: str, api_base_dev: str) -> str:
    return (
        TEMPLATE
        .replace("__GENERATED__", datetime.now(timezone.utc)
                 .isoformat(timespec="seconds"))
        .replace("__CONFIG__", _js_config(api_base, api_base_dev))
    )


def write() -> Path:
    api_base = os.getenv("API_BASE_URL", DEFAULT_API).strip()
    api_base_dev = os.getenv("API_BASE_URL_DEV", LOCAL_API).strip()
    content = render(api_base, api_base_dev)

    DIST.mkdir(parents=True, exist_ok=True)
    target = DIST / "config.js"
    target.write_text(content, encoding="utf-8")
    return target


def check() -> int:
    """Is the deployed config.js consistent with the current environment?"""
    target = DIST / "config.js"
    if not target.exists():
        print("  config.js missing. Run: python scripts/gen_config.py")
        return 1

    existing = target.read_text(encoding="utf-8")
    api_base = os.getenv("API_BASE_URL", DEFAULT_API).strip().rstrip("/")
    # The config object is emitted as JSON, so keys are quoted.
    if f'"apiBase": "{api_base}"' in existing:
        print(f"  config.js is current ({api_base})")
        return 0

    found = re.search(r'"apiBase"\s*:\s*"([^"]+)"', existing)
    print(
        f"  STALE: config.js points at {found.group(1) if found else '?'}, "
        f"environment says {api_base}"
    )
    print("  Regenerate: python scripts/gen_config.py")
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check", action="store_true",
        help="verify config.js matches the environment; do not write",
    )
    args = parser.parse_args()

    if args.check:
        return check()

    target = write()
    print(f"  wrote {target}")
    print(f"  apiBase    = {os.getenv('API_BASE_URL', DEFAULT_API)}")
    print(f"  apiBaseDev = {os.getenv('API_BASE_URL_DEV', LOCAL_API)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())