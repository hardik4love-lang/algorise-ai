"""
Adaptive Concurrency Limiter (Vegas AIMD Algorithm derived from Little's Law)
Prevents queue saturation and cascading latency degradation under external
API backpressure or internal compute contention.
"""

import time
import math
import threading
from typing import Optional

class ConcurrencyLimitExceededException(Exception):
    """Raised when inflight requests exceed the adaptive concurrency threshold."""
    pass

class VegasAdaptiveConcurrencyLimiter:
    def __init__(
        self,
        name: str,
        initial_limit: int = 10,
        min_limit: int = 2,
        max_limit: int = 100,
        alpha: float = 3.0,
        beta: float = 6.0,
        smoothing_factor: float = 0.2
    ):
        self.name = name
        self.limit = float(initial_limit)
        self.min_limit = min_limit
        self.max_limit = max_limit
        self.alpha = alpha
        self.beta = beta
        self.smoothing_factor = smoothing_factor

        self._inflight = 0
        self._min_rtt = float("inf")
        self._lock = threading.Lock()

    def acquire(self) -> float:
        with self._lock:
            if self._inflight >= math.floor(self.limit):
                raise ConcurrencyLimitExceededException(
                    f"Concurrency limit ({int(self.limit)}) exceeded for '{self.name}'. Inflight: {self._inflight}."
                )
            self._inflight += 1
            return time.time()

    def release(self, start_time: float):
        rtt = time.time() - start_time
        with self._lock:
            self._inflight = max(0, self._inflight - 1)
            if rtt <= 0:
                return

            if rtt < self._min_rtt:
                self._min_rtt = rtt

            # Queue estimate based on Vegas algorithm
            # queue = current_limit * (1 - min_rtt / actual_rtt)
            queue_size = self.limit * (1.0 - (self._min_rtt / rtt))

            if queue_size > self.beta:
                # Congestion: Multiplicative Decrease
                self.limit = max(self.min_limit, self.limit - 1.0)
            elif queue_size < self.alpha and self._inflight >= (self.limit * 0.7):
                # Underutilized & Headroom: Additive Increase
                self.limit = min(self.max_limit, self.limit + 1.0)

    @property
    def current_limit(self) -> int:
        with self._lock:
            return math.floor(self.limit)

    @property
    def inflight_count(self) -> int:
        with self._lock:
            return self._inflight
