"""
Self-Healing & Autonomous Remediation Framework Package (Phase 3 Baseline)
Provides:
- ClosedLoopRemediator (asymmetric hysteresis damping, velocity limit, dead-man switch)
- NodeHealthState, RemediationAction
"""

from engine.self_healing.closed_loop import (
    ClosedLoopRemediator,
    NodeHealthState,
    RemediationAction
)

__all__ = [
    "ClosedLoopRemediator",
    "NodeHealthState",
    "RemediationAction"
]
