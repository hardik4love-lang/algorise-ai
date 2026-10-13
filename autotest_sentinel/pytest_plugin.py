"""
AutoTest Sentinel: Pytest Integration Plugin
Hooks into pytest lifecycle to record execution telemetry and isolate quarantined tests.
"""

import json
import os
import time
import pytest

from .models import TestExecutionRecord, TestStatus
from .quarantine import QuarantineManager

TELEMETRY_LOG = os.path.join(".autotest", "telemetry.json")


def pytest_addoption(parser):
    group = parser.getgroup("autotest-sentinel", "AutoTest Sentinel Flakiness & Quarantine")
    group.addoption(
        "--autotest-quarantine",
        action="store_true",
        default=False,
        help="Skip tests registered in .autotest/quarantine.json",
    )
    group.addoption(
        "--autotest-record",
        action="store_true",
        default=True,
        help="Record run durations and failure outcomes for Bayesian analysis",
    )


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "quarantine(reason): mark test as quarantined due to non-deterministic flakiness"
    )


def pytest_collection_modifyitems(config, items):
    if not config.getoption("--autotest-quarantine", default=False):
        return

    qm = QuarantineManager()
    quarantined_ids = set(qm.get_quarantined_ids())

    for item in items:
        # Check against test nodeid
        if item.nodeid in quarantined_ids or any(qid in item.nodeid for qid in quarantined_ids):
            item.add_marker(
                pytest.mark.skip(
                    reason="AutoTest Sentinel: Quarantined non-deterministic test"
                )
            )


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()

    # Only record call phase (not setup/teardown unless failure occurs there)
    if report.when == "call" or (report.when in ("setup", "teardown") and report.failed):
        duration = getattr(report, "duration", 0.0)
        status = (
            TestStatus.PASSED if report.passed
            else TestStatus.SKIPPED if report.skipped
            else TestStatus.FAILED
        )

        error_msg = None
        stack_trace = None
        if report.failed and call.excinfo:
            error_msg = str(call.excinfo.value)
            stack_trace = str(call.excinfo.traceback)

        record = {
            "test_id": item.nodeid,
            "file_path": str(item.fspath),
            "duration_seconds": round(duration, 4),
            "status": status.value,
            "error_message": error_msg,
            "stack_trace": stack_trace,
            "timestamp": time.time(),
        }

        # Append to telemetry log
        os.makedirs(".autotest", exist_ok=True)
        try:
            records = []
            if os.path.exists(TELEMETRY_LOG):
                with open(TELEMETRY_LOG, "r", encoding="utf-8") as f:
                    records = json.load(f)
            records.append(record)
            with open(TELEMETRY_LOG, "w", encoding="utf-8") as f:
                json.dump(records, f, indent=2)
        except Exception:
            pass
