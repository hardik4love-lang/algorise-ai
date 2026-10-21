"""Keep the pyproject server extra and requirements.txt identical.

The Docker image installs from pyproject while Render installs from
requirements.txt. When the two lists differ, the image and the deployed
service run different library versions, and a build can pass while the
deployed service fails. A clean install of the previously unpinned
server extra resolved SQLAlchemy 2.1.6, which the OpenTelemetry
SQLAlchemy instrumentor does not support.

This check fails when the two sets drift, and fails when either set
contains an unpinned version.
"""
import re
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# colorama is Windows-only and is declared conditionally, so it is not
# part of the runtime dependency set for the Linux image.
CONDITIONAL = {"colorama"}


def parse_requirements() -> dict:
    packages = {}
    for raw in (ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines():
        line = raw.split("#")[0].strip()
        if not line:
            continue
        match = re.match(r"^([A-Za-z0-9._-]+)", line)
        if not match:
            continue
        name = match.group(1).lower().replace("_", "-")
        if name in CONDITIONAL:
            continue
        packages[name] = line
    return packages


def parse_server_extra() -> dict:
    with open(ROOT / "pyproject.toml", "rb") as handle:
        data = tomllib.load(handle)
    packages = {}
    for entry in data["project"]["optional-dependencies"]["server"]:
        match = re.match(r"^\s*([A-Za-z0-9._-]+)", entry)
        if not match:
            continue
        name = match.group(1).lower().replace("_", "-")
        packages[name] = entry.strip()
    return packages


def main() -> int:
    requirements = parse_requirements()
    server = parse_server_extra()

    problems = []

    only_requirements = sorted(set(requirements) - set(server))
    if only_requirements:
        problems.append("missing from the pyproject server extra:")
        problems.extend(f"  {name}" for name in only_requirements)

    only_server = sorted(set(server) - set(requirements))
    if only_server:
        problems.append("missing from requirements.txt:")
        problems.extend(f"  {name}" for name in only_server)

    # A version range means the resolution changes over time.
    for name, entry in list(server.items()) + list(requirements.items()):
        if "==" not in entry:
            problems.append(f"unpinned version: {entry}")

    if problems:
        print("DEPENDENCY DRIFT DETECTED")
        print()
        for line in problems:
            print(line)
        print()
        print("The container installs from pyproject and Render installs from")
        print("requirements.txt. They must declare the same pinned versions.")
        return 1

    print(f"dependency sets agree ({len(server)} pinned packages)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
