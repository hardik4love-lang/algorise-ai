"""
ModernizeAI: Data Models
Defines representations for AST migration rules, migration plans, and transformation results.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


class RuleType(str, Enum):
    RENAME_FUNCTION = "RENAME_FUNCTION"
    REPLACE_IMPORT = "REPLACE_IMPORT"
    RENAME_METHOD_CALL = "RENAME_METHOD_CALL"
    REFACTOR_DECORATOR = "REFACTOR_DECORATOR"
    REPLACE_CALL_WITH_EXPR = "REPLACE_CALL_WITH_EXPR"


@dataclass
class MigrationRule:
    rule_id: str
    package_name: str
    target_version: str
    rule_type: RuleType
    source_symbol: str
    target_symbol: str
    description: str
    old_module: Optional[str] = None
    new_module: Optional[str] = None
    is_breaking: bool = True


@dataclass
class MigrationPlan:
    package_name: str
    from_version: str
    to_version: str
    rules: List[MigrationRule] = field(default_factory=list)
    estimated_callsites: int = 0


@dataclass
class TransformResult:
    file_path: str
    transformations_applied: int
    modified_code: str
    original_code: str
    unified_diff: Optional[str] = None
    syntax_valid: bool = True
    error_message: Optional[str] = None
