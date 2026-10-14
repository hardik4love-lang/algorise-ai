"""
Revenue Engine: Command-Line Interface (CLI)
Automates opportunity scanning, 7-gate scoring, and audit ledger generation.
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

from .reporter import RevenueReporter
from .scanner import OpportunityScanner


def main():
    parser = argparse.ArgumentParser(
        prog="revenue",
        description="Autonomous Revenue Orchestrator & Bounty Opportunity Evaluation CLI",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # 1. Scan command
    scan_parser = subparsers.add_parser("scan", help="Scan and evaluate open bounty opportunities")
    scan_parser.add_argument("--query", default="bounty", help="Issue search query (default: bounty)")
    scan_parser.add_argument("--limit", type=int, default=10, help="Max candidates to evaluate")
    scan_parser.add_argument("--allow-cost", action="store_true", help="Permit non-zero compute cost")
    scan_parser.add_argument("--output", help="Output path for Markdown summary")
    scan_parser.add_argument("--ledger", help="Custom ledger file destination")

    # 2. Ledger command
    ledger_parser = subparsers.add_parser("ledger", help="Display current audit ledger")
    ledger_parser.add_argument(
        "--path", default=os.path.join("live_ledger", "evaluation_ledger.json"), help="Ledger path"
    )

    args = parser.parse_args()
    scanner = OpportunityScanner(ledger_path=getattr(args, "ledger", None))
    reporter = RevenueReporter()

    if args.command == "scan":
        print(f"[*] Scanning opportunities for query: '{args.query}' (limit: {args.limit})...")
        ledger = scanner.scan_opportunities(
            query=args.query,
            limit=args.limit,
            enforce_zero_cost=(not args.allow_cost),
        )
        report = reporter.generate_markdown_report(ledger)

        if args.output:
            with open(args.output, "w", encoding="utf-8") as out:
                out.write(report)
            print(f"[+] Wrote evaluation report to {args.output}")
        else:
            print(report)

    elif args.command == "ledger":
        if not os.path.exists(args.path):
            print(f"[!] No ledger found at {args.path}")
            sys.exit(0)

        with open(args.path, "r", encoding="utf-8") as f:
            data = json.load(f)

        print(f"[*] Audit Ledger: {data.get('ledger_id')}")
        print(f"[*] Timestamp:    {data.get('timestamp')}")
        print(f"[*] Total Staged: {data.get('total_evaluated')}")
        for opp in data.get("opportunities", []):
            print(f"    • [{opp.get('task_id')}] {opp.get('title')} (ENR: ${opp.get('expected_net_revenue')}) - {opp.get('status')}")


if __name__ == "__main__":
    main()
