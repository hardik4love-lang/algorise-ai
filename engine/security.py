"""
Security utilities for Algorise AI Engine.
Handles encryption, API key management, rate limiting, and input validation.
"""
import hashlib
import hmac
import json
import time
from collections import deque
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
from fastapi import Header, HTTPException
from engine.config import get_settings
from engine.cache import redis_manager, CacheKeys
from engine.logging import get_logger
from engine.metrics import record_error
logger = get_logger(__name__)
settings = get_settings()

class EncryptionManager:
    """Manages encryption/decryption of sensitive data."""

    def __init__(self):
        self._fernet: Optional[Fernet] = None
        self._initialize()

    def _initialize(self) -> None:
        """Initialize Fernet with key derived from secret_key."""
        import os
        salt_val = os.environ.get('ENCRYPTION_SALT', 'algorise-ai-production-salt-2026')
        kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt_val.encode(), iterations=100000)
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
    scopes: Tuple[str, ...] = ('read', 'write', 'execute')
    usage_count: int = 0

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
                client_id=info.get('client', 'unknown'),
                client_name=info.get('client', 'unknown'),
                tier=info.get('tier', 'Growth'),
                quota=info.get('quota', 10000),
                created_at=datetime.now(timezone.utc),
                usage_count=0
            )

    def _hash_key(self, key: str) -> str:
        """Hash an API key for storage."""
        return hashlib.sha256(key.encode()).hexdigest()

    def validate_key(self, api_key: str) -> Optional[APIKeyInfo]:
        """Validate an API key and return key info if valid."""
        key_hash = self._hash_key(api_key)
        key_info = self._keys_cache.get(key_hash)
        if key_info and key_info.is_active:
            key_info.last_used = datetime.now(timezone.utc)
            return key_info
        return None

    def check_quota(self, key_info: APIKeyInfo) -> Tuple[bool, int]:
        """Check if key has quota remaining. Returns (has_quota, remaining)."""
        current_usage = getattr(key_info, "usage_count", 0)
        remaining = max(0, key_info.quota - current_usage)
        return (remaining > 0, remaining)

    def increment_usage(self, key_info: APIKeyInfo, amount: int = 1) -> int:
        """Increment usage counter for a key. Returns updated usage count."""
        key_info.usage_count = getattr(key_info, "usage_count", 0) + amount
        key_info.last_used = datetime.now(timezone.utc)
        return key_info.usage_count

    def reset_usage(self, key_info: APIKeyInfo) -> None:
        """Reset usage counter for a key."""
        key_info.usage_count = 0

api_key_manager = APIKeyManager()
from collections import deque
import threading

class _LocalSlidingLimiter:
    """Thread-safe in-process sliding window limiter with bounded memory eviction."""

    def __init__(self, limit: int=100, window: int=60, max_keys: int=5000):
        self.limit = limit
        self.window = window
        self.max_keys = max_keys
        self.records: Dict[str, deque] = {}
        self.lock = threading.Lock()

    def check(self, key: str, req_limit: Optional[int]=None, req_window: Optional[int]=None) -> Tuple[bool, int]:
        now = time.time()
        max_req = req_limit or self.limit
        win = req_window or self.window
        with self.lock:
            if len(self.records) > self.max_keys:
                cutoff = now - win
                expired = [k for k, q in self.records.items() if not q or q[-1] < cutoff]
                for k in expired:
                    del self.records[k]
            if key not in self.records:
                self.records[key] = deque()
            q = self.records[key]
            while q and q[0] < now - win:
                q.popleft()
            if len(q) >= max_req:
                return (False, 0)
            q.append(now)
            return (True, max(0, max_req - len(q)))
_local_fallback_limiter = _LocalSlidingLimiter()

