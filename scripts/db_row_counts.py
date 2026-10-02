"""Actual row counts across every table in the local production DB."""
import sqlite3
from pathlib import Path

DB = Path(__file__).resolve().parent.parent / "algorise_prod.db"
conn = sqlite3.connect(DB)
cur = conn.cursor()

tables = [
    r[0] for r in cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    )
]
print(f"database: {DB}")
print(f"size    : {DB.stat().st_size / 1024:.0f} KB")
print(f"tables  : {len(tables)}\n")

print(f"{'table':<32} {'rows':>8}  newest")
print("-" * 72)

non_empty = []
for t in tables:
    try:
        n = cur.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
    except sqlite3.Error as exc:
        print(f"{t:<32} {'ERR':>8}  {exc}")
        continue

    newest = ""
    cols = [r[1] for r in cur.execute(f'PRAGMA table_info("{t}")')]
    for cand in ("created_at", "run_at", "start_date", "started_at"):
        if cand in cols:
            newest = cur.execute(
                f'SELECT MAX("{cand}") FROM "{t}"'
            ).fetchone()[0] or ""
            break

    print(f"{t:<32} {n:>8}  {newest}")
    if n:
        non_empty.append((t, n, newest))

print(f"\nnon-empty tables: {len(non_empty)}")
for t, n, newest in non_empty:
    print(f"  {t}: {n} rows, newest {newest or 'n/a'}")

conn.close()