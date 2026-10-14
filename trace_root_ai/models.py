"""
TraceRoot AI: Data Models
Defines representations for OpenTelemetry crash telemetry, Git blame mappings, and hotfix plans.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional


class IncidentSeverity(str, Enum):
    P1_CRITICAL = "P1_CRITICAL"
    P2_HIGH = "P2_HIGH"
    P3_MEDIUM = "P3_MEDIUM"
    P4_LOW = "P4_LOW"


class HotfixStatus(str, Enum):
    SIMULATED = "SIMULATED"
    VERIFIED = "VERIFIED"
    BRANCH_STAGED = "BRANCH_STAGED"
    REJECTED = "REJECTED"


@dataclass
class StackFrame:
    file_path: str
    line_number: int
    function_name: str
    code_line: str
    is_internal: bool = True


@dataclass
class IncidentPayload:
    incident_id: str
    service_name: str
    error_type: str
    error_message: str
    raw_stack_trace: str
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    severity: IncidentSeverity = IncidentSeverity.P2_HIGH
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    frames: List[StackFrame] = field(default_factory=list)


@dataclass
class BlameContext:
    file_path: str
    line_number: int
    culprit_commit_sha: str
    author_name: str
    commit_date: str
    commit_summary: str
    failing_function: str
    surrounding_code: str = ""


@dataclass
class HotfixPlan:
    incident_id: str
    target_file: str
    line_number: int
    root_cause_explanation: str
    original_snippet: str
    remediated_snippet: str
    patch_diff: str
    confidence_score: float  # Range: 0.0 - 1.0
    status: HotfixStatus = HotfixStatus.SIMULATED
    branch_name: Optional[str] = None
