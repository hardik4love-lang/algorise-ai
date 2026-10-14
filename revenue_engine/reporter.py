"""
Revenue Engine: Executive Opportunity & Ledger Reporter
Renders structured Markdown summaries of autonomous revenue opportunity evaluations.
"""

from __future__ import annotations

from typing import List
from .models import EvaluationLedger, OpportunityStatus


class RevenueReporter:
    """
    Renders audit summaries and economic impact metrics for the Revenue Orchestrator.
    """

    def generate_markdown_report(self, ledger: EvaluationLedger) -> str:
        """Constructs an executive revenue pipeline report."""
        approved = [o for o in ledger.opportunities if o.status == OpportunityStatus.APPROVED_FOR_TRIAGE]
        total_gross = sum(o.gross_payout_usd for o in approved)
        total_enr = sum(o.expected_net_revenue for o in approved)

        md = []
        md.append("# 💰 Revenue Orchestrator: Autonomous Opportunity Ledger\n")
        md.append(f"> **Audit Run:** `{ledger.ledger_id[:8]}` — **Policy:** `{ledger.policy}` — **Agent:** `{ledger.agent}`\n")

        md.append("## 📊 Pipeline Summary Metrics\n")
        md.append("| Metric | Value | Details |")
        md.append("| :--- | :--- | :--- |")
        md.append(f"| **Opportunities Evaluated** | `{ledger.total_evaluated}` | Screened through 7 Execution Gates |")
        md.append(f"| **Approved for Triage** | `{len(approved)}` | Confidence $\\ge 0.90$, Zero Cost |")
        md.append(f"| **Pipeline Gross Value** | `\\${total_gross:,.2f} USD` | Staged bounty target pool |")
        md.append(f"| **Expected Net Revenue (ENR)** | `\\${total_enr:,.2f} USD` | Risk & confidence discounted |")
        md.append("")

        if ledger.opportunities:
            md.append("## 🎯 Evaluated Opportunities Registry\n")
            md.append("| Task ID | Title | Repository | ENR ($) | Priority Score | Status |")
            md.append("| :--- | :--- | :--- | :---: | :---: | :---: |")
            for opp in ledger.opportunities:
                status_icon = "✅ APPROVED" if opp.status == OpportunityStatus.APPROVED_FOR_TRIAGE else "❌ REJECTED"
                md.append(
                    f"| [{opp.task_id}]({opp.url}) | `{opp.title[:35]}...` | `{opp.repository}` | **\\${opp.expected_net_revenue:.2f}** | `{opp.prioritization_score:.2f}` | {status_icon} |"
                )
            md.append("")

        md.append("---")
        md.append("*Generated autonomously by Revenue Orchestrator v1.0.0 (Algorise Platform)*")
        return "\n".join(md)
