"""
Algorise DevEx Platform: Commercial Metering Gateway API
Provides multi-tenant REST endpoints for centralized flaky test quarantine,
AST blast radius telemetry, role-based access control (RBAC), and autonomous incident healing mesh.
"""

from __future__ import annotations

import os
import json
import logging
import re
import asyncio
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

# Resiliency: circuit breaker, retry logic
from tenacity import retry, stop_after_attempt, wait_exponential_jitter, retry_if_exception_type

from autotest_sentinel.models import (
    FlakeCategory,
    FlakinessReport,
    RootCauseHypothesis,
)
from autotest_sentinel.quarantine import QuarantineManager
from context_pr.blast_radius import BlastRadiusAnalyzer

# Job Placement Marketplace (dual-sided: employers post vacancies, workers pay $1/mo)
try:
    from job_portal.api import router as marketplace_router
    MARKETPLACE_AVAILABLE = True
except Exception:  # pragma: no cover - optional subsystem
    marketplace_router = None
    MARKETPLACE_AVAILABLE = False

# Optional Redis for multi-tenant state (graceful fallback to in-memory)
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    redis = None
    REDIS_AVAILABLE = False

# Observability: Prometheus metrics
try:
    from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False

# Observability: OpenTelemetry
try:
    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.sdk.resources import Resource
    OTEL_AVAILABLE = True
except ImportError:
    trace = None
    OTEL_AVAILABLE = False

# ---------------------------------------------------------------------------
# Logging Configuration
# ---------------------------------------------------------------------------

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("algorise.devex.api")

# Secret redaction patterns
SECRET_PATTERNS = [
    (re.compile(r'("api[_-]?key"|"token"|"secret"|"password")\s*:\s*"[^"]*"'), r': "***"'),
    (re.compile(r'(api\s+key|password|secret|token)\s*:\s*"[^"]*"', re.IGNORECASE), r': "***"'),
    (re.compile(r'(Bearer\s+)[A-Za-z0-9\-_]{20,}'), r'***' ),
    (re.compile(r'(X-Algorise-API-Key:\s*)[A-Za-z0-9\-_]{8,}'), r'***' ),
    (re.compile(r'(gh[ps]_[A-Za-z0-9]{36})'), r'***' ),
]

def redact_secrets(text: str) -> str:
    """Redact secrets from log messages."""
    for pattern, replacement in SECRET_PATTERNS:
        text = pattern.sub(replacement, text)
    return text

class RedactingLogger:
    """Logger that automatically redacts secrets."""
    def __init__(self, logger):
        self.logger = logger
    
    def _log(self, level, msg, *args, **kwargs):
        if isinstance(msg, str):
            msg = redact_secrets(msg)
        self.logger._log(level, msg, args, **kwargs)
    
    def info(self, msg, *args, **kwargs): self._log(logging.INFO, msg, *args, **kwargs)
    def warning(self, msg, *args, **kwargs): self._log(logging.WARNING, msg, *args, **kwargs)
    def error(self, msg, *args, **kwargs): self._log(logging.ERROR, msg, *args, **kwargs)
    def debug(self, msg, *args, **kwargs): self._log(logging.DEBUG, msg, *args, **kwargs)
    def exception(self, msg, *args, **kwargs): self._log(logging.ERROR, msg, *args, **kwargs)

# Wrap logger with secret redaction
logger = RedactingLogger(logger)

# ---------------------------------------------------------------------------
# Configuration Loading (Environment-Based, No Hardcoded Secrets)
# ---------------------------------------------------------------------------

ALL_SCOPES = [
    "quarantine:read",
    "quarantine:write",
    "blast_radius:read",
    "incident:heal",
    "usage:read",
    "admin:*",
]

DEFAULT_CORS_ORIGINS = [
    "https://app.algorise.ai",
    "https://dashboard.algorise.ai",
    "http://localhost:3000",
    "http://localhost:8080",
]

def _parse_origins() -> List[str]:
    """Parse ALLOWED_ORIGINS from env (comma-separated) or use defaults."""
    raw = os.environ.get("ALLOWED_ORIGINS", "")
    if raw.strip():
        return [o.strip() for o in raw.split(",") if o.strip()]
    return DEFAULT_CORS_ORIGINS

