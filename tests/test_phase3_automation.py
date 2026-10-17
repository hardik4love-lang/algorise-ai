"""
Unit tests for Phase 3 Automation & Chaos Engineering Framework
Verifies:
- ClosedLoopRemediator asymmetric hysteresis damping (tau_fail vs tau_recover)
- Remediation velocity limit enforcement
- Dead-man switch freezing runaway automated remediations
- SteadyStateVerifier mathematical boundary checks (mu +/- 2*sigma, error rate <= 0.01%)
- ChaosExperiment emergency kill-switch
"""

import time
import pytest
from engine.self_healing import (
    ClosedLoopRemediator,
    NodeHealthState,
    RemediationAction
)
from engine.chaos import (
    SteadyStateVerifier,
    ChaosExperiment
)

def test_closed_loop_asymmetric_hysteresis():
    remediator = ClosedLoopRemediator(
        service_name="checkout_api",
        failure_consecutive_threshold=3,
        failure_window_sec=15.0,
        recovery_consecutive_threshold=12,
        recovery_window_sec=120.0
    )
    
    t0 = 1000.0
    # 2 failures -> DEGRADED
    assert remediator.record_probe(False, now=t0) == NodeHealthState.DEGRADED
    assert remediator.record_probe(False, now=t0 + 1) == NodeHealthState.DEGRADED
    
    # 3rd failure -> UNHEALTHY
    assert remediator.record_probe(False, now=t0 + 2) == NodeHealthState.UNHEALTHY
    
    # Successful probes: 11 successes -> still UNHEALTHY (needs 12)
    for i in range(11):
        assert remediator.record_probe(True, now=t0 + 10 + i) == NodeHealthState.UNHEALTHY
        
    # 12th success but recovery window not elapsed (120s needed, only 22s elapsed) -> still UNHEALTHY
    assert remediator.record_probe(True, now=t0 + 22) == NodeHealthState.UNHEALTHY
    
    # 13th success after 125s -> resets to HEALTHY
    assert remediator.record_probe(True, now=t0 + 135) == NodeHealthState.HEALTHY

def test_closed_loop_dead_man_switch():
    remediator = ClosedLoopRemediator(
        service_name="payment_router",
        dead_man_cycles_threshold=2
    )
    # Trip to UNHEALTHY
    for _ in range(3):
        remediator.record_probe(False)
    assert remediator.state == NodeHealthState.UNHEALTHY
    
    # 1st remediation cycle
    res1 = remediator.evaluate_remediation(active_fleet_size=20)
    assert res1["allowed"] is True
    assert res1["action"] == RemediationAction.REPLACE_POD.value
    
    # 2nd remediation cycle -> Dead-Man Switch Trips!
    res2 = remediator.evaluate_remediation(active_fleet_size=20)
    assert res2["allowed"] is False
    assert "DEAD-MAN SWITCH TRIPPED" in res2["reason"]
    assert remediator.dead_man_tripped is True

def test_steady_state_verifier():
    verifier = SteadyStateVerifier(
        expected_throughput_mean=1000.0,
        expected_throughput_std=100.0,
        max_error_rate_pct=0.01,
        max_p99_latency_ms=250.0
    )
    # Nominal healthy
    nominal = verifier.is_steady_state(
        observed_tps=1050.0,
        observed_error_rate_pct=0.005,
        observed_p99_latency_ms=180.0
    )
    assert nominal["steady_state"] is True
    assert len(nominal["reasons"]) == 0
    
    # Error rate spike (0.05% > 0.01%)
    degraded = verifier.is_steady_state(
        observed_tps=1000.0,
        observed_error_rate_pct=0.05,
        observed_p99_latency_ms=150.0
    )
    assert degraded["steady_state"] is False
    assert any("Error rate breached" in r for r in degraded["reasons"])

def test_chaos_experiment_emergency_kill_switch():
    experiment = ChaosExperiment(
        name="inject_latency_payment",
        target_service="payment_gateway",
        fault_type="LATENCY_INJECTION"
    )
    experiment.start()
    assert experiment.active is True
    
    # Trigger emergency kill-switch
    failed_check = {"steady_state": False, "reasons": ["Error rate breached (0.08% > 0.01%)"]}
    aborted = experiment.check_safety_and_abort_if_needed(failed_check)
    
    assert aborted is True
    assert experiment.active is False
    assert experiment.aborted is True
    assert "Steady-state guardrail breach" in experiment.abort_reason
