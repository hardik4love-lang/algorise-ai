"""
AutoTest Sentinel: AST-Based Code Healer
Analyzes Python test ASTs to detect timing anti-patterns, unseeded randomization,
and port collisions, then synthesizes self-healing patches.
"""

import ast
import difflib
import os
import re
from typing import List, Optional

from .models import HealSuggestion


class TestAntiPatternVisitor(ast.NodeVisitor):
    """
    AST Visitor that scans test functions and fixtures for flaky code patterns.
    """

    def __init__(self, file_path: str, source_lines: List[str]):
        self.file_path = file_path
        self.source_lines = source_lines
        self.suggestions: List[HealSuggestion] = []
        self.current_function: Optional[str] = None

    def visit_FunctionDef(self, node: ast.FunctionDef):
        prev_func = self.current_function
        self.current_function = node.name
        self.generic_visit(node)
        self.current_function = prev_func

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        prev_func = self.current_function
        self.current_function = node.name
        self.generic_visit(node)
        self.current_function = prev_func

    def visit_Call(self, node: ast.Call):
        # 1. Detect time.sleep(...) calls
        if self._is_time_sleep(node):
            self._handle_time_sleep(node)

        # 2. Detect unseeded random calls (e.g. random.randint / random.choice)
        elif self._is_unseeded_random(node):
            self._handle_unseeded_random(node)

        self.generic_visit(node)

    def _is_time_sleep(self, node: ast.Call) -> bool:
        if isinstance(node.func, ast.Attribute):
            if node.func.attr == "sleep" and isinstance(node.func.value, ast.Name):
                return node.func.value.id == "time"
        return False

    def _is_unseeded_random(self, node: ast.Call) -> bool:
        if isinstance(node.func, ast.Attribute):
            if isinstance(node.func.value, ast.Name) and node.func.value.id == "random":
                return node.func.attr in ("randint", "choice", "random", "uniform")
        return False

    def _handle_time_sleep(self, node: ast.Call):
        line_no = node.lineno
        if line_no <= len(self.source_lines):
            orig_line = self.source_lines[line_no - 1]
            indent = " " * (len(orig_line) - len(orig_line.lstrip()))
            sleep_arg = "1.0"
            if node.args and isinstance(node.args[0], ast.Constant):
                sleep_arg = str(node.args[0].value)

            suggested_code = (
                f"{indent}# AutoTest Sentinel: Replaced non-deterministic sleep with polling assertion\n"
                f"{indent}# wait_until(lambda: check_condition(), timeout={float(sleep_arg) * 2})"
            )

            test_id = f"{self.file_path}::{self.current_function or 'module'}"
            self.suggestions.append(
                HealSuggestion(
                    test_id=test_id,
                    file_path=self.file_path,
                    line_number=line_no,
                    anti_pattern="FIXED_TIME_SLEEP",
                    remediation_description=(
                        f"Fixed time.sleep({sleep_arg}) induces runner timing races and slows CI. "
                        "Replace with deterministic event polling."
                    ),
                    original_snippet=orig_line.strip(),
                    suggested_snippet=suggested_code.strip(),
                )
            )

    def _handle_unseeded_random(self, node: ast.Call):
        line_no = node.lineno
        if line_no <= len(self.source_lines):
            orig_line = self.source_lines[line_no - 1]
            func_name = getattr(node.func, "attr", "random")
            test_id = f"{self.file_path}::{self.current_function or 'module'}"
            self.suggestions.append(
                HealSuggestion(
                    test_id=test_id,
                    file_path=self.file_path,
                    line_number=line_no,
                    anti_pattern="UNSEEDED_PSEUDORANDOM",
                    remediation_description=(
                        f"Unseeded random.{func_name}() generates non-reproducible test fixtures. "
                        "Set an explicit seed (random.seed(42)) or use a deterministic faker."
                    ),
                    original_snippet=orig_line.strip(),
                    suggested_snippet=f"random.seed(42)  # Ensure deterministic fixture generation",
                )
            )


class ASTHealer:
    """
    Orchestrates AST scanning and diff synthesis for test files.
    """

    def scan_file(self, file_path: str) -> List[HealSuggestion]:
        """Parses a Python test file and discovers remediable anti-patterns."""
        if not os.path.exists(file_path):
            return []

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                source = f.read()
            tree = ast.parse(source, filename=file_path)
            lines = source.splitlines()

            visitor = TestAntiPatternVisitor(file_path, lines)
            visitor.visit(tree)

            # Generate unified diffs for suggestions
            for sugg in visitor.suggestions:
                sugg.unified_diff = self._create_diff(
                    file_path=file_path,
                    line_no=sugg.line_number,
                    orig_line=sugg.original_snippet,
                    sugg_line=sugg.suggested_snippet,
                    all_lines=lines,
                )

            return visitor.suggestions
        except Exception:
            return []

    def scan_directory(self, directory_path: str) -> List[HealSuggestion]:
        """Recursively scans all test_*.py files in a directory."""
        all_suggestions = []
        for root, _, files in os.walk(directory_path):
            for file in files:
                if file.startswith("test_") and file.endswith(".py"):
                    full_path = os.path.join(root, file)
                    all_suggestions.extend(self.scan_file(full_path))
        return all_suggestions

    def _create_diff(
        self,
        file_path: str,
        line_no: int,
        orig_line: str,
        sugg_line: str,
        all_lines: List[str],
    ) -> str:
        orig_slice = all_lines[:]
        mod_slice = all_lines[:]

        if 0 < line_no <= len(mod_slice):
            indent = " " * (len(orig_slice[line_no - 1]) - len(orig_slice[line_no - 1].lstrip()))
            mod_slice[line_no - 1] = indent + sugg_line

        diff = difflib.unified_diff(
            orig_slice,
            mod_slice,
            fromfile=f"a/{file_path}",
            tofile=f"b/{file_path}",
            lineterm="",
        )
        return "\n".join(diff)