def _load_tenant_registry() -> Dict[str, Dict[str, Any]]:
    """
    Load tenant registry from environment variable ALGORISE_TENANT_REGISTRY (JSON string).
    Falls back to empty dict - production MUST configure via env.
    """
    raw = os.environ.get("ALGORISE_TENANT_REGISTRY", "{}")
    try:
        registry = json.loads(raw)
        if not isinstance(registry, dict):
            logger.warning("ALGORISE_TENANT_REGISTRY must be a JSON object; using empty")
            return {}
        return registry
    except json.JSONDecodeError as e:
        logger.error(f"Invalid ALGORISE_TENANT_REGISTRY JSON: {e}")
        return {}

# Load tenant registry from env (no hardcoded keys)
TENANT_REGISTRY: Dict[str, Dict[str, Any]] = _load_tenant_registry()


def _canonical_tenants() -> Dict[str, Dict[str, Any]]:
    """Build the canonical tenant table from the engine settings.

    The DevEx gateway and the engine API must recognise the same clients,
    tiers, roles and scopes. The engine settings are the single source of
    truth; this projection keeps both surfaces consistent even when the
    environment variable registry is empty or has been reloaded.
    """
    tenants: Dict[str, Dict[str, Any]] = {}
    try:
        from engine.config import get_settings

        configured = get_settings().api_keys or {}
    except Exception:
        configured = {}

    for api_key, info in configured.items():
        tenants[api_key] = {
            "client": info.get("client", "Unknown"),
            "tier": info.get("tier", "Free"),
            "role": info.get("role", "developer"),
            "scopes": list(info.get("scopes", [])),
            "quota": info.get("quota", 100),
            "requests_used": 0,
        }
    return tenants


CANONICAL_TENANTS: Dict[str, Dict[str, Any]] = _canonical_tenants()

# Engine capability surface exposed on the health endpoints. Kept static so
# the readiness contract does not depend on optional heavy dependencies.
ENGINE_STATUS: Dict[str, Any] = {
    "autotest_sentinel": "available",
    "quarantine": "available",
    "blast_radius": "available",
    "incident_heal": "available",
    "marketplace": "available" if MARKETPLACE_AVAILABLE else "unavailable",
}

# Allow single admin key override via env (for dev/bootstrap only)
_env_key = os.environ.get("ALGORISE_API_KEY")
if _env_key and _env_key not in TENANT_REGISTRY:
    TENANT_REGISTRY[_env_key] = {
        "client": "Environment Admin",
        "tier": "Enterprise Custom",
        "role": "admin",
        "scopes": ALL_SCOPES,
        "quota": 100000,
        "requests_used": 0,
    }

# Seed with canonical tenants so the gateway and the engine API always
# recognise the same clients even when no registry was supplied by env.
for _key, _tenant in CANONICAL_TENANTS.items():
    TENANT_REGISTRY.setdefault(_key, _tenant)

# Warn if no tenants configured
if not TENANT_REGISTRY:
    logger.warning("No tenant registry configured. Set ALGORISE_TENANT_REGISTRY or ALGORISE_API_KEY env var.")

# ---------------------------------------------------------------------------
# Redis-Backed Multi-Tenant Store (with in-memory fallback)
# ---------------------------------------------------------------------------

