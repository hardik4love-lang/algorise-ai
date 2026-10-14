"""
TraceRoot AI: Autonomous Telemetry-to-Code Incident Resolver & Hotfix Sentry
Part of the Algorise DevEx & Autonomous Systems Platform.
"""

from __future__ import annotations

from .blame_analyzer import BlameAnalyzer
from .healer import IncidentHealer
from .ingestor import TelemetryIngestor
from .models import (
    BlameContext,
    HotfixPlan,
    HotfixStatus,
    IncidentPayload,
    IncidentSeverity,
    StackFrame,
)
from .reporter import IncidentReporter

__version__ = "1.0.0"

__all__ = [
    "TelemetryIngestor",
    "BlameAnalyzer",
    "IncidentHealer",
    "IncidentReporter",
    "IncidentPayload",
    "BlameContext",
    "HotfixPlan",
    "IncidentSeverity",
    "HotfixStatus",
    "StackFrame",
]
