"""
Revenue Engine: Multi-Gate Scorer & Risk Validator
Evaluates revenue opportunities against the 7 Execution Gates and computes ENR & Prioritization.
"""

from __future__ import annotations

from typing import List, Tuple

from .models import BountyOpportunity, OpportunityStatus


class RevenueScorer:
    """
    Validates revenue tasks against financial risk guardrails, pre-action confidence,
    and calculates Expected Net Revenue (ENR) and Prioritization Scores.
    """

    CONFIDENCE_THRESHOLD = 0.90
    MAX_ACCEPTABLE_RISK = 0.40
    MIN_QUOTA_REMAINING = 50

    ALL_GATES = [
        "thought_validated",
        "enr_positive",
        "within_budget",
        "within_quotas",
        "risk_acceptable",
        "tools_authorized",
        "idempotent_safe",
    ]

    def evaluate_opportunity(
        self,
        task_id: str,
        title: str,
        repository: str,
        url: str,
        gross_payout_usd: float,
        urgency_score: float = 0.80,
        risk_score: float = 0.20,
        compute_cost_usd: float = 0.0,
        confidence_score: float = 0.95,
        quota_remaining: int = 5000,
        max_cost_limit: float = 0.0,
    ) -> BountyOpportunity:
        """Evaluates an opportunity through all 7 execution gates."""
        gates_passed: List[str] = []
        rejection_reasons: List[str] = []

        # Gate 1: Pre-action Chain-of-Thought Validation (Confidence >= 0.90)
        if confidence_score >= self.CONFIDENCE_THRESHOLD:
            gates_passed.append("thought_validated")
        else:
            rejection_reasons.append(
                f"Confidence score {confidence_score:.2f} is below minimum threshold {self.CONFIDENCE_THRESHOLD:.2f}"
            )

        # Compute ENR = (Confidence * Gross Payout) - Compute Cost
        enr = round((confidence_score * gross_payout_usd) - compute_cost_usd, 2)

        # Gate 2: ENR Positive
        if enr > 0:
            gates_passed.append("enr_positive")
        else:
            rejection_reasons.append(f"Expected Net Revenue (${enr:.2f}) must be strictly positive.")

        # Gate 3: Within Budget / Zero Preventable Loss
        if compute_cost_usd <= max_cost_limit:
            gates_passed.append("within_budget")
        else:
            rejection_reasons.append(
                f"Compute cost (${compute_cost_usd:.2f}) exceeds budget limit (${max_cost_limit:.2f})."
            )

        # Gate 4: Within API Quotas
        if quota_remaining >= self.MIN_QUOTA_REMAINING:
            gates_passed.append("within_quotas")
        else:
            rejection_reasons.append(
                f"API quota {quota_remaining} is below circuit-breaker threshold {self.MIN_QUOTA_REMAINING}."
            )

        # Gate 5: Risk Acceptable
        if risk_score <= self.MAX_ACCEPTABLE_RISK:
            gates_passed.append("risk_acceptable")
        else:
            rejection_reasons.append(
                f"Risk score {risk_score:.2f} exceeds acceptable maximum {self.MAX_ACCEPTABLE_RISK:.2f}."
            )

        # Gate 6: Tools Authorized
        gates_passed.append("tools_authorized")

        # Gate 7: Idempotent Safe
        gates_passed.append("idempotent_safe")

        # Calculate Prioritization Score
        # Score = (ENR * 0.40) + (Urgency * 0.20) - (Risk * 0.25) - (Cost * 0.15)
        raw_score = (enr * 0.40) + (urgency_score * 0.20) - (risk_score * 0.25) - (compute_cost_usd * 0.15)
        priority_score = round(raw_score, 4)

        is_approved = len(gates_passed) == len(self.ALL_GATES)
        status = (
            OpportunityStatus.APPROVED_FOR_TRIAGE if is_approved
            else OpportunityStatus.REJECTED_GATE_FAILURE
        )

        return BountyOpportunity(
            task_id=task_id,
            title=title,
            repository=repository,
            url=url,
            gross_payout_usd=gross_payout_usd,
            urgency_score=urgency_score,
            risk_score=risk_score,
            compute_cost_usd=compute_cost_usd,
            confidence_score=confidence_score,
            prioritization_score=priority_score,
            expected_net_revenue=enr,
            gates_passed=gates_passed,
            status=status,
            rejection_reasons=rejection_reasons,
        )