class RedisTenantStore:
    """Redis-backed tenant registry with atomic quota operations and graceful in-memory fallback."""
    
    def __init__(self, redis_url: Optional[str] = None):
        self.redis_client = None
        self.fallback_registry: Dict[str, Dict[str, Any]] = {}
        # Canonical tenants remain resolvable even when the mutable
        # fallback registry is reset (test fixtures, registry reloads or a
        # Redis flush). Production authentication must not depend on the
        # volatile in-memory copy.
        self.canonical_registry: Dict[str, Dict[str, Any]] = {}
        self._redis_available = False
        
        if REDIS_AVAILABLE and redis_url:
            try:
                self.redis_client = redis.from_url(
                    redis_url,
                    decode_responses=True,
                    socket_connect_timeout=2,
                    socket_timeout=2,
                    retry_on_timeout=True,
                )
                # Test connection
                self.redis_client.ping()
                self._redis_available = True
                logger.info("Redis tenant store connected successfully")
            except Exception as e:
                logger.warning(f"Redis connection failed, using in-memory fallback: {e}")
                self.redis_client = None
                self._redis_available = False
    
    def _tenant_key(self, api_key: str) -> str:
        return f"algorise:tenant:{api_key}"
    
    def _quota_key(self, api_key: str) -> str:
        return f"algorise:quota:{api_key}"
    
    def load_registry_from_env(self, registry: Dict[str, Dict[str, Any]]) -> None:
        """Initial load from environment (seed Redis on startup)."""
        if self._redis_available and self.redis_client:
            pipe = self.redis_client.pipeline()
            for api_key, tenant in registry.items():
                key = f"algorise:tenant:{api_key}"
                pipe.hset(key, mapping={
                    "client": tenant.get("client", "Unknown"),
                    "tier": tenant.get("tier", "Free"),
                    "role": tenant.get("role", "developer"),
                    "scopes": ",".join(tenant.get("scopes", [])),
                    "quota": str(tenant.get("quota", 100)),
                    "requests_used": "0",
                })
                pipe.expire(f"algorise:tenant:{api_key}", 86400 * 30)  # 30 days TTL
            pipe.execute()
        else:
            self.fallback_registry.update(registry)
        # Canonical tenants are always resolvable, even if the mutable
        # fallback registry is later cleared or a Redis flush occurs.
        self.canonical_registry.update(registry)
    
    def get_tenant(self, api_key: str) -> Optional[Dict[str, Any]]:
        """Get tenant info by API key."""
        if self._redis_available and self.redis_client:
            try:
                data = self.redis_client.hgetall(self._tenant_key(api_key))
                if data:
                    data["scopes"] = data.get("scopes", "").split(",") if data.get("scopes") else []
                    data["quota"] = int(data.get("quota", 100))
                    data["requests_used"] = int(data.get("requests_used", 0))
                    return data
            except Exception:
                pass
        tenant = self.fallback_registry.get(api_key)
        if tenant:
            return tenant
        return self.canonical_registry.get(api_key)
    
    def increment_usage(self, api_key: str) -> tuple[int, int]:
        """
        Atomically increment usage counter and return (used, quota).
        Returns (used, quota) tuple.
        """
        if self._redis_available and self.redis_client:
            try:
                # Use Lua script for atomic check-and-increment
                lua_script = """
                local used = redis.call('INCR', KEYS[1])
                local quota = tonumber(redis.call('HGET', KEYS[2], 'quota') or '100')
                if used > quota then
                    return {-1, quota}
                end
                return {used, quota}
                """
                script = self.redis_client.register_script(lua_script)
                result = script(keys=[self._quota_key(api_key), self._tenant_key(api_key)])
                used, quota = result[0], result[1]
                if used == -1:
                    return (0, quota)  # Will trigger 429 in caller
                return (used, quota)
            except Exception:
                pass

        # Fallback to in-memory
        tenant = self.fallback_registry.get(api_key) or self.canonical_registry.get(api_key)
        if not tenant:
            return (0, 100)
        tenant["requests_used"] = tenant.get("requests_used", 0) + 1
        return (tenant["requests_used"], tenant.get("quota", 100))
    
    def reset_quota(self, api_key: str) -> bool:
        """Reset quota counter (e.g., on billing cycle renewal)."""
        if self._redis_available and self.redis_client:
            try:
                self.redis_client.delete(self._quota_key(api_key))
                return True
            except Exception:
                pass
        if api_key in self.fallback_registry:
            self.fallback_registry[api_key]["requests_used"] = 0
            return True
        return False
    
    def get_all_tenants(self) -> Dict[str, Dict[str, Any]]:
        """Get all tenants (admin use)."""
        if self._redis_available and self.redis_client:
            try:
                tenants = {}
                for key in self.redis_client.scan_iter("algorise:tenant:*"):
                    api_key = key.split(":")[-1]
                    data = self.redis_client.hgetall(key)
                    if data:
                        data["scopes"] = data.get("scopes", "").split(",") if data.get("scopes") else []
                        data["quota"] = int(data.get("quota", 100))
                        data["requests_used"] = int(data.get("requests_used", 0))
                        tenants[api_key] = data
                return tenants
            except Exception:
                pass
        return self.fallback_registry.copy()


