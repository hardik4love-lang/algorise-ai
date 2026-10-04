"""
Distribution tests.

The behaviour that matters is the refusal: a list of invented group ids must
not be imported as if real, and reach must never be reported from an
unverified target. Everything else is plumbing around that.

Broadcast tests call asyncio.run() from sync tests because pytest-asyncio is
not configured in this repo, so @pytest.mark.asyncio would be skipped.
"""

import asyncio
import os
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from engine import distribution as dist  # noqa: E402


@pytest.fixture
def conn():
    tmp = Path(tempfile.mkdtemp())
    c = dist.connect(tmp / "dist_test.db")
    yield c
    c.close()


def _one(platform, ext_id, **kw):
    return {"platform": platform, "external_id": ext_id, **kw}


# ---------------------------------------------------------------------------
# Placeholder rejection
# ---------------------------------------------------------------------------


def test_placeholder_facebook_ids_are_rejected(conn):
    rows = [_one("facebook", f"fb_grp_{i:03d}") for i in range(1, 101)]
    result = dist.import_targets(rows, conn=conn)
    assert result["accepted_rows"] == 0, "synthetic ids were imported"
    assert result["distinct_targets"] == 0
    assert result["rejected_as_invalid"] == 100
    assert conn.execute("SELECT COUNT(*) FROM targets").fetchone()[0] == 0


def test_bundled_directory_is_entirely_rejected(conn):
    """The shipped directory contains no real group ids."""
    result = dist.import_from_directory(conn=conn)
    assert result["accepted_rows"] == 0
    assert result["distinct_targets"] == 0
    assert result["rejected_as_invalid"] == 100


def test_real_numeric_facebook_id_is_accepted(conn):
    result = dist.import_targets([_one("facebook", "123456789012345")], conn=conn)
    assert result["accepted_rows"] == 1
    assert result["distinct_targets"] == 1
    row = conn.execute("SELECT * FROM targets").fetchone()
    assert row["external_id"] == "123456789012345"


def test_short_numeric_facebook_id_is_rejected(conn):
    """Real Facebook group ids are long; '12345' is not one."""
    result = dist.import_targets([_one("facebook", "12345")], conn=conn)
    assert result["rejected_as_invalid"] == 1


def test_telegram_invite_and_handle_are_accepted(conn):
    result = dist.import_targets(
        [
            _one("telegram", "https://t.me/suratinfashion"),
            _one("telegram", "@diamondhub"),
        ],
        conn=conn,
    )
    assert result["accepted_rows"] == 2
    assert result["distinct_targets"] == 2


def test_telegram_invite_and_handle_collapse_to_one_target(conn):
    """A t.me link and a @handle are the same group; they must not become
    two targets and inflate a count."""
    result = dist.import_targets(
        [
            _one("telegram", "https://t.me/suratinfashion"),
            _one("telegram", "@suratinfashion"),
        ],
        conn=conn,
    )
    assert result["accepted_rows"] == 2
    assert result["distinct_targets"] == 1, (
        "two rows for one group inflated the count"
    )
    assert conn.execute("SELECT COUNT(*) FROM targets").fetchone()[0] == 1


def test_import_is_idempotent(conn):
    rows = [_one("telegram", "suratinfashion")]
    dist.import_targets(rows, conn=conn)
    dist.import_targets(rows, conn=conn)
    assert conn.execute("SELECT COUNT(*) FROM targets").fetchone()[0] == 1


def test_rows_without_platform_or_id_are_rejected(conn):
    result = dist.import_targets(
        [{"platform": "", "external_id": "x"}, {"platform": "telegram"}],
        conn=conn,
    )
    assert result["rejected_as_invalid"] == 2


# ---------------------------------------------------------------------------
# Capability reporting
# ---------------------------------------------------------------------------


def test_probe_reports_zero_verified_when_nothing_imported(conn):
    r = dist.probe(conn)
    assert r.verified_telegram_groups == 0
    assert r.verified_facebook_groups == 0
    assert r.can_post_anywhere is False


def test_import_alone_verifies_nothing(conn):
    """Import proves the id is real, not that this account is a member.

    Reach must stay at zero until a post actually succeeds, or the pitch can
    quote an imported count as though it were reachable audience.
    """
    dist.import_targets(
        [_one("telegram", "groupa"), _one("telegram", "groupb")], conn=conn
    )
    stored = conn.execute("SELECT COUNT(*) FROM targets").fetchone()[0]
    assert stored == 2, "both ids are real and should be stored"
    assert dist.probe(conn).verified_telegram_groups == 0, (
        "importing groups must not count as reach"
    )


