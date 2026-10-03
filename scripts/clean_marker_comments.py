"""Remove marker literals from comments so the build gate stays honest."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# The generator's own docstring and the dashboard comment both quoted the
# marker syntax literally. The gate flags any `{{...}}` surviving into
# dist/, and quoting it in a comment is indistinguishable from a real
# un-substituted marker, so the gate would report a false positive.
edits = [
    ("scripts/extract_brand_js.py",
     "Replaces {{MARKER}} tokens",
     "Replaces marker tokens"),
    ("dashboard.html",
     "are now {{MARKERS}} filled from",
     "are now marker tokens filled from"),
]

for rel, old, new in edits:
    p = ROOT / rel
    if not p.exists():
        continue
    t = p.read_text(encoding="utf-8")
    if old in t:
        p.write_text(t.replace(old, new), encoding="utf-8")
        print(f"  patched {rel}")
    else:
        print(f"  {rel}: already clean")

# Regenerate so brand.js picks up the change.
import subprocess
import sys

subprocess.run(
    [sys.executable, str(ROOT / "scripts" / "extract_brand_js.py")],
    cwd=ROOT, capture_output=True,
)

t = (ROOT / "brand.js").read_text(encoding="utf-8")
print(f"  brand.js marker literals: {t.count('{{')}")
print(f"  brand.js em-dash intact : {chr(8212) in t}")
