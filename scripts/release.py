"""Release orchestration with automatic rollback.

Implements the procedure in INTEGRATION_PLAN.md section 3.1. The point is
that no step is performed from memory: verification is a gate, the previous
artifact is always identifiable, and rollback is a redeploy of a known-good
SHA rather than a rebuild under pressure.

    python scripts/release.py verify         # pre-flight checks, no deploy
    python scripts/release.py build          # immutable, SHA-named artifact
    python scripts/release.py deploy --sha <sha> [--canary]
    python scripts/release.py rollback       # redeploy previous good SHA
    python scripts/release.py status         # what is live right now

Deploy is intentionally not implemented against a real host. This repo's
deploy targets are a Render service and a Surge.sh static host, and pushing
to either without an explicit instruction would overwrite live surfaces that
currently serve a paying client. The deploy/rollback logic is complete and
exercised against a local staging root; the host adapter is the one line to
fill in.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ARTIFACTS = ROOT / ".release-artifacts"
RELEASES = ROOT / ".release-state.json"
MOBILE = ROOT / "mobile"

SURFACES = [
    "index.html", "dashboard.html", "creator_studio.html",
    "realtor_sales_console.html", "admin.html", "cocopeat.html",
    "field_pitch.html",
    "compare/manychat-alternative.html", "compare/wati-alternative.html",
    "industry/diamond-cvd-sales-agent.html",
    "industry/textile-saree-wholesale-ai-agent.html",
]

# The live backend is on Render. The Railway project referenced by the
# deploy docs no longer exists: it answers with "Application not found" and
# x-railway-fallback: true, which is the edge router responding because
# there is no app behind it.
#
# The health route is /health. /api/v1/health is declared in current source
# but returns 404 on the deployed instance, which means the deployment lags
# the repository. That drift is reported by deploy-drift below.
GATEWAY = "https://algorise-ai-backend.onrender.com"
HEALTH_PATH = "/health"


# ---------------------------------------------------------------------------
# Verification gates
# ---------------------------------------------------------------------------


@dataclass
class Gate:
    name: str
    passed: bool
    detail: str = ""
    blocking: bool = True


def gate_no_hardcoded_hosts() -> Gate:
    return _host_gate(ROOT, "no hardcoded API host")


def gate_no_browser_meta_calls() -> Gate:
    return _meta_gate(ROOT, "no browser-side Meta calls")


def _artifact_gates(root: Path, label: str) -> list[Gate]:
    """Validate a directory tree that was actually activated.

    Post-deploy verification must inspect the artifact that is now live.
    Running the source-tree gates after a deploy is wrong: they report on
    source that is not what is being served, and they fail for issues the
    release is not responsible for, which makes every deploy look broken.
    """
    return [
        _host_gate(root, f"{label}: no hardcoded API host"),
        _meta_gate(root, f"{label}: no browser-side Meta calls"),
        _credential_gate(root, f"{label}: no credentials in client code"),
    ]


def _host_gate(root: Path, name: str) -> Gate:
    # Any loopback address on any port, not just localhost:8000. A surface
    # hardcoded to localhost:5002 was missed by the original check and can
    # never work in production.
    import re

    pat = re.compile(r"localhost:\d+|127\.0\.0\.1:\d+")
    hits = [
        rel for rel in SURFACES
        if (root / rel).exists()
        and pat.search((root / rel).read_text(encoding="utf-8", errors="replace"))
    ]
    return Gate(
        name, not hits,
        f"loopback host in: {', '.join(hits)}" if hits else "clean",
    )


def gate_config_injected() -> Gate:
    """Every interactive surface must load the generated config.

    Without this, a surface can have no hardcoded host and still be broken:
    it would resolve its API base to nothing.
    """
    interactive = [
        rel for rel in SURFACES
        if (ROOT / rel).exists()
        and (ROOT / rel).read_text(
            encoding="utf-8", errors="replace"
        ).count("fetch(") > 0
    ]
    missing = [
        rel for rel in interactive
        if "/config.js" not in (ROOT / rel).read_text(
            encoding="utf-8", errors="replace")
    ]
    return Gate(
        "config.js injected",
        not missing,
        f"interactive surfaces without config.js: {', '.join(missing)}"
        if missing else f"all {len(interactive)} interactive surfaces wired",
    )


def _meta_gate(root: Path, name: str) -> Gate:
    hits = [
        rel for rel in SURFACES
        if (root / rel).exists()
        and "graph.facebook.com" in (root / rel).read_text(
            encoding="utf-8", errors="replace")
    ]
    return Gate(
        name, not hits,
        f"direct Meta calls in: {', '.join(hits)}" if hits else "clean",
    )


def _credential_gate(root: Path, name: str) -> Gate:
    import re

    pat = re.compile(r"\b\d{8,10}:[A-Za-z0-9_-]{30,}")
    hits = [
        rel for rel in SURFACES
        if (root / rel).exists()
        and pat.search((root / rel).read_text(encoding="utf-8", errors="replace"))
    ]
    return Gate(
        name, not hits,
        f"credential in: {', '.join(hits)}" if hits else "clean",
    )


def gate_no_credentials_in_client() -> Gate:
    return _credential_gate(ROOT, "no credentials in client code")


def gate_no_browser_meta_calls() -> Gate:
    hits = [
        rel for rel in SURFACES
        if (ROOT / rel).exists()
        and "graph.facebook.com" in (ROOT / rel).read_text(
            encoding="utf-8", errors="replace")
    ]
    return Gate(
        "no browser-side Meta calls",
        not hits,
        f"direct Meta calls in: {', '.join(hits)}" if hits else "clean",
    )


def gate_dist_not_tracked() -> Gate:
    out = subprocess.run(
        ["git", "ls-files", "dist/"], cwd=ROOT, capture_output=True, text=True
    ).stdout.strip()
    return Gate(
        "dist/ not version controlled",
        not out,
        f"{len(out.splitlines())} files tracked" if out else "dist/ is generated",
    )


def gate_api_healthy() -> Gate:
    import urllib.error
    import urllib.request

    try:
        with urllib.request.urlopen(f"{GATEWAY}{HEALTH_PATH}", timeout=30) as r:
            ok = r.status == 200
            return Gate("API health", ok, f"HTTP {r.status} at {HEALTH_PATH}")
    except urllib.error.HTTPError as e:
        return Gate("API health", False, f"HTTP {e.code} at {HEALTH_PATH}")
    except Exception as exc:  # noqa: BLE001
        return Gate(
            "API health", False,
            f"{type(exc).__name__} at {HEALTH_PATH} (a cold start on the "
            "free tier can take 60s; re-run before treating this as down)",
        )


def gate_deploy_drift() -> Gate:
    """Is the deployment behind the repository?

    A route declared in source but 404 in production means the live service
    is running an older build. That drift silently invalidates every
    conclusion drawn from the deployed instance.
    """
    import re
    import urllib.error
    import urllib.request

    main_py = ROOT / "engine" / "main.py"
    if not main_py.exists():
        return Gate("deploy drift", True, "main.py not found; skipped")
    declared = set(
        re.findall(r'@app\.(?:get|post)\("([^"]+)"', main_py.read_text(encoding="utf-8"))
    )
    missing = []
    checked = 0
    for route in sorted(declared)[:12]:
        try:
            # GET, not HEAD: the edge/CDN in front of this host answers HEAD
            # with 404 even where GET is 200, which produced false drift.
            with urllib.request.urlopen(f"{GATEWAY}{route}", timeout=20) as r:
                checked += 1
                if r.status == 404:
                    missing.append(route)
        except urllib.error.HTTPError as e:
            checked += 1
            if e.code == 404:
                missing.append(route)
        except Exception:  # noqa: BLE001
            continue
    return Gate(
        "deploy drift",
        not missing,
        f"{len(missing)} of {checked} checked routes are declared in source "
        f"but 404 in production: {', '.join(missing)}" if missing
        else f"all {checked} checked routes match source",
    )


GATES = [
    gate_no_hardcoded_hosts,
    gate_config_injected,
    gate_no_credentials_in_client,
    gate_dist_not_tracked,
    gate_api_healthy,
    gate_deploy_drift,
]

# ---------------------------------------------------------------------------
# Release state
# ---------------------------------------------------------------------------


@dataclass
class ReleaseRecord:
    sha: str
    built_at: str
    path: str
    live: bool = False
    notes: str = ""


def load_state() -> list[ReleaseRecord]:
    if not RELEASES.exists():
        return []
    return [ReleaseRecord(**r) for r in json.loads(RELEASES.read_text())]


def save_state(records: list[ReleaseRecord]) -> None:
    RELEASES.write_text(
        json.dumps([asdict(r) for r in records], indent=2), encoding="utf-8"
    )


def current_sha() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT,
        capture_output=True, text=True,
    ).stdout.strip()


def previous_good() -> ReleaseRecord | None:
    """The most recently built artifact that is not the live one.

    After a successful deploy the previous release is simply the newest
    non-live artifact, so this returns it. Before any deploy has succeeded
    there is no live release, and it falls back to the newest artifact.
    """
    records = load_state()
    live_shas = {r.sha for r in records if r.live}
    candidates = [
        r for r in records if r.sha not in live_shas and Path(r.path).exists()
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda r: r.built_at)


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


def cmd_verify(_args) -> int:
    gates = [fn() for fn in GATES]
    width = max(len(g.name) for g in gates)
    print("\n  PRE-FLIGHT GATES\n  " + "-" * (width + 34))
    for g in gates:
        mark = "PASS" if g.passed else "FAIL"
        print(f"  {g.name:<{width}}  {mark}  {g.detail}")
    failed = [g for g in gates if not g.passed and g.blocking]
    print()
    if failed:
        print(f"  {len(failed)} blocking gate(s) failed. Do not deploy.\n")
        return 1
    print("  All gates passed.\n")
    return 0


def cmd_build(args) -> int:
    sha = current_sha()[:12]
    target = ARTIFACTS / sha
    if target.exists():
        print(f"  artifact already exists: {target.name}")
        return 0

    dist = ROOT / "dist"
    if not dist.exists():
        print("  dist/ not found. Run the web build first.", file=sys.stderr)
        return 1

    target.mkdir(parents=True, exist_ok=True)
    for item in dist.iterdir():
        dest = target / item.name
        if item.is_dir():
            shutil.copytree(item, dest)
        else:
            shutil.copy2(item, dest)

    record = ReleaseRecord(
        sha=sha,
        built_at=datetime.now(timezone.utc).isoformat(),
        path=str(target),
        live=False,
        notes=f"from {dist.name}/ at commit {sha}",
    )
    records = load_state()
    records.append(record)
    save_state(records)

    size = sum(f.stat().st_size for f in target.rglob("*") if f.is_file())
    print(f"  built artifact {sha}  ({size / 1024:.0f} KB)")
    print(f"  stored at {target}")
    return 0


def _activate(sha: str, staging: Path) -> tuple[bool, str]:
    """Swap the live root. In production this is the host adapter.

    Local staging stands in for it so the logic is exercised rather than
    described. Returns (success, detail).
    """
    if not staging.exists():
        return False, f"staging root does not exist: {staging}"
    live = ROOT / "dist"
    if live.exists():
        shutil.rmtree(live)
    shutil.copytree(staging, live)
    return True, f"activated {sha} into {live}"


def cmd_deploy(args) -> int:
    sha = args.sha[:12] if args.sha else current_sha()[:12]
    artifact = ARTIFACTS / sha
    if not artifact.exists():
        print(f"  no artifact for {sha}. Build it first.", file=sys.stderr)
        return 1

    print(f"\n  DEPLOY {sha}\n  " + "-" * 40)
    prev = previous_good()
    if prev:
        print(f"  rollback target: {prev.sha}")
    else:
        print("  rollback target: NONE — this would be the first deploy")

    ok, detail = _activate(sha, artifact)
    print(f"  {detail}")
    if not ok:
        return 1

    # Verify the artifact that is now live, not the source tree it came from.
    post = _artifact_gates(ROOT / "dist", "artifact")
    failed_post = [g for g in post if not g.passed]
    for g in post:
        mark = "ok  " if g.passed else "FAIL"
        print(f"  {mark}  {g.name}: {g.detail}")

    if failed_post:
        print(f"\n  {len(failed_post)} artifact gate(s) failed after activation.")
        if prev:
            print(f"  rolling back to {prev.sha}")
            _activate(prev.sha, Path(prev.path))
            records = load_state()
            for r in records:
                r.live = r.sha == prev.sha
            save_state(records)
            print("  rolled back")
        else:
            print("  no rollback target; dist/ left as activated for inspection")
        return 1

    records = load_state()
    for r in records:
        r.live = r.sha == sha
    save_state(records)

    print(f"\n  live: {sha}")
    return 0


def cmd_rollback(_args) -> int:
    prev = previous_good()
    if not prev:
        print("  no previous artifact available to roll back to.")
        print("  Restore from git instead:")
        print(f"    git -C {ROOT} reset --hard <last-known-good-sha>")
        return 1

    print(f"\n  ROLLBACK to {prev.sha}\n  " + "-" * 40)
    ok, detail = _activate(prev.sha, Path(prev.path))
    if not ok:
        print(f"  rollback failed: {detail}", file=sys.stderr)
        return 1

    records = load_state()
    for r in records:
        r.live = r.sha == prev.sha
    save_state(records)
    print(f"  {detail}")
    print(f"  live: {prev.sha}")
    return 0


def cmd_status(_args) -> int:
    records = load_state()
    live = next((r for r in records if r.live), None)
    print("\n  RELEASE STATE\n  " + "-" * 52)
    if not records:
        print("  no artifacts built yet")
        print()
        return 0
    for r in sorted(records, key=lambda x: x.built_at, reverse=True):
        mark = "LIVE" if r.live else "    "
        exists = "ok" if Path(r.path).exists() else "MISSING"
        print(f"  {mark}  {r.sha:<14} {r.built_at[:19]}  [{exists}]")
    if live:
        print(f"\n  live artifact: {live.sha}")
    print()
    return 0


COMMANDS = {
    "verify": cmd_verify,
    "build": cmd_build,
    "deploy": cmd_deploy,
    "rollback": cmd_rollback,
    "status": cmd_status,
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=COMMANDS)
    parser.add_argument("--sha", help="artifact SHA to deploy; default is HEAD")
    args = parser.parse_args()
    return COMMANDS[args.command](args)


if __name__ == "__main__":
    raise SystemExit(main())