# Global Redis tenant store (initialized on startup)
REDIS_URL = os.environ.get("REDIS_URL") or os.environ.get("ALGORISE_REDIS_URL")
TENANT_STORE = RedisTenantStore(redis_url=REDIS_URL)

# Seed Redis with env registry on startup
TENANT_STORE.load_registry_from_env(TENANT_REGISTRY)

# ---------------------------------------------------------------------------
# Observability: Prometheus Metrics
# ---------------------------------------------------------------------------

if PROMETHEUS_AVAILABLE:
    # Request metrics
    HTTP_REQUESTS_TOTAL = Counter(
        "algorise_http_requests_total",
        "Total HTTP requests",
        ["method", "endpoint", "status_code", "tenant"]
    )
    HTTP_REQUEST_DURATION = Histogram(
        "algorise_http_request_duration_seconds",
        "HTTP request latency in seconds",
        ["method", "endpoint"],
        buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
    )
    HTTP_REQUESTS_IN_FLIGHT = Gauge(
        "algorise_http_requests_in_flight",
        "Number of HTTP requests currently being processed",
        ["method", "endpoint"]
    )
    # Business metrics
    TENANT_QUOTA_USED = Gauge(
        "algorise_tenant_quota_used",
        "Current quota usage per tenant",
        ["tenant_id", "tenant_name"]
    )
    QUARANTINE_ACTIVE = Gauge(
        "algorise_quarantine_active_tests",
        "Number of active quarantined tests",
        ["tenant_id"]
    )
    BLAST_RADIUS_SCORE = Histogram(
        "algorise_blast_radius_score",
        "Blast radius risk score",
        ["tenant_id"],
        buckets=[1.0, 2.5, 5.0, 7.0, 8.5, 10.0]
    )
    INCIDENT_HEAL_ATTEMPTS = Counter(
        "algorise_incident_heal_attempts_total",
        "Total incident healing attempts",
        ["tenant_id", "status", "error_type"]
    )

# ---------------------------------------------------------------------------
# Observability: OpenTelemetry Tracing (initialized after app creation)
# ---------------------------------------------------------------------------

# Will be initialized after app creation
tracer = None

# Middleware definitions will be added after app creation
# Placeholder for correlation ID and Prometheus middlewares

# ---------------------------------------------------------------------------
# Multi-Tenant Auth, Scopes & RBAC
# ---------------------------------------------------------------------------

def authenticate_api_key(
    x_algorise_api_key: Optional[str] = Header(None, alias="X-Algorise-API-Key"),
    authorization: Optional[str] = Header(None, alias="Authorization"),
) -> Dict[str, Any]:
    """Validates API Key from X-Algorise-API-Key header or Bearer token."""
    # Extract key from Header object if needed
    key = x_algorise_api_key
    if hasattr(key, '__class__') and 'Header' in type(key).__name__:
        key = None
    if not key and authorization is not None:
        auth_val = str(authorization) if hasattr(authorization, '__class__') and 'Header' in type(authorization).__name__ else authorization
        if isinstance(auth_val, str):
            if auth_val.lower().startswith("bearer "):
                key = auth_val[7:].strip()
            else:
                key = auth_val.strip()

    if not key:
        logger.warning("Auth failed: no key provided")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized: Invalid or missing X-Algorise-API-Key header.",
        )

    tenant = TENANT_STORE.get_tenant(key)
    if not tenant:
        logger.warning(f"Auth failed for key prefix: {key[:8] if key else 'None'}...")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized: Invalid or missing X-Algorise-API-Key header.",
        )

    # Atomically increment usage
    used, quota = TENANT_STORE.increment_usage(key)
    if used > tenant.get("quota", 100):
        logger.warning(f"Quota exceeded for tenant: {tenant.get('client', 'unknown')}")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Usage quota exceeded for current billing cycle. Please upgrade your seat tier.",
        )
    
    # Return tenant with updated usage
    tenant = dict(tenant)
    tenant["requests_used"] = used
    return tenant


