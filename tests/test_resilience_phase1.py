"""
Unit tests for Phase 1 Architectural Resilience Framework
Verifies:
- CircuitBreaker 3-state state machine and fast-fail
- VegasAdaptiveConcurrencyLimiter dynamic throttling
- CellularBulkhead thread-pool and queue isolation
"""

import time
import pytest
from engine.resilience import (
    CircuitBreaker,
    CircuitState,
    CircuitBreakerOpenException,
    VegasAdaptiveConcurrencyLimiter,
    ConcurrencyLimitExceededException,
    CellularBulkhead,
    BulkheadFullException
)

def test_circuit_breaker_closed_nominal():
    cb = CircuitBreaker("test-service", failure_threshold_pct=50.0, sliding_window_size=10, min_requests_to_evaluate=5)
    def ok_fn():
        return "success"
    
    for _ in range(10):
        res = cb.call(ok_fn)
        assert res == "success"
    assert cb.state == CircuitState.CLOSED

def test_circuit_breaker_trips_to_open_on_failures():
    cb = CircuitBreaker("test-service-fail", failure_threshold_pct=50.0, recovery_time_sec=0.2, sliding_window_size=10, min_requests_to_evaluate=4)
    def fail_fn():
        raise ValueError("Service error")
    
    for _ in range(4):
        with pytest.raises(ValueError):
            cb.call(fail_fn)
            
    assert cb.state == CircuitState.OPEN
    # Immediate subsequent calls must fast-fail with CircuitBreakerOpenException
    with pytest.raises(CircuitBreakerOpenException):
        cb.call(lambda: "should not run")

def test_circuit_breaker_half_open_recovery():
    cb = CircuitBreaker("test-service-rec", failure_threshold_pct=50.0, recovery_time_sec=0.1, sliding_window_size=10, half_open_probes=2, min_requests_to_evaluate=2)
    def fail_fn():
        raise ValueError("Error")
    
    for _ in range(2):
        with pytest.raises(ValueError):
            cb.call(fail_fn)
    assert cb.state == CircuitState.OPEN
    
    time.sleep(0.15) # Wait for recovery cooling duration
    assert cb.state == CircuitState.HALF_OPEN
    
    # Successful probes in HALF_OPEN reset to CLOSED
    cb.call(lambda: "probe 1")
    cb.call(lambda: "probe 2")
    assert cb.state == CircuitState.CLOSED

def test_adaptive_concurrency_limiter_bounds():
    limiter = VegasAdaptiveConcurrencyLimiter("aria-inference", initial_limit=3, min_limit=1, max_limit=10)
    tokens = []
    
    # Acquire up to limit
    for _ in range(3):
        tokens.append(limiter.acquire())
    assert limiter.inflight_count == 3
    
    # Next acquire must raise ConcurrencyLimitExceededException
    with pytest.raises(ConcurrencyLimitExceededException):
        limiter.acquire()
        
    # Release tokens
    for t in tokens:
        limiter.release(t)
    assert limiter.inflight_count == 0

def test_cellular_bulkhead_isolation():
    bulkhead = CellularBulkhead("bounty-solvers", max_workers=2, max_queue_size=2)
    
    def slow_task():
        time.sleep(0.1)
        return "done"
        
    futures = []
    # Submit up to max_workers (2) + max_queue (2) = 4
    for _ in range(4):
        futures.append(bulkhead.submit(slow_task))
        
    # 5th task must exceed queue and raise BulkheadFullException
    with pytest.raises(BulkheadFullException):
        bulkhead.submit(slow_task)
        
    for f in futures:
        assert f.result() == "done"
    bulkhead.shutdown()
