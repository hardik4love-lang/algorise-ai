"""
Revenue Engine: Data Models
Defines representations for bounty opportunities, gate evaluations, and audit ledgers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional


class OpportunityStatus(str, Enum):
    APPROVED_FOR_TRIAGE = "APPROVED_FOR_TRIAGE"
    REJECTED_GATE_FAILURE = "REJECTED_GATE_FAILURE"
    IN_PROGRESS = "IN_PROGRESS"
    CLAIMED = "CLAIMED"


@dataclass
class BountyOpportunity:
    task_id: str
    title: str
    repository: str
    url: str
    gross_payout_usd: float
    urgency_score: float  # Range: [0.0, 1.0]
    risk_score: float     # Range: [0.0, 1.0]
    compute_cost_usd: float
    confidence_score: float  # Range: [0.0, 1.0]
    prioritization_score: float
    expected_net_revenue: float
    gates_passed: List[str] = field(default_factory=list)
    status: OpportunityStatus = OpportunityStatus.APPROVED_FOR_TRIAGE
    rejection_reasons: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class EvaluationLedger:
    ledger_id: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    agent: str = "RevenueOrchestratorAgent"
    version: str = "1.0.0"
    policy: str = "zero_cost_enforced"
    total_evaluated: int = 0
    opportunities: List[BountyOpportunity] = field(default_factory=list)
