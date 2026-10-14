"""
Unit and Integration Tests for ContextPR
Validates AST invariant extraction, downstream blast radius calculation,
property test synthesis, and PR review markdown generation.
"""

import os
import tempfile
import pytest

from context_pr.blast_radius import BlastRadiusAnalyzer
from context_pr.invariants import InvariantExtractor
from context_pr.models import ChangeType, RiskLevel
from context_pr.reviewer import PRReviewer
from context_pr.synthesizer import PropertyTestSynthesizer


def test_invariant_extractor_backward_compatible():
    extractor = InvariantExtractor()
    old_code = """
def compute_metrics(data: list) -> dict:
    return {"count": len(data)}
"""
    new_code = """
def compute_metrics(data: list, normalize: bool = False) -> dict:
    return {"count": len(data), "normalized": normalize}
"""
    changes = extractor.analyze_diff("analytics.py", old_code, new_code)
    assert len(changes) == 1
    sym = changes[0]
    assert sym.symbol_name == "compute_metrics"
    assert sym.is_breaking is False
    assert sym.change_type == ChangeType.FUNCTION_MODIFIED


def test_invariant_extractor_breaking_signature():
    extractor = InvariantExtractor()
    old_code = """
def transfer_funds(account_id: str, amount: float):
    pass
"""
    new_code = """
def transfer_funds(account_id: str, amount: float, auth_token: str):
    pass
"""
    changes = extractor.analyze_diff("banking.py", old_code, new_code)
    assert len(changes) == 1
    sym = changes[0]
    assert sym.is_breaking is True
    assert sym.change_type == ChangeType.SIGNATURE_BREAK
    assert "New required argument" in sym.details


def test_invariant_extractor_deleted_symbol():
    extractor = InvariantExtractor()
    old_code = """
def legacy_helper():
    pass

def active_service():
    pass
"""
    new_code = """
def active_service():
    pass
"""
    changes = extractor.analyze_diff("service.py", old_code, new_code)
    assert len(changes) == 1
    sym = changes[0]
    assert sym.symbol_name == "legacy_helper"
    assert sym.is_breaking is True
    assert sym.change_type == ChangeType.DELETED_SYMBOL


def test_blast_radius_dependency_chain():
    with tempfile.TemporaryDirectory() as tmpdir:
        # File A: core module
        file_a = os.path.join(tmpdir, "core.py")
        with open(file_a, "w") as f:
            f.write("def core_utility():\n    return 42\n")

        # File B: direct importer of A
        file_b = os.path.join(tmpdir, "service.py")
        with open(file_b, "w") as f:
            f.write("from core import core_utility\ndef run_service():\n    return core_utility()\n")

        # File C: importer of B
        file_c = os.path.join(tmpdir, "app.py")
        with open(file_c, "w") as f:
            f.write("from service import run_service\ndef main():\n    run_service()\n")

        analyzer = BlastRadiusAnalyzer(root_dir=tmpdir)
        report = analyzer.compute_blast_radius(changed_files=["core.py"])

        impacted_paths = [node.file_path for node in report.impacted_downstream_files]
        assert "service.py" in impacted_paths
        assert "app.py" in impacted_paths

        # Check depth
        service_node = next(n for n in report.impacted_downstream_files if n.file_path == "service.py")
        app_node = next(n for n in report.impacted_downstream_files if n.file_path == "app.py")
        assert service_node.depth == 1
        assert service_node.direct_dependency is True
        assert app_node.depth == 2


def test_property_synthesizer():
    extractor = InvariantExtractor()
    old_code = "def process(x: int): pass"
    new_code = "def process(x: int, y: int = 10): pass"
    changes = extractor.analyze_diff("calc.py", old_code, new_code)

    synthesizer = PropertyTestSynthesizer()
    tests = synthesizer.synthesize_tests_for_symbol(changes[0])
    assert len(tests) >= 1
    assert "test_invariant_process" in tests[0].test_code


def test_pr_reviewer_markdown():
    analyzer = BlastRadiusAnalyzer(root_dir=".")
    report = analyzer.compute_blast_radius(changed_files=["test_api.py"])
    reviewer = PRReviewer()
    markdown = reviewer.generate_review_markdown(report, synthetic_tests=[])

    assert "# 🔍 ContextPR: Semantic Blast-Radius & Invariant Review" in markdown
    assert "Direct Files Modified" in markdown
    assert "Recommended Peer-Review Checklist" in markdown
