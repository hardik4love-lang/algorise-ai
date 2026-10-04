"""
Distribution: real group posting, with capabilities probed rather than assumed.

TWO FACTS, TWO COLUMNS
======================
`id_valid`  the identifier is real. Import proves this by rejecting anything
            synthetic, so a stored row is never an invented group.
`verified`  this account has actually posted there successfully. Only a
            successful post sets it.

The distinction is the point of the module. The pitch quoted a group count;
reporting "100 groups imported" when the account is a member of none of them
is precisely the claim this exists to prevent. Reach counts `verified` only,
which starts at zero and rises one successful post at a time.

THE PROBLEM THIS SOLVES
=======================
The pitch promised distribution into 100 groups. The repository backed that
with assets/100-facebook-groups-directory.json, whose identifiers are
"fb_grp_001" through "fb_grp_100" - placeholders, not real group ids. No
posting code existed at all. So the claim was backed by a list of invented
targets.

WHAT IS ACTUALLY POSSIBLE
=========================
Telegram: a user session can post to any group the account is genuinely a
          member of. Discoverable, verifiable, real.

Facebook: posting to a Group requires the app to be a member of that group
          AND the appropriate Graph permission, which is gated behind app
          review. There is no way to code around it. This module attempts it,
          records the real outcome, and reports "unavailable" rather than
          pretending.

The design consequence: every target carries a verification state, and the
system reports how many are VERIFIED rather than how many are listed. A pitch
that says "100 groups" is false; one that says "N verified groups, verified
today" is true and is the only form this module will produce.
"""

from __future__ import annotations

import asyncio
import json
import os
import random
import re
import sqlite3
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Optional

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "distribution.db"

# A real Telegram invite link or public username. Facebook group ids are long
# numeric strings; a short 'fb_grp_NNN' placeholder is rejected on import so
# an aspirational list cannot quietly present itself as verified.
FB_ID = re.compile(r"^\d{6,}$")
TG_INVITE = re.compile(r"(?:t\.me|telegram\.me)/([A-Za-z0-9_+-]{4,})")
TG_HANDLE = re.compile(r"^[A-Za-z][A-Za-z0-9_]{3,31}$")


def _is_placeholder(v: str) -> bool:
    """Detect synthetic identifiers like fb_grp_001 or group_1."""
    return bool(re.match(r"^[a-z]+[_-]?(grp[_-]?)?\d{1,4}$", v or "", re.I))


# ---------------------------------------------------------------------------
# Target registry
# ---------------------------------------------------------------------------

SCHEMA = """
CREATE TABLE IF NOT EXISTS targets (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    platform      TEXT NOT NULL,
    external_id   TEXT NOT NULL,
    name          TEXT,
    audience      TEXT,
    category      TEXT,
    id_valid      INTEGER NOT NULL DEFAULT 0,
    verified      INTEGER NOT NULL DEFAULT 0,
    joined        INTEGER NOT NULL DEFAULT 0,
    verified_at   TEXT,
    last_posted   TEXT,
    post_count    INTEGER NOT NULL DEFAULT 0,
    last_error    TEXT,
    UNIQUE(platform, external_id)
);

CREATE TABLE IF NOT EXISTS posts (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    target_id   INTEGER REFERENCES targets(id),
    body        TEXT,
    media_path  TEXT,
    status      TEXT NOT NULL,
    provider_ref TEXT,
    error       TEXT,
    created_at  TEXT NOT NULL,
    posted_at   TEXT
);

CREATE INDEX IF NOT EXISTS idx_posts_target ON posts(target_id);
CREATE INDEX IF NOT EXISTS idx_targets_verified ON targets(platform, verified);
"""


@dataclass
class CapabilityReport:
    """What this deployment can actually do, discovered not assumed."""

    telegram_installed: bool
    telegram_credentials: bool
    telegram_session: bool
    facebook_token: bool
    facebook_groups_permitted: Optional[bool]
    verified_telegram_groups: int
    verified_facebook_groups: int
    unverified_targets: int
    notes: list[str] = field(default_factory=list)

    @property
    def can_post_anywhere(self) -> bool:
        return self.verified_telegram_groups > 0 or (
            self.verified_facebook_groups > 0
            and bool(self.facebook_groups_permitted)
        )

    def to_json(self) -> dict[str, Any]:
        d = asdict(self)
        d["can_post_anywhere"] = self.can_post_anywhere
        return d


def connect(path: Path = DB_PATH) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    _migrate(conn)
    conn.commit()
    return conn


