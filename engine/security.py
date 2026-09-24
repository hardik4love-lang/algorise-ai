"""
Security utilities for Algorise AI Engine.
Handles encryption, API key management, rate limiting, and input validation.
"""

import hashlib
import hmac
import secrets
import time
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64

from engine.config import get_settings
from engine.cache import redis_manager, CacheKeys
from engine.logging import get_logger
from engine.metrics import record_error

logger = get_logger(__name__)
settings = get_settings()


# ============================================================================
# ENCRYPTION
# ============================================================================

class EncryptionManager:
    """Manages encryption/decryption of sensitive data."""

    def __init__(self):
        self._fernet: Optional[Fernet] = None
        self._initialize()

    def _initialize(self) -> None:
        """Initialize Fernet with key derived from secret_key."""
        import os
        salt_val = os.environ.get("ENCRYPTION_SALT", "algorise-ai-production-salt-2026")
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt_val.encode(),
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(settings.secret_key.encode()))
        self._fernet = Fernet(key)

    def encrypt(self, plaintext: str) -> str:
        """Encrypt a string."""
        if self._fernet is None:
            self._initialize()
        return self._fernet.encrypt(plaintext.encode()).decode()

    def decrypt(self, ciphertext: str) -> str:
        """Decrypt a string."""
        if self._fernet is None:
            self._initialize()
        return self._fernet.decrypt(ciphertext.encode()).decode()


encryption_manager = EncryptionManager()


# ============================================================================
# API KEY MANAGEMENT
# ============================================================================

@dataclass
class APIKeyInfo:
    """Information about an API key."""
    client_id: str
    client_name: str
    tier: str
    quota: int
    created_at: datetime
    last_used: Optional[datetime] = None
    is_active: bool = True
    scopes: Tuple[str, ...] = ("read", "write", "execute")


class APIKeyManager:
    """Manages API key validation and quota tracking."""

    def __init__(self):
        self._keys_cache: Dict[str, APIKeyInfo] = {}
        self._load_keys()

    def _load_keys(self) -> None:
        """Load API keys from settings."""
        for key, info in settings.api_keys.items():
            key_hash = self._hash_key(key)
            self._keys_cache[key_hash] = APIKeyInfo(
                client_id=info.get("client", "unknown"),
                client_name=info.get("client", "unknown"),
                tier=info.get("tier", "Growth"),
                quota=info.get("quota", 10000),
                created_at=datetime.utcnow(),
            )

    def _hash_key(self, key: str) -> str:
        """Hash an API key for storage."""
        return hashlib.sha256(key.encode()).hexdigest()

    def validate_key(self, api_key: str) -> Optional[APIKeyInfo]:
        """Validate an API key and return key info if valid."""
        key_hash = self._hash_key(api_key)
        key_info = self._keys_cache.get(key_hash)
        
        if key_info and key_info.is_active:
            key_info.last_used = datetime.utcnow()
            return key_info
        
        return None

    def check_quota(self, key_info: APIKeyInfo) -> Tuple[bool, int]:
        """Check if key has quota remaining. Returns (has_quota, remaining)."""
        # In production, this would check Redis for current usage
        # For now, return based on static quota
        return True, key_info.quota

    def increment_usage(self, key_info: APIKeyInfo) -> None:
        """Increment usage counter for a key."""
        # In production, this would increment a Redis counter
        pass


api_key_manager = APIKeyManager()


# ============================================================================
# RATE LIMITING
# ============================================================================

from collections import deque
import threading

class _LocalSlidingLimiter:
    """Thread-safe in-process sliding window limiter used when Redis is unreachable."""
    def __init__(self, limit: int = 100, window: int = 60):
        self.limit = limit
        self.window = window
        self.records: Dict[str, deque] = {}
        self.lock = threading.Lock()

    def check(self, key: str, req_limit: Optional[int] = None, req_window: Optional[int] = None) -> Tuple[bool, int]:
        now = time.time()
        max_req = req_limit or self.limit
        win = req_window or self.window
        with self.lock:
            if key not in self.records:
                self.records[key] = deque()
            q = self.records[key]
            while q and q[0] < now - win:
                q.popleft()
            if len(q) >= max_req:
                return False, 0
            q.append(now)
            return True, max(0, max_req - len(q))

_local_fallback_limiter = _LocalSlidingLimiter()


