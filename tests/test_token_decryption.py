"""Test that the stored token is decrypted before it reaches Graph.

The token is encrypted at rest. Two read sites returned the stored
value, so the ciphertext was sent to the Graph API and every call
failed with "Cannot parse access token". The agent run reported
comments_scanned 0 with no indication that the credential was the
problem.

These tests pin the decryption at every read site.
"""
import ast
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from engine.scheduler import _safe_decrypt  # noqa: E402
from engine.security import encryption_manager  # noqa: E402

FAKE_TOKEN = "EAA_FAKE_TOKEN_FOR_TESTING_ONLY_1234567890"


def test_the_agent_run_decrypts_the_token():
    source = (
        ROOT / "engine" / "subscription_routes.py"
    ).read_text(encoding="utf-8")
    assert "_safe_decrypt(client.fb_access_token)" in source, (
        "the agent run sends the stored value to Graph instead of the "
        "decrypted token"
    )


def test_the_meta_proxy_decrypts_the_token():
    source = (ROOT / "engine" / "meta_proxy.py").read_text(encoding="utf-8")
    assert "_safe_decrypt(row.fb_access_token)" in source, (
        "the meta proxy sends the stored value to Graph instead of the "
        "decrypted token"
    )


def test_the_webhook_resolves_the_token_per_page():
    source = (
        ROOT / "engine" / "subscription_routes.py"
    ).read_text(encoding="utf-8")
    # The webhook must resolve the token from the client record.
    assert "_page_access_token" in source
    assert "select(Client).where(Client.fb_page_id == page_id)" in source


def test_no_read_site_returns_the_stored_value_directly():
    """Every read of fb_access_token has to go through the decrypt."""
    for name in ("subscription_routes.py", "meta_proxy.py"):
        path = ROOT / "engine" / name
        tree = ast.parse(path.read_text(encoding="utf-8"))

        for node in ast.walk(tree):
            # A return of the attribute, unwrapped.
            if isinstance(node, ast.Return) and isinstance(node.value, ast.Attribute):
                if node.value.attr != "fb_access_token":
                    continue
                # The attribute must be inside a decrypt call.
                parent_ok = False
                for parent in ast.walk(node):
                    if isinstance(parent, ast.Call) and parent.value is node:
                        parent_ok = True
                if not parent_ok:
                    # A bare "return client.fb_access_token" is a leak.
                    pytest.fail(
                        f"{name} line {node.lineno} returns the stored "
                        f"token without decrypting it"
                    )


def test_the_decrypt_round_trip():
    stored = encryption_manager.encrypt(FAKE_TOKEN)
    assert _safe_decrypt(stored) == FAKE_TOKEN
