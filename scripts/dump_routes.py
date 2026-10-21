"""Dump the API route table and record it for the render build check.

The engine registers routers lazily. A router that fails to import is
swallowed, the build succeeds, and the service serves a subset of the
API while reporting healthy. This script makes the route table
explicit so a silent drop is detectable.

The route list is written to data/routes_seen.txt. The build check
compares the count against the expected minimum and fails when routers
are missing.
"""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SEEN = ROOT / "data" / "routes_seen.txt"

sys.path.insert(0, str(ROOT))


def main() -> int:
    from engine.main import app

    routes = []
    for route in app.routes:
        path = getattr(route, "path", None)
        if not path:
            continue
        methods = sorted(getattr(route, "methods", None) or [])
        routes.append({"path": path, "methods": methods})

    paths = sorted({r["path"] for r in routes})

    SEEN.parent.mkdir(parents=True, exist_ok=True)
    SEEN.write_text("\n".join(paths) + "\n", encoding="utf-8")

    print(f"ROUTE_COUNT={len(paths)}")
    print(f"ROUTE_ENDPOINT_COUNT={len(routes)}")

    # A machine-readable dump for the workflow, kept out of stdout so the
    # printed summary stays readable.
    (ROOT / "data" / "routes_seen.json").write_text(
        json.dumps(routes, indent=2, sort_keys=True), encoding="utf-8"
    )

    for path in paths:
        print(path)

    return 0


if __name__ == "__main__":
    sys.exit(main())