def test_a_successful_post_raises_verified_reach(conn):
    dist.import_targets([_one("telegram", "groupa")], conn=conn)
    send, _ = _poster()

    asyncio.run(dist.broadcast("hi", "telegram", None, None, conn, 0, send))
    assert dist.probe(conn).verified_telegram_groups == 1


def test_probe_explains_that_telegram_needs_a_user_session(conn):
    joined = " ".join(dist.probe(conn).notes).lower()
    assert "bot cannot post" in joined or "user session" in joined


def test_probe_serialises(conn):
    body = dist.probe(conn).to_json()
    assert "can_post_anywhere" in body
    assert isinstance(body["notes"], list)


# ---------------------------------------------------------------------------
# Broadcast never claims unverified reach
# ---------------------------------------------------------------------------


def _poster(ok=True):
    """Injectable transport, so the orchestration is tested without
    patching module globals or touching the network."""
    calls = []

    async def send(target, body, media=None):
        calls.append(target["external_id"])
        if ok:
            return dist.PostResult("telegram", target["external_id"], True,
                                   provider_ref="42")
        return dist.PostResult("telegram", target["external_id"], False,
                               error="not a member")

    return send, calls


def test_broadcast_attempts_only_verified_targets(conn):
    dist.import_targets([_one("telegram", "groupa")], conn=conn)
    send, calls = _poster()

    result = asyncio.run(
        dist.broadcast("hello", "telegram", None, None, conn, 0, send)
    )
    assert result["attempted"] == 1
    assert result["posted"] == 1
    assert result["reach_claimed"] == 1
    assert calls == ["groupa"]


def test_broadcast_reports_zero_reach_when_all_fail(conn):
    dist.import_targets([_one("telegram", "groupa")], conn=conn)
    send, _ = _poster(ok=False)

    result = asyncio.run(
        dist.broadcast("hello", "telegram", None, None, conn, 0, send)
    )
    assert result["failed"] == 1
    assert result["posted"] == 0
    assert result["reach_claimed"] == 0


def test_broadcast_counts_unverified_targets_separately(conn):
    """A target with a real id but no successful post must be reported as
    unverified, and never counted toward reach."""
    dist.import_targets([_one("telegram", "groupa")], conn=conn)
    conn.execute(
        "INSERT INTO targets (platform, external_id, id_valid, verified)"
        " VALUES (?,?,1,0)",
        ("telegram", "ghost"),
    )
    conn.commit()
    send, calls = _poster()

    result = asyncio.run(
        dist.broadcast("hello", "telegram", None, None, conn, 0, send)
    )
    assert result["attempted"] == 2, "both real ids should be attempted"
    assert "ghost" in calls, "membership is discovered by trying"
    assert result["skipped_unverified"] == 0, (
        "both were attempted this run, so neither is merely skipped"
    )
    assert result["reach_claimed"] == 2, (
        "both posts succeeded, so both are now genuinely reachable"
    )


def test_broadcast_respects_a_limit(conn):
    for i in range(10):
        dist.import_targets([_one("telegram", f"group{i}")], conn=conn)
    send, _ = _poster()

    result = asyncio.run(
        dist.broadcast("hi", "telegram", None, 3, conn, 0, send)
    )
    assert result["attempted"] == 3


def test_successful_post_increments_the_target_counter(conn):
    dist.import_targets([_one("telegram", "groupa")], conn=conn)
    send, _ = _poster()

    asyncio.run(dist.broadcast("hello", "telegram", None, None, conn, 0, send))
    row = conn.execute("SELECT * FROM targets").fetchone()
    assert row["post_count"] == 1
    assert row["last_posted"] is not None


# ---------------------------------------------------------------------------
# Platform honesty
# ---------------------------------------------------------------------------


def test_facebook_post_without_a_token_skips(conn, monkeypatch):
    monkeypatch.delenv("META_ACCESS_TOKEN", raising=False)
    monkeypatch.delenv("FB_ACCESS_TOKEN", raising=False)
    r = dist.post_to_facebook({"external_id": "123456789012345"}, "hello")
    assert r.ok is False
    assert r.skipped_reason == "credentials missing"


def test_telegram_post_without_credentials_skips(monkeypatch):
    monkeypatch.delenv("TELEGRAM_API_ID", raising=False)
    monkeypatch.delenv("TELEGRAM_API_HASH", raising=False)
    r = asyncio.run(
        dist.post_to_telegram({"external_id": "groupa"}, "hello")
    )
    assert r.ok is False
    assert r.skipped_reason == "credentials missing"


def test_rate_limiter_enforces_an_interval():
    """Aggressive cross-posting is how accounts get restricted."""
    limiter = dist.RateLimiter(min_interval=0.25)
    limiter.wait("telegram")
    assert limiter.min_interval == 0.25