"""
Client Authentication & Authorization Domain Service for Algorise AI Solutions.
Handles PIN hashing, credential verification, and admin key validation.
"""

import hashlib
from typing import Optional
from fastapi import HTTPException


def hash_pin(pin: str) -> str:
    """Computes SHA-256 hash of a 4-digit PIN."""
    return hashlib.sha256(pin.encode("utf-8")).hexdigest()


def verify_pin(stored_hash: Optional[str], provided_pin: Optional[str]) -> bool:
    """Verifies whether provided PIN matches the stored SHA-256 hash."""
    if not stored_hash:
        return True
    if not provided_pin:
        return False
    return stored_hash == hash_pin(provided_pin)


def verify_client_pin(
    client_pin_hash: Optional[str],
    provided_pin: Optional[str],
    is_production: bool = False,
) -> None:
    """
    Enforces client PIN verification.
    Raises HTTPException(401) on mismatch or missing credential in production.
    """
    if not client_pin_hash:
        return

    if is_production or provided_pin is not None:
        if not provided_pin or client_pin_hash != hash_pin(provided_pin):
            detail_msg = (
                "Unauthorized: Valid 4-digit PIN required"
                if is_production
                else "Invalid 4-digit PIN"
            )
            raise HTTPException(status_code=401, detail=detail_msg)


def verify_admin_key(
    provided_key: Optional[str],
    expected_secret: str,
) -> None:
    """
    Owner/Admin endpoint gatekeeper.
    Raises HTTPException(403) if the admin secret is incorrect or missing.
    """
    if not provided_key or provided_key != expected_secret:
        raise HTTPException(
            status_code=403,
            detail="Unauthorized: Invalid admin secret key",
        )
