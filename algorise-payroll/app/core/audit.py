"""
Algorise PayHR - Tamper-Evident Immutable Audit Ledger
Cryptographically chained audit trail (SHA-256 hash chaining) for all HR & Payroll actions.
"""

import hashlib
import json
from datetime import datetime, timezone
from typing import Optional, Dict, Any


def generate_audit_hash(
    prev_hash: str,
    timestamp: str,
    actor_id: str,
    action: str,
    payload: Dict[str, Any]
) -> str:
    """
    Computes a cryptographic block hash chaining to the previous audit entry.
    Ensures that any direct database tampering breaks the audit chain verification.
    """
    payload_str = json.dumps(payload, sort_keys=True)
    raw_block = f"{prev_hash}|{timestamp}|{actor_id}|{action}|{payload_str}".encode("utf-8")
    return hashlib.sha256(raw_block).hexdigest()


class AuditLogger:
    """
    In-memory / DB ledger generator for audit events.
    """
    GENESIS_HASH = "0000000000000000000000000000000000000000000000000000000000000000"

    @classmethod
    def create_entry(
        cls,
        actor_id: str,
        action: str,
        target_entity: str,
        target_id: str,
        details: Dict[str, Any],
        prev_hash: Optional[str] = None
    ) -> Dict[str, Any]:
        prev = prev_hash or cls.GENESIS_HASH
        now_iso = datetime.now(timezone.utc).isoformat()
        
        block_hash = generate_audit_hash(
            prev_hash=prev,
            timestamp=now_iso,
            actor_id=actor_id,
            action=action,
            payload=details
        )

        return {
            "timestamp": now_iso,
            "actor_id": actor_id,
            "action": action,
            "target_entity": target_entity,
            "target_id": target_id,
            "details": details,
            "previous_hash": prev,
            "chain_hash": block_hash
        }