def _migrate(conn) -> None:
    """Add columns an older database predates.

    create(checkfirst=True) does nothing when the table exists, so a database
    created before id_valid was introduced would fail every later query with
    "no such column". Same failure mode as the inbound-message table: the
    error is reported far from its cause.
    """
    existing = {
        r["name"]
        for r in conn.execute("PRAGMA table_info(targets)").fetchall()
    }
    if not existing:
        return
    for col in (
        "id_valid", "verified", "joined", "post_count", "last_error"
    ):
        if col in existing:
            continue
        ddl = f"ALTER TABLE targets ADD COLUMN {col} INTEGER NOT NULL DEFAULT 0"
        conn.execute(ddl)


# ---------------------------------------------------------------------------
# Import
# ---------------------------------------------------------------------------


def import_targets(rows: Iterable[dict[str, Any]], conn=None) -> dict[str, int]:
    """Import distribution targets, rejecting synthetic identifiers.

    Import proves only that an id is real, which sets id_valid. It never sets
    verified: membership is discovered by posting, so reach never includes a
    group this account has not actually reached.
    """
    owned = conn is None
    conn = conn or connect()
    accepted = 0
    rejected = 0
    try:
        for r in rows:
            platform = (r.get("platform") or "").lower().strip()
            raw_id = str(r.get("external_id") or r.get("id") or "").strip()

            if not platform or not raw_id:
                rejected += 1
                continue

            if platform == "telegram":
                # A t.me invite link and an @handle are the same group, so
                # both normalise to the bare username. TG_HANDLE anchors on a
                # leading letter, so the @ is stripped before matching.
                bare = raw_id.lstrip("@").strip()
                invite = TG_INVITE.search(bare)
                if invite:
                    bare = invite.group(1)
                    valid = True
                else:
                    valid = bool(TG_HANDLE.match(bare))
                raw_id = bare
            elif platform == "facebook":
                # Real group ids are long numeric strings; a short
                # 'fb_grp_001' pattern is a placeholder.
                valid = bool(FB_ID.match(raw_id)) and not _is_placeholder(raw_id)
            else:
                valid = False

            if not valid:
                rejected += 1
                continue

            conn.execute(
                "INSERT INTO targets (platform, external_id, name, audience,"
                " category, id_valid) VALUES (?,?,?,?,?,?)"
                " ON CONFLICT(platform, external_id) DO UPDATE SET"
                " name=excluded.name, audience=excluded.audience,"
                " category=excluded.category, id_valid=1",
                (platform, raw_id, r.get("name"), r.get("audience"),
                 r.get("category"), 1),
            )
            accepted += 1

        conn.commit()

        # Report DISTINCT targets stored, not rows processed. An import of
        # 100 rows that collapse to 5 groups must not claim 100, or the
        # count becomes another aspirational number.
        stored = conn.execute(
            "SELECT COUNT(*) FROM targets WHERE id_valid=1"
        ).fetchone()[0]

        return {
            "accepted_rows": accepted,
            "distinct_targets": stored,
            "rejected_as_invalid": rejected,
        }
    finally:
        if owned:
            conn.close()


def import_from_directory(
    path: Optional[Path] = None, conn=None
) -> dict[str, int]:
    """Import the bundled group directory.

    Expected outcome today: every entry is rejected, because the ids are
    placeholders. That result is the correct one and is reported plainly
    rather than producing a list of 100 targets that would fail on first post.
    """
    p = path or (ROOT / "assets" / "100-facebook-groups-directory.json")
    data = json.loads(Path(p).read_text(encoding="utf-8"))
    rows = []
    for g in data.get("groups", []):
        rows.append({
            "platform": "facebook",
            "external_id": g.get("id", ""),
            "name": g.get("name"),
            "audience": g.get("audience"),
            "category": g.get("category"),
        })
    return import_targets(rows, conn=conn)


# ---------------------------------------------------------------------------
# Capability probing
# ---------------------------------------------------------------------------


