"""Aria cloud agent loop entrypoint (runs in GitHub Actions)."""
from __future__ import annotations

import asyncio
import os

from aria.model_router import FreeModelRouter


async def main() -> None:
    router = FreeModelRouter(token_budget=int(os.environ.get("ARIA_TOKEN_BUDGET", "50000")))
    result = await router.generate(
        prompt="Summarize repository status and propose next improvement.",
        system="You are Aria, an autonomous cloud agent. Be concise.",
    )
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
