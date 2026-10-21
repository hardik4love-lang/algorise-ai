"""
Unit and Integration Tests for AutoTest Sentinel
Validates Bayesian flakiness classification, timing jitter evaluation,
AST anti-pattern scanning, quarantine manifest management, and pytest plugin.
"""

import os
import tempfile
import pytest
import math

from autotest_sentinel.classifier import FlakeClassifier
from autotest_sentinel.quarantine import QuarantineManager, QuarantineManifest
from autotest_sentinel.models import FlakeCategory, RootCauseHypothesis, FlakinessReport, TestExecutionRecord, TestStatus
import autotest_sentinel.pytest_plugin as pytest_plugin


class TestFlakeClassifier:
    """Tests for Bayesian flakiness classifier."""

    def test_classifier_initialization(self):
        clf = FlakeClassifier()
        assert clf.prior_flakiness == 0.05

    def test_analyze_executions_consistent_passes(self):
        """Consistent passes should yield low flakiness score."""
        clf = FlakeClassifier()
        records = [
            TestExecutionRecord(
                test_id="tests/test_api.py::test_pass",
                file_path="tests/test_api.py",
                status=TestStatus.PASSED,
                duration_seconds=1.0,
            ) for _ in range(10)
        ]
        report = clf.analyze_executions(records)
        assert report.flakiness_score < 0.1

    def test_analyze_executions_mixed_results(self):
        """Mixed passes/fails should yield moderate flakiness score."""
        clf = FlakeClassifier()
        records = [
            TestExecutionRecord(
                test_id="tests/test_api.py::test_flaky",
                file_path="tests/test_api.py",
                status=TestStatus.PASSED,
                duration_seconds=1.0,
            ) for _ in range(7)
        ] + [
            TestExecutionRecord(
                test_id="tests/test_api.py::test_flaky",
                file_path="tests/test_api.py",
                status=TestStatus.FAILED,
                duration_seconds=1.0,
            ) for _ in range(3)
        ]
        report = clf.analyze_executions(records)
        assert 0.1 < report.flakiness_score <= 1.0

    def test_analyze_executions_frequent_fails(self):
        """Frequent fails should yield high flakiness score."""
        clf = FlakeClassifier()
        records = [
            TestExecutionRecord(
                test_id="tests/test_api.py::test_broken",
                file_path="tests/test_api.py",
                status=TestStatus.PASSED,
                duration_seconds=1.0,
            ) for _ in range(2)
        ] + [
            TestExecutionRecord(
                test_id="tests/test_api.py::test_broken",
                file_path="tests/test_api.py",
                status=TestStatus.FAILED,
                duration_seconds=1.0,
            ) for _ in range(8)
        ]
        report = clf.analyze_executions(records)
        assert report.flakiness_score > 0.7

    def test_timing_jitter_evaluation_low_variance(self):
        """Low timing variance should not trigger jitter flag."""
        clf = FlakeClassifier()
        durations = [1.0, 1.02, 0.98, 1.01, 0.99]
        assert not clf.evaluate_jitter(durations)

    def test_timing_jitter_evaluation_high_variance(self):
        """High timing variance should trigger jitter flag."""
        clf = FlakeClassifier()
        durations = [1.0, 5.0, 0.5, 3.0, 2.0]
        assert clf.evaluate_jitter(durations)

    def test_anti_pattern_detection_fixed_sleep(self):
        """Should detect time.sleep() calls as anti-pattern."""
        clf = FlakeClassifier()
        code_with_sleep = "import time\n\ndef test_something():\n    time.sleep(2)\n    assert True"
        patterns = clf.scan_anti_patterns(code_with_sleep)
        assert any("sleep" in p.lower() for p in patterns)

    def test_anti_pattern_detection_unseeded_random(self):
        """Should detect unseeded random calls as anti-pattern."""
        clf = FlakeClassifier()
        code_with_random = "import random\n\ndef test_something():\n    x = random.randint(0, 10)\n    assert x > 0"
        patterns = clf.scan_anti_patterns(code_with_random)
        assert any("random" in p.lower() for p in patterns)


