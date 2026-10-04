"""
Reproduce the Render build locally.

Render runs `pip install -r requirements.txt` then
`uvicorn engine.main:app`. This creates an isolated virtual environment
containing ONLY what requirements.txt lists, installs it, and tries the same
import. Whatever fails here fails on Render.

The local interpreter has packages installed that requirements.txt does not
declare, which is exactly how a missing dependency reaches production.
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def run(cmd, cwd=None, timeout=900):
    return subprocess.run(
        cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout, shell=False
    )


def main():
    venv = Path(tempfile.mkdtemp()) / "rendercheck"
    print("  creating isolated venv (this takes a minute)...")

    r = run([sys.executable, "-m", "venv", str(venv)])
    if r.returncode != 0:
        print("  venv creation failed:", r.stderr[-400:])
        return 1

    py = venv / "Scripts" / "python.exe"
    if not py.exists():
        py = venv / "bin" / "python"

    r = run([str(py), "-m", "pip", "install", "-q", "--upgrade", "pip"], timeout=600)
    r = run([str(py), "-m", "pip", "install", "-q", "-r", "requirements.txt"],
            cwd=ROOT, timeout=1800)
    if r.returncode != 0:
        print("  REQUIREMENTS INSTALL FAILED:")
        print("   ", r.stderr[-1500:])
        return 1
    print("  requirements.txt installed cleanly")

    # Same import Render performs, plus a route dump written to a file so the
    # comparison does not depend on parsing stdout.
    r = run(
        [str(py), "scripts/dump_routes.py"], cwd=ROOT, timeout=300,
    )
    if r.returncode != 0:
        print("  IMPORT FAILED — this is the deploy failure:")
        print("   ", (r.stdout + r.stderr)[-2500:])
        return 1
    print(f"  {r.stdout.strip()}")

    seen_file = ROOT / "data" / "routes_seen.txt"
    here = set(
        p.strip() for p in seen_file.read_text(encoding="utf-8").splitlines()
        if p.strip()
    )
    count = len(here)

    # A build that silently drops routers is worse than one that fails: it
    # serves a subset of the API and reports success. Locally the app exposes
    # 49 routes; anything materially below that means a router failed to
    # import and was swallowed.
    EXPECTED_MIN = 45
    if count < EXPECTED_MIN:
        print(f"  ROUTE COUNT TOO LOW — expected >= {EXPECTED_MIN}, got {count}.")
        print("  Routers are failing to import silently.")
        return 1
    print(f"  route count healthy ({count})")

    # Restore the local view of the routes file.
    run([sys.executable, "scripts/dump_routes.py"], cwd=ROOT)

    # Confirm the declared dependency set covers what the code imports.
    r = run(
        [str(py), "-c",
         "import sys; sys.path.insert(0, '.');"
         "import engine.distribution, engine.meta_proxy, engine.attribution,"
         "engine.attribution_routes, engine.brand_routes,"
         "engine.whatsapp_webhook, engine.enquiry_tracking;"
         "print('all new modules import')"],
        cwd=ROOT, timeout=300,
    )
    if r.returncode != 0:
        print("  A NEW MODULE FAILED TO IMPORT:")
        print("   ", (r.stdout + r.stderr)[-1500:])
        return 1
    print(f"  {r.stdout.strip()}")

    print("\n  BUILD REPRODUCES CLEANLY")
    return 0


if __name__ == "__main__":
    sys.exit(main())