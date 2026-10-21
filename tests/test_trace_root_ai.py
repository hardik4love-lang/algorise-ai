"""
Unit and Integration Tests for TraceRoot AI
Validates incident ingestion, blame analysis, hotfix synthesis for common exceptions,
AST patch validation, and emergency hotfix branch staging.
"""

import os
import tempfile
import pytest
import subprocess

from trace_root_ai.ingestor import TelemetryIngestor
from trace_root_ai.blame_analyzer import BlameAnalyzer
from trace_root_ai.healer import IncidentHealer
from trace_root_ai.models import IncidentPayload, BlameContext, HotfixPlan, HotfixStatus
from trace_root_ai.mesh import AutonomousHealingMesh


class TestTelemetryIngestor:
    """Tests for telemetry ingestion and parsing."""

    def test_ingest_json_payload(self):
        """Should parse JSON incident payload correctly."""
        ingestor = TelemetryIngestor()
        payload = {
            "incident_id": "INC-001",
            "service_name": "payment-service",
            "error_type": "KeyError",
            "error_message": "'user_id'",
            "raw_stack_trace": "Traceback (most recent call last):\n  File \"app.py\", line 42, in process\n    user = data['user_id']\nKeyError: 'user_id'",
        }
        incident = ingestor.parse_json_payload(payload)
        assert incident.incident_id == "INC-001"
        assert incident.error_type == "KeyError"
        assert "user_id" in incident.error_message

    def test_ingest_stderr_traceback(self):
        """Should parse raw stderr traceback."""
        ingestor = TelemetryIngestor()
        stderr = """Traceback (most recent call last):
  File "calc.py", line 10, in divide
    result = a / b
ZeroDivisionError: division by zero"""
        incident = ingestor.parse_traceback(stderr, service_name="calc-service")
        assert incident.error_type == "ZeroDivisionError"
        assert "division by zero" in incident.error_message

    def test_ingest_with_missing_fields(self):
        """Should handle missing optional fields gracefully."""
        ingestor = TelemetryIngestor()
        payload = {"incident_id": "INC-002", "error_type": "AttributeError"}
        incident = ingestor.parse_json_payload(payload)
        assert incident.incident_id == "INC-002"
        assert incident.error_type == "AttributeError"
        assert incident.service_name == "algorise-service"


class TestBlameAnalyzer:
    """Tests for git blame correlation."""

    def test_blame_finds_culprit_commit(self):
        """Should correlate crash line with introducing commit."""
        with tempfile.TemporaryDirectory() as tmpdir:
            subprocess.run(["git", "init"], cwd=tmpdir, capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmpdir)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=tmpdir)

            buggy_file = os.path.join(tmpdir, "buggy.py")
            with open(buggy_file, "w") as f:
                f.write("def divide(a, b):\n    return a / b\n")
            subprocess.run(["git", "add", "buggy.py"], cwd=tmpdir)
            subprocess.run(["git", "commit", "-m", "Add divide"], cwd=tmpdir)

            with open(buggy_file, "w") as f:
                f.write("def divide(a, b):\n    return a / b\n\ndef bad_divide(a, b):\n    return a / 0\n")
            subprocess.run(["git", "add", "buggy.py"], cwd=tmpdir)
            subprocess.run(["git", "commit", "-m", "Add bad_divide"], cwd=tmpdir)

            analyzer = BlameAnalyzer(root_dir=tmpdir)

            # Create incident payload with frame pointing to buggy line
            from trace_root_ai.models import IncidentPayload, StackFrame
            buggy_file_abs = os.path.join(tmpdir, "buggy.py").replace("\\", "/")
            payload = IncidentPayload(
                incident_id="INC-TEST-001",
                service_name="test",
                error_type="ZeroDivisionError",
                error_message="division by zero",
                raw_stack_trace="ZeroDivisionError: division by zero",
                frames=[
                    StackFrame(
                        file_path=buggy_file_abs,
                        line_number=4,
                        function_name="bad_divide",
                        code_line="return a / 0",
                        is_internal=True,
                    )
                ],
            )

            context = analyzer.analyze_culprit_frame(payload)
            assert context is not None
            assert context.culprit_commit_sha is not None


