"""Test that the Meta access token is encrypted at rest.

A Page Access Token is a long-lived credential. It was written to the
client record in plaintext, which left a live credential readable in
the database and in any database dump.

These tests pin the round trip: the token is stored encrypted, the
scheduler reads it back, and a plaintext token is never persisted.
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from engine.security import encryption_manager  # noqa: E402
from engine.scheduler import _safe_decrypt  # noqa: E402

FAKE_TOKEN = "EAA_FAKE_TOKEN_FOR_TESTING_ONLY_1234567890"


def test_token_is_not_stored_in_plaintext():
    stored = encryption_manager.encrypt(FAKE_TOKEN)

    assert stored != FAKE_TOKEN
    assert FAKE_TOKEN not in stored
    assert not stored.startswith("EAA")


def test_the_scheduler_reads_the_token_back():
    """The scheduler decrypts the token before calling Graph."""
    stored = encryption_manager.encrypt(FAKE_TOKEN)
    assert _safe_decrypt(stored) == FAKE_TOKEN


def test_a_missing_token_reads_as_empty():
    assert _safe_decrypt(None) == ""
    assert _safe_decrypt("") == ""


def test_a_simulated_token_reads_as_empty():
    """A simulated token is not a credential and must not be used."""
    assert _safe_decrypt("simulated_token") == ""


def test_the_route_encrypts_the_token():
    """The manual token route must not write a plaintext token."""
    source = (
        ROOT / "engine" / "subscription_routes.py"
    ).read_text(encoding="utf-8")

    # The assignment must go through the encryption manager, not the
    # raw payload value.
    assert "client.fb_access_token = payload.access_token.strip()" not in source
    assert "client.fb_access_token = tok" not in source
    assert "encryption_manager.encrypt" in source
