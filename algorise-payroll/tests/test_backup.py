"""
Unit Tests for Zero-Knowledge Encrypted Backup Engine
Verifies encryption, decryption roundtrip, anti-tamper rejection, and SHA-256 checksums.
"""

import os
import pytest
from app.services.backup_engine import ZeroKnowledgeBackupEngine


def test_backup_encryption_and_decryption_roundtrip(tmp_path):
    """
    Verifies that raw data can be encrypted to a file and decrypted back with exact byte match.
    """
    raw_payload = b"CRITICAL_PAYROLL_DATA: Employee EMP001 Basic Salary = 50000; Bank Acc = 1234567890"
    backup_file = str(tmp_path / "test_backup.sql.gz.enc")

    # 1. Encrypt
    meta = ZeroKnowledgeBackupEngine.encrypt_data_to_file(
        raw_data=raw_payload,
        output_file_path=backup_file
    )
    assert os.path.exists(backup_file)
    assert meta["size_bytes"] > 0
    assert len(meta["sha256_checksum"]) == 64

    # 2. Decrypt
    decrypted_bytes = ZeroKnowledgeBackupEngine.decrypt_file_to_data(backup_file)
    assert decrypted_bytes == raw_payload


def test_backup_anti_tampering_detection(tmp_path):
    """
    Ensures that modifying even a single byte of the encrypted file causes decryption failure.
    """
    raw_payload = b"SECRET_LEDGER_BLOCK"
    backup_file = str(tmp_path / "tamper_test.sql.gz.enc")

    ZeroKnowledgeBackupEngine.encrypt_data_to_file(
        raw_data=raw_payload,
        output_file_path=backup_file
    )

    # Tamper with file
    with open(backup_file, "r+b") as f:
        f.seek(20)  # Seek into ciphertext
        byte = f.read(1)
        # Invert byte
        tampered_byte = bytes([byte[0] ^ 0xFF])
        f.seek(20)
        f.write(tampered_byte)

    # Decryption MUST fail due to authentication tag failure
    with pytest.raises(Exception):
        ZeroKnowledgeBackupEngine.decrypt_file_to_data(backup_file)
