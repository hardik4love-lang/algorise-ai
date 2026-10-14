"""
ContextPR: Data Models
Defines core representations for blast radius analysis, contract invariants, and PR reviews.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ChangeType(str, Enum):
    FUNCTION_MODIFIED = "FUNCTION_MODIFIED"
    SIGNATURE_BREAK = "SIGNATURE_BREAK"
    TYPE_ANNOTATION_CHANGED = "TYPE_ANNOTATION_CHANGED"
    CLASS_MODIFIED = "CLASS_MODIFIED"
    NEW_SYMBOL = "NEW_SYMBOL"
    DELETED_SYMBOL = "DELETED_SYMBOL"


@dataclass
class ChangedSymbol:
    symbol_name: str
    file_path: str
    change_type: ChangeType
    line_number: int
    old_signature: Optional[str] = None
    new_signature: Optional[str] = None
    is_breaking: bool = False
    details: str = ""


@dataclass
class BlastRadiusNode:
    file_path: str
    direct_dependency: bool
    imported_symbols: List[str] = field(default_factory=list)
    depth: int = 1


@dataclass
class BlastRadiusReport:
    base_ref: str
    head_ref: str
    risk_level: RiskLevel
    risk_score: float  # Range: 0.0 - 10.0
    total_files_changed: int
    impacted_downstream_files: List[BlastRadiusNode] = field(default_factory=list)
    changed_symbols: List[ChangedSymbol] = field(default_factory=list)
    breaking_changes_detected: int = 0
    high_risk_reasons: List[str] = field(default_factory=list)


@dataclass
class SyntheticInvariantTest:
    target_function: str
    file_path: str
    test_code: str
    property_description: str
    passed: bool = False
    error: Optional[str] = None
