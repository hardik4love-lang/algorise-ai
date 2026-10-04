"""Declare the dependencies the code imports but requirements.txt omitted.

loguru was added at module level in engine/meta_proxy.py and
engine/whatsapp_webhook.py but never declared. Render installs only what
requirements.txt lists, so the import raised ModuleNotFoundError and the
deployment failed.

telethon is imported inside try/except, so its absence degraded distribution
silently rather than failing the build: Telegram posting would have reported
"dependency missing" forever with no obvious cause.

colorama is imported guardedly for Windows console colour.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
p = ROOT / "requirements.txt"
text = p.read_text(encoding="utf-8")

ADDITIONS = """
# --- added when the Meta proxy and distribution engine landed ---
# loguru: module-level import in engine/meta_proxy.py and
# engine/whatsapp_webhook.py. Its absence broke the Render build.
loguru>=0.7.3
# telethon: Telegram user-session posting. Imported guardedly, so a missing
# declaration degraded distribution silently instead of failing loudly.
telethon>=1.45.0
# colorama: colour output for structlog's ConsoleRenderer on Windows.
# Guarded, Windows only.
colorama>=0.4.6; sys_platform == "win32"
"""

if "loguru" in text:
    print("  already declared")
else:
    p.write_text(text.rstrip() + "\n" + ADDITIONS, encoding="utf-8")
    print("  added loguru, telethon, colorama to requirements.txt")