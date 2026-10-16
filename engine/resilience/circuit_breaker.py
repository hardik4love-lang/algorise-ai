"""
Distributed Circuit Breaker Implementation (Phase 1 Resilience)
Implements a 3-state state machine (Closed, Open, HalfOpen) with a sliding
window error counter and configurable cooling duration.
"""

import time
import threading
from enum import Enum
from typing import Callable, Any, Optional
from collections import deque

class CircuitState(Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"

class CircuitBreakerOpenException(Exception):
    """Raised when an execution attempt is blocked by an OPEN circuit breaker."""
    pass

class CircuitBreaker:
    def __init__(
        self,
        name: str,
        failure_threshold_pct: float = 50.0,
        recovery_time_sec: float = 30.0,
        sliding_window_size: int = 50,
        half_open_probes: int = 10,
        min_requests_to_evaluate: int = 10
    ):
        self.name = name
        self.failure_threshold_pct = failure_threshold_pct
        self.recovery_time_sec = recovery_time_sec
        self.sliding_window_size = sliding_window_size
        self.half_open_probes = half_open_probes
        self.min_requests_to_evaluate = min_requests_to_evaluate

        self._state = CircuitState.CLOSED
        self._lock = threading.Lock()
        self._window: deque = deque(maxlen=sliding_window_size)
        self._last_state_change = time.time()
        self._half_open_successes = 0

    @property
    def state(self) -> CircuitState:
        with self._lock:
            if self._state == CircuitState.OPEN:
                if (time.time() - self._last_state_change) >= self.recovery_time_sec:
                    self._state = CircuitState.HALF_OPEN
                    self._last_state_change = time.time()
                    self._half_open_successes = 0
            return self._state

    def call(self, func: Callable, *args, **kwargs) -> Any:
        current_state = self.state

        if current_state == CircuitState.OPEN:
            raise CircuitBreakerOpenException(
                f"Circuit breaker '{self.name}' is OPEN. Fast-failing downstream request."
            )

        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            self._record_success()
            return result
        except Exception as e:
            self._record_failure()
            raise e

    def _record_success(self):
        with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                self._half_open_successes += 1
                if self._half_open_successes >= self.half_open_probes:
                    self._state = CircuitState.CLOSED
                    self._last_state_change = time.time()
                    self._window.clear()
            elif self._state == CircuitState.CLOSED:
                self._window.append(True)

    def _record_failure(self):
        with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                self._state = CircuitState.OPEN
                self._last_state_change = time.time()
            elif self._state == CircuitState.CLOSED:
                self._window.append(False)
                if len(self._window) >= self.min_requests_to_evaluate:
                    failures = self._window.count(False)
                    failure_rate = (failures / len(self._window)) * 100.0
                    if failure_rate >= self.failure_threshold_pct:
                        self._state = CircuitState.OPEN
                        self._last_state_change = time.time()
