"""
AutoTest Sentinel: Command-Line Interface (CLI)
Provides operators and CI pipelines with automated scanning, quarantine control,
and DevEx ROI reporting.
"""

import argparse
import json
import os
import sys
from typing import Dict, List

from .classifier import FlakeClassifier
from .healer import ASTHealer
from .models import FlakinessReport, TestExecutionRecord, TestStatus
from .quarantine import QuarantineManager
from .reporter import ReportGenerator


def load_telemetry(file_path: str) -> Dict[str, List[TestExecutionRecord]]:
    """Loads and groups execution records by test_id."""
    if not os.path.exists(file_path):
        return {}

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    grouped: Dict[str, List[TestExecutionRecord]] = {}
    for entry in data:
        rec = TestExecutionRecord(
            test_id=entry["test_id"],
            file_path=entry["file_path"],
            duration_seconds=float(entry.get("duration_seconds", 0.0)),
            status=TestStatus(entry["status"]),
            error_message=entry.get("error_message"),
            stack_trace=entry.get("stack_trace"),
            commit_sha=entry.get("commit_sha"),
        )
        grouped.setdefault(rec.test_id, []).append(rec)
    return grouped


def main():
    parser = argparse.ArgumentParser(
        prog="autotest-sentinel",
        description="Autonomous Flaky Test Sentry, Quarantine, and Remediation CLI",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # 1. Scan command (AST Anti-Patterns)
    scan_parser = subparsers.add_parser("scan", help="Scan test code for flaky anti-patterns")
    scan_parser.add_argument("--dir", default=".", help="Root directory to scan (default: .)")

    # 2. Analyze command (Bayesian Classifier)
    analyze_parser = subparsers.add_parser("analyze", help="Analyze telemetry runs for flakiness")
    analyze_parser.add_argument(
        "--telemetry", default=os.path.join(".autotest", "telemetry.json"), help="Telemetry file path"
    )

    # 3. Quarantine command
    quar_parser = subparsers.add_parser("quarantine", help="Quarantine tests exceeding threshold")
    quar_parser.add_argument(
        "--telemetry", default=os.path.join(".autotest", "telemetry.json"), help="Telemetry file path"
    )
    quar_parser.add_argument(
        "--threshold", type=float, default=0.75, help="Flakiness score threshold (0.0 - 1.0)"
    )

    # 4. Report command
    report_parser = subparsers.add_parser("report", help="Generate DevEx impact & ROI report")
    report_parser.add_argument(
        "--telemetry", default=os.path.join(".autotest", "telemetry.json"), help="Telemetry file path"
    )
    report_parser.add_argument("--output", help="Optional output file path (e.g. $GITHUB_STEP_SUMMARY)")

    args = parser.parse_args()

    if args.command == "scan":
        healer = ASTHealer()
        suggestions = healer.scan_directory(args.dir)
        print(f"[*] Scanned directory '{args.dir}': found {len(suggestions)} anti-pattern(s).")
        for idx, s in enumerate(suggestions, 1):
            print(f"[{idx}] {s.test_id} (Line {s.line_number}): {s.anti_pattern}")
            print(f"    -> {s.remediation_description}")

    elif args.command == "analyze":
        grouped = load_telemetry(args.telemetry)
        if not grouped:
            print(f"[!] No telemetry records found in {args.telemetry}.")
            sys.exit(0)

        classifier = FlakeClassifier()
        print(f"[*] Analyzing {len(grouped)} test suites from {args.telemetry}...\n")
        print(f"{'Test ID':<50} | {'Runs':<6} | {'Fail Rate':<10} | {'Score':<6} | {'Action'}")
        print("-" * 88)
        for tid, records in grouped.items():
            rep = classifier.analyze_executions(records)
            print(
                f"{tid[:48]:<50} | {rep.total_runs:<6} | {rep.failure_rate*100:>6.1f}%   | {rep.flakiness_score:<6.2f} | {rep.recommended_action}"
            )

    elif args.command == "quarantine":
        grouped = load_telemetry(args.telemetry)
        classifier = FlakeClassifier()
        qm = QuarantineManager()

        quarantined_new = 0
        for tid, records in grouped.items():
            rep = classifier.analyze_executions(records)
            if rep.flakiness_score >= args.threshold:
                if qm.quarantine_test(rep):
                    quarantined_new += 1
                    print(f"[+] QUARANTINED: {tid} (Score: {rep.flakiness_score:.2f}, Cause: {rep.root_cause.value})")

        print(f"[*] Quarantine update complete. {quarantined_new} new test(s) quarantined.")
        for note in qm.emit_github_actions_annotations():
            print(note)

    elif args.command == "report":
        grouped = load_telemetry(args.telemetry)
        classifier = FlakeClassifier()
        qm = QuarantineManager()
        healer = ASTHealer()
        reporter = ReportGenerator()

        reports = [classifier.analyze_executions(recs) for recs in grouped.values()] if grouped else []
        suggestions = healer.scan_directory(".")
        md = reporter.generate_markdown_summary(reports, qm.manifest, suggestions)

        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(md)
            print(f"[+] Wrote markdown report to {args.output}")
        else:
            print(md)


if __name__ == "__main__":
    main()
