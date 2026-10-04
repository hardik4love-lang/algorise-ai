"""Verify the Pipeline tab is wired: registered, reachable, and present in dist."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
src = ROOT / "dashboard.html"
dist = ROOT / "dist" / "dashboard.html"

text = src.read_text(encoding="utf-8")

checks = []

def check(name, ok, detail=""):
    checks.append((name, ok, detail))

# Tab registered in the switchTab list.
tabs = re.search(r"const tabs = \[([^\]]+)\]", text)
check("pipeline tab registered",
      tabs and "pipeline" in tabs.group(1),
      tabs.group(1)[:90] if tabs else "tab list not found")

# Lazy loader hooked.
check("lazy loader hooked", "loadPipeline()" in text)

# Button exists and is wired.
check("tab button present", 'id="tabBtnPipeline"' in text)
check("button calls switchTab", "switchTab('pipeline')" in text)

# Panel exists.
check("panel exists", 'id="tabContentPipeline"' in text)

# Render function and the coverage guard.
check("render function present", "function renderPipeline" in text)
check("coverage guard present", "PF_RATE_MIN" in text)

# It must not fabricate: no hardcoded fallback numbers in the render path.
render = text[text.find("function renderPipeline"):]
render = render[:render.find("\n    async function loadPipelineEnquiries")]
fabricated = re.findall(r"(?:conversion|rate)[^=\n]*=\s*0?\.\d{2,}", render)
check("no fabricated rate constants", not fabricated, str(fabricated[:3]))

# dist/ must carry the same tab.
if dist.exists():
    d = dist.read_text(encoding="utf-8")
    check("dist has the tab", 'id="tabContentPipeline"' in d)
    check("dist has the button", 'id="tabBtnPipeline"' in d)
    check("dist has the coverage guard", "PF_RATE_MIN" in d)

# No credential or merchant leakage introduced.
check("no merchant numbers", not re.search(
    r"(?:63552\s?85433|90542\s?41725|87370\s?13099)", text))
check("no bot token", not re.search(r"\b\d{8,10}:[A-Za-z0-9_-]{30,}", text))

print()
w = max(len(n) for n, _, _ in checks)
failed = 0
for name, ok, detail in checks:
    mark = "PASS" if ok else "FAIL"
    if not ok:
        failed += 1
    print(f"  {mark}  {name:<{w}}" + (f"  {detail}" if detail and not ok else ""))

print()
print(f"  {len(checks) - failed}/{len(checks)} checks passed")
print()
raise SystemExit(1 if failed else 0)