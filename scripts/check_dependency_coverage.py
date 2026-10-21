"""Check that the pyproject server extra covers the runtime imports.

The Docker image installs from pyproject while Render installs from
requirements.txt. A package that is imported by the engine but missing
from the installed set produces an ImportError at startup, which is
exactly the failure the container smoke test catches.

This check resolves the declared dependency set and compares it with
the packages the engine actually imports, so the gap is found here
rather than in a deployed container.
"""
import ast
import importlib.util
import os
import re
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE_DIRS = ["engine", "devex", "synthesis", "job_portal", "policy",
               "context_pr", "autotest_sentinel", "trace_root_ai",
               "revenue_engine", "modernize_ai"]

# Third-party modules that are imported lazily or behind a feature flag,
# and are therefore allowed to be absent.
OPTIONAL = {
    "telethon",      # Telegram posting, guarded by a capability check
    "apscheduler",   # scheduled jobs
    "redis",         # cache, degrades gracefully
    "asyncpg",       # PostgreSQL driver, only needed for PostgreSQL
    "playwright",    # browser automation
    "cv2",           # image processing
    "numpy",         # numeric work
    "pandas",        # data frames
    "torch",         # local model inference
    "transformers",  # local model inference
    "mcp",           # MCP transport
    "openai",        # model provider, optional
    "anthropic",     # model provider, optional
    "colorama",      # Windows console colour only
    "pytest",        # test-only dependency
    "pytest_asyncio",
}

STDLIB = set(sys.stdlib_module_names)

# Import name -> distribution name. The import name and the package name
# differ for several dependencies, so the comparison has to go through
# this map.
IMPORT_TO_DISTRIBUTION = {
    "pydantic_settings": "pydantic-settings",
    "prometheus_client": "prometheus-client",
    "pythonjsonlogger": "python-json-logger",
    "yaml": "pyyaml",
    "dotenv": "python-dotenv",
    "jwt": "python-jose",
    "jose": "python-jose",
    "sklearn": "scikit-learn",
    "cv2": "opencv-python",
    "PIL": "pillow",
    "bs4": "beautifulsoup4",
    "dateutil": "python-dateutil",
    "serializers": "djangorestframework",
}


def declared_packages() -> set:
    with open(ROOT / "pyproject.toml", "rb") as handle:
        data = tomllib.load(handle)
    server = data["project"]["optional-dependencies"]["server"]
    names = set()
    for entry in server:
        match = re.match(r"^\s*([A-Za-z0-9._-]+)", entry)
        if match:
            names.add(match.group(1).lower().replace("_", "-"))
    return names


def imported_top_level() -> set:
    found = set()
    for directory in SOURCE_DIRS:
        base = ROOT / directory
        if not base.is_dir():
            continue
        for path in base.rglob("*.py"):
            try:
                tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        found.add(alias.name.split(".")[0].lower())
                elif isinstance(node, ast.ImportFrom):
                    if node.level:  # relative import
                        continue
                    if node.module:
                        found.add(node.module.split(".")[0].lower())
    return found


def is_third_party(module: str) -> bool:
    if module in STDLIB or module in OPTIONAL:
        return False
    if module in {"engine", "devex", "synthesis", "job_portal", "policy",
                  "context_pr", "autotest_sentinel", "trace_root_ai",
                  "revenue_engine", "modernize_ai", "omi_test_backend",
                  "scripts", "tests", "config"}:
        return False
    # A module that is importable locally is either a local package or an
    # installed distribution. Anything with a distribution install name is
    # a real dependency.
    try:
        spec = importlib.util.find_spec(module)
    except (ImportError, ValueError):
        return False
    if spec is None:
        return False
    origin = spec.origin or ""
    if origin.startswith(str(ROOT)) and "site-packages" not in origin:
        return False
    return "site-packages" in origin or "dist-packages" in origin


def main() -> int:
    declared = declared_packages()
    imported = {m for m in imported_top_level() if is_third_party(m)}

    # Map the import name to the distribution name before comparing.
    mapped = {IMPORT_TO_DISTRIBUTION.get(m, m) for m in imported}

    missing = sorted(mapped - declared)

    print(f"declared in the server extra: {len(declared)}")
    print(f"third-party modules imported by the source: {len(imported)}")

    if missing:
        print()
        print("MISSING FROM THE SERVER EXTRA:")
        for name in missing:
            print(f"  {name}")
        print()
        print("The container installs from pyproject. A module missing here")
        print("raises ImportError at startup.")
        return 1

    print("no third-party import is missing from the server extra")
    return 0


if __name__ == "__main__":
    sys.exit(main())
