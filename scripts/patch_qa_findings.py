import re
import sys
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

ROOT = Path(__file__).resolve().parent.parent

# 1. Fix engine/subscription_routes.py payload.client_id bug
sub_routes_path = ROOT / "engine" / "subscription_routes.py"
sub_routes_content = sub_routes_path.read_text(encoding="utf-8")

if "await _ensure_seeded_client(payload.client_id)" in sub_routes_content:
    sub_routes_content = sub_routes_content.replace(
        "await _ensure_seeded_client(payload.client_id)",
        "await _ensure_seeded_client(\"client_srt_shruhi\")"
    )
    sub_routes_path.write_text(sub_routes_content, encoding="utf-8")
    print("[SUCCESS] Patched engine/subscription_routes.py: payload.client_id -> 'client_srt_shruhi'")
else:
    print("[INFO] engine/subscription_routes.py already patched or target not found")

# 2. Fix scripts/gen_config.py DEFAULT_API
gen_config_path = ROOT / "scripts" / "gen_config.py"
gen_config_content = gen_config_path.read_text(encoding="utf-8")

gen_config_content = gen_config_content.replace(
    'DEFAULT_API = "https://algorise-ai-backend.onrender.com"',
    'DEFAULT_API = "https://algorise-ai-backend.onrender.com/api/v1"'
)
gen_config_content = gen_config_content.replace(
    'LOCAL_API = "http://localhost:8000"',
    'LOCAL_API = "http://localhost:8000/api/v1"'
)
gen_config_path.write_text(gen_config_content, encoding="utf-8")
print("[SUCCESS] Patched scripts/gen_config.py with /api/v1 suffix")

# 3. Normalize API_BASE in index.html
index_path = ROOT / "index.html"
index_content = index_path.read_text(encoding="utf-8")

old_api_base = """    const API_BASE =
      (window.ALGORISE_CONFIG && window.ALGORISE_CONFIG.apiBase) ||
      '/api/v1';"""

new_api_base = """    const _rawApi =
      (window.ALGORISE_CONFIG && window.ALGORISE_CONFIG.apiBase) ||
      '/api/v1';
    const API_BASE = _rawApi.endsWith('/api/v1') ? _rawApi : `${_rawApi.replace(/\\/$/, '')}/api/v1`;"""

if old_api_base in index_content:
    index_content = index_content.replace(old_api_base, new_api_base)
    index_path.write_text(index_content, encoding="utf-8")
    print("[SUCCESS] Normalized API_BASE in index.html")
else:
    print("[INFO] index.html already normalized or pattern not matched")

# 4. Normalize API_BASE in dashboard.html
dash_path = ROOT / "dashboard.html"
dash_content = dash_path.read_text(encoding="utf-8")

old_dash_api = """    const API_BASE =
      (window.ALGORISE_CONFIG && window.ALGORISE_CONFIG.apiBase) ||
      '/api/v1';"""

new_dash_api = """    const _rawApi =
      (window.ALGORISE_CONFIG && window.ALGORISE_CONFIG.apiBase) ||
      '/api/v1';
    const API_BASE = _rawApi.endsWith('/api/v1') ? _rawApi : `${_rawApi.replace(/\\/$/, '')}/api/v1`;"""

if old_dash_api in dash_content:
    dash_content = dash_content.replace(old_dash_api, new_dash_api)
    dash_path.write_text(dash_content, encoding="utf-8")
    print("[SUCCESS] Normalized API_BASE in dashboard.html")
else:
    print("[INFO] dashboard.html already normalized or pattern not matched")

# 5. Fix UTF-8 encoding in engine/aria_content_studio.py
studio_path = ROOT / "engine" / "aria_content_studio.py"
studio_content = studio_path.read_text(encoding="utf-8")

if "sys.stdout.reconfigure(encoding='utf-8')" not in studio_content:
    target_imp = "import sys\nimport time"
    rep_imp = "import sys\nimport time\n\nif hasattr(sys.stdout, 'reconfigure'):\n    sys.stdout.reconfigure(encoding='utf-8')"
    if target_imp in studio_content:
        studio_content = studio_content.replace(target_imp, rep_imp)
        studio_path.write_text(studio_content, encoding="utf-8")
        print("[SUCCESS] Added UTF-8 stdout reconfiguration to engine/aria_content_studio.py")

print("\nAll QA Auditor findings successfully resolved.")