class TestIncidentHealer:
    """Tests for defensive patch synthesis."""

    def test_healer_keyerror_patch_synthesis(self):
        """Should synthesize .get() fallback for KeyError."""
        healer = IncidentHealer()
        incident = IncidentPayload(
            incident_id="INC-KEY-001",
            service_name="test",
            error_type="KeyError",
            error_message="'config'",
            raw_stack_trace="KeyError: 'config'",
        )
        blame = BlameContext(
            file_path="settings.py",
            line_number=2,
            culprit_commit_sha="abc123",
            author_name="test",
            commit_date="2024-01-01T00:00:00Z",
            commit_summary="Add config",
            failing_function="load_config",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = os.path.join(tmpdir, "settings.py")
            with open(test_file, "w") as f:
                f.write("# Line 9\nconfig_value = data['config']  # Line 10\n")
            healer.root_dir = tmpdir

            plan = healer.synthesize_hotfix(incident, blame)
            assert plan is not None
            assert plan.confidence_score >= 0.9
            assert ".get(" in plan.remediated_snippet
            assert "config" in plan.remediated_snippet
            assert plan.status == HotfixStatus.SIMULATED

    def test_healer_zerodivision_patch_synthesis(self):
        """Should synthesize zero-denominator guard for ZeroDivisionError."""
        healer = IncidentHealer()
        incident = IncidentPayload(
            incident_id="INC-ZDIV-001",
            service_name="test",
            error_type="ZeroDivisionError",
            error_message="division by zero",
            raw_stack_trace="ZeroDivisionError: division by zero",
        )
        blame = BlameContext(
            file_path="calc.py",
            line_number=2,
            culprit_commit_sha="abc123",
            author_name="test",
            commit_date="2024-01-01T00:00:00Z",
            commit_summary="Add calc",
            failing_function="divide",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = os.path.join(tmpdir, "calc.py")
            with open(test_file, "w") as f:
                f.write("# Line 4\nresult = a / b  # Line 5\n")
            healer.root_dir = tmpdir

            plan = healer.synthesize_hotfix(incident, blame)
            assert plan is not None
            assert plan.confidence_score >= 0.9
            assert "if" in plan.remediated_snippet.lower() or "else" in plan.remediated_snippet.lower()
            assert "b" in plan.remediated_snippet

    def test_healer_attributeerror_patch_synthesis(self):
        """Should synthesize None guard for AttributeError."""
        healer = IncidentHealer()
        incident = IncidentPayload(
            incident_id="INC-ATTR-001",
            service_name="test",
            error_type="AttributeError",
            error_message="'NoneType' object has no attribute 'name'",
            raw_stack_trace="AttributeError: 'NoneType' object has no attribute 'name'",
        )
        blame = BlameContext(
            file_path="model.py",
            line_number=2,
            culprit_commit_sha="abc123",
            author_name="test",
            commit_date="2024-01-01T00:00:00Z",
            commit_summary="Add model",
            failing_function="get_user",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = os.path.join(tmpdir, "model.py")
            with open(test_file, "w") as f:
                f.write("# Line 2\nuser.name = 'test'  # Line 3\n")
            healer.root_dir = tmpdir

            plan = healer.synthesize_hotfix(incident, blame)
            assert plan is not None
            assert plan.confidence_score >= 0.85
            assert "if" in plan.remediated_snippet.lower() or "is not none" in plan.remediated_snippet.lower()

    def test_healer_indexerror_patch_synthesis(self):
        """Should synthesize boundary check for IndexError."""
        healer = IncidentHealer()
        incident = IncidentPayload(
            incident_id="INC-IDX-001",
            service_name="test",
            error_type="IndexError",
            error_message="list index out of range",
            raw_stack_trace="IndexError: list index out of range",
        )
        blame = BlameContext(
            file_path="processor.py",
            line_number=2,
            culprit_commit_sha="abc123",
            author_name="test",
            commit_date="2024-01-01T00:00:00Z",
            commit_summary="Add processor",
            failing_function="process_items",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = os.path.join(tmpdir, "processor.py")
            with open(test_file, "w") as f:
                f.write("# Line 6\nitem = items[5]  # Line 7\n")
            healer.root_dir = tmpdir

            plan = healer.synthesize_hotfix(incident, blame)
            assert plan is not None
            assert plan.confidence_score >= 0.85
            assert "len(" in plan.remediated_snippet

    def test_healer_syntax_validation(self):
        """Should reject patches that produce invalid syntax."""
        healer = IncidentHealer()
        incident = IncidentPayload(
            incident_id="INC-SYN-001",
            service_name="test",
            error_type="KeyError",
            error_message="'x'",
            raw_stack_trace="KeyError: 'x'",
        )
        blame = BlameContext(
            file_path="bad.py",
            line_number=2,
            culprit_commit_sha="abc123",
            author_name="test",
            commit_date="2024-01-01T00:00:00Z",
            commit_summary="Bad",
            failing_function="bad",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = os.path.join(tmpdir, "bad.py")
            with open(test_file, "w") as f:
                f.write("x = data['x'  # Syntax error - missing bracket")
            healer.root_dir = tmpdir

            plan = healer.synthesize_hotfix(incident, blame)
            assert plan is None

    def test_stage_hotfix_branch_dry_run(self):
        """Should stage branch in dry-run mode without committing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            subprocess.run(["git", "init"], cwd=tmpdir, capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmpdir)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=tmpdir)

            test_file = os.path.join(tmpdir, "main.py")
            with open(test_file, "w") as f:
                f.write("def divide(a, b):\n    return a / b\n")
            subprocess.run(["git", "add", "main.py"], cwd=tmpdir)
            subprocess.run(["git", "commit", "-m", "Initial"], cwd=tmpdir)

            healer = IncidentHealer(root_dir=tmpdir)

            plan = HotfixPlan(
                incident_id="INC-DRY-001",
                target_file="main.py",
                line_number=2,
                root_cause_explanation="Test dry run",
                original_snippet="return a / b",
                remediated_snippet="return a / b if b else 0.0",
                patch_diff="@@ -1,2 +1,2 @@\n def divide(a, b):\n-    return a / b\n+    return a / b if b else 0.0",
                confidence_score=0.9,
                status=HotfixStatus.SIMULATED,
            )

            success = healer.stage_hotfix_branch(plan, create_branch=False)
            assert success is True

            with open(test_file, "r") as f:
                content = f.read()
            assert "if b else 0.0" in content

    def test_stage_hotfix_branch_with_git(self):
        """Should create git branch and commit when create_branch=True."""
        with tempfile.TemporaryDirectory() as tmpdir:
            subprocess.run(["git", "init"], cwd=tmpdir, capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmpdir)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=tmpdir)

            test_file = os.path.join(tmpdir, "main.py")
            with open(test_file, "w") as f:
                f.write("def divide(a, b):\n    return a / b\n")
            subprocess.run(["git", "add", "main.py"], cwd=tmpdir)
            subprocess.run(["git", "commit", "-m", "Initial"], cwd=tmpdir)

            healer = IncidentHealer(root_dir=tmpdir)

            plan = HotfixPlan(
                incident_id="INC-GIT-001",
                target_file="main.py",
                line_number=2,
                root_cause_explanation="Test git branch",
                original_snippet="return a / b",
                remediated_snippet="return a / b if b else 0.0",
                patch_diff="@@ -1,2 +1,2 @@\n def divide(a, b):\n-    return a / b\n+    return a / b if b else 0.0",
                confidence_score=0.9,
                status=HotfixStatus.SIMULATED,
            )

            success = healer.stage_hotfix_branch(plan, create_branch=True)
            assert success is True

            result = subprocess.run(["git", "branch"], cwd=tmpdir, capture_output=True, text=True)
            assert "hotfix/incident-inc-git-001" in result.stdout


class TestAutonomousHealingMesh:
    """Tests for end-to-end incident processing mesh."""

    def test_mesh_processes_incident_end_to_end(self):
        """Mesh should ingest, analyze blame, synthesize fix, and return result."""
        with tempfile.TemporaryDirectory() as tmpdir:
            subprocess.run(["git", "init"], cwd=tmpdir, capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=tmpdir)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=tmpdir)

            test_file = os.path.join(tmpdir, "service.py")
            with open(test_file, "w") as f:
                f.write("def get_user(id):\n    return users['user_123']\n")
            subprocess.run(["git", "add", "service.py"], cwd=tmpdir)
            subprocess.run(["git", "commit", "-m", "Add service"], cwd=tmpdir)

            mesh = AutonomousHealingMesh(root_dir=tmpdir)

            incident = IncidentPayload(
                incident_id="INC-MESH-001",
                service_name="user-service",
                error_type="KeyError",
                error_message="'user_123'",
                raw_stack_trace="Traceback (most recent call last):\n  File \"service.py\", line 2, in get_user\n    return users['user_123']\nKeyError: 'user_123'",
            )

            result = mesh.process_incident(incident=incident, auto_stage=False)
            assert result.incident_id == "INC-MESH-001"
            assert result.hotfix_plan is not None
            assert result.hotfix_plan["confidence_score"] >= 0.85
            assert result.hotfix_synthesized is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])