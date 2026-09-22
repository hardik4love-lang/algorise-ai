from functools import wraps
from typing import Callable, Optional

from prometheus_client import Counter, Gauge, Histogram, Info, generate_latest
from prometheus_client.core import CollectorRegistry

from engine.config import get_settings

# Custom registry for Algorise metrics
REGISTRY = CollectorRegistry()

# Application info
APP_INFO = Info(
    "algorise_app_info",
    "Algorise AI Application Information",
    registry=REGISTRY,
)

# HTTP metrics
HTTP_REQUESTS_TOTAL = Counter(
    "algorise_http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code"],
    registry=REGISTRY,
)

HTTP_REQUEST_DURATION = Histogram(
    "algorise_http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
    registry=REGISTRY,
)

# Bot execution metrics
BOT_EXECUTIONS_TOTAL = Counter(
    "algorise_bot_executions_total",
    "Total bot executions",
    ["bot_id", "bot_name", "sector", "success"],
    registry=REGISTRY,
)

BOT_EXECUTION_DURATION = Histogram(
    "algorise_bot_execution_duration_seconds",
    "Bot execution duration in seconds",
    ["bot_id", "bot_name"],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
    registry=REGISTRY,
)

BOT_CONFIDENCE = Histogram(
    "algorise_bot_confidence",
    "Bot confidence scores",
    ["bot_id", "bot_name"],
    buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 0.99, 1.0],
    registry=REGISTRY,
)

# Safety gate metrics
SAFETY_GATE_DECISIONS = Counter(
    "algorise_safety_gate_decisions_total",
    "Safety gate decisions",
    ["decision", "bot_id"],
    registry=REGISTRY,
)

# Autoflow metrics
AUTOFLOW_EXECUTIONS_TOTAL = Counter(
    "algorise_autoflow_executions_total",
    "Total autoflow executions",
    ["pipeline_id", "status"],
    registry=REGISTRY,
)

AUTOFLOW_EXECUTION_DURATION = Histogram(
    "algorise_autoflow_execution_duration_seconds",
    "Autoflow execution duration in seconds",
    ["pipeline_id"],
    buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0],
    registry=REGISTRY,
)

# Freelance metrics
FREELANCE_JOBS_SCRAPED = Counter(
    "algorise_freelance_jobs_scraped_total",
    "Total freelance jobs scraped",
    ["source", "category"],
    registry=REGISTRY,
)

FREELANCE_CLOSE_ATTEMPTS = Counter(
    "algorise_freelance_close_attempts_total",
    "Total freelance close attempts",
    ["closer_id", "status"],
    registry=REGISTRY,
)

# Real estate metrics
REALESTATE_LEADS_TOTAL = Counter(
    "algorise_realestate_leads_total",
    "Total real estate leads",
    ["client_id", "buyer_type", "tier"],
    registry=REGISTRY,
)

REALESTATE_OUTREACH_SENT = Counter(
    "algorise_realestate_outreach_sent_total",
    "Total outreach messages sent",
    ["channel", "status"],
    registry=REGISTRY,
)

# Client metrics
CLIENT_QUOTA_USAGE = Gauge(
    "algorise_client_quota_usage",
    "Client quota usage",
    ["client_id", "client_name", "tier"],
    registry=REGISTRY,
)

ACTIVE_CLIENTS = Gauge(
    "algorise_active_clients",
    "Number of active clients",
    ["tier"],
    registry=REGISTRY,
)

# External API metrics
EXTERNAL_API_CALLS = Counter(
    "algorise_external_api_calls_total",
    "Total external API calls",
    ["service", "endpoint", "status"],
    registry=REGISTRY,
)

EXTERNAL_API_DURATION = Histogram(
    "algorise_external_api_duration_seconds",
    "External API call duration in seconds",
    ["service", "endpoint"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0],
    registry=REGISTRY,
)

