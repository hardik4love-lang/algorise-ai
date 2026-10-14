"""
TraceRoot AI: Automated Incident Healer & Hotfix Synthesizer
Synthesizes defensive code patches for common unhandled production exceptions
and stages hotfix branches.
"""

from __future__ import annotations

import ast
import difflib
import os
import re
import subprocess
from typing import Optional

from .models import BlameContext, HotfixPlan, HotfixStatus, IncidentPayload


class IncidentHealer:
    """
    Synthesizes localized defensive patches and manages emergency hotfix git branches.
    """

    def __init__(self, root_dir: str = "."):
        self.root_dir = os.path.abspath(root_dir)

    def synthesize_hotfix(
        self, payload: IncidentPayload, blame_context: BlameContext
    ) -> Optional[HotfixPlan]:
        """Derives a defensive code patch targeting the culprit code line."""
        file_path = os.path.join(self.root_dir, blame_context.file_path)
        if not os.path.exists(file_path):
            return None

        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()

        target_idx = blame_context.line_number - 1
        if target_idx < 0 or target_idx >= len(lines):
            return None

        orig_line = lines[target_idx]
        indent = " " * (len(orig_line) - len(orig_line.lstrip()))
        remediated_line = None
        explanation = ""
        confidence = 0.85

        err_type = payload.error_type

        # 1. KeyError Defense: data['key'] -> data.get('key')
        if err_type == "KeyError":
            match = re.search(r'\[["\'](?P<key>[^"\']+)["\']\]', orig_line)
            if match:
                key_name = match.group("key")
                remediated_line = re.sub(
                    r'\[(["\'])' + re.escape(key_name) + r'\1\]',
                    f'.get("{key_name}", None)',
                    orig_line,
                )
                explanation = f"Protected missing dictionary key '{key_name}' using defensive .get() fallback."
                confidence = 0.95

        # 2. ZeroDivisionError Defense: x / y -> x / y if y else 0.0
        elif err_type == "ZeroDivisionError":
            div_match = re.search(r'(?P<num>[A-Za-z0-9_().]+)\s*/\s*(?P<den>[A-Za-z0-9_().]+)', orig_line)
            if div_match:
                den = div_match.group("den")
                num = div_match.group("num")
                replacement = f"({num} / {den} if {den} else 0.0)"
                remediated_line = orig_line.replace(f"{num} / {den}", replacement)
                explanation = f"Added zero-denominator guard to prevent ZeroDivisionError on variable '{den}'."
                confidence = 0.92

        # 3. AttributeError (NoneType object): obj.attr -> obj.attr if obj is not None else None
        elif err_type == "AttributeError":
            attr_match = re.search(r'(?P<obj>[A-Za-z0-9_]+)\.(?P<attr>[A-Za-z0-9_]+)', orig_line.strip())
            if attr_match:
                obj = attr_match.group("obj")
                attr = attr_match.group("attr")
                explanation = f"Guarded potential NoneType dereference on '{obj}' before accessing '.{attr}'."
                remediated_line = f"{indent}if {obj} is not None:\n    {orig_line}"
                confidence = 0.88

        # 4. IndexError: items[i] -> items[i] if len(items) > i else None
        elif err_type == "IndexError":
            idx_match = re.search(r'(?P<arr>[A-Za-z0-9_]+)\[(?P<idx>\d+)\]', orig_line)
            if idx_match:
                arr = idx_match.group("arr")
                idx_val = int(idx_match.group("idx"))
                remediated_line = orig_line.replace(
                    f"{arr}[{idx_val}]",
                    f"({arr}[{idx_val}] if len({arr}) > {idx_val} else None)",
                )
                explanation = f"Added boundary check for array '{arr}' index {idx_val}."
                confidence = 0.90

        if not remediated_line or remediated_line == orig_line:
            return None

        # Verify new file syntax parses
        candidate_lines = lines[:]
        candidate_lines[target_idx] = remediated_line
        new_source = "".join(candidate_lines)

        try:
            ast.parse(new_source)
        except SyntaxError:
            return None

        diff = difflib.unified_diff(
            lines,
            candidate_lines,
            fromfile=f"a/{blame_context.file_path}",
            tofile=f"b/{blame_context.file_path}",
        )

        return HotfixPlan(
            incident_id=payload.incident_id,
            target_file=blame_context.file_path,
            line_number=blame_context.line_number,
            root_cause_explanation=explanation,
            original_snippet=orig_line.strip(),
            remediated_snippet=remediated_line.strip(),
            patch_diff="".join(diff),
            confidence_score=confidence,
            status=HotfixStatus.SIMULATED,
        )

    def stage_hotfix_branch(
        self, plan: HotfixPlan, create_branch: bool = True
    ) -> bool:
        """Applies patch to disk and optionally cuts a git branch."""
        file_path = os.path.join(self.root_dir, plan.target_file)
        if not os.path.exists(file_path):
            return False

        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        target_idx = plan.line_number - 1
        lines[target_idx] = plan.remediated_snippet + "\n"

        if create_branch:
            branch_name = f"hotfix/incident-{plan.incident_id.lower()}"
            try:
                subprocess.run(["git", "checkout", "-b", branch_name], cwd=self.root_dir, check=True, capture_output=True)
                with open(file_path, "w", encoding="utf-8") as f:
                    f.writelines(lines)
                subprocess.run(["git", "add", plan.target_file], cwd=self.root_dir, check=True, capture_output=True)
                msg = f"fix(hotfix): autonomous remediation for {plan.incident_id}\n\n{plan.root_cause_explanation}"
                subprocess.run(["git", "commit", "-m", msg], cwd=self.root_dir, check=True, capture_output=True)
                plan.branch_name = branch_name
                plan.status = HotfixStatus.BRANCH_STAGED
                # Return back to master
                subprocess.run(["git", "checkout", "master"], cwd=self.root_dir, check=True, capture_output=True)
                return True
            except Exception:
                subprocess.run(["git", "checkout", "master"], cwd=self.root_dir, capture_output=True)
                return False
        else:
            with open(file_path, "w", encoding="utf-8") as f:
                f.writelines(lines)
            plan.status = HotfixStatus.VERIFIED
            return True
