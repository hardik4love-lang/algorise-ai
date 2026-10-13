"""
AutoTest Sentinel: Data Models
Defines core representations for test executions, flakiness classifications, and repair suggestions.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional


class TestStatus(str, Enum):
    __test__ = False
    PASSED = "PASSED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class FlakeCategory(str, Enum):
    DETERMINISTIC_PASS = "DETERMINISTIC_PASS"
    DETERMINISTIC_FAIL = "DETERMINISTIC_FAIL"
    FLAKY_HIGH = "FLAKY_HIGH"
    FLAKY_MEDIUM = "FLAKY_MEDIUM"
    LOW_CONFIDENCE = "LOW_CONFIDENCE"


class RootCauseHypothesis(str, Enum):
    TIMING_RACE = "TIMING_RACE"
    SHARED_STATE = "SHARED_STATE"
    NETWORK_IO = "NETWORK_IO"
    ORDER_DEPENDENT = "ORDER_DEPENDENT"
    ENVIRONMENT_COLLISION = "ENVIRONMENT_COLLISION"
    UNKNOWN = "UNKNOWN"


@dataclass
class TestExecutionRecord:
    __test__ = False
    test_id: str
    file_path: str
    duration_seconds: float
    status: TestStatus
    error_message: Optional[str] = None
    stack_trace: Optional[str] = None
    commit_sha: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class FlakinessReport:
    test_id: str
    file_path: str
    flakiness_score: float  # Range: [0.0, 1.0]
    category: FlakeCategory
    root_cause: RootCauseHypothesis
    total_runs: int
    failure_rate: float
    duration_jitter: float  # Coefficient of variation (std_dev / mean)
    recommended_action: str  # "QUARANTINE", "AUTO_HEAL", "OBSERVE", "IGNORE"
    remediation_notes: str = ""


@dataclass
class HealSuggestion:
    test_id: str
    file_path: str
    line_number: int
    anti_pattern: str
    remediation_description: str
    original_snippet: str
    suggested_snippet: str
    unified_diff: Optional[str] = None


@dataclass
class QuarantineManifest:
    version: str = "1.0.0"
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    quarantined_tests: Dict[str, Dict] = field(default_factory=dict)
