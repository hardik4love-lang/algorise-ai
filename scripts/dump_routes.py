"""Dump the API route table and record it for the render build check.

The engine registers routers lazily. A router that fails to import is
swallowed, the build succeeds, and the service serves a subset of the
API while reporting healthy. This script makes the route table
explicit so a silent drop is detectable.

The route list is written to data/routes_seen.txt. The build check
compares the count against the expected minimum and fails when routers
are missing.

FastAPI 0.159 changed include_router to keep the included router as a
single _IncludedRouter entry instead of copying its routes into
app.routes. A flat scan of app.routes therefore undercounts on the
newer release, so the walk is recursive and the OpenAPI schema is used
as an independent cross-check.
"""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SEEN = ROOT / "data" / "routes_seen.txt"

sys.path.insert(0, str(ROOT))


def collect_paths(routes, seen=None, depth=0):
    """Recursively collect every registered path.

    Handles the flat form used by FastAPI before 0.159, where the
    routes of an included router are copied into app.routes, and the
    nested form used from 0.159, where the router is kept as a single
    _IncludedRouter entry that exposes the original router and the
    effective candidate routes.
    """
    if seen is None:
        seen = set()
    if depth > 6:
        return seen

    for route in routes or []:
        path = getattr(route, "path", None)
        if path:
            seen.add(path)

        # FastAPI 0.159: an included router is kept as one entry.
        original = getattr(route, "original_router", None)
        if original is not None:
            collect_paths(getattr(original, "routes", None), seen, depth + 1)

        candidates = getattr(route, "effective_candidates", None)
        if callable(candidates):
            try:
                candidates = candidates()
            except Exception:
                candidates = None
        if candidates:
            for candidate in candidates:
                candidate_path = getattr(candidate, "path", None)
                if candidate_path:
                    seen.add(candidate_path)
                nested = getattr(candidate, "routes", None)
                if nested:
                    collect_paths(nested, seen, depth + 1)

        # A router that exposes its own routes.
        inner = getattr(route, "router", None)
        if inner is not None and getattr(inner, "routes", None):
            collect_paths(inner.routes, seen, depth + 1)

        nested = getattr(route, "routes", None)
        if nested and not path:
            collect_paths(nested, seen, depth + 1)

    return seen


def main() -> int:
    from engine.main import app

    flat = {r.path for r in app.routes if getattr(r, "path", None)}
    nested = collect_paths(app.routes)
    paths = sorted(flat | nested)

    try:
        openapi_paths = set(app.openapi().get("paths", {}))
    except Exception:
        openapi_paths = set()

    SEEN.parent.mkdir(parents=True, exist_ok=True)
    SEEN.write_text("\n".join(paths) + "\n", encoding="utf-8")

    print(f"ROUTE_COUNT={len(paths)}")
    print(f"ROUTE_FLAT_COUNT={len(flat)}")
    print(f"ROUTE_OPENAPI_COUNT={len(openapi_paths)}")

    # The OpenAPI schema is the authoritative view of what the service
    # serves. When the two disagree, the route walk is wrong.
    only_in_openapi = sorted(openapi_paths - set(paths))
    if only_in_openapi:
        print("ROUTE_WALK_MISSING=" + ",".join(only_in_openapi))
    else:
        print("ROUTE_WALK_MISSING=")

    (ROOT / "data" / "routes_seen.json").write_text(
        json.dumps(
            {
                "routes": paths,
                "openapi_paths": sorted(openapi_paths),
                "flat_count": len(flat),
                "nested_count": len(nested),
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    for path in paths:
        print(path)

    return 0


if __name__ == "__main__":
    sys.exit(main())
