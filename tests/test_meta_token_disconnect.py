"""Test that the Meta access token can be removed.

A Page Access Token is a long-lived credential. It has to be removable
when it expires, when the page access is revoked, or before it is
replaced with a new one. There was no route to clear it, so a stale
token stayed in the database.
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


@pytest.fixture(scope="module")
def production_client():
    previous = dict(__import__("os").environ)
    __import__("os").environ.update({
        "ENVIRONMENT": "production",
        "MIGRATE_ON_START": "false",
        "REDIS_REQUIRED": "false",
        "ENABLE_EMBEDDED_SCHEDULER": "false",
        "SECRET_KEY": "test-not-a-real-secret",
        "ADMIN_SECRET": "test-not-a-real-secret",
        "FB_APP_SECRET": "test-not-a-real-secret",
    })

    from fastapi.testclient import TestClient
    from engine.main import app

    with TestClient(app) as client:
        yield client

    __import__("os").environ.clear()
    __import__("os").environ.update(previous)


def test_the_disconnect_route_exists():
    source = (ROOT / "engine" / "subscription_routes.py").read_text(
        encoding="utf-8"
    )
    assert "/auth/facebook/disconnect" in source


def test_a_token_can_be_removed(production_client):
    # Store a token.
    response = production_client.post(
        "/api/v1/auth/facebook/manual-token",
        json={
            "client_id": "client_srt_shruhi",
            "pin": "2026",
            "page_id": "61586357894191",
            "page_name": "Disconnect Test",
            "access_token": "EAA_DISCONNECT_TEST_1234567890",
        },
    )
    assert response.status_code == 200, response.text

    # Remove it.
    response = production_client.post(
        "/api/v1/auth/facebook/disconnect",
        json={"client_id": "client_srt_shruhi", "pin": "2026"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["fb_connected"] is False

    # Confirm it is gone.
    import asyncio

    from engine.database import db_manager
    from engine.models_sqlalchemy import Client
    from sqlalchemy import select

    async def read_token():
        async with db_manager.session() as session:
            result = await session.execute(
                select(Client).where(Client.id == "client_srt_shruhi")
            )
            row = result.scalars().first()
            return row.fb_access_token if row else None

    assert asyncio.run(read_token()) is None


def test_an_empty_token_is_rejected(production_client):
    """An empty token must not overwrite a stored one."""
    response = production_client.post(
        "/api/v1/auth/facebook/manual-token",
        json={
            "client_id": "client_srt_shruhi",
            "pin": "2026",
            "page_id": "61586357894191",
            "page_name": "Empty",
            "access_token": "",
        },
    )
    assert response.status_code == 400
