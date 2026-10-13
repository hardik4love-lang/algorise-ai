"""
AutoTest Sentinel: DevEx & Financial Impact Reporter
Generates executive summaries, GitHub Actions step summaries, and quantified
ROI / compute savings analyses.
"""

from typing import List
from .models import FlakinessReport, HealSuggestion, QuarantineManifest


class ReportGenerator:
    """
    Translates test triage and quarantine outcomes into quantified DevEx ROI metrics.
    """

    DEFAULT_HOURLY_DEV_COST = 160.0  # $160/hr fully loaded
    DEFAULT_RUNNER_COST_PER_MIN = 0.008  # $0.008/min standard Linux GitHub Actions runner
    AVG_PIPELINE_RUNTIME_MIN = 22.0  # Average CI pipeline duration in minutes

    def __init__(
        self,
        hourly_dev_cost: float = DEFAULT_HOURLY_DEV_COST,
        runner_cost_per_min: float = DEFAULT_RUNNER_COST_PER_MIN,
    ):
        self.hourly_dev_cost = hourly_dev_cost
        self.runner_cost_per_min = runner_cost_per_min

    def generate_markdown_summary(
        self,
        reports: List[FlakinessReport],
        quarantine_manifest: QuarantineManifest,
        heal_suggestions: List[HealSuggestion],
    ) -> str:
        """
        Creates a rich Markdown summary suitable for $GITHUB_STEP_SUMMARY
        or PR comments.
        """
        quarantined_count = len(quarantine_manifest.quarantined_tests)
        flaky_count = sum(1 for r in reports if r.category.value.startswith("FLAKY"))

        # Calculate estimated savings per month
        # Assume each quarantined flaky test prevents 12 unnecessary CI re-runs per month
        reruns_prevented = quarantined_count * 12
        compute_minutes_saved = reruns_prevented * self.AVG_PIPELINE_RUNTIME_MIN
        direct_compute_savings = compute_minutes_saved * self.runner_cost_per_min
        dev_hours_saved = reruns_prevented * (self.AVG_PIPELINE_RUNTIME_MIN / 60.0)
        dev_productivity_savings = dev_hours_saved * self.hourly_dev_cost
        total_monthly_savings = direct_compute_savings + dev_productivity_savings

        md = []
        md.append("# 🛡️ AutoTest Sentinel: DevEx & Test Flakiness Report\n")
        md.append(
            "> **Autonomous SRE Guardrail:** Continuous detection, quarantine, "
            "and AST remediation of non-deterministic CI failures.\n"
        )

        md.append("## 📊 Executive Summary Metrics\n")
        md.append("| Metric | Value | Impact |")
        md.append("| :--- | :--- | :--- |")
        md.append(f"| **Active Quarantined Tests** | `{quarantined_count}` | Unblocks critical PR merge path |")
        md.append(f"| **Identified Flaky Tests** | `{flaky_count}` | Statistical confidence $\\ge 0.75$ |")
        md.append(f"| **AST Healing Candidates** | `{len(heal_suggestions)}` | Actionable code patches ready |")
        md.append(f"| **Est. Monthly Runner Mins Saved** | `{compute_minutes_saved:,.0f} mins` | Direct GitHub Actions compute |")
        md.append(f"| **Est. Monthly Cost Savings** | `\\${total_monthly_savings:,.2f}` | Compute + Developer Wait Time |\n")

        if quarantine_manifest.quarantined_tests:
            md.append("## 🛑 Active Quarantined Test Registry\n")
            md.append("| Test ID | Flakiness Score | Root Cause Hypothesis | Quarantined At |")
            md.append("| :--- | :--- | :--- | :--- |")
            for tid, data in quarantine_manifest.quarantined_tests.items():
                score = data.get("flakiness_score", 0.0)
                cause = data.get("root_cause", "UNKNOWN")
                date = data.get("quarantined_at", "")[:10]
                md.append(f"| `{tid}` | **{score:.2f}** | `{cause}` | {date} |")
            md.append("")

        if heal_suggestions:
            md.append("## 🩹 AST Auto-Healing Suggestions\n")
            for idx, sugg in enumerate(heal_suggestions[:5], 1):
                md.append(f"### {idx}. `{sugg.test_id}`")
                md.append(f"- **Anti-Pattern:** `{sugg.anti_pattern}` (Line {sugg.line_number})")
                md.append(f"- **Remediation:** {sugg.remediation_description}")
                md.append("```diff")
                md.append(sugg.unified_diff or f"- {sugg.original_snippet}\n+ {sugg.suggested_snippet}")
                md.append("```\n")

        md.append("---")
        md.append("*Generated automatically by AutoTest Sentinel v1.0.0 (Revenue Orchestrator Platform)*")
        return "\n".join(md)