# Redis metrics
REDIS_OPERATIONS = Counter(
    "algorise_redis_operations_total",
    "Total Redis operations",
    ["operation", "status"],
    registry=REGISTRY,
)

REDIS_OPERATION_DURATION = Histogram(
    "algorise_redis_operation_duration_seconds",
    "Redis operation duration in seconds",
    ["operation"],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0],
    registry=REGISTRY,
)

# Database metrics
DB_QUERY_DURATION = Histogram(
    "algorise_db_query_duration_seconds",
    "Database query duration in seconds",
    ["operation", "table"],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
    registry=REGISTRY,
)

DB_CONNECTIONS_ACTIVE = Gauge(
    "algorise_db_connections_active",
    "Active database connections",
    registry=REGISTRY,
)

# Error metrics
ERRORS_TOTAL = Counter(
    "algorise_errors_total",
    "Total errors",
    ["error_type", "component"],
    registry=REGISTRY,
)


def init_metrics(app_name: str = "algorise-ai", version: str = "1.0.0") -> None:
    """Initialize application info metrics."""
    settings = get_settings()
    APP_INFO.info({
        "name": app_name,
        "version": version,
        "environment": settings.environment,
    })


def get_metrics() -> bytes:
    """Get Prometheus metrics output."""
    return generate_latest(REGISTRY)


def track_bot_execution(bot_id: str, bot_name: str, sector: str):
    """Decorator to track bot execution metrics."""
    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            import time
            start = time.perf_counter()
            success = False
            confidence = 0.0
            try:
                result = await func(*args, **kwargs)
                success = getattr(result, 'success', True)
                confidence = getattr(result, 'data', {}).get('confidence_score', 0.0)
                return result
            finally:
                duration = time.perf_counter() - start
                BOT_EXECUTIONS_TOTAL.labels(
                    bot_id=bot_id, bot_name=bot_name, sector=sector, success=str(success).lower()
                ).inc()
                BOT_EXECUTION_DURATION.labels(bot_id=bot_id, bot_name=bot_name).observe(duration)
                if confidence > 0:
                    BOT_CONFIDENCE.labels(bot_id=bot_id, bot_name=bot_name).observe(confidence)

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            import time
            start = time.perf_counter()
            success = False
            confidence = 0.0
            try:
                result = func(*args, **kwargs)
                success = getattr(result, 'success', True)
                confidence = getattr(result, 'data', {}).get('confidence_score', 0.0)
                return result
            finally:
                duration = time.perf_counter() - start
                BOT_EXECUTIONS_TOTAL.labels(
                    bot_id=bot_id, bot_name=bot_name, sector=sector, success=str(success).lower()
                ).inc()
                BOT_EXECUTION_DURATION.labels(bot_id=bot_id, bot_name=bot_name).observe(duration)
                if confidence > 0:
                    BOT_CONFIDENCE.labels(bot_id=bot_id, bot_name=bot_name).observe(confidence)

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    return decorator


def track_external_api_call(service: str, endpoint: str):
    """Decorator to track external API call metrics."""
    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            import time
            start = time.perf_counter()
            status = "error"
            try:
                result = await func(*args, **kwargs)
                status = "success"
                return result
            finally:
                duration = time.perf_counter() - start
                EXTERNAL_API_CALLS.labels(service=service, endpoint=endpoint, status=status).inc()
                EXTERNAL_API_DURATION.labels(service=service, endpoint=endpoint).observe(duration)

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            import time
            start = time.perf_counter()
            status = "error"
            try:
                result = func(*args, **kwargs)
                status = "success"
                return result
            finally:
                duration = time.perf_counter() - start
                EXTERNAL_API_CALLS.labels(service=service, endpoint=endpoint, status=status).inc()
                EXTERNAL_API_DURATION.labels(service=service, endpoint=endpoint).observe(duration)

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    return decorator


def record_error(error_type: str, component: str) -> None:
    """Record an error metric."""
    ERRORS_TOTAL.labels(error_type=error_type, component=component).inc()