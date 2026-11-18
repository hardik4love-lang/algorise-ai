"""
Algorise PayHR - Core Security & Cryptography Engine
Zero-compromise cryptography: AES-256-GCM for PII, salted BCrypt, and hardened JWT.
"""

import base64
import os
import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Union
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from passlib.context import CryptContext
from jose import jwt, JWTError

from app.core.config import settings

# Password Hashing Context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class PIIEncryptor:
    """
    Military-grade AES-256-GCM authenticated encryption for sensitive PII.
    Guarantees both confidentiality and tamper detection for:
    - Bank Account Numbers & IFSC
    - PAN (Permanent Account Number)
    - UAN (Universal Account Number)
    - Aadhaar references
    """

    def __init__(self, hex_key: str = settings.PII_ENCRYPTION_KEY):
        try:
            self.key = bytes.fromhex(hex_key)
            if len(self.key) != 32:
                # Fallback to SHA256 derived 32-byte key if raw hex length differs
                import hashlib
                self.key = hashlib.sha256(hex_key.encode()).digest()
        except Exception:
            import hashlib
            self.key = hashlib.sha256(hex_key.encode()).digest()
        self.aesgcm = AESGCM(self.key)

    def encrypt(self, plaintext: str) -> str:
        """
        Encrypts plaintext string into base64-encoded payload (12-byte nonce + ciphertext + 16-byte tag)
        """
        if not plaintext:
            return ""
        # 96-bit (12-byte) cryptographically secure random nonce
        nonce = os.urandom(12)
        ciphertext = self.aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
        combined = nonce + ciphertext
        return base64.b64encode(combined).decode("utf-8")

    def decrypt(self, encrypted_b64: str) -> str:
        """
        Decrypts base64 payload back to plaintext. Raises ValueError if tampered.
        """
        if not encrypted_b64:
            return ""
        try:
            combined = base64.b64decode(encrypted_b64.encode("utf-8"))
            if len(combined) < 28:  # 12 nonce + 16 tag minimum
                raise ValueError("Invalid ciphertext length")
            nonce = combined[:12]
            ciphertext = combined[12:]
            decrypted = self.aesgcm.decrypt(nonce, ciphertext, None)
            return decrypted.decode("utf-8")
        except Exception as e:
            raise ValueError(f"Decryption failed or data tampered: {str(e)}")


# Singleton instance
pii_cipher = PIIEncryptor()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Constant-time BCrypt password comparison"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Generate salted BCrypt hash with cost factor 12"""
    return pwd_context.hash(password)


def create_access_token(
    subject: Union[str, Any],
    role: str = "EMPLOYEE",
    expires_delta: Optional[timedelta] = None
) -> str:
    """Creates a hardened JWT access token"""
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode = {
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "sub": str(subject),
        "role": role,
        "iss": "algorise.ai",
        "type": "access"
    }
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(subject: Union[str, Any]) -> str:
    """Creates long-lived refresh token for token rotation"""
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode = {
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "sub": str(subject),
        "iss": "algorise.ai",
        "type": "refresh"
    }
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> Dict[str, Any]:
    """Validates signature and claims of JWT token"""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            issuer="algorise.ai"
        )
        return payload
    except JWTError as e:
        raise ValueError(f"Token validation failed: {str(e)}")
