"""Locate the remaining blobs containing the token and identify them."""
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
TOKEN = b"AAHaPPybfby3G"

objects = subprocess.run(
    ["git", "rev-list", "--objects", "--all"],
    cwd=REPO, capture_output=True,
).stdout.decode("utf-8", "replace").splitlines()

hits = []
for line in objects:
    parts = line.split(" ", 1)
    sha = parts[0]
    name = parts[1] if len(parts) > 1 else ""
    blob = subprocess.run(
        ["git", "cat-file", "-p", sha], cwd=REPO, capture_output=True
    ).stdout
    if TOKEN in blob:
        hits.append((sha, name, blob.count(TOKEN)))

print(f"blobs still containing the token: {len(hits)}\n")
for sha, name, count in hits:
    label = name or "(no path - tree or tag)"
    print(f"  {sha[:12]}  {count:>2}x  {label}")

if hits:
    print("\noccurrences per blob, with surrounding context:")
    for sha, name, _ in hits[:4]:
        blob = subprocess.run(
            ["git", "cat-file", "-p", sha], cwd=REPO, capture_output=True
        ).stdout.decode("utf-8", "replace")
        idx = blob.find("AAHaPPybfby3G")
        start = max(0, idx - 70)
        print(f"\n  --- {sha[:12]} ({name or 'unlabelled'}) ---")
        print(f"  {blob[start:idx + 60]!r}")