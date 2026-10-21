"""
Algorise Circuit Breaker & Retry Engine
Phase 2 Flywheel: Resilience primitives for the Autoflow pipeline.

Implements:
  - CircuitBreaker  : per-bot state machine (CLOSED → OPEN → HALF_OPEN → CLOSED)
  - RetryPolicy     : exponential backoff with full jitter for transient failures
  - BotStepGuard    : combined decorator applied to every autoflow step execution

Usage (in autoflow.py):
    guard = BotStepGuard(bot_name="nexus", max_retries=3, failure_threshold=5)
    result = guard.execute(bot.execute, task)
"""

from __future__ import annotations

import functools
import logging
import random
import time
from dataclasses import dataclass, field
from enum import Enum
from threading import Lock
from typing import Any, Callable, Dict, List, Optional, Tuple, Type

from engine.logging import get_logger

log = get_logger(__name__)


# ---------------------------------------------------------------------------
# Circuit Breaker
# ---------------------------------------------------------------------------

class CircuitState(Enum):
    CLOSED    = "closed"     # Normal — calls pass through
    OPEN      = "open"       # Failing — fast-fail immediately
    HALF_OPEN = "half_open"  # Probing recovery


@dataclass
class CircuitBreakerConfig:
    failure_threshold: int   = 5     # Consecutive failures before OPEN
    recovery_timeout:  float = 60.0  # Seconds in OPEN before attempting HALF_OPEN
    success_threshold: int   = 2     # Successes in HALF_OPEN to return to CLOSED
    call_timeout:      float = 30.0  # Per-call deadline in seconds (sync context)


class CircuitBreakerOpenError(RuntimeError):
    """Raised when a call is rejected by an open circuit."""


