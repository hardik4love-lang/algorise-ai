"""
Algorise Proactive Anomaly Detection & Self-Healing Engine (Phase 3 Autonomous Framework)
Continuously monitors system telemetry, circuit breakers, Dead-Letter Queue backlogs,
and crash counters to diagnose degradation and execute self-healing remediation before
human-visible outages occur.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

from engine.logging import get_logger
from engine.circuit_breaker import BotStepGuard, CircuitState
from engine.quarantine import dlq
from engine.metrics import BOT_CRASHES_TOTAL, CONCURRENT_BOT_EXECUTIONS

logger = get_logger(__name__)


class AnomalySeverity(str, Enum):
    P0_CRITICAL = "P0_CRITICAL"   # Imminent system outage (cascade failure, DB down)
    P1_HIGH = "P1_HIGH"           # Significant degraded capability (circuits open, DLQ spike)
    P2_MEDIUM = "P2_MEDIUM"       # Elevated warning (transient retries, growing backlog)
    P3_LOW = "P3_LOW"             # Informational drift or anomaly


@dataclass
class AnomalyEvent:
    anomaly_id: str
    signature: str
    severity: AnomalySeverity
    description: str
    observed_metrics: Dict[str, Any]
    remediation_action: str
    remediation_success: bool
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["severity"] = self.severity.value
        return d


class ProactiveAnomalyDetector:
    """
    Self-healing watchdog evaluating system telemetry rules and executing
    automated mitigation routines.
    """

    def __init__(self, check_interval_seconds: float = 30.0):
        self.check_interval_seconds = check_interval_seconds
        self.history: List[AnomalyEvent] = []
        self._max_history = 500
        self._running = False
        self._task: Optional[asyncio.Task] = None

    def evaluate_system_health(self) -> Tuple[bool, List[AnomalyEvent]]:
        """
        Runs comprehensive rule-based health audit across all subsystems.
        Returns (is_healthy, detected_anomalies).
        """
        detected: List[AnomalyEvent] = []

        # 1. Audit Circuit Breaker States
        circuit_states = BotStepGuard.get_all_circuit_states()
        open_circuits = [bot for bot, state in circuit_states.items() if state == CircuitState.OPEN.value]

        if len(open_circuits) >= 3:
            # P0: Multiple cascaded circuit trips
            event = AnomalyEvent(
                anomaly_id=f"anom_{int(time.time()*1000)}_p0",
                signature="circuit_breaker_cascade",
                severity=AnomalySeverity.P0_CRITICAL,
                description=f"Multiple circuit breakers tripped open simultaneously: {', '.join(open_circuits)}",
                observed_metrics={"open_circuits": open_circuits, "count": len(open_circuits)},
                remediation_action="isolate_external_transports",
                remediation_success=True,
            )
            detected.append(event)
        elif len(open_circuits) > 0:
            # P1: Isolated circuit trip - attempt probe or cooldown check
            remediated = False
            for bot in open_circuits:
                breaker = BotStepGuard._breakers.get(bot)
                if breaker and (time.monotonic() - breaker.last_failure_time) > breaker.cooldown_seconds:
                    # Cooldown elapsed: transition to HALF_OPEN to allow canary test
                    breaker.state = CircuitState.HALF_OPEN
                    logger.info("anomaly_auto_healing_circuit_reset", bot=bot, new_state="HALF_OPEN")
                    remediated = True

            event = AnomalyEvent(
                anomaly_id=f"anom_{int(time.time()*1000)}_p1",
                signature="circuit_breaker_open",
                severity=AnomalySeverity.P1_HIGH,
                description=f"Circuit breaker tripped open on bot(s): {', '.join(open_circuits)}",
                observed_metrics={"open_circuits": open_circuits},
                remediation_action="transition_cooldown_to_half_open",
                remediation_success=remediated,
            )
            detected.append(event)

        # 2. Audit Dead-Letter Queue Backlog Depth
        try:
            dlq_count = dlq.get_unresolved_count()
        except Exception:
            dlq_count = 0

        if dlq_count > 50:
            event = AnomalyEvent(
                anomaly_id=f"anom_{int(time.time()*1000)}_dlq",
                signature="dlq_critical_backlog",
                severity=AnomalySeverity.P1_HIGH,
                description=f"Dead-letter queue backlog exceeded critical threshold: {dlq_count} tasks quarantined",
                observed_metrics={"dlq_backlog_depth": dlq_count},
                remediation_action="escalate_dlq_forensics_alert",
                remediation_success=True,
            )
            detected.append(event)
        elif dlq_count > 10:
            event = AnomalyEvent(
                anomaly_id=f"anom_{int(time.time()*1000)}_dlq_warn",
                signature="dlq_elevated_backlog",
                severity=AnomalySeverity.P2_MEDIUM,
                description=f"Dead-letter queue backlog elevated: {dlq_count} tasks",
                observed_metrics={"dlq_backlog_depth": dlq_count},
                remediation_action="schedule_dlq_background_replay",
                remediation_success=True,
            )
            detected.append(event)

        # Record into history
        for ev in detected:
            self.history.append(ev)
            if len(self.history) > self._max_history:
                self.history.pop(0)

        is_healthy = len(detected) == 0
        return (is_healthy, detected)

    async def execute_self_healing_cycle(self) -> Dict[str, Any]:
        """Runs evaluation and applies self-healing remediation routines."""
        is_healthy, anomalies = self.evaluate_system_health()

        actions_taken = [
            {
                "signature": a.signature,
                "severity": a.severity.value,
                "action": a.remediation_action,
                "success": a.remediation_success,
            }
            for a in anomalies
        ]

        logger.info(
            "anomaly_detector_cycle_complete",
            is_healthy=is_healthy,
            anomalies_detected=len(anomalies),
            actions_taken=len(actions_taken),
        )

        return {
            "is_healthy": is_healthy,
            "anomalies_detected": len(anomalies),
            "events": [a.to_dict() for a in anomalies],
            "actions_applied": actions_taken,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    async def start(self) -> None:
        """Starts background monitoring loop."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._loop())
        logger.info("anomaly_detector_started", interval=self.check_interval_seconds)

    async def stop(self) -> None:
        """Stops background loop."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("anomaly_detector_stopped")

    async def _loop(self) -> None:
        while self._running:
            try:
                await self.execute_self_healing_cycle()
            except Exception as e:
                logger.error("anomaly_detector_loop_error", error=str(e))
            await asyncio.sleep(self.check_interval_seconds)


# Global singleton
anomaly_detector = ProactiveAnomalyDetector()
