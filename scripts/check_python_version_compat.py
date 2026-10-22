"""Check that every source file parses with the CI Python version.

The CI pipeline runs Python 3.11 while a developer may be on a newer
interpreter. Python 3.12 relaxed the rule that an f-string placeholder
cannot contain the same quote that delimits the string, so a line that
is valid locally fails the build. This catches that before it reaches
CI.

The check uses ast.parse with feature_version, so it applies the target
grammar regardless of the interpreter running it.
"""
import ast
import io
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TARGET = (3, 11)

DIRECTORIES = (
    "engine",
    "tests",
    "scripts",
    "devex",
    "synthesis",
    "job_portal",
    "policy",
    "context_pr",
    "autotest_sentinel",
    "trace_root_ai",
    "revenue_engine",
    "modernize_ai",
)

failures = []
checked = 0

for directory in DIRECTORIES:
    base = ROOT / directory
    if not base.is_dir():
        continue
    for path in sorted(base.rglob("*.py")):
        try:
            source = path.read_text(encoding="utf-8")
        except OSError:
            continue
        checked += 1
        try:
            ast.parse(source, feature_version=TARGET)
        except SyntaxError as exc:
            failures.append((path, exc))
        except ValueError:
            # A source file with null bytes or similar.
            failures.append((path, None))

for path, exc in failures:
    relative = path.relative_to(ROOT)
    if exc is None:
        print(f"{relative}: could not be read as source")
        continue
    print(f"{relative}:{exc.lineno}: {exc.msg}")
    lines = path.read_text(encoding="utf-8").splitlines()
    if exc.lineno and exc.lineno <= len(lines):
        print(f"    {lines[exc.lineno - 1].strip()[:150]}")

print()
version = ".".join(str(part) for part in TARGET)
print(f"{checked} files checked against Python {version}, {len(failures)} incompatible")
sys.exit(1 if failures else 0)