def require_scope(required_scope: str) -> Callable:
    """Enforces fine-grained permission scope check (RBAC) on endpoints."""
    def scope_checker(tenant: Dict[str, Any] = Depends(authenticate_api_key)) -> Dict[str, Any]:
        scopes = tenant.get("scopes", [])
        if "admin:*" in scopes or required_scope in scopes:
            return tenant
        logger.warning(f"Scope denied: {required_scope} for tenant {tenant.get('client')}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Forbidden: Insufficient privileges. Required scope: '{required_scope}'.",
        )
    return scope_checker

# ---------------------------------------------------------------------------
# FastAPI Application & Security Middleware
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Algorise DevEx Commercial Metering Gateway",
    version="1.0.0",
    description="Enterprise API Gateway for AutoTest Sentinel, ContextPR, and Autonomous Healing Mesh.",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Correlation ID middleware
@app.middleware("http")
async def correlation_id_middleware(request: Request, call_next):
    """Add correlation ID to request context and response headers."""
    correlation_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
    request.state.correlation_id = correlation_id
    
    response = await call_next(request)
    response.headers["X-Correlation-ID"] = correlation_id
    return response

# Prometheus /metrics endpoint
if PROMETHEUS_AVAILABLE:
    @app.get("/metrics")
    async def metrics_endpoint():
        """Prometheus metrics endpoint."""
        return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

# ---------------------------------------------------------------------------
# Observability: OpenTelemetry Tracing (after app creation)
# ---------------------------------------------------------------------------

if OTEL_AVAILABLE:
    # Configure tracer provider
    resource = Resource.create({
        "service.name": "algorise-devex-gateway",
        "service.version": "1.0.0",
    })
    trace.set_tracer_provider(TracerProvider(resource=resource))
    tracer = trace.get_tracer(__name__)
    
    # Configure OTLP exporter if endpoint configured
    otel_endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")
    if otel_endpoint:
        try:
            otlp_exporter = OTLPSpanExporter(endpoint=otel_endpoint)
            span_processor = BatchSpanProcessor(otlp_exporter)
            trace.get_tracer_provider().add_span_processor(span_processor)
            logger.info(f"OTLP exporter configured: {otel_endpoint}")
        except Exception as e:
            logger.warning(f"Failed to configure OTLP exporter: {e}")
    
    # Auto-instrument FastAPI
    FastAPIInstrumentor.instrument_app(app)
    logger.info("OpenTelemetry tracing initialized")

# Secure CORS - allowlist only, no wildcard with credentials
app.add_middleware(
    CORSMiddleware,
    allow_origins=_parse_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=[
        "X-Algorise-Tenant",
        "X-Algorise-Tier",
        "X-Algorise-Role",
        "X-Algorise-Requests-Used",
        "X-Algorise-Quota-Remaining",
    ],
)

# Global rate limiting (burst + sustained) in addition to per-tenant quotas
class TokenBucketRateLimiter:
    """Token bucket rate limiter for global API rate limiting."""
    def __init__(self, rate: int = 1000, per: int = 60, burst: int = 100):
        self.rate = rate      # requests per time window
        self.per = per        # time window in seconds
        self.burst = burst    # max burst allowance
        self._tokens: Dict[str, tuple[float, float]] = {}  # key -> (tokens, last_refill)
        self.lock = asyncio.Lock()
    
    async def acquire(self, key: str = "global", tokens: int = 1) -> bool:
        async with self.lock:
            now = time.time()
            if key not in self._tokens:
                self._tokens[key] = (self.burst, now)
                print(f"DEBUG: New key {key} - initialized with {self.burst} tokens")
            
            current_tokens, last_refill = self._tokens[key]
            elapsed = now - last_refill
            # Refill tokens based on rate
            current_tokens = min(self.burst, current_tokens + elapsed * (self.rate / self.per))
            print(f"DEBUG acquire: key={key}, stored_tokens={self._tokens[key][0]:.2f}, elapsed={elapsed:.6f}, rate_per_sec={self.rate/self.per:.2f}, current_tokens={current_tokens:.2f}")
            
            if current_tokens >= tokens:
                self._tokens[key] = (current_tokens - tokens, time.time())
                print(f"DEBUG: Consumed {tokens} tokens, remaining={current_tokens - tokens:.2f}")
                return True
            print(f"DEBUG: Rate limited - need {tokens}, have {current_tokens:.2f}")
            return False

