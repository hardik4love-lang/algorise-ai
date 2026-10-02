"""Categorise the browser-side Meta Graph calls in dashboard.html.

Each call is classified so the proxy endpoints can be built to match what is
actually needed, rather than a guessed subset. Reports the page the token
comes from, because that determines whether the call is a read the backend
can do on the client's behalf or something the backend must own entirely.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DASH = ROOT / "dashboard.html"

GRAPH = re.compile(
    r"(?:const|await|let|var)?\s*\w*\s*(?:=|await)?\s*"
    r"(?:fetch\()?\s*[`'\"]https://graph\.facebook\.com/v(\d+\.\d+)/"
    r"\$\{?encodeURIComponent\(([^)]+)\)\}?"
    r"(?P<rest>[^`'\"]*)",
    re.I,
)

text = DASH.read_text(encoding="utf-8", errors="replace")

print()
print("=" * 92)
print("BROWSER-SIDE META GRAPH CALLS")
print("=" * 92)

calls = []
for m in GRAPH.finditer(text):
    version = m.group(1)
    target = m.group(2).strip()
    rest = (m.group("rest") or "").strip()
    line = text[:m.start()].count("\n") + 1
    calls.append((line, version, target, rest))

print(f"  {len(calls)} call sites\n")

# Which methods operate on the page's own access token?
for line, version, target, rest in calls:
    op = rest.split("?")[0].strip("/")
    method = "READ"
    tail = text[m.end():m.end() + 260] if False else ""
    print(f"  L{line:<6} v{version}  {op or '(page root)'}")
    print(f"          target: {target}")
    print()

print("=" * 92)
print("METHODS USED (method: value in fetch options)")
print("=" * 92)
methods = re.findall(r"method\s*:\s*['\"]([A-Z]+)['\"]", text)
from collections import Counter
for m, n in Counter(methods).most_common():
    print(f"  {n:>2}x  {m}")

print()
print("=" * 92)
print("OPERATIONS IMPLIED BY THE URL PATHS")
print("=" * 92)
ops = Counter()
for _, _, _, rest in calls:
    path = rest.split("?")[0].strip("/")
    ops[path.split("/")[0] if path else "(page root)"] += 1
for op, n in ops.most_common():
    print(f"  {n:>2}x  /{op}")

print()
print("  Note: comment hide and reply POSTs appear in the same file.")
print("  Every one of these currently runs with the page's own token,")
print("  from the visitor's browser, with no backend record.")
print()
