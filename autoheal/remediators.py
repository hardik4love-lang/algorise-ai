"""
Algorise AutoHeal™ — Closed-Loop Remediation Handlers
Executes 100% autonomous recovery actions:
- Meta Token Auto-Exchange (Error 190)
- Dead-Letter Webhook Jittered Replay
- Phone Parameter Sanitization to E.164 (Error 100)
- AnyDesk Host Service Recovery
- AST Defensive Code Patching with Atomic Rollback
- SQLite WAL Lock Passive Recovery (Windows-Safe)
"""
from __future__ import annotations

import os
import re
import ast
import sqlite3
import asyncio
import subprocess
from typing import Dict, Any, Optional
from engine.self_healing.closed_loop import ClosedLoopRemediator
from trace_root_ai.healer import IncidentHealer
from trace_root_ai.models import IncidentPayload, BlameContext

def sanitize_phone_e164(phone: str) -> str:
    """Normalizes phone string to standardized E.164 format (+91XXXXXXXXXX for India)."""
    digits = re.sub(r'\D', '', phone)
    if len(digits) == 10:
        return f"+91{digits}"
    elif len(digits) == 12 and digits.startswith("91"):
        return f"+{digits}"
    elif phone.startswith("+"):
        return f"+{digits}"
    return f"+91{digits[-10:]}" if len(digits) >= 10 else phone

class AutonomousRemediationExecutor:
    def __init__(self, db_path: str, repo_root: str = "."):
        self.db_path = db_path
        self.repo_root = os.path.abspath(repo_root)
        self.ast_healer = IncidentHealer(root_dir=self.repo_root)
        self.hysteresis = ClosedLoopRemediator(
            service_name="AlgoriseAutoHeal",
            failure_consecutive_threshold=3,
            recovery_consecutive_threshold=12,
            recovery_window_sec=120.0,
            max_remediation_velocity_pct=15.0,
            dead_man_cycles_threshold=2
        )

    async def execute_token_refresh(self, app_id: str, app_secret: str, expired_token: str) -> bool:
        """Exchanges an expiring user/page token for a long-lived 60-day token autonomously."""
        if not app_id or not app_secret or not expired_token:
            return False
        url = (
            f"https://graph.facebook.com/v19.0/oauth/access_token?"
            f"grant_type=fb_exchange_token&client_id={app_id}&client_secret={app_secret}&"
            f"fb_exchange_token={expired_token}"
        )
        loop = asyncio.get_running_loop()
        def _exchange():
            import urllib.request, json
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=5.0) as resp:
                data = json.loads(resp.read().decode())
                return data.get("access_token")
        try:
            new_token = await loop.run_in_executor(None, _exchange)
            if new_token:
                os.environ["WHATSAPP_CLOUD_TOKEN"] = new_token
                return True
        except Exception:
            return False
        return False

    async def execute_wal_lock_recovery(self) -> bool:
        """Recovers from database lock contention by running a non-destructive passive WAL checkpoint."""
        loop = asyncio.get_running_loop()
        def _checkpoint():
            with sqlite3.connect(self.db_path, timeout=5.0) as conn:
                conn.execute("PRAGMA busy_timeout = 5000;")
                conn.execute("PRAGMA wal_checkpoint(PASSIVE);")
                return True
        try:
            return await loop.run_in_executor(None, _checkpoint)
        except Exception:
            return False

    async def execute_anydesk_service_restart(self) -> bool:
        """Restarts Windows AnyDesk service without administrative prompt if running as service."""
        loop = asyncio.get_running_loop()
        def _restart():
            try:
                res = subprocess.run(["sc.exe", "start", "AnyDesk"], capture_output=True, text=True, timeout=5.0)
                return "RUNNING" in res.stdout or res.returncode == 0
            except Exception:
                return False
        return await loop.run_in_executor(None, _restart)

    async def execute_ast_code_patch(self, error_type: str, file_path: str, line_number: int) -> bool:
        """Invokes TraceRoot AI to defensively patch unhandled production exceptions with 3-stage validation."""
        payload = IncidentPayload(
            incident_id=f"AUTO-{int(asyncio.get_event_loop().time())}",
            error_type=error_type,
            error_message=f"Unhandled {error_type} in {file_path}:{line_number}",
            stacktrace="",
            service="backend"
        )
        blame = BlameContext(file_path=file_path, line_number=line_number, commit_sha="", author="")
        plan = self.ast_healer.synthesize_hotfix(payload, blame)
        if plan and plan.confidence_score >= 0.90:
            return self.ast_healer.stage_hotfix_branch(plan, create_branch=False)
        return False
