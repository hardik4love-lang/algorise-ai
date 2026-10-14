"""
Unit and Integration Tests for TraceRoot AI
Validates telemetry ingestion, Git blame frame isolation, defensive patch synthesis,
and MTTR post-mortem reporting.
"""

from __future__ import annotations

import os
import tempfile
import pytest

from trace_root_ai.blame_analyzer import BlameAnalyzer
from trace_root_ai.healer import IncidentHealer
from trace_root_ai.ingestor import TelemetryIngestor
from trace_root_ai.models import IncidentSeverity
from trace_root_ai.reporter import IncidentReporter


def test_telemetry_ingestor_parsing():
    ingestor = TelemetryIngestor()
    sample_traceback = """
Traceback (most recent call last):
  File "/opt/hostedtoolcache/Python/3.11.17/lib/python3.11/asyncio/base_events.py", line 640, in run_forever
    self._run_once()
  File "engine/pipeline.py", line 85, in execute_step
    score = weights["threshold"]
KeyError: 'threshold'
"""
    payload = ingestor.parse_traceback(sample_traceback, service_name="order-service")
    assert payload.service_name == "order-service"
    assert payload.error_type == "KeyError"
    assert payload.error_message == "'threshold'"
    assert payload.severity == IncidentSeverity.P2_HIGH
    assert len(payload.frames) == 2

    # Verify frame categorization (vendor vs internal)
    assert payload.frames[0].is_internal is False
    assert payload.frames[1].is_internal is True
    assert payload.frames[1].file_path == "engine/pipeline.py"
    assert payload.frames[1].line_number == 85


def test_healer_keyerror_patch_synthesis():
    with tempfile.TemporaryDirectory() as tmpdir:
        sample_file = os.path.join(tmpdir, "service.py")
        code = """
def process_data(config):
    limit = config["max_items"]
    return limit * 2
"""
        with open(sample_file, "w") as f:
            f.write(code)

        sample_tb = f"""
Traceback (most recent call last):
  File "service.py", line 3, in process_data
    limit = config["max_items"]
KeyError: 'max_items'
"""
        ingestor = TelemetryIngestor()
        payload = ingestor.parse_traceback(sample_tb)

        blame_analyzer = BlameAnalyzer(root_dir=tmpdir)
        blame = blame_analyzer.analyze_culprit_frame(payload)
        assert blame is not None

        healer = IncidentHealer(root_dir=tmpdir)
        plan = healer.synthesize_hotfix(payload, blame)

        assert plan is not None
        assert plan.confidence_score >= 0.90
        assert 'config.get("max_items", None)' in plan.remediated_snippet
        assert "-    limit = config[\"max_items\"]" in plan.patch_diff
        assert "+    limit = config.get(\"max_items\", None)" in plan.patch_diff


def test_healer_zerodivision_patch_synthesis():
    with tempfile.TemporaryDirectory() as tmpdir:
        sample_file = os.path.join(tmpdir, "metrics.py")
        code = """
def calculate_ratio(success, total):
    ratio = success / total
    return ratio
"""
        with open(sample_file, "w") as f:
            f.write(code)

        sample_tb = f"""
Traceback (most recent call last):
  File "metrics.py", line 3, in calculate_ratio
    ratio = success / total
ZeroDivisionError: division by zero
"""
        ingestor = TelemetryIngestor()
        payload = ingestor.parse_traceback(sample_tb)

        blame_analyzer = BlameAnalyzer(root_dir=tmpdir)
        blame = blame_analyzer.analyze_culprit_frame(payload)

        healer = IncidentHealer(root_dir=tmpdir)
        plan = healer.synthesize_hotfix(payload, blame)

        assert plan is not None
        assert plan.confidence_score >= 0.90
        assert "success / total if total else 0.0" in plan.remediated_snippet


def test_incident_reporter_markdown():
    ingestor = TelemetryIngestor()
    sample_tb = """
Traceback (most recent call last):
  File "app.py", line 12, in main
    res = data["missing"]
KeyError: 'missing'
"""
    payload = ingestor.parse_traceback(sample_tb, incident_id="INC-999001")
    reporter = IncidentReporter()
    md = reporter.generate_incident_report(payload, blame=None, plan=None)

    assert "# 🚨 TraceRoot AI: Autonomous Incident Triage Report — `INC-999001`" in md
    assert "KeyError" in md
    assert "Incident Telemetry Summary" in md
