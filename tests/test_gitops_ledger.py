"""
Unit tests for GitOps Transactional Ledger & WAL
Verifies:
- Linearizable event sequencing via SHA-256 hash chains
- Idempotent recording
- Dual-Key SRE Emergency Override key verification
"""

import os
import time
import pytest
from engine.gitops_ledger import GitOpsLedger

def test_gitops_ledger_record_and_hash_chain(tmp_path):
    ledger_file = str(tmp_path / "test_ledger.json")
    wal_file = str(tmp_path / "test_wal.jsonl")
    
    ledger = GitOpsLedger(ledger_path=ledger_file, wal_path=wal_file)
    
    tx1 = ledger.record_transaction(
        task_id="tx-omi-21876",
        repository="BasedHardware/omi",
        pr_number=21876,
        status="MAINTAINER_APPROVED",
        gross_value_usd=50.0
    )
    assert tx1["prev_hash"] == "0" * 64
    assert len(tx1["sha256_hash"]) == 64
    
    tx2 = ledger.record_transaction(
        task_id="tx-omi-21855",
        repository="BasedHardware/omi",
        pr_number=21855,
        status="MAINTAINER_APPROVED",
        gross_value_usd=50.0
    )
    assert tx2["prev_hash"] == tx1["sha256_hash"]
    assert len(tx2["sha256_hash"]) == 64

def test_gitops_ledger_idempotency(tmp_path):
    ledger_file = str(tmp_path / "test_ledger_idemp.json")
    wal_file = str(tmp_path / "test_wal_idemp.jsonl")
    
    ledger = GitOpsLedger(ledger_path=ledger_file, wal_path=wal_file)
    
    tx1 = ledger.record_transaction(
        task_id="tx-ticket-146152932",
        repository="BasedHardware/omi",
        pr_number=21811,
        status="SUBMITTED_IN_CLAIM",
        gross_value_usd=100.0
    )
    
    # Second attempt with identical status should be a no-op idempotent return
    tx2 = ledger.record_transaction(
        task_id="tx-ticket-146152932",
        repository="BasedHardware/omi",
        pr_number=21811,
        status="SUBMITTED_IN_CLAIM",
        gross_value_usd=100.0
    )
    assert tx1["sha256_hash"] == tx2["sha256_hash"]

def test_emergency_override_key_validation():
    current_ts = int(time.time())
    valid_key = f"SRE-OVERRIDE-{current_ts}-SECUREAUTH99"
    assert GitOpsLedger.validate_emergency_override_key(valid_key) is True
    
    # Expired key (> 4 hours old)
    expired_ts = current_ts - 15000
    expired_key = f"SRE-OVERRIDE-{expired_ts}-SECUREAUTH99"
    assert GitOpsLedger.validate_emergency_override_key(expired_key) is False
    
    # Malformed key
    assert GitOpsLedger.validate_emergency_override_key("INVALID-KEY") is False
