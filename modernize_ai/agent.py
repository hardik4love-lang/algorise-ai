"""
ModernizeAI: Autonomous Migration Agent
Coordinates repository-wide code scanning, transformation application, and verification reporting.
"""

from __future__ import annotations

import os
from typing import List, Tuple

from .models import MigrationPlan, TransformResult
from .transformer import ASTCodeTransformer


class ModernizeAgent:
    """
    Autonomous agent that executes SDK upgrades and refactors deprecated call-sites.
    """

    def __init__(self, root_dir: str = "."):
        self.root_dir = os.path.abspath(root_dir)
        self.transformer = ASTCodeTransformer()

    def execute_plan(
        self, plan: MigrationPlan, write: bool = False
    ) -> List[TransformResult]:
        """Runs the migration plan across all Python files in the repository."""
        results: List[TransformResult] = []

        for root, _, files in os.walk(self.root_dir):
            if any(p in root for p in [".git", ".pytest_cache", "node_modules", "dist", "build", "venv"]):
                continue
            for file in files:
                if file.endswith(".py"):
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, self.root_dir).replace("\\", "/")

                    try:
                        with open(full_path, "r", encoding="utf-8", errors="ignore") as fp:
                            source = fp.read()
                    except Exception:
                        continue

                    res = self.transformer.transform_code(rel_path, source, plan.rules)
                    if res.transformations_applied > 0:
                        results.append(res)
                        if write and res.syntax_valid:
                            with open(full_path, "w", encoding="utf-8") as fp:
                                fp.write(res.modified_code + "\n")

        return results

    def generate_markdown_report(
        self, plan: MigrationPlan, results: List[TransformResult], write_mode: bool
    ) -> str:
        """Generates an executive-grade Markdown summary of modernization transforms."""
        total_transforms = sum(r.transformations_applied for r in results)
        files_modified = len(results)
        syntax_ok = all(r.syntax_valid for r in results)

        md = []
        md.append("# 🚀 ModernizeAI: Autonomous SDK Migration Report\n")
        mode_str = "Applied & Written to Disk" if write_mode else "Dry-Run Simulation (Preview Only)"
        md.append(f"> **Target Migration:** `{plan.package_name}` ({plan.from_version} $\\to$ {plan.to_version}) — **Mode:** `{mode_str}`\n")

        md.append("## 📊 Modernization Metrics\n")
        md.append("| Metric | Value | Status |")
        md.append("| :--- | :--- | :--- |")
        md.append(f"| **Files Refactored** | `{files_modified}` | AST transforms applied |")
        md.append(f"| **Call-Sites / Imports Rewritten** | `{total_transforms}` | Zero manual effort |")
        md.append(f"| **Syntax Verification Rate** | `{'100% Passed' if syntax_ok else 'Syntax Error Flagged'}` | {'✅ Complete' if syntax_ok else '⚠️ Needs Attention'} |")
        md.append(f"| **Active Rules Evaluated** | `{len(plan.rules)}` | Semantic pattern matching |")
        md.append("")

        if results:
            md.append("## 📝 Refactored Files Summary\n")
            md.append("| File Path | Transforms Count | Status | Diff Preview |")
            md.append("| :--- | :---: | :---: | :--- |")
            for r in results:
                status_icon = "✅ Clean" if r.syntax_valid else "❌ Error"
                preview = "Available" if r.unified_diff else "No Diff"
                md.append(f"| `{r.file_path}` | `{r.transformations_applied}` | {status_icon} | {preview} |")
            md.append("")

            md.append("## 🔍 Sample AST Unified Diffs\n")
            for r in results[:3]:
                if r.unified_diff:
                    md.append(f"### `{r.file_path}`")
                    md.append("```diff")
                    md.append(r.unified_diff)
                    md.append("```\n")

        md.append("---")
        md.append("*Generated autonomously by ModernizeAI v1.0.0 (Algorise DevEx Platform)*")
        return "\n".join(md)
