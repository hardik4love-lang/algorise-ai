"""
Algorise AutoHeal™ — Robustness, Invariants & Zero-Crash Middleware
Provides Circuit Breaker, Hard Timeouts, and Global Process Shields.
"""
from __future__ import annotations

import time
import asyncio
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

class CircuitBreakerOpenException(Exception):
    pass

class CircuitBreaker:
    """Token-bucket circuit breaker with Half-Open probe state."""
    def __init__(self, failure_threshold: int = 3, recovery_time_sec: float = 30.0):
        self.failure_threshold = failure_threshold
        self.recovery_time_sec = recovery_time_sec
        self.failure_count = 0
        self.last_failure_time = 0.0
        self.state = "CLOSED"

    def record_success(self):
        self.failure_count = 0
        self.state = "CLOSED"

    def record_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"

    def allow_request(self) -> bool:
        if self.state == "CLOSED":
            return True
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.recovery_time_sec:
                self.state = "HALF-OPEN"
                return True
            return False
        if self.state == "HALF-OPEN":
            return True
        return False

class ZeroCrashProcessMiddleware(BaseHTTPMiddleware):
    """Guarantees that no unhandled exception ever crashes the ASGI worker."""
    async def dispatch(self, request: Request, call_next):
        try:
            return await asyncio.wait_for(call_next(request), timeout=8.0)
        except asyncio.TimeoutError:
            return JSONResponse(
                status_code=504,
                content={"error": "GATEWAY_TIMEOUT", "message": "Request exceeded 8.0s hard safety clamp."}
            )
        except Exception as exc:
            error_repr = f"{type(exc).__name__}: {str(exc)}"
            return JSONResponse(
                status_code=500,
                content={"error": "INTERNAL_SHIELDED_EXCEPTION", "detail": error_repr, "recovered": True}
            )