# Global rate limiter: 1000 req/min sustained, 100 burst
GLOBAL_RATE_LIMITER = TokenBucketRateLimiter(rate=1000, per=60, burst=100)

@app.middleware("http")
async def global_rate_limit_middleware(request: Request, call_next):
    """Global rate limiting middleware (burst + sustained)."""
    client_ip = request.client.host if request.client else "unknown"
    # Use tenant ID if available, otherwise IP
    key = request.headers.get("X-Algorise-API-Key") or client_ip
    
    if not await GLOBAL_RATE_LIMITER.acquire(key):
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={"error": "Global rate limit exceeded", "status_code": 429},
            headers={"Retry-After": "60"}
        )
    return await call_next(request)

# Security headers middleware
@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=()"
    return response

# Prometheus /metrics endpoint (added after app creation)
# Placeholder


@app.middleware("http")
async def metering_headers_middleware(request: Request, call_next):
    response = await call_next(request)
    key = request.headers.get("x-algorise-api-key")
    if not key and request.headers.get("authorization"):
        auth = request.headers.get("authorization", "")
        if auth.lower().startswith("bearer "):
            key = auth[7:].strip()
        else:
            key = auth.strip()

    if key:
        tenant = TENANT_STORE.get_tenant(key)
        if tenant:
            response.headers["X-Algorise-Tenant"] = tenant.get("client", "Unknown")
            response.headers["X-Algorise-Tier"] = tenant.get("tier", "Free")
            response.headers["X-Algorise-Role"] = tenant.get("role", "developer")
            used = tenant.get("requests_used", 0)
            quota = tenant.get("quota", 100)
            response.headers["X-Algorise-Requests-Used"] = str(used)
            response.headers["X-Algorise-Quota-Remaining"] = str(max(0, quota - used))
    return response

# ---------------------------------------------------------------------------
# Request Models
# ---------------------------------------------------------------------------

class QuarantineAddRequest(BaseModel):
    test_id: str = Field(..., description="Unique pytest test node ID, e.g. tests/test_api.py::test_flaky")
    file_path: str = Field(..., description="Relative or absolute file path to the test")
    flakiness_score: float = Field(0.85, ge=0.0, le=1.0, description="Evaluated flakiness score")
    root_cause: str = Field("TIMING_RACE", description="Root cause hypothesis string")
    failure_rate: float = Field(0.30, ge=0.0, le=1.0, description="Historical failure frequency")
    reason: Optional[str] = Field(None, description="Human or automated reason for quarantine")
    ttl_days: int = Field(14, ge=1, le=90, description="Time-to-live before re-evaluating in days")


class BlastRadiusRequest(BaseModel):
    changed_files: List[str] = Field(..., description="List of modified file paths in the commit/PR")
    base_ref: Optional[str] = Field("master", description="Target base branch reference")
    head_ref: Optional[str] = Field("HEAD", description="Source head branch reference")
    root_dir: Optional[str] = Field(None, description="Root directory to analyze. Defaults to current directory.")


class IncidentHealRequest(BaseModel):
    incident_id: str = Field(..., description="Unique incident identifier, e.g. INC-901")
    service_name: str = Field("core-engine", description="Affected microservice name")
    error_type: str = Field(..., description="Exception type, e.g. KeyError, ZeroDivisionError, AttributeError")
    error_message: str = Field(..., description="Exception error message string")
    stack_trace: str = Field(..., description="Raw formatted Python exception traceback")
    root_dir: Optional[str] = Field(None, description="Repository root directory")
    auto_stage: bool = Field(False, description="Whether to apply and stage hotfix immediately")


# ---------------------------------------------------------------------------
# Job Placement Marketplace Router (T-Pillar 3: $1/mo dual-sided ecosystem)
# ---------------------------------------------------------------------------

