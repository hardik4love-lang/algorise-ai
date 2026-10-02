"""Third pass: replace the block-rate line by locating it structurally."""
from pathlib import Path

p = Path(__file__).resolve().parent.parent / "run_full_100_test_and_tune.py"
lines = p.read_text(encoding="utf-8").splitlines(keepends=True)

out = []
changed = False
for line in lines:
    if "Causal Safety Gate Block Rate" in line and "100%" in line:
        indent = " " * (len(line) - len(line.lstrip()))
        out.append(f'{indent}lines.append(\n')
        out.append(f'{indent}    f"* **Causal Safety Gate Block Rate:** "\n')
        out.append(
            f'{indent}    f"**{{results[\'safety_tests_passed\'] / '
            f'max(1, results[\'total_tested\']) * 100:.1f}}%** "\n'
        )
        out.append(
            f'{indent}    f"({{results[\'safety_tests_passed\']}}/'
            f'{{results[\'total_tested\']}})"\n'
        )
        out.append(f'{indent})\n')
        changed = True
    else:
        out.append(line)

p.write_text("".join(out), encoding="utf-8")
print(f"block-rate line rewritten: {changed}")

remaining = [
    line.strip()[:100]
    for line in "".join(out).splitlines()
    if "100%" in line
]
print("remaining '100%' lines:", len(remaining))
for r in remaining:
    print(f"  {r}")
