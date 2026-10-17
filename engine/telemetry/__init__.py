"""
Telemetry & Reliability Governance Framework Package (Phase 2 Baseline)
Provides:
- TraceSpan, TailBasedSampler (W3C distributed tracing)
- ErrorBudgetEngine, DeploymentGateStatus (quantitative SLO & burn rate alerting)
"""

from engine.telemetry.w3c_tracer import TraceSpan, TailBasedSampler
from engine.telemetry.error_budget_engine import ErrorBudgetEngine, DeploymentGateStatus

__all__ = [
    "TraceSpan",
    "TailBasedSampler",
    "ErrorBudgetEngine",
    "DeploymentGateStatus"
]