class RateLimiter:
    """Token bucket rate limiter using atomic Redis transactions with local fallback."""

    def __init__(self):
        self.default_limit = settings.rate_limit_requests
        self.default_window = settings.rate_limit_window_seconds

    async def check_rate_limit(self, key: str, limit: Optional[int]=None, window: Optional[int]=None) -> Tuple[bool, Dict[str, Any]]:
        """
        Check rate limit for a key.
        Returns (allowed, info_dict).
        """
        limit = limit or self.default_limit
        window = window or self.default_window
        cache_key = CacheKeys.rate_limit(key)
        try:
            now = time.time()
            async with redis_manager.client.pipeline(transaction=True) as pipe:
                await pipe.watch(cache_key)
                raw_bucket = await pipe.get(cache_key)
                bucket = json.loads(raw_bucket) if raw_bucket else None
                if bucket is None:
                    bucket = {'tokens': limit - 1, 'last_refill': now, 'max_tokens': limit, 'refill_rate': limit / window}
                    pipe.multi()
                    pipe.set(cache_key, json.dumps(bucket), ex=window * 2)
                    await pipe.execute()
                    return (True, {'remaining': limit - 1, 'reset_in': window})
                elapsed = now - bucket.get('last_refill', now)
                refill = elapsed * bucket.get('refill_rate', limit / window)
                current_tokens = min(bucket.get('max_tokens', limit), bucket.get('tokens', limit) + refill)
                bucket['last_refill'] = now
                if current_tokens >= 1:
                    bucket['tokens'] = current_tokens - 1
                    pipe.multi()
                    pipe.set(cache_key, json.dumps(bucket), ex=window * 2)
                    await pipe.execute()
                    return (True, {'remaining': int(bucket['tokens']), 'reset_in': max(0, int(window - elapsed))})
                else:
                    bucket['tokens'] = current_tokens
                    pipe.multi()
                    pipe.set(cache_key, json.dumps(bucket), ex=window * 2)
                    await pipe.execute()
                    retry_after = max(1, int((1 - current_tokens) / bucket.get('refill_rate', limit / window)))
                    return (False, {'remaining': 0, 'reset_in': max(0, int(window - elapsed)), 'retry_after': retry_after})
        except Exception as e:
            logger.warning('Rate limiter Redis unavailable, activating in-process sliding window fallback', error=str(e))
            record_error('rate_limiter_redis_fallback', 'security')
            allowed, rem = _local_fallback_limiter.check(key, limit, window)
            return (allowed, {'remaining': rem, 'reset_in': window, 'fallback_mode': True, 'retry_after': 5 if not allowed else 0})

    async def get_rate_limit_info(self, key: str) -> Dict[str, Any]:
        """Get current rate limit info without consuming tokens."""
        cache_key = CacheKeys.rate_limit(key)
        bucket = await redis_manager.get(cache_key)
        if bucket is None:
            return {'remaining': self.default_limit, 'reset_in': self.default_window}
        now = time.time()
        elapsed = now - bucket['last_refill']
        refill = elapsed * bucket['refill_rate']
        tokens = min(bucket['max_tokens'], bucket['tokens'] + refill)
        return {'remaining': int(tokens), 'reset_in': int(self.default_window - elapsed)}
rate_limiter = RateLimiter()