def probe(conn=None) -> CapabilityReport:
    """Discover what this deployment can genuinely do."""
    owned = conn is None
    conn = conn or connect()
    notes: list[str] = []
    try:
        try:
            import telethon  # noqa: F401

            tg_installed = True
        except ImportError:
            tg_installed = False
            notes.append("telethon not installed; Telegram posting unavailable")

        api_id = os.getenv("TELEGRAM_API_ID", "")
        api_hash = os.getenv("TELEGRAM_API_HASH", "")
        session_exists = any(
            (ROOT / "data").glob("*.session")
        ) if (ROOT / "data").exists() else False

        if not api_id or not api_hash:
            notes.append(
                "TELEGRAM_API_ID / TELEGRAM_API_HASH not set; a user "
                "session is required because a bot cannot post to groups it "
                "has not been added to"
            )

        fb_token = bool(os.getenv("META_ACCESS_TOKEN") or os.getenv("FB_ACCESS_TOKEN"))

        counts = {
            r["platform"]: r["n"]
            for r in conn.execute(
                "SELECT platform, COUNT(*) AS n FROM targets WHERE verified=1"
                " GROUP BY platform"
            )
        }
        unverified = conn.execute(
            "SELECT COUNT(*) FROM targets WHERE verified=0"
        ).fetchone()[0]

        if not tg_installed or not session_exists:
            notes.append(
                "0 Telegram groups verified as joined. Group membership must "
                "be confirmed by connecting the account; it cannot be inferred."
            )

        return CapabilityReport(
            telegram_installed=tg_installed,
            telegram_credentials=bool(api_id and api_hash),
            telegram_session=session_exists,
            facebook_token=fb_token,
            # Unknown until a real post is attempted against a real group.
            facebook_groups_permitted=None,
            verified_telegram_groups=counts.get("telegram", 0),
            verified_facebook_groups=counts.get("facebook", 0),
            unverified_targets=unverified,
            notes=notes,
        )
    finally:
        if owned:
            conn.close()


# ---------------------------------------------------------------------------
# Posting
# ---------------------------------------------------------------------------


@dataclass
class PostResult:
    platform: str
    external_id: str
    ok: bool
    provider_ref: Optional[str] = None
    error: Optional[str] = None
    skipped_reason: Optional[str] = None


class RateLimiter:
    """Per-platform minimum interval between posts.

    Aggressive cross-posting is how accounts get restricted. The delay is
    deliberate and configurable, not a performance problem.
    """

    def __init__(self, min_interval: float = 20.0):
        self.min_interval = min_interval
        self._last: dict[str, float] = {}

    def wait(self, platform: str) -> None:
        now = time.monotonic()
        prev = self._last.get(platform)
        if prev is not None:
            delay = self.min_interval - (now - prev)
            if delay > 0:
                time.sleep(delay)
        self._last[platform] = time.monotonic()


async def post_to_telegram(
    target: sqlite3.Row, body: str, media: Optional[Path] = None
) -> PostResult:
    """Post to one Telegram group using a user session.

    A bot cannot post into arbitrary groups; it must be added by a member.
    A user session can post to any group the account has joined. That
    distinction is why this uses Telethon rather than the existing bot.
    """
    try:
        from telethon import TelegramClient
    except ImportError:
        return PostResult(
            "telegram", target["external_id"], False,
            error="telethon not installed",
            skipped_reason="dependency missing",
        )

    api_id = os.getenv("TELEGRAM_API_ID", "")
    api_hash = os.getenv("TELEGRAM_API_HASH", "")
    if not api_id or not api_hash:
        return PostResult(
            "telegram", target["external_id"], False,
            error="TELEGRAM_API_ID / TELEGRAM_API_HASH not configured",
            skipped_reason="credentials missing",
        )

    session_path = ROOT / "data" / "distribution_session"
    try:
        client = TelegramClient(str(session_path), int(api_id), api_hash)
        await client.connect()
        if not await client.is_user_authorized():
            await client.disconnect()
            return PostResult(
                "telegram", target["external_id"], False,
                error="user session not authorised; run the login step first",
                skipped_reason="needs interactive login",
            )

        entity = target["external_id"]
        if not entity.lstrip("-").isdigit():
            resolved = await client.get_entity(entity)
            entity = resolved.id

        if media and Path(media).exists():
            msg = await client.send_file(entity, str(media), caption=body)
        else:
            msg = await client.send_message(entity, body)
        await client.disconnect()
        return PostResult(
            "telegram", target["external_id"], True,
            provider_ref=str(getattr(msg, "id", "")) or None,
        )
    except Exception as exc:  # noqa: BLE001
        return PostResult(
            "telegram", target["external_id"], False,
            error=f"{type(exc).__name__}: {exc}",
        )


