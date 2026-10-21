"""
AutoTest Sentinel: Data Models
Defines core representations for test executions, flakiness classifications, and repair suggestions.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional

class TestStatus(str, Enum):
    __test__ = False
    PASSED = 'PASSED'
    FAILED = 'FAILED'
    SKIPPED = 'SKIPPED'

class FlakeCategory(str, Enum):
    DETERMINISTIC_PASS = 'DETERMINISTIC_PASS'
    DETERMINISTIC_FAIL = 'DETERMINISTIC_FAIL'
    FLAKY_HIGH = 'FLAKY_HIGH'
    FLAKY_MEDIUM = 'FLAKY_MEDIUM'
    LOW_CONFIDENCE = 'LOW_CONFIDENCE'

class RootCauseHypothesis(str, Enum):
    TIMING_RACE = 'TIMING_RACE'
    SHARED_STATE = 'SHARED_STATE'
    NETWORK_IO = 'NETWORK_IO'
    ORDER_DEPENDENT = 'ORDER_DEPENDENT'
    ENVIRONMENT_COLLISION = 'ENVIRONMENT_COLLISION'
    UNKNOWN = 'UNKNOWN'

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
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

@dataclass
class FlakinessReport:
    test_id: str
    file_path: str
    flakiness_score: float
    category: FlakeCategory
    root_cause: RootCauseHypothesis
    total_runs: int
    failure_rate: float
    duration_jitter: float
    recommended_action: str
    remediation_notes: str = ''

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
    version: str = '1.0.0'
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    quarantined_tests: Dict[str, Dict] = field(default_factory=dict)

    def generate_pytest_deselection_args(self) -> List[str]:
        """Generates pytest --deselect arguments for all quarantined tests."""
        args = []
        for test_id in self.quarantined_tests.keys():
            args.extend(["--deselect", test_id])
        return args
