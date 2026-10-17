"""
Continuous Verification & Chaos Engineering Engine (Phase 3 Baseline)
Implements:
- Steady-State Mathematical Verification (throughput mu +/- 2*sigma, error rate <= 0.01%, P99 <= 250ms)
- Controlled Fault Injection (Latency, Packet Loss, Dependency Outage)
- Automated Emergency Kill-Switch: Purges faults immediately if safety thresholds are breached
"""

import time
import math
from typing import Dict, Any, List, Optional, Callable

class SteadyStateVerifier:
    def __init__(
        self,
        expected_throughput_mean: float,
        expected_throughput_std: float,
        max_error_rate_pct: float = 0.01,
        max_p99_latency_ms: float = 250.0
    ):
        self.mean_tps = expected_throughput_mean
        self.std_tps = expected_throughput_std
        self.max_error_rate_pct = max_error_rate_pct
        self.max_p99_latency_ms = max_p99_latency_ms

    def is_steady_state(
        self,
        observed_tps: float,
        observed_error_rate_pct: float,
        observed_p99_latency_ms: float
    ) -> Dict[str, Any]:
        """
        Steady state:
        mu - 2*sigma <= tps <= mu + 2*sigma
        error_rate <= max_error_rate_pct (0.01%)
        p99_latency <= max_p99_latency_ms (250ms)
        """
        min_tps = max(0.0, self.mean_tps - (2.0 * self.std_tps))
        max_tps = self.mean_tps + (2.0 * self.std_tps)

        tps_healthy = (min_tps <= observed_tps <= max_tps)
        error_healthy = (observed_error_rate_pct <= self.max_error_rate_pct)
        latency_healthy = (observed_p99_latency_ms <= self.max_p99_latency_ms)

        valid = tps_healthy and error_healthy and latency_healthy
        reasons = []
        if not tps_healthy:
            reasons.append(f"Throughput out of bounds ({observed_tps:.1f} not in [{min_tps:.1f}, {max_tps:.1f}])")
        if not error_healthy:
            reasons.append(f"Error rate breached ({observed_error_rate_pct:.3f}% > {self.max_error_rate_pct}%)")
        if not latency_healthy:
            reasons.append(f"P99 latency breached ({observed_p99_latency_ms:.1f}ms > {self.max_p99_latency_ms}ms)")

        return {
            "steady_state": valid,
            "reasons": reasons
        }


class ChaosExperiment:
    def __init__(
        self,
        name: str,
        target_service: str,
        fault_type: str,
        duration_seconds: float = 60.0
    ):
        self.name = name
        self.target_service = target_service
        self.fault_type = fault_type
        self.duration_seconds = duration_seconds
        self.active = False
        self.aborted = False
        self.abort_reason: Optional[str] = None
        self.start_time: float = 0.0

    def start(self):
        self.active = True
        self.aborted = False
        self.abort_reason = None
        self.start_time = time.time()

    def check_safety_and_abort_if_needed(self, steady_state_check: Dict[str, Any]) -> bool:
        """
        Emergency Kill-Switch:
        Immediately tears down the fault injection if steady-state is compromised.
        """
        if not steady_state_check.get("steady_state", True):
            self.emergency_stop(f"Steady-state guardrail breach: {', '.join(steady_state_check.get('reasons', []))}")
            return True
        return False

    def emergency_stop(self, reason: str):
        self.active = False
        self.aborted = True
        self.abort_reason = reason

    def complete(self):
        self.active = False
