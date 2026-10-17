"""
Unit tests for Phase 2 Telemetry & Error Budget Governance Framework
Verifies:
- W3C TraceContext propagation (injection / extraction)
- Tail-Based Sampling retention criteria
- Multi-Window Multi-Burn-Rate alerting (Google SRE Standard)
- Deployment Gate lockout & SRE Emergency Override bypass
"""

import time
import pytest
from engine.telemetry import (
    TraceSpan,
    TailBasedSampler,
    ErrorBudgetEngine,
    DeploymentGateStatus
)

def test_w3c_traceparent_injection_and_extraction():
    span = TraceSpan(name="test_checkout", sampled=True)
    header = span.to_traceparent()
    assert header.startswith("00-")
    assert header.endswith("-01")
    
    # Extract in downstream service
    child_span = TraceSpan.from_traceparent(header, span_name="downstream_payment")
    assert child_span.trace_id == span.trace_id
    assert child_span.parent_span_id == span.span_id
    assert child_span.sampled is True

def test_tail_based_sampling_rules():
    sampler = TailBasedSampler(p99_latency_threshold_ms=250.0, nominal_sample_rate=0.0)
    
    # 1. Nominal fast request -> should not be sampled with rate 0.0
    nominal_span = TraceSpan("fast_search")
    nominal_span.finish()
    nominal_span.duration_ms = 45.0
    assert sampler.should_sample(nominal_span) is False
    
    # 2. Error request -> MUST be retained 100%
    error_span = TraceSpan("failed_auth")
    error_span.set_error("Invalid token", status_code=500)
    error_span.finish()
    assert sampler.should_sample(error_span) is True
    
    # 3. Latency anomaly exceeding P99 threshold -> MUST be retained 100%
    slow_span = TraceSpan("slow_query")
    slow_span.finish()
    slow_span.duration_ms = 480.0  # > 250ms
    assert sampler.should_sample(slow_span) is True

def test_error_budget_burn_rate_alerts():
    engine = ErrorBudgetEngine(target_slo=0.9999) # 99.99% target, budget = 0.0001
    
    # 1h window with 14.4x burn rate (e.g. 100,000 requests, 15 failures -> error rate 0.00015 -> burn 1.5x)
    # 14.4x burn: 10,000 requests, 15 failures -> 0.0015 -> burn 15.0x
    res = engine.evaluate_burn_rate_alerts(
        window_1h_total=10000,
        window_1h_failed=15,
        window_6h_total=60000,
        window_6h_failed=10
    )
    assert res["severity"] == "P0_PAGE"
    assert res["burn_rate_1h"] >= 14.4

def test_deployment_gate_lock_and_emergency_override():
    engine = ErrorBudgetEngine(target_slo=0.9999)
    
    # Budget exhausted: 1,000,000 requests, 150 failures (allowable was 100) -> 150% consumed
    gate = engine.evaluate_deployment_gate(
        total_monthly_requests=1000000,
        failed_monthly_requests=150
    )
    assert gate["status"] == DeploymentGateStatus.LOCKED.value
    
    # Provide valid SRE Emergency Override Key
    current_ts = int(time.time())
    valid_key = f"SRE-OVERRIDE-{current_ts}-AUTH99"
    gate_override = engine.evaluate_deployment_gate(
        total_monthly_requests=1000000,
        failed_monthly_requests=150,
        emergency_override_key=valid_key
    )
    assert gate_override["status"] == DeploymentGateStatus.OVERRIDDEN.value