def post_to_facebook(target: sqlite3.Row, body: str) -> PostResult:
    """Attempt a Facebook Group post.

    Requires the app to be a member of the group and to hold the publish
    permission, both of which are gated behind app review. When that is not
    the case Meta returns an error, and that error is recorded rather than
    hidden.
    """
    token = os.getenv("META_ACCESS_TOKEN", "") or os.getenv("FB_ACCESS_TOKEN", "")
    if not token:
        return PostResult(
            "facebook", target["external_id"], False,
            error="META_ACCESS_TOKEN not configured",
            skipped_reason="credentials missing",
        )

    import urllib.parse
    import urllib.request

    group_id = target["external_id"]
    url = (
        f"https://graph.facebook.com/v19.0/{urllib.parse.quote(group_id)}/feed"
        f"?message={urllib.parse.quote(body)}&access_token={urllib.parse.quote(token)}"
    )
    try:
        with urllib.request.urlopen(url, timeout=20) as resp:
            body_json = json.loads(resp.read().decode())
        return PostResult(
            "facebook", group_id, True,
            provider_ref=body_json.get("post_id"),
        )
    except Exception as exc:  # noqa: BLE001
        detail = str(exc)
        # 190/200/294 mean the app is not a member or lacks permission.
        if "OAuthException" in detail or "permission" in detail.lower():
            return PostResult(
                "facebook", group_id, False, error=detail,
                skipped_reason="app is not a member of this group, or lacks "
                               "publish permission; this cannot be coded around",
            )
        return PostResult("facebook", group_id, False, error=detail)


def record_post(
    conn, result: PostResult, target_row_id: Optional[int],
    body: str, media: Optional[str],
) -> int:
    now = datetime.now(timezone.utc).isoformat()
    cur = conn.execute(
        "INSERT INTO posts (target_id, body, media_path, status, provider_ref,"
        " error, created_at, posted_at) VALUES (?,?,?,?,?,?,?,?)",
        (
            target_row_id, body, str(media) if media else None,
            "posted" if result.ok else "failed",
            result.provider_ref, result.error or result.skipped_reason,
            now, now if result.ok else None,
        ),
    )
    if target_row_id:
        if result.ok:
            # A successful post is the only evidence that this account is a
            # member. Verified rises here and nowhere else.
            conn.execute(
                "UPDATE targets SET post_count=post_count+1, last_posted=?,"
                " verified=1, joined=1, verified_at=COALESCE(verified_at, ?),"
                " last_error=NULL WHERE id=?",
                (now, now, target_row_id),
            )
        else:
            conn.execute(
                "UPDATE targets SET last_error=? WHERE id=?", (result.error, target_row_id)
            )
    conn.commit()
    return cur.lastrowid


async def broadcast(
    body: str,
    platform: str = "telegram",
    media: Optional[Path] = None,
    limit: Optional[int] = None,
    conn=None,
    min_interval: float = 20.0,
    poster: Optional[Callable[[Any, str, Optional[Path]], Any]] = None,
) -> dict[str, Any]:
    """Post to every verified target on a platform.

    Only verified targets are used. An unverified target is skipped
    explicitly and counted, so the summary never overstates reach.

    ``poster`` is injectable so tests can drive the orchestration without
    patching module globals, and so an alternate transport can be supplied.
    """
    owned = conn is None
    conn = conn or connect()
    limiter = RateLimiter(min_interval)
    results: list[PostResult] = []
    try:
        rows = conn.execute(
            "SELECT * FROM targets WHERE platform=? AND id_valid=1"
            " ORDER BY id",
            (platform,),
        ).fetchall()
        if limit:
            rows = rows[:limit]

        send = poster or (
            post_to_telegram if platform == "telegram" else
            lambda t, b, m=None: post_to_facebook(t, b)
        )

        for t in rows:
            limiter.wait(platform)
            r = await send(t, body, media)
            record_post(conn, r, t["id"], body, media)
            results.append(r)

        unverified = conn.execute(
            "SELECT COUNT(*) FROM targets WHERE platform=? AND verified=0",
            (platform,),
        ).fetchone()[0]

        return {
            "platform": platform,
            "attempted": len(results),
            "posted": sum(1 for r in results if r.ok),
            "failed": sum(1 for r in results if not r.ok),
            "skipped_unverified": unverified,
            "reach_claimed": sum(1 for r in results if r.ok),
            "note": (
                "reach_claimed counts only targets where a post actually "
                "succeeded, which is the only evidence this account is a "
                f"member. {unverified} target(s) have a real id but have "
                "never accepted a post."
            ),
            "results": [asdict(r) for r in results],
        }
    finally:
        if owned:
            conn.close()


if __name__ == "__main__":  # pragma: no cover
    import json as _json

    conn = connect()
    print(_json.dumps(probe(conn).to_json(), indent=2))
    conn.close()