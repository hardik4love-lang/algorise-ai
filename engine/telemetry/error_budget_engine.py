"""
Error Budget & Multi-Window Burn Rate Engine (Phase 2 Baseline)
Implements quantitative SRE reliability governance:
- Calculates error budget consumption over rolling windows
- Multi-window multi-burn-rate alerting (Google SRE Standard)
- Automated CI/CD deployment gate with Dual-Key SRE Emergency Override integration
"""

import time
from enum import Enum
from typing import Dict, Any, Optional
from engine.gitops_ledger import GitOpsLedger

class DeploymentGateStatus(Enum):
    UNLOCKED = "UNLOCKED"
    RESTRICTED = "RESTRICTED"
    LOCKED = "LOCKED"
    OVERRIDDEN = "OVERRIDDEN"

class ErrorBudgetEngine:
    def __init__(self, target_slo: float = 0.9999, rolling_window_days: int = 30):
        self.target_slo = target_slo
        self.allowable_error_rate = 1.0 - target_slo  # 0.0001 for 99.99%
        self.rolling_window_seconds = rolling_window_days * 86400

    def calculate_burn_rate(self, total_requests: int, failed_requests: int) -> float:
        """
        Burn rate = observed_error_rate / allowable_error_rate.
        A burn rate of 1.0 consumes 100% of the budget in exactly 30 days.
        A burn rate of 14.4 consumes 2% of the budget in 1 hour.
        """
        if total_requests <= 0:
            return 0.0
        observed_error_rate = failed_requests / total_requests
        return observed_error_rate / self.allowable_error_rate

    def evaluate_burn_rate_alerts(
        self,
        window_1h_total: int,
        window_1h_failed: int,
        window_6h_total: int,
        window_6h_failed: int
    ) -> Dict[str, Any]:
        """
        Multi-window multi-burn-rate alert evaluation:
        - 1h window: Burn rate >= 14.4 -> CRITICAL (P0 Page)
        - 6h window: Burn rate >= 6.0  -> HIGH (P1 Ticket)
        """
        burn_1h = self.calculate_burn_rate(window_1h_total, window_1h_failed)
        burn_6h = self.calculate_burn_rate(window_6h_total, window_6h_failed)

        alerts = []
        severity = "NORMAL"

        if burn_1h >= 14.4:
            alerts.append("CRITICAL: 1-hour error budget burn rate >= 14.4x (2% budget consumed in 1 hour)")
            severity = "P0_PAGE"
        elif burn_6h >= 6.0:
            alerts.append("HIGH: 6-hour error budget burn rate >= 6.0x (5% budget consumed in 6 hours)")
            severity = "P1_TICKET"

        return {
            "severity": severity,
            "burn_rate_1h": round(burn_1h, 2),
            "burn_rate_6h": round(burn_6h, 2),
            "alerts": alerts
        }

    def evaluate_deployment_gate(
        self,
        total_monthly_requests: int,
        failed_monthly_requests: int,
        emergency_override_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Evaluates whether CI/CD should allow new feature deployments.
        If budget is depleted (100% consumed), locks deployments unless
        a valid SRE Leadership Emergency Override Key is provided.
        """
        if total_monthly_requests <= 0:
            budget_consumed_pct = 0.0
        else:
            allowable_failures = total_monthly_requests * self.allowable_error_rate
            budget_consumed_pct = (failed_monthly_requests / max(1.0, allowable_failures)) * 100.0

        if budget_consumed_pct < 80.0:
            status = DeploymentGateStatus.UNLOCKED
            reason = "Budget healthy (> 20% remaining)"
        elif budget_consumed_pct < 100.0:
            status = DeploymentGateStatus.RESTRICTED
            reason = "Budget warning (< 20% remaining); mandatory SRE review"
        else:
            # 100% or more consumed: attempt emergency override check
            if emergency_override_key and GitOpsLedger.validate_emergency_override_key(emergency_override_key):
                status = DeploymentGateStatus.OVERRIDDEN
                reason = "SRE Leadership Emergency Override Key verified (Time-bounded window active)"
            else:
                status = DeploymentGateStatus.LOCKED
                reason = "Error budget depleted (100% consumed). Automated CI/CD freeze active."

        return {
            "status": status.value,
            "budget_consumed_pct": round(budget_consumed_pct, 2),
            "reason": reason
        }
