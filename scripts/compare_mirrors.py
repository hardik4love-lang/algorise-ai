"""Compare each source surface against its dist/ mirror.

dist/ was hand-maintained, so the two copies diverged. Before adopting one
over the other, establish which is newer: a mirror that contains a fix never
back-ported to source would be lost by blindly copying source into dist.

Reported per file: whether the mirror has edits the source lacks, whether
source has edits the mirror lacks, and the size of the difference.
"""
import difflib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

SURFACES = [
    "index.html", "dashboard.html", "creator_studio.html",
    "realtor_sales_console.html", "admin.html", "cocopeat.html",
    "field_pitch.html",
    "compare/manychat-alternative.html", "compare/wati-alternative.html",
    "industry/diamond-cvd-sales-agent.html",
    "industry/textile-saree-wholesale-ai-agent.html",
]


def classify(src: str, mir: str) -> tuple[str, int, int]:
    """Return (verdict, added_in_mirror, added_in_source)."""
    if src == mir:
        return "identical", 0, 0

    src_lines = src.splitlines()
    mir_lines = mir.splitlines()

    sm = difflib.SequenceMatcher(None, src_lines, mir_lines)

    added_in_mirror = 0   # present in mirror, absent from source
    added_in_source = 0   # present in source, absent from mirror

    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag in ("replace", "delete"):
            added_in_source += i2 - i1
        if tag in ("replace", "insert"):
            added_in_mirror += j2 - j1

    if added_in_mirror > added_in_source:
        verdict = "MIRROR NEWER - mirror has edits source lacks"
    elif added_in_source > added_in_mirror:
        verdict = "SOURCE NEWER - source has edits mirror lacks"
    else:
        verdict = "balanced divergence"

    return verdict, added_in_mirror, added_in_source


print()
identical = diverged = 0
for rel in SURFACES:
    src_p, mir_p = ROOT / rel, ROOT / "dist" / rel
    if not src_p.exists() or not mir_p.exists():
        continue

    src = src_p.read_text(encoding="utf-8", errors="replace")
    mir = mir_p.read_text(encoding="utf-8", errors="replace")

    if src == mir:
        identical += 1
        continue

    diverged += 1
    verdict, in_mir, in_src = classify(src, mir)
    print(f"  {rel}")
    print(f"    {verdict}")
    print(f"    +{in_mir} lines only in mirror | +{in_src} lines only in source")
    print(f"    size: source {len(src):,} B, mirror {len(mir):,} B")
    print()

print(f"  identical: {identical}   diverged: {diverged}")
print()

# Show a sample of what differs for the first diverged file, so the verdict
# can be sanity-checked by eye.
for rel in SURFACES:
    src_p, mir_p = ROOT / rel, ROOT / "dist" / rel
    if not (src_p.exists() and mir_p.exists()):
        continue
    src = src_p.read_text(encoding="utf-8", errors="replace").splitlines()
    mir = mir_p.read_text(encoding="utf-8", errors="replace").splitlines()
    if src == mir:
        continue
    print(f"  first 12 differing lines in {rel} (- source, + mirror):")
    shown = 0
    for line in difflib.unified_diff(src, mir, lineterm="", n=0):
        if line.startswith(("---", "+++")):
            continue
        if not line.startswith(("+", "-")):
            continue
        print(f"    {line[:110]}")
        shown += 1
        if shown >= 12:
            break
    print()
    break