class CircuitBreaker:
    """
    Thread-safe circuit breaker for synchronous bot.execute() calls.

    State transitions:
        CLOSED  → (N consecutive failures) → OPEN
        OPEN    → (recovery_timeout elapsed) → HALF_OPEN
        HALF_OPEN → (success_threshold successes) → CLOSED
        HALF_OPEN → (any failure) → OPEN
    """

    def __init__(self, name: str, config: Optional[CircuitBreakerConfig] = None):
        self.name   = name
        self.config = config or CircuitBreakerConfig()
        self._state = CircuitState.CLOSED
        self._failure_count   = 0
        self._success_count   = 0
        self._last_failure_ts: Optional[float] = None
        self._lock = Lock()

    @property
    def state(self) -> CircuitState:
        return self._state

    @property
    def is_open(self) -> bool:
        return self._state == CircuitState.OPEN

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute *func* through the circuit breaker.
        Raises CircuitBreakerOpenError if the circuit is OPEN and not yet
        eligible for HALF_OPEN probing.
        """
        with self._lock:
            self._maybe_attempt_half_open()
            if self._state == CircuitState.OPEN:
                log.warning(
                    "circuit_breaker_open_fast_fail",
                    circuit=self.name,
                    state=self._state.value,
                )
                raise CircuitBreakerOpenError(
                    f"Circuit '{self.name}' is OPEN — call rejected (fast-fail)."
                )

        # Execute outside the lock so other threads are not blocked
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except CircuitBreakerOpenError:
            raise
        except Exception as exc:
            self._on_failure(exc)
            raise

    # ------------------------------------------------------------------
    # Internal state management
    # ------------------------------------------------------------------

    def _maybe_attempt_half_open(self) -> None:
        """Transition OPEN → HALF_OPEN if recovery timeout has elapsed."""
        if (
            self._state == CircuitState.OPEN
            and self._last_failure_ts is not None
            and (time.monotonic() - self._last_failure_ts) >= self.config.recovery_timeout
        ):
            self._state = CircuitState.HALF_OPEN
            self._success_count = 0
            log.info("circuit_breaker_transition", circuit=self.name,
                     transition="OPEN-to-HALF_OPEN")

    def _on_success(self) -> None:
        with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                self._success_count += 1
                if self._success_count >= self.config.success_threshold:
                    self._state = CircuitState.CLOSED
                    self._failure_count = 0
                    self._success_count = 0
                    log.info("circuit_breaker_transition", circuit=self.name,
                             transition="HALF_OPEN-to-CLOSED")
            elif self._state == CircuitState.CLOSED:
                # Reset failure streak on any success
                self._failure_count = 0

    def _on_failure(self, exc: Exception) -> None:
        with self._lock:
            self._failure_count += 1
            self._last_failure_ts = time.monotonic()
            log.warning(
                "circuit_breaker_failure_recorded",
                circuit=self.name,
                failure_count=self._failure_count,
                threshold=self.config.failure_threshold,
                exception_type=type(exc).__name__,
            )
            if self._failure_count >= self.config.failure_threshold:
                prev = self._state
                self._state = CircuitState.OPEN
                self._success_count = 0
                if prev != CircuitState.OPEN:
                    log.error(
                        "circuit_breaker_transition",
                        circuit=self.name,
                        transition=f"{prev.value.upper()}-to-OPEN",
                        triggered_by=str(exc),
                    )


# ---------------------------------------------------------------------------
# Retry Policy
# ---------------------------------------------------------------------------

# Exceptions that warrant a retry (transient / recoverable)
DEFAULT_RETRYABLE: Tuple[Type[Exception], ...] = (
    TimeoutError,
    ConnectionError,
    ConnectionResetError,
    OSError,
)


@dataclass
class RetryConfig:
    max_attempts:        int   = 3
    base_delay_seconds:  float = 1.0
    max_delay_seconds:   float = 30.0
    jitter:              bool  = True   # Full jitter: delay = random(0, computed_delay)
    retryable_exceptions: Tuple[Type[Exception], ...] = field(
        default_factory=lambda: DEFAULT_RETRYABLE
    )


class RetryExhaustedError(RuntimeError):
    """Raised when all retry attempts are exhausted."""
    def __init__(self, attempts: int, last_exc: Exception):
        super().__init__(
            f"All {attempts} retry attempts exhausted. Last error: {last_exc}"
        )
        self.last_exception = last_exc


class RetryPolicy:
    """
    Synchronous exponential-backoff retry with full jitter.

    Backoff formula (before jitter):
        delay = min(base * 2^(attempt-1), max_delay)
    With full jitter:
        delay = random(0, computed_delay)
    """

    def __init__(self, config: Optional[RetryConfig] = None):
        self.config = config or RetryConfig()

    def execute(self, func: Callable, *args, **kwargs) -> Any:
        last_exc: Optional[Exception] = None

        for attempt in range(1, self.config.max_attempts + 1):
            try:
                return func(*args, **kwargs)
            except self.config.retryable_exceptions as exc:
                last_exc = exc
                if attempt == self.config.max_attempts:
                    log.error(
                        "retry_exhausted",
                        func=getattr(func, "__name__", str(func)),
                        attempt=attempt,
                        exception=str(exc),
                    )
                    raise RetryExhaustedError(attempt, exc) from exc

                raw_delay = min(
                    self.config.base_delay_seconds * (2 ** (attempt - 1)),
                    self.config.max_delay_seconds,
                )
                delay = random.uniform(0, raw_delay) if self.config.jitter else raw_delay
                log.warning(
                    "retry_attempt",
                    func=getattr(func, "__name__", str(func)),
                    attempt=attempt,
                    next_retry_in_seconds=round(delay, 2),
                    exception_type=type(exc).__name__,
                )
                time.sleep(delay)
            except Exception as exc:
                # Non-retryable — raise immediately
                raise

        # Should not reach here
        raise RetryExhaustedError(self.config.max_attempts, last_exc)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# BotStepGuard — unified wrapper applied per autoflow step
# ---------------------------------------------------------------------------

class BotStepGuard:
    """
    Composes CircuitBreaker + RetryPolicy for a single bot type.

    The retry layer executes *inside* the circuit breaker — i.e., retries
    consume circuit-breaker failure budget. This is intentional: a bot that
    needs 3 retries every call is genuinely unhealthy.

    Usage:
        guard = BotStepGuard(bot_name="nexus")
        result = guard.execute(bot.execute, task)
    """

    # Registry: one CircuitBreaker per bot_name (shared across all pipeline executions)
    _circuit_registry: Dict[str, CircuitBreaker] = {}
    _registry_lock = Lock()

    def __init__(
        self,
        bot_name: str,
        cb_config:     Optional[CircuitBreakerConfig] = None,
        retry_config:  Optional[RetryConfig]          = None,
    ):
        self.bot_name    = bot_name
        self.retry       = RetryPolicy(retry_config)

        with self._registry_lock:
            if bot_name not in self._circuit_registry:
                self._circuit_registry[bot_name] = CircuitBreaker(
                    name=bot_name, config=cb_config
                )
        self.circuit = self._circuit_registry[bot_name]

    def execute(self, func: Callable, *args, **kwargs) -> Any:
        """Execute func through the circuit breaker + retry policy."""
        def _attempt():
            return self.circuit.call(func, *args, **kwargs)

        return self.retry.execute(_attempt)

    @classmethod
    def get_all_circuit_states(cls) -> Dict[str, str]:
        """Returns current state of every registered circuit breaker."""
        with cls._registry_lock:
            return {name: cb.state.value for name, cb in cls._circuit_registry.items()}

    @classmethod
    def reset_circuit(cls, bot_name: str) -> bool:
        """Manually reset a named circuit to CLOSED (human override after incident)."""
        with cls._registry_lock:
            if bot_name in cls._circuit_registry:
                cb = cls._circuit_registry[bot_name]
                cb._state = CircuitState.CLOSED
                cb._failure_count = 0
                cb._success_count = 0
                log.info("circuit_breaker_manual_reset", circuit=bot_name)
                return True
            return False
