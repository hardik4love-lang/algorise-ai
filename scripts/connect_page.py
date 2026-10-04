"""Connect Shruhi's Facebook Page token via the production API.

PowerShell mangles the long token when passed through the shell, so the
request is made from Python. The token is read from an environment variable
and never written to disk.
"""
import json
import os
import urllib.request
import urllib.error

BASE = os.getenv("ALG_BASE", "https://algorise-ai-backend.onrender.com")
TOKEN = os.getenv("SHRUHI_PAGE_TOKEN", "")

if not TOKEN:
    raise SystemExit("  set SHRUHI_PAGE_TOKEN first")

payload = json.dumps({
    "client_id": "client_srt_shruhi",
    "page_id": "61586357894191",
    "page_name": "Shruhi Collections",
    "access_token": TOKEN,
    "pin": "2026",
}).encode()

req = urllib.request.Request(
    f"{BASE}/api/v1/auth/facebook/manual-token",
    data=payload,
    headers={"Content-Type": "application/json"},
    method="POST",
)
try:
    with urllib.request.urlopen(req, timeout=120) as r:
        print(f"  HTTP {r.status}")
        print("  " + r.read().decode()[:400])
except urllib.error.HTTPError as e:
    print(f"  HTTP {e.code}")
    print("  " + e.read().decode()[:400])
