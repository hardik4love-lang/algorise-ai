"""
Regression test for the silent recording failure.

engine/meta_proxy._record imported `SessionLocal` from engine.database, which
does not exist there, and wrapped both the import and the call in
try/except. Every proxied Meta operation therefore appeared to record an
audit row and recorded nothing. This is the same failure mode as the
fabricated scheduler telemetry, except quieter: there the data was invented,
here it was simply absent.

These tests fail if recording ever stops writing again.
"""

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from engine.database import sync_engine, sync_session  # noqa: E402
from engine.models_sqlalchemy import BotExecution  # noqa: E402


@pytest.fixture
def session():
    s = sync_session()
    yield s
    s.close()


def test_sync_engine_is_really_synchronous():
    """An async driver here raises MissingGreenlet on first connect.

    The configured URL is sqlite+aiosqlite because the request path is
    async. Passing it straight to create_engine() produces an engine that
    cannot connect.
    """
    eng = sync_engine()
    with eng.connect() as conn:
        assert conn.exec_driver_sql("SELECT 1").scalar() == 1


def test_record_actually_writes_a_bot_execution_row(session):
    from engine.meta_proxy import _record

    before = session.query(BotExecution).count()

    _record(
        client_id="test-client",
        bot_id="meta_reply",
        operation="reply_comment",
        success=True,
        output={"comment_id": "cmt-xyz", "reply_id": "rep-1"},
        latency_ms=42.0,
        reasoning="regression test",
    )
    session.expire_all()

    assert session.query(BotExecution).count() == before + 1

    row = (
        session.query(BotExecution)
        .filter(BotExecution.bot_id == "meta_reply")
        .order_by(BotExecution.id.desc())
        .first()
    )
    assert row is not None, "no row written: recording is silently failing again"
    assert row.success is True
    assert row.output_data["comment_id"] == "cmt-xyz"
    assert row.latency_ms == pytest.approx(42.0)


def test_record_failure_is_logged_not_swallowed():
    """A recording error must be visible.

    The original swallowed it with a bare except and no logging, which is
    why the failure went unnoticed across five phases.
    """
    import inspect

    from engine.meta_proxy import _record

    src = inspect.getsource(_record)
    assert "logger.error" in src, "_record must log failures"
    assert "pass\n" not in src, "_record must not silently pass"


def test_stored_client_token_does_not_raise_on_missing_config():
    """_stored_client_token runs before every proxied call.

    It previously caught a broad Exception around an import that cannot
    work, which hid the problem. It must return None quietly but must not
    be capable of raising.
    """
    from engine.meta_proxy import _stored_client_token

    result = _stored_client_token()
    assert result is None or isinstance(result, str)