class TestQuarantineManager:
    """Tests for quarantine manifest management."""

    def test_quarantine_add_and_retrieve(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_path = os.path.join(tmpdir, "quarantine.json")
            qm = QuarantineManager(manifest_path=manifest_path)

            report = FlakinessReport(
                test_id="tests/test_api.py::test_flaky",
                file_path="tests/test_api.py",
                flakiness_score=0.85,
                category=FlakeCategory.FLAKY_HIGH,
                root_cause=RootCauseHypothesis.TIMING_RACE,
                total_runs=10,
                failure_rate=0.3,
                duration_jitter=0.1,
                recommended_action="Quarantine test and notify owner",
                remediation_notes="Detected via CI",
            )

            is_new = qm.quarantine_test(report=report, reason="Flaky test", ttl_days=14)
            assert is_new is True

            quarantined = qm.get_quarantined_ids()
            assert "tests/test_api.py::test_flaky" in quarantined

    def test_quarantine_unquarantine(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_path = os.path.join(tmpdir, "quarantine.json")
            qm = QuarantineManager(manifest_path=manifest_path)

            report = FlakinessReport(
                test_id="tests/test_api.py::test_healed",
                file_path="tests/test_api.py",
                flakiness_score=0.1,
                category=FlakeCategory.DETERMINISTIC_PASS,
                root_cause=RootCauseHypothesis.UNKNOWN,
                total_runs=100,
                failure_rate=0.0,
                duration_jitter=0.01,
                recommended_action="Restore",
                remediation_notes="Fixed flakiness",
            )

            qm.quarantine_test(report=report, reason="Test", ttl_days=14)
            removed = qm.unquarantine_test("tests/test_api.py::test_healed")
            assert removed is True
            assert "tests/test_api.py::test_healed" not in qm.get_quarantined_ids()

    def test_quarantine_ttl_expiry(self):
        """Expired quarantines should be filtered out."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_path = os.path.join(tmpdir, "quarantine.json")
            qm = QuarantineManager(manifest_path=manifest_path)

            report = FlakinessReport(
                test_id="tests/test_api.py::test_expired",
                file_path="tests/test_api.py",
                flakiness_score=0.8,
                category=FlakeCategory.FLAKY_HIGH,
                root_cause=RootCauseHypothesis.TIMING_RACE,
                total_runs=10,
                failure_rate=0.3,
                duration_jitter=0.1,
                recommended_action="Quarantine test and notify owner",
                remediation_notes="Old quarantine",
            )

            qm.quarantine_test(report=report, reason="Test", ttl_days=0)
            active_ids = qm.get_quarantined_ids()
            assert "tests/test_api.py::test_expired" not in active_ids

    def test_manifest_persistence(self):
        """Manifest should persist to disk and reload correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_path = os.path.join(tmpdir, "quarantine.json")
            qm = QuarantineManager(manifest_path=manifest_path)

            report = FlakinessReport(
                test_id="tests/test_api.py::test_persist",
                file_path="tests/test_api.py",
                flakiness_score=0.9,
                category=FlakeCategory.FLAKY_HIGH,
                root_cause=RootCauseHypothesis.TIMING_RACE,
                total_runs=10,
                failure_rate=0.4,
                duration_jitter=0.2,
                recommended_action="Quarantine test and notify owner",
                remediation_notes="Persist test",
            )

            qm.quarantine_test(report=report, reason="Test", ttl_days=14)

            # Reload from disk
            qm2 = QuarantineManager(manifest_path=manifest_path)
            assert "tests/test_api.py::test_persist" in qm2.get_quarantined_ids()
            assert qm2.manifest.version == qm.manifest.version


class TestQuarantineManifest:
    """Tests for QuarantineManifest data model."""

    def test_manifest_versioning(self):
        manifest = QuarantineManifest()
        assert manifest.version == "1.0.0"
        assert isinstance(manifest.quarantined_tests, dict)
        assert isinstance(manifest.updated_at, str)

    def test_pytest_deselection_args(self):
        manifest = QuarantineManifest()
        manifest.quarantined_tests = {
            "tests/test_a.py::test_1": {},
            "tests/test_b.py::test_2": {},
        }
        args = manifest.generate_pytest_deselection_args()
        assert "--deselect" in args
        assert "tests/test_a.py::test_1" in " ".join(args)


class TestPytestPlugin:
    """Tests for pytest plugin hooks."""

    def test_pytest_addoption_registers_flags(self):
        """Plugin should register --autotest-quarantine and --autotest-record."""
        class MockParser:
            def __init__(self):
                self.options = []
            def getgroup(self, name, desc):
                class MockGroup:
                    def __init__(self, parser_ref):
                        self.parser_ref = parser_ref
                    def addoption(self, *args, **kwargs):
                        self.parser_ref.options.append(args[0])
                return MockGroup(self)
        parser = MockParser()
        pytest_plugin.pytest_addoption(parser)
        assert "--autotest-quarantine" in parser.options
        assert "--autotest-record" in parser.options

    def test_pytest_configure_registers_marker(self):
        """Plugin should register quarantine marker."""
        class MockConfig:
            def addinivalue_line(self, marker, line):
                self.marker_line = line
        config = MockConfig()
        pytest_plugin.pytest_configure(config)
        assert "quarantine" in config.marker_line

    def test_pytest_collection_modifyitems_skips_quarantined(self):
        """Should add skip marker to quarantined tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create quarantine manifest in default location
            import autotest_sentinel.quarantine as quarantine_module
            original_default = quarantine_module.QuarantineManager.DEFAULT_MANIFEST_PATH
            quarantine_module.QuarantineManager.DEFAULT_MANIFEST_PATH = os.path.join(tmpdir, ".autotest", "quarantine.json")
            
            try:
                manifest_path = os.path.join(tmpdir, ".autotest", "quarantine.json")
                qm = QuarantineManager(manifest_path=manifest_path)
                from autotest_sentinel.models import FlakinessReport, FlakeCategory, RootCauseHypothesis
                report = FlakinessReport(
                    test_id="tests/test_quarantined.py::test_bad",
                    file_path="tests/test_quarantined.py",
                    flakiness_score=0.9,
                    category=FlakeCategory.FLAKY_HIGH,
                    root_cause=RootCauseHypothesis.TIMING_RACE,
                    total_runs=10,
                    failure_rate=0.5,
                    duration_jitter=0.2,
                    recommended_action="Quarantine",
                    remediation_notes="Test",
                )
                qm.quarantine_test(report=report, reason="Test", ttl_days=14)

                # Mock items
                class MockItem:
                    def __init__(self, nodeid):
                        self.nodeid = nodeid
                        self.markers = []
                    def add_marker(self, marker):
                        self.markers.append(marker)

                class MockConfig:
                    def getoption(self, name, default=False):
                        if name == "--autotest-quarantine":
                            return True
                        return default

                items = [
                    MockItem("tests/test_quarantined.py::test_bad"),
                    MockItem("tests/test_good.py::test_ok"),
                ]
                config = MockConfig()

                pytest_plugin.pytest_collection_modifyitems(config, items)

                # First item should have skip marker
                assert any("skip" in str(m) for m in items[0].markers)
            finally:
                quarantine_module.QuarantineManager.DEFAULT_MANIFEST_PATH = original_default
            # Second item should not
            assert not any("skip" in str(m) for m in items[1].markers)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])