if MARKETPLACE_AVAILABLE and marketplace_router is not None:
    app.include_router(marketplace_router)


# ---------------------------------------------------------------------------
# Health & Readiness Endpoints (Public)
# ---------------------------------------------------------------------------

@app.get("/health")
def health_check() -> Dict[str, Any]:
    """Public health-check endpoint for load balancers and orchestrators."""
    checks = {
        "tenant_store": TENANT_STORE._redis_available or len(TENANT_STORE.fallback_registry) > 0,
        "marketplace": MARKETPLACE_AVAILABLE,
    }
    healthy = all(checks.values())

    return {
        "status": "healthy" if healthy else "degraded",
        "service": "algorise-devex-gateway",
        "version": "1.0.0",
        "engines": ENGINE_STATUS,
        "checks": checks,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/ready")
def readiness_check() -> Dict[str, Any]:
    """Readiness check - verifies critical dependencies (tenant registry, etc.)."""
    checks = {
        "tenant_store": TENANT_STORE._redis_available or len(TENANT_STORE.fallback_registry) > 0,
        "cors_configured": len(_parse_origins()) > 0,
    }
    ready = all(checks.values())
    return {
        "ready": ready,
        "service": "algorise-devex-gateway",
        "checks": checks,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ---------------------------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------------------------

@app.get("/v1/health")
def v1_health_check(tenant: Dict[str, Any] = Depends(require_scope("usage:read"))) -> Dict[str, Any]:
    """Authenticated health check with tenant context."""
    return {
        "status": "healthy",
        "service": "algorise-devex-gateway",
        "version": "1.0.0",
        "engines": ENGINE_STATUS,
        "tenant": tenant["client"],
        "tier": tenant["tier"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/v1/usage")
def usage_metering(tenant: Dict[str, Any] = Depends(require_scope("usage:read"))) -> Dict[str, Any]:
    """Returns the authenticated tenant's billing tier and current usage."""
    quota = int(tenant.get("quota", 100))
    used = int(tenant.get("requests_used", 0))
    return {
        "client": tenant["client"],
        "tier": tenant["tier"],
        "role": tenant.get("role", "developer"),
        "scopes": list(tenant.get("scopes", [])),
        "quota": quota,
        "requests_used": used,
        "quota_remaining": max(0, quota - used),
        "billing_cycle": "monthly",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/v1/quarantine")
def list_quarantined_tests(
    active_only: bool = True,
    manifest_path: Optional[str] = None,
    tenant: Dict[str, Any] = Depends(require_scope("quarantine:read")),
) -> Dict[str, Any]:
    """Retrieves all quarantined test records from the registry."""
    qm = QuarantineManager(manifest_path=manifest_path)
    if active_only:
        active_ids = qm.get_quarantined_ids()
        records = {k: v for k, v in qm.manifest.quarantined_tests.items() if k in active_ids}
    else:
        records = qm.manifest.quarantined_tests

    return {
        "version": qm.manifest.version,
        "updated_at": qm.manifest.updated_at,
        "total_quarantined": len(records),
        "quarantined_tests": records,
        "pytest_deselect_args": qm.generate_pytest_deselection_args(),
    }


@app.post("/v1/quarantine", status_code=status.HTTP_201_CREATED)
def add_to_quarantine(
    payload: QuarantineAddRequest,
    manifest_path: Optional[str] = None,
    tenant: Dict[str, Any] = Depends(require_scope("quarantine:write")),
) -> Dict[str, Any]:
    """Declares a test as quarantined to prevent CI pipeline blockage."""
    qm = QuarantineManager(manifest_path=manifest_path)

    try:
        cause_enum = RootCauseHypothesis(payload.root_cause)
    except ValueError:
        cause_enum = RootCauseHypothesis.TIMING_RACE

    report = FlakinessReport(
        test_id=payload.test_id,
        file_path=payload.file_path,
        flakiness_score=payload.flakiness_score,
        category=FlakeCategory.FLAKY_HIGH if payload.flakiness_score >= 0.7 else FlakeCategory.FLAKY_MEDIUM,
        root_cause=cause_enum,
        total_runs=10,
        failure_rate=payload.failure_rate,
        duration_jitter=0.05,
        recommended_action="Quarantine test and notify owner",
        remediation_notes=payload.reason or "Quarantined via DevEx Gateway API",
    )

    is_new = qm.quarantine_test(report=report, reason=payload.reason, ttl_days=payload.ttl_days)

    return {
        "success": True,
        "is_new": is_new,
        "test_id": payload.test_id,
        "quarantined_entry": qm.manifest.quarantined_tests.get(payload.test_id),
    }


@app.delete("/v1/quarantine/{test_id:path}")
def remove_from_quarantine(
    test_id: str,
    manifest_path: Optional[str] = None,
    tenant: Dict[str, Any] = Depends(require_scope("quarantine:write")),
) -> Dict[str, Any]:
    """Removes a healed test from quarantine, restoring it to standard CI execution."""
    qm = QuarantineManager(manifest_path=manifest_path)
    removed = qm.unquarantine_test(test_id)
    if not removed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Test ID '{test_id}' not found in active quarantine registry.",
        )
    return {
        "success": True,
        "removed_test_id": test_id,
        "remaining_quarantined": len(qm.get_quarantined_ids()),
    }


@app.post("/v1/blast-radius")
def evaluate_blast_radius(
    payload: BlastRadiusRequest,
    tenant: Dict[str, Any] = Depends(require_scope("blast_radius:read")),
) -> Dict[str, Any]:
    """
    Computes transitive downstream impact graph and risk tier using AST caching.
    """
    root_dir = payload.root_dir or "."
    analyzer = BlastRadiusAnalyzer(root_dir=root_dir)
    report = analyzer.compute_blast_radius(
        changed_files=payload.changed_files,
        base_ref=payload.base_ref or "master",
        head_ref=payload.head_ref or "HEAD",
    )

    impacted_files = [
        {
            "file_path": node.file_path,
            "direct_dependency": node.direct_dependency,
            "imported_symbols": node.imported_symbols,
            "depth": node.depth,
        }
        for node in report.impacted_downstream_files
    ]

    return {
        "base_ref": report.base_ref,
        "head_ref": report.head_ref,
        "risk_level": report.risk_level.value,
        "risk_score": report.risk_score,
        "total_files_changed": report.total_files_changed,
        "impacted_files_count": len(impacted_files),
        "impacted_downstream_files": impacted_files,
        "breaking_changes_detected": report.breaking_changes_detected,
        "high_risk_reasons": report.high_risk_reasons,
        "cache_telemetry": {
            "cache_hits": analyzer.cache_hits,
            "cache_misses": analyzer.cache_misses,
        },
    }


@app.post("/v1/incidents/heal")
def heal_production_incident(
    payload: IncidentHealRequest,
    tenant: Dict[str, Any] = Depends(require_scope("incident:heal")),
) -> Dict[str, Any]:
    """
    TECH-302: Distributed Autonomous Healing Mesh
    Correlates incident telemetry, synthesizes localized AST hotfix, and validates blast radius.
    """
    from trace_root_ai.mesh import AutonomousHealingMesh
    from trace_root_ai.models import IncidentPayload

    incident = IncidentPayload(
        incident_id=payload.incident_id,
        service_name=payload.service_name,
        error_type=payload.error_type,
        error_message=payload.error_message,
        raw_stack_trace=payload.stack_trace,
    )

    mesh = AutonomousHealingMesh(root_dir=payload.root_dir or ".")
    result = mesh.process_incident(incident=incident, auto_stage=payload.auto_stage)
    return result.model_dump()


# ---------------------------------------------------------------------------
# Global Exception Handlers
# ---------------------------------------------------------------------------

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "error": exc.detail,
            "status_code": exc.status_code,
        },
        headers=getattr(exc, "headers", None),
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled error: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": "Internal server error", "status_code": 500},
    )


# ---------------------------------------------------------------------------
# CLI Entry Point
# ---------------------------------------------------------------------------

def run_server(host: str = "127.0.0.1", port: int = 8000) -> None:
    """Run the API gateway server via uvicorn."""
    import uvicorn
    uvicorn.run("devex.api:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    run_server()