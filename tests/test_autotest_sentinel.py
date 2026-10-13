"""
Unit and Integration Tests for AutoTest Sentinel
Validates statistical Bayesian flakiness classification, quarantine management,
AST anti-pattern detection, and ROI reporting.
"""

import json
import os
import tempfile
import pytest

from autotest_sentinel.classifier import FlakeClassifier
from autotest_sentinel.healer import ASTHealer
from autotest_sentinel.models import (
    FlakeCategory,
    FlakinessReport,
    RootCauseHypothesis,
    TestExecutionRecord,
    TestStatus,
)
from autotest_sentinel.quarantine import QuarantineManager
from autotest_sentinel.reporter import ReportGenerator


def test_deterministic_pass_classification():
    classifier = FlakeClassifier()
    records = [
        TestExecutionRecord(
            test_id="test_suite.py::test_math_add",
            file_path="test_suite.py",
            duration_seconds=0.05,
            status=TestStatus.PASSED,
        )
        for _ in range(5)
    ]
    report = classifier.analyze_executions(records)
    assert report.category == FlakeCategory.DETERMINISTIC_PASS
    assert report.flakiness_score < 0.20
    assert report.recommended_action == "NONE"


def test_deterministic_fail_classification():
    classifier = FlakeClassifier()
    records = [
        TestExecutionRecord(
            test_id="test_suite.py::test_broken_logic",
            file_path="test_suite.py",
            duration_seconds=0.04,
            status=TestStatus.FAILED,
            error_message="AssertionError: expected 5 got 4",
        )
        for _ in range(5)
    ]
    report = classifier.analyze_executions(records)
    assert report.category == FlakeCategory.DETERMINISTIC_FAIL
    assert report.failure_rate == 1.0
    assert report.recommended_action == "IGNORE"  # Do not quarantine real regressions


def test_flaky_timing_race_classification():
    classifier = FlakeClassifier()
    # 3 passes, 2 failures with timeout errors and timing jitter
    records = [
        TestExecutionRecord(
            test_id="test_suite.py::test_async_websocket",
            file_path="test_suite.py",
            duration_seconds=0.12,
            status=TestStatus.PASSED,
        ),
        TestExecutionRecord(
            test_id="test_suite.py::test_async_websocket",
            file_path="test_suite.py",
            duration_seconds=5.02,
            status=TestStatus.FAILED,
            error_message="asyncio.exceptions.TimeoutError: Operation timed out waiting for socket ACK",
        ),
        TestExecutionRecord(
            test_id="test_suite.py::test_async_websocket",
            file_path="test_suite.py",
            duration_seconds=0.15,
            status=TestStatus.PASSED,
        ),
        TestExecutionRecord(
            test_id="test_suite.py::test_async_websocket",
            file_path="test_suite.py",
            duration_seconds=5.01,
            status=TestStatus.FAILED,
            error_message="TimeoutError: timed out waiting for queue buffer",
        ),
        TestExecutionRecord(
            test_id="test_suite.py::test_async_websocket",
            file_path="test_suite.py",
            duration_seconds=0.14,
            status=TestStatus.PASSED,
        ),
    ]
    report = classifier.analyze_executions(records)
    assert report.category == FlakeCategory.FLAKY_HIGH
    assert report.flakiness_score >= 0.75
    assert report.root_cause == RootCauseHypothesis.TIMING_RACE
    assert report.recommended_action == "QUARANTINE"


def test_quarantine_manager_lifecycle():
    with tempfile.TemporaryDirectory() as tmpdir:
        manifest_file = os.path.join(tmpdir, "quarantine.json")
        qm = QuarantineManager(manifest_path=manifest_file)

        mock_report = FlakinessReport(
            test_id="test_network.py::test_flaky_call",
            file_path="test_network.py",
            flakiness_score=0.88,
            category=FlakeCategory.FLAKY_HIGH,
            root_cause=RootCauseHypothesis.NETWORK_IO,
            total_runs=6,
            failure_rate=0.33,
            duration_jitter=0.65,
            recommended_action="QUARANTINE",
            remediation_notes="Intermittent network drop",
        )

        # 1. Quarantine test
        is_new = qm.quarantine_test(mock_report, reason="High intermittent timeout")
        assert is_new is True
        assert qm.is_quarantined("test_network.py::test_flaky_call") is True

        # 2. Verify persistence on reload
        qm2 = QuarantineManager(manifest_path=manifest_file)
        assert qm2.is_quarantined("test_network.py::test_flaky_call") is True
        assert "test_network.py::test_flaky_call" in qm2.get_quarantined_ids()

        # 3. Check pytest deselection args
        desel_args = qm2.generate_pytest_deselection_args()
        assert "--deselect" in desel_args
        assert "test_network.py::test_flaky_call" in desel_args

        # 4. Check GitHub Actions step annotations
        notes = qm2.emit_github_actions_annotations()
        assert len(notes) == 1
        assert "::warning file=test_network.py" in notes[0]

        # 5. Unquarantine
        assert qm2.unquarantine_test("test_network.py::test_flaky_call") is True
        assert qm2.is_quarantined("test_network.py::test_flaky_call") is False


def test_ast_healer_pattern_detection():
    sample_code = """
import time
import random

def test_flaky_worker():
    x = random.randint(1, 100)
    time.sleep(2.5)
    assert x > 0
"""
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
        f.write(sample_code)
        f_path = f.name

    try:
        healer = ASTHealer()
        suggestions = healer.scan_file(f_path)
        assert len(suggestions) >= 2

        anti_patterns = [s.anti_pattern for s in suggestions]
        assert "FIXED_TIME_SLEEP" in anti_patterns
        assert "UNSEEDED_PSEUDORANDOM" in anti_patterns

        # Verify unified diff generation
        sleep_sugg = next(s for s in suggestions if s.anti_pattern == "FIXED_TIME_SLEEP")
        assert sleep_sugg.unified_diff is not None
        assert "wait_until" in sleep_sugg.suggested_snippet
    finally:
        if os.path.exists(f_path):
            os.remove(f_path)


def test_report_generator_formatting():
    rg = ReportGenerator(hourly_dev_cost=150.0, runner_cost_per_min=0.008)
    qm = QuarantineManager(manifest_path=tempfile.mktemp())
    mock_report = FlakinessReport(
        test_id="test_db.py::test_deadlock",
        file_path="test_db.py",
        flakiness_score=0.91,
        category=FlakeCategory.FLAKY_HIGH,
        root_cause=RootCauseHypothesis.SHARED_STATE,
        total_runs=8,
        failure_rate=0.25,
        duration_jitter=0.52,
        recommended_action="QUARANTINE",
        remediation_notes="Database locked during concurrent insert",
    )
    qm.quarantine_test(mock_report)

    md = rg.generate_markdown_summary(
        reports=[mock_report],
        quarantine_manifest=qm.manifest,
        heal_suggestions=[],
    )

    assert "# 🛡️ AutoTest Sentinel: DevEx & Test Flakiness Report" in md
    assert "Active Quarantined Tests" in md
    assert "Est. Monthly Cost Savings" in md
    assert "test_db.py::test_deadlock" in md