class RateLimiter:
    """Token bucket rate limiter using Redis."""

    def __init__(self):
        self.default_limit = settings.rate_limit_requests
        self.default_window = settings.rate_limit_window_seconds

    async def check_rate_limit(
        self,
        key: str,
        limit: Optional[int] = None,
        window: Optional[int] = None,
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Check rate limit for a key.
        Returns (allowed, info_dict).
        """
        limit = limit or self.default_limit
        window = window or self.default_window
        cache_key = CacheKeys.rate_limit(key)

        try:
            # Get current bucket state
            bucket = await redis_manager.get(cache_key)
            
            now = time.time()
            
            if bucket is None:
                # Create new bucket
                bucket = {
                    "tokens": limit - 1,
                    "last_refill": now,
                    "max_tokens": limit,
                    "refill_rate": limit / window,
                }
                await redis_manager.set(cache_key, bucket, expire=window * 2)
                return True, {"remaining": limit - 1, "reset_in": window}
            
            # Refill tokens based on time passed
            elapsed = now - bucket["last_refill"]
            refill = elapsed * bucket["refill_rate"]
            bucket["tokens"] = min(bucket["max_tokens"], bucket["tokens"] + refill)
            bucket["last_refill"] = now
            
            if bucket["tokens"] >= 1:
                bucket["tokens"] -= 1
                await redis_manager.set(cache_key, bucket, expire=window * 2)
                return True, {
                    "remaining": int(bucket["tokens"]),
                    "reset_in": int(window - elapsed),
                }
            else:
                await redis_manager.set(cache_key, bucket, expire=window * 2)
                return False, {
                    "remaining": 0,
                    "reset_in": int(window - elapsed),
                    "retry_after": int((1 - bucket["tokens"]) / bucket["refill_rate"]),
                }
                
        except Exception as e:
            logger.warning("Rate limiter Redis unavailable, activating in-process sliding window fallback", error=str(e))
            record_error("rate_limiter_redis_fallback", "security")
            allowed, rem = _local_fallback_limiter.check(key, limit, window)
            return allowed, {
                "remaining": rem,
                "reset_in": window,
                "fallback_mode": True,
                "retry_after": 5 if not allowed else 0,
            }

    async def get_rate_limit_info(self, key: str) -> Dict[str, Any]:
        """Get current rate limit info without consuming tokens."""
        cache_key = CacheKeys.rate_limit(key)
        bucket = await redis_manager.get(cache_key)
        
        if bucket is None:
            return {"remaining": self.default_limit, "reset_in": self.default_window}
        
        now = time.time()
        elapsed = now - bucket["last_refill"]
        refill = elapsed * bucket["refill_rate"]
        tokens = min(bucket["max_tokens"], bucket["tokens"] + refill)
        
        return {
            "remaining": int(tokens),
            "reset_in": int(self.default_window - elapsed),
        }


rate_limiter = RateLimiter()


# ============================================================================
# INPUT VALIDATION
# ============================================================================

class InputValidator:
    """Validates and sanitizes input data."""

    # Maximum sizes
    MAX_QUERY_LENGTH = 10000
    MAX_PAYLOAD_SIZE = 1024 * 1024  # 1 MB
    MAX_STRING_LENGTH = 5000

    # Dangerous patterns to detect
    DANGEROUS_PATTERNS = [
        r"(?i)(drop|delete|truncate|alter)\s+table",
        r"(?i)union\s+select",
        r"(?i)insert\s+into",
        r"(?i)update\s+.*\s+set",
        r"(?i)exec\s*\(",
        r"(?i)eval\s*\(",
        r"(?i)system\s*\(",
        r"(?i)subprocess",
        r"(?i)__import__",
        r"(?i)getattr\s*\(",
        r"(?i)setattr\s*\(",
        r"<script",
        r"javascript:",
        r"on\w+\s*=",
    ]

    @classmethod
    def validate_query(cls, query: str) -> Tuple[bool, str]:
        """Validate a query string."""
        if not query:
            return False, "Query cannot be empty"
        
        if len(query) > cls.MAX_QUERY_LENGTH:
            return False, f"Query exceeds maximum length of {cls.MAX_QUERY_LENGTH}"
        
        # Check for dangerous patterns
        for pattern in cls.DANGEROUS_PATTERNS:
            import re
            if re.search(pattern, query):
                logger.warning("Dangerous pattern detected in query", pattern=pattern)
                return False, f"Query contains potentially dangerous pattern: {pattern}"
        
        return True, "OK"

    @classmethod
    def validate_payload(cls, payload: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate a JSON payload."""
        if not isinstance(payload, dict):
            return False, "Payload must be a JSON object"
        
        # Check total size
        import json
        payload_str = json.dumps(payload)
        if len(payload_str) > cls.MAX_PAYLOAD_SIZE:
            return False, f"Payload exceeds maximum size of {cls.MAX_PAYLOAD_SIZE} bytes"
        
        # Recursively validate string values
        def check_value(value, path="root"):
            if isinstance(value, str):
                if len(value) > cls.MAX_STRING_LENGTH:
                    return False, f"String at {path} exceeds maximum length"
                for pattern in cls.DANGEROUS_PATTERNS:
                    import re
                    if re.search(pattern, value):
                        return False, f"Dangerous pattern at {path}: {pattern}"
            elif isinstance(value, dict):
                for k, v in value.items():
                    result = check_value(v, f"{path}.{k}")
                    if not result[0]:
                        return result
            elif isinstance(value, list):
                for i, v in enumerate(value):
                    result = check_value(v, f"{path}[{i}]")
                    if not result[0]:
                        return result
            return True, "OK"
        
        return check_value(payload)

    @classmethod
    def sanitize_string(cls, value: str) -> str:
        """Sanitize a string for safe usage."""
        # Remove null bytes
        value = value.replace('\x00', '')
        # Limit length
        if len(value) > cls.MAX_STRING_LENGTH:
            value = value[:cls.MAX_STRING_LENGTH]
        return value


input_validator = InputValidator()


# ============================================================================
# SECURITY HEADERS
# ============================================================================

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline';",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
}


