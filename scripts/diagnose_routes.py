"""Diagnose why a clean install mounts fewer routes than local development.

Run this with any interpreter:
    python scripts/diagnose_routes.py

It reports, for the interpreter running it, whether every router module is
fully built at the moment app.include_router() consumes it.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

MODULES = [
    ("subscription", "engine.subscription_routes", "router"),
    ("meta", "engine.meta_proxy", "router"),
    ("attribution", "engine.attribution_routes", "router"),
    ("brand", "engine.brand_routes", "router"),
    ("whatsapp", "engine.whatsapp_webhook", "router"),
    ("distribution", "engine.distribution_routes", "router"),
]

print(f"python  : {sys.executable}")
print(f"version : {sys.version.split()[0]}")
print()

from importlib import import_module  # noqa: E402

# Import main FIRST, exactly as uvicorn does, then inspect.
import engine.main as m  # noqa: E402

app = m.app
present = {r.path for r in app.routes if hasattr(r, "path")}

print(f"app distinct routes after import: {len(present)}\n")
print(f"{'router':<14} {'has':>4} {'mounted':>8}  paths missing")
print("-" * 78)

total_missing = 0
for label, mod_name, attr in MODULES:
    mod = import_module(mod_name)
    router = getattr(mod, attr)
    have = len(router.routes)
    missing = [
        r.path for r in router.routes
        if hasattr(r, "path") and r.path not in present
    ]
    total_missing += len(missing)
    status = "OK" if not missing else "MISSING"
    print(f"{label:<14} {have:>4} {status:>8}  "
          f"{', '.join(missing[:2]) if missing else ''}")

print()
print(f"total routes declared but not served: {total_missing}")
print()
if total_missing:
    print("VERDICT: this deployment would serve an incomplete API.")
    print("A router module has routes that never reached app.routes.")
else:
    print("VERDICT: every declared route is mounted.")
