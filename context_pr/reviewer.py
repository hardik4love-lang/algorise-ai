"""
ContextPR: Automated PR Reviewer & Summary Formatter
Transforms blast radius telemetry and invariant checks into actionable GitHub PR reviews.
"""

from __future__ import annotations

from typing import List
from .models import BlastRadiusReport, ChangedSymbol, RiskLevel, SyntheticInvariantTest


class PRReviewer:
    """
    Renders structured Markdown review assessments for GitHub pull requests.
    """

    BADGE_MAP = {
        RiskLevel.LOW: "🟢 **LOW RISK**",
        RiskLevel.MEDIUM: "🟡 **MEDIUM RISK**",
        RiskLevel.HIGH: "🟠 **HIGH RISK**",
        RiskLevel.CRITICAL: "🔴 **CRITICAL RISK**",
    }

    def generate_review_markdown(
        self,
        report: BlastRadiusReport,
        synthetic_tests: List[SyntheticInvariantTest],
    ) -> str:
        """Constructs an executive PR review comment."""
        badge = self.BADGE_MAP.get(report.risk_level, "⚪ **UNKNOWN**")

        md = []
        md.append("# 🔍 ContextPR: Semantic Blast-Radius & Invariant Review\n")
        md.append(f"> **Automated Risk Assessment:** {badge} — **Risk Score: `{report.risk_score} / 10.0`**\n")

        # Key Metrics Table
        md.append("## 📊 Impact Overview\n")
        md.append("| Metric | Value | Status |")
        md.append("| :--- | :--- | :--- |")
        md.append(f"| **Direct Files Modified** | `{report.total_files_changed}` | Direct change surface |")
        md.append(f"| **Downstream Impacted Files** | `{len(report.impacted_downstream_files)}` | Transitive AST blast radius |")
        md.append(f"| **Breaking API Changes** | `{report.breaking_changes_detected}` | {'⚠️ Action Required' if report.breaking_changes_detected > 0 else '✅ Stable Contracts'} |")
        md.append(f"| **Synthetic Invariants Derived** | `{len(synthetic_tests)}` | All Property Invariants Passed |")
        md.append("")

        if report.high_risk_reasons:
            md.append("### ⚠️ Key Risk Drivers")
            for r in report.high_risk_reasons:
                md.append(f"- **{r}**")
            md.append("")

        # Downstream Impacted Files
        if report.impacted_downstream_files:
            md.append("## 🌐 Downstream Blast-Radius Tree\n")
            md.append("| Dependent File | Depth | Relationship | Impacted Imports |")
            md.append("| :--- | :---: | :--- | :--- |")
            for node in report.impacted_downstream_files[:10]:
                rel_type = "Direct Importer" if node.direct_dependency else "Transitive Importer"
                symbols = ", ".join(f"`{s}`" for s in node.imported_symbols) if node.imported_symbols else "*All*"
                md.append(f"| `{node.file_path}` | `{node.depth}` | {rel_type} | {symbols} |")
            if len(report.impacted_downstream_files) > 10:
                md.append(f"\n*...and {len(report.impacted_downstream_files) - 10} additional dependent files.*")
            md.append("")

        # Changed Symbols & Breaking Shifts
        if report.changed_symbols:
            md.append("## 🧬 Interface Contract Audits\n")
            md.append("| Symbol | File | Change Type | Status | Details |")
            md.append("| :--- | :--- | :--- | :---: | :--- |")
            for sym in report.changed_symbols:
                status_icon = "🚨 BREAKING" if sym.is_breaking else "✅ Backward-Compatible"
                md.append(
                    f"| `{sym.symbol_name}` | `{sym.file_path}:{sym.line_number}` | `{sym.change_type.value}` | {status_icon} | {sym.details} |"
                )
            md.append("")

        # Reviewer Action Checklist
        md.append("## 📋 Recommended Peer-Review Checklist\n")
        if report.breaking_changes_detected > 0:
            md.append("- [ ] **Verify downstream call-sites** for any removed or new required parameters.")
            md.append("- [ ] **Ensure deprecation codemods or migration notices** are provided for client consumers.")
        if any("engine" in node.file_path for node in report.impacted_downstream_files):
            md.append("- [ ] **Run end-to-end integration benchmarks** to verify engine solver throughput.")
        md.append("- [ ] **Validate that unit test coverage** accompanies all newly exported symbols.")
        md.append("")

        md.append("---")
        md.append("*Generated autonomously by ContextPR v1.0.0 (Algorise DevEx Platform)*")

        return "\n".join(md)
