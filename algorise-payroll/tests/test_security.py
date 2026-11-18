"""
Unit Tests for Cryptography, HMAC Signatures, and Anti-Spoofing
"""

import time
import pytest
from app.core.security import pii_cipher, create_access_token, decode_token
from app.core.hmac_auth import verify_hmac_signature
from app.core.anti_spoofing import AntiSpoofingValidator


def test_pii_aes_gcm_encryption():
    """
    Verifies authenticated AES-256-GCM encryption & decryption for bank/PAN numbers.
    """
    sensitive_pan = "ABCDE1234F"
    encrypted = pii_cipher.encrypt(sensitive_pan)
    assert encrypted != sensitive_pan

    decrypted = pii_cipher.decrypt(encrypted)
    assert decrypted == sensitive_pan


def test_jwt_token_creation_and_claims():
    """
    Verifies JWT token issuance and claim extraction.
    """
    token = create_access_token(subject="EMP-001", role="HR_ADMIN")
    payload = decode_token(token)
    assert payload["sub"] == "EMP-001"
    assert payload["role"] == "HR_ADMIN"
    assert payload["iss"] == "algorise.ai"


def test_hmac_replay_and_tamper_detection():
    """
    Verifies hardware HMAC-SHA256 signature and replay prevention.
    """
    import hmac
    import hashlib

    secret = "test-secret-key-123"
    body = b'{"device_sn": "ZK123", "pin": "EMP01"}'
    ts = str(int(time.time()))
    nonce = "test-nonce-1"

    body_hash = hashlib.sha256(body).hexdigest()
    signing_input = f"{ts}.{nonce}.{body_hash}".encode("utf-8")
    valid_sig = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).hexdigest()

    # 1. Valid signature passes
    assert verify_hmac_signature(body, valid_sig, ts, nonce, secret) is True

    # 2. Tampered body fails
    tampered_body = b'{"device_sn": "ZK123", "pin": "EMP99"}'
    assert verify_hmac_signature(tampered_body, valid_sig, ts, "test-nonce-2", secret) is False

    # 3. Expired timestamp fails
    expired_ts = str(int(time.time()) - 400)
    assert verify_hmac_signature(body, valid_sig, expired_ts, "test-nonce-3", secret) is False


def test_anti_spoofing_mock_location_rejection():
    """
    Ensures mock GPS providers are instantly rejected.
    """
    check = AntiSpoofingValidator.validate_punch_authenticity(
        current_lat=19.0760,
        current_lon=72.8777,
        accuracy_meters=10.0,
        is_mock_provider=True,  # Mock provider active
        office_lat=19.0760,
        office_lon=72.8777,
        allowed_radius_meters=50.0
    )
    assert check["is_valid"] is False
    assert check["error_code"] == "MOCK_LOCATION_DETECTED"
