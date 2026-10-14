"""
Revenue Engine: Autonomous Opportunity Valuation & Execution Gate System
Part of the Algorise DevEx & Autonomous Systems Platform.
"""

from __future__ import annotations

from .models import BountyOpportunity, EvaluationLedger, OpportunityStatus
from .reporter import RevenueReporter
from .scanner import OpportunityScanner
from .scorer import RevenueScorer

__version__ = "1.0.0"

__all__ = [
    "OpportunityScanner",
    "RevenueScorer",
    "RevenueReporter",
    "BountyOpportunity",
    "EvaluationLedger",
    "OpportunityStatus",
]
