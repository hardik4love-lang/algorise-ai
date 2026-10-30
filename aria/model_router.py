"""Aria cloud-only free model router.

Selects among free cloud LLM endpoints with fallback and token budgeting.
No local compute; all providers are free-tier cloud services.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import httpx


@dataclass
class Provider:
    name: str
    base_url: str
    model: str
    api_key_env: str
    priority: int = 0


FREE_PROVIDERS: List[Provider] = [
    Provider("groq", "https://api.groq.com/openai/v1", "llama-3.3-70b-versatile", "GROQ_API_KEY", 0),
    Provider("google", "https://generativelanguage.googleapis.com/v1beta", "gemini-2.0-flash", "GOOGLE_API_KEY", 1),
    Provider("huggingface", "https://api-inference.huggingface.co/v1", "meta-llama/Llama-3.3-70B-Instruct", "HF_TOKEN", 2),
    Provider("openrouter", "https://openrouter.ai/api/v1", "meta-llama/llama-3.3-70b-instruct:free", "OPENROUTER_API_KEY", 3),
    Provider("cloudflare", "https://api.cloudflare.com/client/v4/accounts", "", "CF_API_TOKEN", 4),
]


class FreeModelRouter:
    def __init__(self, providers: Optional[List[Provider]] = None, token_budget: int = 100000):
        self.providers = sorted(providers or FREE_PROVIDERS, key=lambda p: p.priority)
        self.token_budget = token_budget
        self.tokens_used = 0

    def available(self) -> List[Provider]:
        return [p for p in self.providers if os.environ.get(p.api_key_env)]

    async def generate(self, prompt: str, system: str = "", max_tokens: int = 1024) -> Dict[str, Any]:
        if self.tokens_used + max_tokens > self.token_budget:
            return {"error": "token budget exceeded", "text": ""}
        for p in self.available():
            try:
                async with httpx.AsyncClient(timeout=60) as client:
                    resp = await client.post(
                        f"{p.base_url}/chat/completions",
                        headers={"Authorization": f"Bearer {os.environ.get(p.api_key_env)}"},
                        json={
                            "model": p.model,
                            "messages": [
                                {"role": "system", "content": system},
                                {"role": "user", "content": prompt},
                            ],
                            "max_tokens": max_tokens,
                            "temperature": 0.2,
                        },
                    )
                if resp.status_code == 200:
                    data = resp.json()
                    text = data["choices"][0]["message"]["content"]
                    self.tokens_used += max_tokens
                    return {"provider": p.name, "model": p.model, "text": text}
            except Exception:
                continue
        return {"error": "all providers failed", "text": ""}
