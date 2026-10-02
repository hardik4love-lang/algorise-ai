"""Audit and quarantine fabricated facebook_agent_jobs rows.

The scheduler wrote a run record every 60 seconds on the branch taken when
no Meta token was configured, claiming comments_scanned=31 and a 3-page
sync that never happened. This quantifies the damage and quarantines it.

Fabricated rows are identifiable by: status='completed' AND
comments_scanned=31 AND replies_sent=0 AND leads_detected=0, because a real
scan that reads 31 comments and replies to none while finding no leads is
possible but rare, AND the log_summary contains the hardcoded marketing
string. That conjunction is specific to the removed code path.

Nothing is deleted. Rows are flagged, so the audit trail survives and the
client dashboard can be corrected to show the truth.
"""
import sqlite3
from pathlib import Path

DB = Path(__file__).resolve().parent.parent / "algorise_prod.db"

MARKER = "3-Page Auto-Update"
SELECT_FABRICATED = """
    SELECT id, client_id, comments_scanned, replies_sent, leads_detected,
           status, log_summary, run_at
    FROM facebook_agent_jobs
    WHERE comments_scanned = 31
      AND replies_sent = 0
      AND leads_detected = 0
      AND (log_summary LIKE ? OR log_summary LIKE '%sweep on Page%')
    ORDER BY run_at
"""

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

cols = [r["name"] for r in cur.execute("PRAGMA table_info(facebook_agent_jobs)")]
print(f"table columns: {', '.join(cols)}")

total = cur.execute("SELECT COUNT(*) FROM facebook_agent_jobs").fetchone()[0]
print(f"\ntotal rows in facebook_agent_jobs: {total:,}")

if "is_fabricated" not in cols:
    cur.execute("ALTER TABLE facebook_agent_jobs ADD COLUMN is_fabricated INTEGER")
    conn.commit()
    print("added is_fabricated column")

fab = cur.execute(SELECT_FABRICATED, (f"%{MARKER}%",)).fetchall()
print(f"rows matching the fabricated signature: {len(fab):,}")

if fab:
    dates = [r["run_at"] for r in fab if r["run_at"]]
    print(f"  date range: {dates[0]} -> {dates[-1]}")
    print(f"  clients affected: {len({r['client_id'] for r in fab})}")
    per_day = len(fab) / max(1, len({d[:10] for d in dates}))
    print(f"  average per day: {per_day:.0f}")

    ids = [r["id"] for r in fab]
    cur.execute(
        f"UPDATE facebook_agent_jobs SET is_fabricated = 1 WHERE id IN "
        f"({','.join('?' * len(ids))})",
        ids,
    )
    conn.commit()
    print(f"\nflagged {cur.rowcount:,} rows as is_fabricated=1")

    cur.execute(
        "UPDATE facebook_agent_jobs SET status='not_configured' "
        "WHERE is_fabricated = 1"
    )
    conn.commit()
    print(f"rewrote {cur.rowcount:,} statuses to 'not_configured'")

cur.execute(
    "SELECT is_fabricated, COUNT(*) FROM facebook_agent_jobs "
    "GROUP BY is_fabricated"
)
print("\nfinal distribution (is_fabricated, count):")
for row in cur.fetchall():
    print(f"  {row[0]}: {row[1]:,}")

conn.close()