class InputValidator:
    """Validates and sanitizes input data."""
    MAX_QUERY_LENGTH = 10000
    MAX_PAYLOAD_SIZE = 1024 * 1024
    MAX_STRING_LENGTH = 5000
    DANGEROUS_PATTERNS = ['(?i)(drop|delete|truncate|alter)\\s+table', '(?i)union\\s+select', '(?i)insert\\s+into', '(?i)update\\s+.*\\s+set', '(?i)exec\\s*\\(', '(?i)eval\\s*\\(', '(?i)system\\s*\\(', '(?i)subprocess', '(?i)__import__', '(?i)getattr\\s*\\(', '(?i)setattr\\s*\\(', '<script', 'javascript:', 'on\\w+\\s*=']

    @classmethod
    def validate_query(cls, query: str) -> Tuple[bool, str]:
        """Validate a query string."""
        if not query:
            return (False, 'Query cannot be empty')
        if len(query) > cls.MAX_QUERY_LENGTH:
            return (False, f'Query exceeds maximum length of {cls.MAX_QUERY_LENGTH}')
        for pattern in cls.DANGEROUS_PATTERNS:
            import re
            if re.search(pattern, query):
                logger.warning('Dangerous pattern detected in query', pattern=pattern)
                return (False, f'Query contains potentially dangerous pattern: {pattern}')
        return (True, 'OK')

    @classmethod
    def validate_payload(cls, payload: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate a JSON payload."""
        if not isinstance(payload, dict):
            return (False, 'Payload must be a JSON object')
        import json
        payload_str = json.dumps(payload)
        if len(payload_str) > cls.MAX_PAYLOAD_SIZE:
            return (False, f'Payload exceeds maximum size of {cls.MAX_PAYLOAD_SIZE} bytes')

        def check_value(value, path='root'):
            if isinstance(value, str):
                if len(value) > cls.MAX_STRING_LENGTH:
                    return (False, f'String at {path} exceeds maximum length')
                for pattern in cls.DANGEROUS_PATTERNS:
                    import re
                    if re.search(pattern, value):
                        return (False, f'Dangerous pattern at {path}: {pattern}')
            elif isinstance(value, dict):
                for k, v in value.items():
                    result = check_value(v, f'{path}.{k}')
                    if not result[0]:
                        return result
            elif isinstance(value, list):
                for i, v in enumerate(value):
                    result = check_value(v, f'{path}[{i}]')
                    if not result[0]:
                        return result
            return (True, 'OK')
        return check_value(payload)

    @classmethod
    def sanitize_string(cls, value: str) -> str:
        """Sanitize a string for safe usage."""
        value = value.replace('\x00', '')
        if len(value) > cls.MAX_STRING_LENGTH:
            value = value[:cls.MAX_STRING_LENGTH]
        return value
input_validator = InputValidator()
SECURITY_HEADERS = {'X-Content-Type-Options': 'nosniff', 'X-Frame-Options': 'DENY', 'X-XSS-Protection': '1; mode=block', 'Referrer-Policy': 'strict-origin-when-cross-origin', 'Content-Security-Policy': "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline';", 'Permissions-Policy': 'geolocation=(), microphone=(), camera=()', 'Strict-Transport-Security': 'max-age=31536000; includeSubDomains'}

def get_security_headers() -> Dict[str, str]:
    """Get security headers for HTTP responses."""
    return SECURITY_HEADERS.copy()

def get_cors_config() -> Dict[str, Any]:
    """Get CORS configuration across production and local environments.

    CORS_ALLOWED_ORIGINS overrides the built-in list. In production a
    missing override is reported loudly rather than fatal, so a deployment
    is never taken down by a configuration gap. When the override is
    provided, only those exact origins are allowed.
    """
    from engine.config import get_settings

    settings = get_settings()
    raw = (settings.cors_allowed_origins or "").strip()
    is_production = settings.environment.lower() in {"production", "prod"}

    if raw:
        origins = [o.strip() for o in raw.split(",") if o.strip()]
    elif is_production:
        print(
            "WARNING: CORS_ALLOWED_ORIGINS is not set; falling back to the built-in origin "
            "profile. Set an explicit comma-separated origin list before serving public traffic."
        )
        origins = [
            'https://algorise-ai.com', 'https://www.algorise-ai.com', 'https://api.algorise-ai.com',
            'https://shruhicollections.in', 'https://www.shruhicollections.in',
            'https://hardik4love-lang.github.io', 'https://algorise.ai', 'https://app.algorise.ai',
            'https://algorise-ai-backend.onrender.com',
        ]
    else:
        origins = [
            'https://algorise-ai.com', 'https://www.algorise-ai.com', 'https://api.algorise-ai.com',
            'https://shruhicollections.in', 'https://www.shruhicollections.in',
            'https://hardik4love-lang.github.io', 'https://algorise.ai', 'https://app.algorise.ai',
            'http://localhost:3000', 'http://localhost:8000', 'http://127.0.0.1:8000',
            'http://localhost:8090', 'http://localhost:8095', 'http://localhost:5173',
        ]

    return {
        'allow_origins': origins,
        'allow_credentials': True,
        'allow_methods': ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS'],
        'allow_headers': ['Authorization', 'Content-Type', 'X-Algorise-Key', 'X-Algorise-API-Key', 'X-Employer-ID'],
    }

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
    """Logs security-relevant events with bounded in-memory buffer."""

    def __init__(self, max_events: int = 1000):
        self.events = deque(maxlen=max_events)

    def log(self, event: AuditEvent) -> None:
        """Log an audit event."""
        self.events.append(event)
        logger.info('AUDIT', event_type=event.event_type, client_id=event.client_id, action=event.action, resource=event.resource, success=event.success, details=event.details)

    def log_api_call(self, client_id: str, endpoint: str, method: str, success: bool, details: Dict[str, Any], ip: Optional[str]=None) -> None:
        """Log an API call."""
        self.log(AuditEvent(event_type='api_call', client_id=client_id, action=f'{method} {endpoint}', resource=endpoint, success=success, details=details, timestamp=datetime.now(timezone.utc), ip_address=ip))

    def log_auth_attempt(self, api_key: Optional[str], success: bool, ip: Optional[str]=None) -> None:
        """Log an authentication attempt.

        A missing or non-string key is the common case here, because this is
        called on the rejection path. Hashing and slicing the raw value
        raised AttributeError and TypeError on None, turning what should be a
        clean 401 into a 500 with a stack trace instead of a message.
        """
        material = api_key if isinstance(api_key, str) else ''
        key_hash = hashlib.sha256(material.encode()).hexdigest()[:16]
        self.log(AuditEvent(event_type='auth_attempt', client_id=key_hash, action='authenticate', resource='api_key', success=success, details={'key_prefix': material[:8] + '...' if material else ''}, timestamp=datetime.now(timezone.utc), ip_address=ip))

    def log_rate_limit_exceeded(self, client_id: str, endpoint: str, ip: Optional[str]=None) -> None:
        """Log a rate limit exceeded event."""
        self.log(AuditEvent(event_type='rate_limit_exceeded', client_id=client_id, action='request', resource=endpoint, success=False, details={'reason': 'rate_limit_exceeded'}, timestamp=datetime.now(timezone.utc), ip_address=ip))
audit_logger = AuditLogger()

async def verify_api_key(api_key: Optional[str]=None, x_api_key: Optional[str]=Header(None, alias='x-api-key'), algorise_key: Optional[str]=Header(None, alias='X-Algorise-Key')) -> Tuple[bool, Optional[APIKeyInfo]]:
    """Verify an API key and check quota.

    Accepts three sources, checked in order:

      1. X-Algorise-Key  the header every pre-existing endpoint in this
                         service already used (main.py:get_api_key). This is
                         the app's own convention and takes precedence.
      2. x-api-key       a generic header some clients send.
      3. api_key         a query parameter, retained because existing callers
                         use it.

    Endpoints added before this accepted only (2) and (3), which meant they
    authenticated differently from the rest of the service: a client using
    the documented X-Algorise-Key header got a 401 from them and a 200 from
    everything else. One scheme, one header, no surprises.

    Query parameters are still supported but are the least preferred form:
    they are written to server access logs, proxy logs and browser history.

    Only str values are accepted. When this dependency is invoked outside
    FastAPI's resolution the un-resolved default arrives as the Header marker
    object itself, and passing that into key hashing raises AttributeError
    deep in the manager.
    """
    for candidate in (algorise_key, x_api_key, api_key):
        if isinstance(candidate, str) and candidate:
            key = candidate
            break
    else:
        key = ''
    if not key:
        if settings.environment in ('production', 'staging'):
            audit_logger.log_auth_attempt(None, success=False)
            return (False, None)
        elif settings.environment in ('development', 'test', 'testing', 'local'):
            key = os.getenv('ALG_TEST_KEY', 'fixture-key')
        else:
            audit_logger.log_auth_attempt(None, success=False)
            return (False, None)
    key_info = api_key_manager.validate_key(key)
    if key_info is None:
        audit_logger.log_auth_attempt(key, success=False)
        return (False, None)
    has_quota, remaining = api_key_manager.check_quota(key_info)
    if not has_quota:
        return (False, key_info)
    api_key_manager.increment_usage(key_info)
    audit_logger.log_auth_attempt(api_key, success=True)
    return (True, key_info)

async def require_api_key(api_key: Optional[str]=None, x_api_key: Optional[str]=Header(None, alias='x-api-key'), algorise_key: Optional[str]=Header(None, alias='X-Algorise-Key')) -> APIKeyInfo:
    """FastAPI dependency that enforces API key authentication.
    
    Raises HTTPException(401) on missing or invalid key.
    Raises HTTPException(429) if quota is exhausted.
    Returns valid APIKeyInfo.
    """
    for candidate in (algorise_key, x_api_key, api_key):
        if isinstance(candidate, str) and candidate:
            key = candidate
            break
    else:
        key = ''
    if not key:
        if settings.environment in ('production', 'staging'):
            audit_logger.log_auth_attempt(None, success=False)
            raise HTTPException(
                status_code=401,
                detail="Authentication failed: Missing required 'X-Algorise-Key' header in production/staging",
                headers={'WWW-Authenticate': 'ApiKey'},
            )
        elif settings.environment in ('development', 'test', 'testing', 'local'):
            key = os.getenv('ALG_TEST_KEY', 'fixture-key')
        else:
            audit_logger.log_auth_attempt(None, success=False)
            raise HTTPException(
                status_code=401,
                detail="Authentication failed: Missing required 'X-Algorise-Key' header",
                headers={'WWW-Authenticate': 'ApiKey'},
            )
    if not key:
        raise HTTPException(status_code=401, detail="Authentication failed: Missing required 'X-Algorise-Key' header", headers={'WWW-Authenticate': 'ApiKey'})
    key_info = api_key_manager.validate_key(key)
    if key_info is None:
        audit_logger.log_auth_attempt(key, success=False)
        raise HTTPException(status_code=401, detail='Authentication failed: Invalid API key', headers={'WWW-Authenticate': 'ApiKey'})
    has_quota, remaining = api_key_manager.check_quota(key_info)
    if not has_quota:
        raise HTTPException(status_code=429, detail='API key quota exceeded')
    api_key_manager.increment_usage(key_info)
    audit_logger.log_auth_attempt(key, success=True)
    return key_info

async def check_rate_limit_middleware(key: str) -> Tuple[bool, Dict[str, Any]]:
    """Check rate limit for middleware."""
    return await rate_limiter.check_rate_limit(key)

def validate_request_payload(payload: Dict[str, Any]) -> Tuple[bool, str]:
    """Validate request payload."""
    return input_validator.validate_payload(payload)

def validate_query_string(query: str) -> Tuple[bool, str]:
    """Validate query string."""
    return input_validator.validate_query(query)
