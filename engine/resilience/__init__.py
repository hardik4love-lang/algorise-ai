"""
Resilience & Stability Framework Package (Phase 1 Baseline)
Provides production stability patterns:
- CircuitBreaker (3-state with sliding-window)
- VegasAdaptiveConcurrencyLimiter (Little's Law AIMD)
- CellularBulkhead (Physical and thread-pool isolation)
"""

from engine.resilience.circuit_breaker import CircuitBreaker, CircuitState, CircuitBreakerOpenException
from engine.resilience.adaptive_concurrency import VegasAdaptiveConcurrencyLimiter, ConcurrencyLimitExceededException
from engine.resilience.bulkhead import CellularBulkhead, BulkheadFullException

__all__ = [
    "CircuitBreaker",
    "CircuitState",
    "CircuitBreakerOpenException",
    "VegasAdaptiveConcurrencyLimiter",
    "ConcurrencyLimitExceededException",
    "CellularBulkhead",
    "BulkheadFullException",
]
