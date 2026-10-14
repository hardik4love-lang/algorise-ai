"""
Unit Tests for Revenue Engine
Validates multi-gate scoring, zero-cost enforcement, ENR calculation, and ledger persistence.
"""

from __future__ import annotations

import os
import tempfile
import pytest

from revenue_engine.models import OpportunityStatus
from revenue_engine.reporter import RevenueReporter
from revenue_engine.scanner import OpportunityScanner
from revenue_engine.scorer import RevenueScorer


def test_revenue_scorer_approval_path():
    scorer = RevenueScorer()
    opp = scorer.evaluate_opportunity(
        task_id="task-101",
        title="Optimize Cache Buffer Ingestion",
        repository="org/repo",
        url="https://github.com/org/repo/issues/101",
        gross_payout_usd=100.0,
        urgency_score=0.85,
        risk_score=0.15,
        compute_cost_usd=0.0,
        confidence_score=0.95,
        quota_remaining=2500,
        max_cost_limit=0.0,
    )
    assert opp.status == OpportunityStatus.APPROVED_FOR_TRIAGE
    assert len(opp.gates_passed) == 7
    assert opp.expected_net_revenue == 95.0  # (0.95 * 100) - 0
    assert opp.prioritization_score > 0.0


def test_revenue_scorer_confidence_gate_rejection():
    scorer = RevenueScorer()
    # Confidence 0.80 is below 0.90 threshold
    opp = scorer.evaluate_opportunity(
        task_id="task-102",
        title="Ambiguous Spec Task",
        repository="org/repo",
        url="https://github.com/org/repo/issues/102",
        gross_payout_usd=50.0,
        confidence_score=0.80,
    )
    assert opp.status == OpportunityStatus.REJECTED_GATE_FAILURE
    assert "thought_validated" not in opp.gates_passed
    assert any("Confidence score" in r for r in opp.rejection_reasons)


def test_revenue_scorer_budget_limit_rejection():
    scorer = RevenueScorer()
    # Compute cost exceeds zero-cost limit
    opp = scorer.evaluate_opportunity(
        task_id="task-103",
        title="Heavy GPU Computation Task",
        repository="org/repo",
        url="https://github.com/org/repo/issues/103",
        gross_payout_usd=50.0,
        compute_cost_usd=2.50,
        max_cost_limit=0.0,
    )
    assert opp.status == OpportunityStatus.REJECTED_GATE_FAILURE
    assert "within_budget" not in opp.gates_passed
    assert any("Compute cost" in r for r in opp.rejection_reasons)


def test_opportunity_scanner_with_mock_data():
    with tempfile.TemporaryDirectory() as tmpdir:
        ledger_path = os.path.join(tmpdir, "test_ledger.json")
        scanner = OpportunityScanner(ledger_path=ledger_path)

        mock_issues = [
            {
                "number": 55,
                "title": "Resolve Memory Leak in Gateway",
                "repository": {"nameWithOwner": "algorise/gateway"},
                "url": "https://github.com/algorise/gateway/issues/55",
                "estimated_payout": 75.0,
                "urgency": 0.90,
                "risk": 0.10,
            }
        ]

        ledger = scanner.scan_opportunities(mock_items=mock_issues, enforce_zero_cost=True)
        assert ledger.total_evaluated == 1
        assert len(ledger.opportunities) == 1
        opp = ledger.opportunities[0]
        assert opp.task_id == "gh-55"
        assert opp.status == OpportunityStatus.APPROVED_FOR_TRIAGE
        assert opp.expected_net_revenue > 0

        # Verify ledger file on disk
        assert os.path.exists(ledger_path)

        # Test Reporter
        reporter = RevenueReporter()
        md = reporter.generate_markdown_report(ledger)
        assert "# 💰 Revenue Orchestrator: Autonomous Opportunity Ledger" in md
        assert "gh-55" in md
        assert "APPROVED" in md
