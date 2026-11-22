import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ops_path = ROOT / "engine" / "client_agent_ops.py"
content = ops_path.read_text(encoding="utf-8")

target = 'api_key_hash="",\n                phone=client_config.get("phone"'
replacement = 'api_key_hash="key_hash_algorise_support_internal_2026",\n                phone=client_config.get("phone"'

if target in content:
    content = content.replace(target, replacement, 1)
    ops_path.write_text(content, encoding="utf-8")
    print("SUCCESS: Updated unique api_key_hash for client_algorise_support")
else:
    print("Target not found or already updated")
