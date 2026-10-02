"""Exercise the release tooling end to end against local staging.

Runs verify -> build -> deploy -> deploy a second artifact -> rollback, and
asserts the live state after each step. This is the rehearsal the release
checklist calls for; doing it here proves the rollback path works before it
is needed under pressure.
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RELEASES = ROOT / ".release-state.json"
ARTIFACTS = ROOT / ".release-artifacts"
DIST = ROOT / "dist"
BACKUP = ROOT / "_release_rehearsal_dist_backup"

PASS, FAIL = "\033[92m  PASS\033[0m", "\033[91m  FAIL\033[0m"
results = []


def run(*args):
    return subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "release.py"), *args],
        cwd=ROOT, capture_output=True, text=True,
    )


def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print(f"{PASS if ok else FAIL}  {name}" + (f"  — {detail}" if detail else ""))


def live_sha():
    if not RELEASES.exists():
        return None
    recs = json.loads(RELEASES.read_text())
    live = [r for r in recs if r.get("live")]
    return live[0]["sha"] if live else None


print("\n  RELEASE TOOLING REHEARSAL\n  " + "=" * 52)

# Preserve the real dist/ so the rehearsal leaves nothing behind.
if DIST.exists():
    shutil.copytree(DIST, BACKUP, dirs_exist_ok=True)

try:
    # --- verify -------------------------------------------------------
    r = run("verify")
    out = r.stdout
    gate_lines = [l for l in out.splitlines() if "PASS" in l or "FAIL" in l]
    check("verify runs and reports every gate", len(gate_lines) >= 4,
          f"{len(gate_lines)} gates reported")
    check("verify fails while known issues remain",
          r.returncode == 1, "expected non-zero with unresolved gates")
    for line in gate_lines:
        print(f"        {line.strip()}")

    # --- build --------------------------------------------------------
    # Fabricate two artifacts so deploy and rollback have distinct targets.
    ARTIFACTS.mkdir(exist_ok=True)
    for sha in ("aaaa1111", "bbbb2222"):
        art = ARTIFACTS / sha
        art.mkdir(parents=True, exist_ok=True)
        (art / "index.html").write_text(
            f"<!-- release {sha} -->", encoding="utf-8"
        )
        (art / "marker.txt").write_text(sha, encoding="utf-8")

    RELEASES.write_text(json.dumps([
        {"sha": "aaaa1111", "built_at": "2026-01-01T00:00:00+00:00",
         "path": str(ARTIFACTS / "aaaa1111"), "live": False, "notes": "rehearsal"},
        {"sha": "bbbb2222", "built_at": "2026-01-02T00:00:00+00:00",
         "path": str(ARTIFACTS / "bbbb2222"), "live": False, "notes": "rehearsal"},
    ]), encoding="utf-8")

    # --- deploy first release ----------------------------------------
    r = run("deploy", "--sha", "aaaa1111")
    check("first deploy succeeds", r.returncode == 0, r.stdout.strip().splitlines()[-1] if r.stdout.strip() else "")
    check("live artifact is the deployed one", live_sha() == "aaaa1111", str(live_sha()))
    check("deployed content reached dist/",
          (DIST / "marker.txt").exists()
          and (DIST / "marker.txt").read_text(encoding="utf-8") == "aaaa1111")

    # --- deploy second release ---------------------------------------
    r = run("deploy", "--sha", "bbbb2222")
    check("second deploy succeeds", r.returncode == 0)
    check("live artifact advanced", live_sha() == "bbbb2222", str(live_sha()))
    check("dist/ now serves the second release",
          (DIST / "marker.txt").read_text(encoding="utf-8") == "bbbb2222")

    # --- rollback -----------------------------------------------------
    r = run("rollback")
    check("rollback succeeds", r.returncode == 0)
    check("live artifact returned to the previous good one",
          live_sha() == "aaaa1111", str(live_sha()))
    check("dist/ restored to the previous content",
          (DIST / "marker.txt").read_text(encoding="utf-8") == "aaaa1111")

    # --- status -------------------------------------------------------
    r = run("status")
    check("status lists artifacts and marks the live one",
          r.returncode == 0 and "LIVE" in r.stdout)

    # --- unknown sha --------------------------------------------------
    r = run("deploy", "--sha", "nosuchsha")
    check("deploying an unknown SHA fails loudly",
          r.returncode == 1 and "no artifact" in r.stderr.lower())

finally:
    # Restore the real dist/ and remove all rehearsal state.
    if BACKUP.exists():
        if DIST.exists():
            shutil.rmtree(DIST)
        shutil.copytree(BACKUP, DIST)
        shutil.rmtree(BACKUP)
    if RELEASES.exists():
        RELEASES.unlink()
    if ARTIFACTS.exists():
        shutil.rmtree(ARTIFACTS)

failed = [n for n, ok, _ in results if not ok]
print("\n  " + "=" * 52)
print(f"  {len(results) - len(failed)}/{len(results)} checks passed")
if failed:
    print("  failed: " + ", ".join(failed))
print("  rehearsal state cleaned up\n")
sys.exit(1 if failed else 0)