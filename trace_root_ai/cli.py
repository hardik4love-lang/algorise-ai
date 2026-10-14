"""
TraceRoot AI: Command-Line Interface (CLI)
Automates runtime crash ingestion, Git blame correlation, defensive patch synthesis,
and emergency hotfix branch staging.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from .blame_analyzer import BlameAnalyzer
from .healer import IncidentHealer
from .ingestor import TelemetryIngestor
from .reporter import IncidentReporter


def main():
    parser = argparse.ArgumentParser(
        prog="traceroot",
        description="Autonomous Telemetry-to-Code Incident Resolver & Hotfix Sentry",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # 1. Triage command
    triage_parser = subparsers.add_parser("triage", help="Triage an incident payload and synthesize hotfix")
    triage_parser.add_argument("--incident", required=True, help="Path to incident JSON or raw traceback file")
    triage_parser.add_argument("--stage", action="store_true", help="Stage hotfix on emergency git branch")
    triage_parser.add_argument("--output", help="Output path for Markdown summary")
    triage_parser.add_argument("--dir", default=".", help="Root repository directory")

    # 2. Demo command
    subparsers.add_parser("demo", help="Run simulated KeyError incident triage")

    args = parser.parse_args()
    ingestor = TelemetryIngestor()
    blame_analyzer = BlameAnalyzer(root_dir=getattr(args, "dir", "."))
    healer = IncidentHealer(root_dir=getattr(args, "dir", "."))
    reporter = IncidentReporter()

    if args.command == "demo":
        sample_tb = """
Traceback (most recent call last):
  File "engine/security.py", line 42, in evaluate_threat
    score = weights["anomaly_factor"]
KeyError: 'anomaly_factor'
"""
        payload = ingestor.parse_traceback(sample_tb, service_name="algorise-security-gateway")
        blame = blame_analyzer.analyze_culprit_frame(payload)
        plan = healer.synthesize_hotfix(payload, blame) if blame else None
        md = reporter.generate_incident_report(payload, blame, plan)
        print(md)

    elif args.command == "triage":
        if not os.path.exists(args.incident):
            print(f"[!] Incident file '{args.incident}' not found.")
            sys.exit(1)

        with open(args.incident, "r", encoding="utf-8") as f:
            content = f.read()

        try:
            data = json.loads(content)
            payload = ingestor.parse_json_payload(data)
        except json.JSONDecodeError:
            payload = ingestor.parse_traceback(content)

        print(f"[*] Triaging Incident `{payload.incident_id}` ({payload.error_type}: {payload.error_message})...")
        blame = blame_analyzer.analyze_culprit_frame(payload)
        plan = None
        if blame:
            print(f"[+] Culprit Frame: {blame.file_path}:{blame.line_number} in {blame.failing_function}")
            plan = healer.synthesize_hotfix(payload, blame)
            if plan and args.stage:
                print(f"[+] Staging emergency hotfix branch...")
                healer.stage_hotfix_branch(plan, create_branch=True)

        md = reporter.generate_incident_report(payload, blame, plan)
        if args.output:
            with open(args.output, "w", encoding="utf-8") as out:
                out.write(md)
            print(f"[+] Wrote incident report to {args.output}")
        else:
            print(md)


if __name__ == "__main__":
    main()