def get_security_headers() -> Dict[str, str]:
    """Get security headers for HTTP responses."""
    return SECURITY_HEADERS.copy()


# ============================================================================
# CORS CONFIGURATION
# ============================================================================

def get_cors_config() -> Dict[str, Any]:
    """Get CORS configuration based on environment."""
    if settings.environment == "production":
        return {
            "allow_origins": [
                "https://algorise-ai.com",
                "https://www.algorise-ai.com",
                "https://api.algorise-ai.com",
                "https://hardik4love-lang.github.io",
                "https://algorise.ai",
                "https://app.algorise.ai",
            ],
            "allow_credentials": True,
            "allow_methods": ["GET", "POST", "OPTIONS"],
            "allow_headers": ["Content-Type", "X-Algorise-Key", "Authorization", "X-Client-Pin"],
        }
    else:
        return {
            "allow_origins": [
                "http://localhost:3000",
                "http://localhost:8000",
                "http://127.0.0.1:8000",
                "http://localhost:5173",
            ],
            "allow_credentials": True,
            "allow_methods": ["*"],
            "allow_headers": ["*"],
        }


# ============================================================================
# AUDIT LOGGING
# ============================================================================

@dataclass
class AuditEvent:
    """Audit log event."""
    event_type: str
    client_id: str
    action: str
    resource: str
    success: bool
    details: Dict[str, Any]
    timestamp: datetime
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None


class AuditLogger:
    """Logs security-relevant events."""

    def __init__(self):
        self.events: list = []  # In production, write to secure log store

    def log(self, event: AuditEvent) -> None:
        """Log an audit event."""
        self.events.append(event)
        logger.info(
            "AUDIT",
            event_type=event.event_type,
            client_id=event.client_id,
            action=event.action,
            resource=event.resource,
            success=event.success,
            details=event.details,
        )

    def log_api_call(
        self,
        client_id: str,
        endpoint: str,
        method: str,
        success: bool,
        details: Dict[str, Any],
        ip: Optional[str] = None,
    ) -> None:
        """Log an API call."""
        self.log(AuditEvent(
            event_type="api_call",
            client_id=client_id,
            action=f"{method} {endpoint}",
            resource=endpoint,
            success=success,
            details=details,
            timestamp=datetime.utcnow(),
            ip_address=ip,
        ))

    def log_auth_attempt(
        self,
        api_key: str,
        success: bool,
        ip: Optional[str] = None,
    ) -> None:
        """Log an authentication attempt."""
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()[:16]
        self.log(AuditEvent(
            event_type="auth_attempt",
            client_id=key_hash,
            action="authenticate",
            resource="api_key",
            success=success,
            details={"key_prefix": api_key[:8] + "..."},
            timestamp=datetime.utcnow(),
            ip_address=ip,
        ))

    def log_rate_limit_exceeded(
        self,
        client_id: str,
        endpoint: str,
        ip: Optional[str] = None,
    ) -> None:
        """Log a rate limit exceeded event."""
        self.log(AuditEvent(
            event_type="rate_limit_exceeded",
            client_id=client_id,
            action="request",
            resource=endpoint,
            success=False,
            details={"reason": "rate_limit_exceeded"},
            timestamp=datetime.utcnow(),
            ip_address=ip,
        ))


audit_logger = AuditLogger()


# ============================================================================
# SECURITY MIDDLEWARE HELPERS
# ============================================================================

async def verify_api_key(api_key: str) -> Tuple[bool, Optional[APIKeyInfo]]:
    """Verify API key and check quota."""
    key_info = api_key_manager.validate_key(api_key)
    
    if key_info is None:
        audit_logger.log_auth_attempt(api_key, success=False)
        return False, None
    
    has_quota, remaining = api_key_manager.check_quota(key_info)
    if not has_quota:
        return False, key_info
    
    audit_logger.log_auth_attempt(api_key, success=True)
    return True, key_info


async def check_rate_limit_middleware(key: str) -> Tuple[bool, Dict[str, Any]]:
    """Check rate limit for middleware."""
    return await rate_limiter.check_rate_limit(key)


def validate_request_payload(payload: Dict[str, Any]) -> Tuple[bool, str]:
    """Validate request payload."""
    return input_validator.validate_payload(payload)


def validate_query_string(query: str) -> Tuple[bool, str]:
    """Validate query string."""
    return input_validator.validate_query(query)