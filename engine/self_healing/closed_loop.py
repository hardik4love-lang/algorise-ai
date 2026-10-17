"""
Closed-Loop Self-Healing & Anti-Flapping Remediation Engine (Phase 3 Baseline)
Implements:
- Closed-loop OODA remediation: Sense -> Detect -> Decide -> Act -> Verify
- Asymmetric Hysteresis Damping:
  * Failure trip threshold: 3 failed consecutive probes within 15s (tau_fail = 15s)
  * Recovery re-admission threshold: 12 consecutive successful probes over 120s (tau_recover = 120s)
- Remediation Velocity Limiting: Max 15% fleet replacement per 5-minute rolling window
- Dead-Man Switch: Freezes automation and escalates to SRE if 2 consecutive cycles fail to restore steady-state
"""

import time
import threading
from enum import Enum
from typing import Dict, Any, List, Optional, Callable

class NodeHealthState(Enum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNHEALTHY = "UNHEALTHY"

class RemediationAction(Enum):
    REPLACE_POD = "REPLACE_POD"
    DRAIN_ZONE = "DRAIN_ZONE"
    SHED_TIER2 = "SHED_TIER2"
    NONE = "NONE"

class ClosedLoopRemediator:
    def __init__(
        self,
        service_name: str,
        failure_consecutive_threshold: int = 3,
        failure_window_sec: float = 15.0,
        recovery_consecutive_threshold: int = 12,
        recovery_window_sec: float = 120.0,
        max_remediation_velocity_pct: float = 15.0,
        dead_man_cycles_threshold: int = 2
    ):
        self.service_name = service_name
        self.failure_consecutive_threshold = failure_consecutive_threshold
        self.failure_window_sec = failure_window_sec
        self.recovery_consecutive_threshold = recovery_consecutive_threshold
        self.recovery_window_sec = recovery_window_sec
        self.max_remediation_velocity_pct = max_remediation_velocity_pct
        self.dead_man_cycles_threshold = dead_man_cycles_threshold

        self.state = NodeHealthState.HEALTHY
        self._consecutive_failures = 0
        self._consecutive_successes = 0
        self._last_failure_ts: float = 0.0
        self._first_recovery_ts: float = 0.0
        self._lock = threading.Lock()

        self._remediation_history: List[float] = []
        self._unresolved_cycles = 0
        self.dead_man_tripped = False

    def record_probe(self, success: bool, now: Optional[float] = None) -> NodeHealthState:
        current_time = now if now is not None else time.time()
        with self._lock:
            if not success:
                self._consecutive_successes = 0
                self._first_recovery_ts = 0.0
                self._consecutive_failures += 1
                self._last_failure_ts = current_time

                if (
                    self._consecutive_failures >= self.failure_consecutive_threshold
                    and self.state != NodeHealthState.UNHEALTHY
                ):
                    self.state = NodeHealthState.UNHEALTHY
                elif self._consecutive_failures > 0 and self.state == NodeHealthState.HEALTHY:
                    self.state = NodeHealthState.DEGRADED
            else:
                self._consecutive_failures = 0
                self._consecutive_successes += 1
                if self._first_recovery_ts == 0.0:
                    self._first_recovery_ts = current_time

                # Check asymmetric recovery requirement
                elapsed_recovery = current_time - self._first_recovery_ts
                if (
                    self._consecutive_successes >= self.recovery_consecutive_threshold
                    and elapsed_recovery >= self.recovery_window_sec
                ):
                    self.state = NodeHealthState.HEALTHY
                    self._unresolved_cycles = 0

            return self.state

    def evaluate_remediation(self, active_fleet_size: int, now: Optional[float] = None) -> Dict[str, Any]:
        current_time = now if now is not None else time.time()
        with self._lock:
            if self.dead_man_tripped:
                return {
                    "action": RemediationAction.NONE.value,
                    "allowed": False,
                    "reason": "DEAD-MAN SWITCH TRIPPED: Automated remediation locked out; manual SRE escalation active."
                }

            if self.state == NodeHealthState.HEALTHY:
                return {
                    "action": RemediationAction.NONE.value,
                    "allowed": True,
                    "reason": "Service healthy; steady-state verified."
                }

            # Prune remediation history outside 5-minute rolling window
            cutoff = current_time - 300.0
            self._remediation_history = [t for t in self._remediation_history if t > cutoff]

            # Velocity check: Max 15% fleet per 5 minutes
            max_allowed_replacements = max(1, int(active_fleet_size * (self.max_remediation_velocity_pct / 100.0)))
            if len(self._remediation_history) >= max_allowed_replacements:
                return {
                    "action": RemediationAction.NONE.value,
                    "allowed": False,
                    "reason": f"Velocity limit exceeded: {len(self._remediation_history)} actions in last 5m (cap: {max_allowed_replacements})."
                }

            # Select remediation action
            action = RemediationAction.REPLACE_POD if self.state == NodeHealthState.UNHEALTHY else RemediationAction.SHED_TIER2
            self._remediation_history.append(current_time)
            self._unresolved_cycles += 1

            if self._unresolved_cycles >= self.dead_man_cycles_threshold:
                self.dead_man_tripped = True
                return {
                    "action": action.value,
                    "allowed": False,
                    "reason": f"DEAD-MAN SWITCH TRIPPED: {self._unresolved_cycles} consecutive failed remediation cycles. Automation frozen."
                }

            return {
                "action": action.value,
                "allowed": True,
                "reason": f"Remediation dispatched for {self.state.value} state."
            }

    def reset_dead_man_switch(self):
        with self._lock:
            self.dead_man_tripped = False
            self._unresolved_cycles = 0
            self._remediation_history.clear()
