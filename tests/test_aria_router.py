import os
import pytest

from aria.model_router import FreeModelRouter


def test_available_empty_without_keys(monkeypatch):
    for v in ("GROQ_API_KEY", "GOOGLE_API_KEY", "HF_TOKEN", "OPENROUTER_API_KEY", "CF_API_TOKEN"):
        monkeypatch.delenv(v, raising=False)
    r = FreeModelRouter()
    assert r.available() == []


def test_budget_gate():
    r = FreeModelRouter(token_budget=10)
    # cannot exceed budget; with no providers returns error
    import asyncio
    res = asyncio.run(r.generate("hi", max_tokens=100))
    assert "error" in res
