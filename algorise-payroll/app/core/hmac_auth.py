"""
Algorise PayHR - Hardware & Camera Webhook HMAC Authentication
Eliminates replay attacks and forged punches on biometric & CCTV stream endpoints.
"""

import hmac
import hashlib
import time
from typing import Optional
from fastapi import Request, HTTPException, status
from app.core.config import settings

# Memory cache for nonces (In production, backed by Redis with TTL)
_seen_nonces = set()


def verify_hmac_signature(
    payload_bytes: bytes,
    signature_header: str,
    timestamp_str: str,
    nonce: str,
    secret_key: str = settings.DEVICE_HMAC_SECRET
) -> bool:
    """
    Verifies that the incoming device push payload was signed by an authorized terminal.
    Validates:
    1. Replay prevention: Timestamp within acceptable window (default 300 seconds)
    2. Nonce freshness: Nonce has not been reused within the tolerance window
    3. Cryptographic integrity: Constant-time HMAC-SHA256 check
    """
    try:
        req_timestamp = int(timestamp_str)
    except (ValueError, TypeError):
        return False

    current_timestamp = int(time.time())

    # 1. Reject if timestamp is in the future or too far in the past
    if abs(current_timestamp - req_timestamp) > settings.HMAC_TIMESTAMP_TOLERANCE_SECONDS:
        return False

    # 2. Replay check via nonce
    nonce_key = f"{nonce}:{req_timestamp}"
    if nonce_key in _seen_nonces:
        return False
    _seen_nonces.add(nonce_key)

    # 3. Canonical string to sign: timestamp + "." + nonce + "." + payload_hex
    payload_hash = hashlib.sha256(payload_bytes).hexdigest()
    signing_input = f"{req_timestamp}.{nonce}.{payload_hash}".encode("utf-8")

    expected_signature = hmac.new(
        secret_key.encode("utf-8"),
        signing_input,
        hashlib.sha256
    ).hexdigest()

    # Constant-time comparison prevents timing side-channel attacks
    return hmac.compare_digest(expected_signature, signature_header)


async def device_hmac_guard(request: Request):
    """
    FastAPI dependency to secure /api/v1/attendance/device/push
    """
    signature = request.headers.get("X-Algorise-Signature")
    timestamp = request.headers.get("X-Algorise-Timestamp")
    nonce = request.headers.get("X-Algorise-Nonce")

    if not signature or not timestamp or not nonce:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing required hardware security headers (X-Algorise-Signature, Timestamp, Nonce)"
        )

    body = await request.body()
    is_valid = verify_hmac_signature(
        payload_bytes=body,
        signature_header=signature,
        timestamp_str=timestamp,
        nonce=nonce
    )

    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid HMAC hardware signature or replay attack detected"
        )
