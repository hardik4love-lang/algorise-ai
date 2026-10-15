"""
TraceRoot AI & ModernizeAI: Distributed Autonomous Healing Mesh (TECH-302)
Interconnects production telemetry incident correlation with automated AST codemod
generation and safety verification to deliver Zero-Touch SRE.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from trace_root_ai.ingestor import TelemetryIngestor
from trace_root_ai.blame_analyzer import BlameAnalyzer
from trace_root_ai.healer import IncidentHealer
from trace_root_ai.models import IncidentPayload, HotfixPlan
from context_pr.blast_radius import BlastRadiusAnalyzer
from modernize_ai.rule_engine import CodemodRuleEngine


class HealingMeshResult(BaseModel):
    incident_id: str
    culprit_file: str
    culprit_line: int
    error_type: str
    hotfix_synthesized: bool
    hotfix_plan: Optional[Dict[str, Any]] = None
    blast_radius_risk: str
    blast_radius_score: float
    auto_staged: bool
    verification_passed: bool
    remediation_summary: str


class AutonomousHealingMesh:
    """
    Zero-Touch SRE Mesh connecting telemetry, root-cause blame, AST healing,
    and blast-radius contract verification.
    """

    def __init__(self, root_dir: str = "."):
        self.root_dir = os.path.abspath(root_dir)
        self.ingestor = TelemetryIngestor()
        self.blame_analyzer = BlameAnalyzer(root_dir=self.root_dir)
        self.healer = IncidentHealer(root_dir=self.root_dir)
        self.blast_analyzer = BlastRadiusAnalyzer(root_dir=self.root_dir)
        self.rule_engine = CodemodRuleEngine()

    def process_incident(
        self, incident: IncidentPayload, auto_stage: bool = False
    ) -> HealingMeshResult:
        """
        Processes an incoming production incident:
        1. Ingests and parses raw traceback frames if not already populated.
        2. Correlates with git blame to locate exact line.
        3. Synthesizes a defensive AST patch or codemod.
        4. Runs blast-radius verification to ensure low regression risk.
        5. Optionally stages hotfix branch.
        """
        if not incident.frames and incident.raw_stack_trace:
            parsed = self.ingestor.parse_traceback(
                raw_traceback=incident.raw_stack_trace,
                service_name=incident.service_name,
                incident_id=incident.incident_id,
            )
            incident.frames = parsed.frames

        blame_context = self.blame_analyzer.analyze_culprit_frame(incident)
        if not blame_context:
            return HealingMeshResult(
                incident_id=incident.incident_id,
                culprit_file="unknown",
                culprit_line=0,
                error_type=incident.error_type,
                hotfix_synthesized=False,
                blast_radius_risk="UNKNOWN",
                blast_radius_score=0.0,
                auto_staged=False,
                verification_passed=False,
                remediation_summary="Unable to locate culprit code from stack trace.",
            )

        hotfix_plan = self.healer.synthesize_hotfix(incident, blame_context)
        if not hotfix_plan:
            return HealingMeshResult(
                incident_id=incident.incident_id,
                culprit_file=blame_context.file_path,
                culprit_line=blame_context.line_number,
                error_type=incident.error_type,
                hotfix_synthesized=False,
                blast_radius_risk="LOW",
                blast_radius_score=0.0,
                auto_staged=False,
                verification_passed=False,
                remediation_summary="No deterministic AST patch available for this error pattern.",
            )

        # Blast radius analysis on target file
        blast_report = self.blast_analyzer.compute_blast_radius(
            changed_files=[blame_context.file_path]
        )

        staged = False
        if auto_stage:
            staged = self.healer.stage_hotfix_branch(hotfix_plan, create_branch=False)

        return HealingMeshResult(
            incident_id=incident.incident_id,
            culprit_file=blame_context.file_path,
            culprit_line=blame_context.line_number,
            error_type=incident.error_type,
            hotfix_synthesized=True,
            hotfix_plan={
                "target_file": hotfix_plan.target_file,
                "line_number": hotfix_plan.line_number,
                "explanation": hotfix_plan.root_cause_explanation,
                "patch_diff": hotfix_plan.patch_diff,
                "confidence_score": hotfix_plan.confidence_score,
            },
            blast_radius_risk=blast_report.risk_level.value,
            blast_radius_score=blast_report.risk_score,
            auto_staged=staged,
            verification_passed=blast_report.risk_score < 7.0,
            remediation_summary=f"Synthesized hotfix for {incident.error_type} in {blame_context.file_path}:{blame_context.line_number} (Risk: {blast_report.risk_level.value}).",
        )
