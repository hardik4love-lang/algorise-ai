"""
ModernizeAI: Autonomous Breaking Change Migration & AST Codemod Engine
Part of the Algorise DevEx & Autonomous Systems Platform.
"""

from __future__ import annotations

from .agent import ModernizeAgent
from .models import MigrationPlan, MigrationRule, RuleType, TransformResult
from .rule_engine import CodemodRuleEngine
from .transformer import ASTCodeTransformer

__version__ = "1.0.0"

__all__ = [
    "ModernizeAgent",
    "CodemodRuleEngine",
    "ASTCodeTransformer",
    "MigrationPlan",
    "MigrationRule",
    "TransformResult",
    "RuleType",
]
