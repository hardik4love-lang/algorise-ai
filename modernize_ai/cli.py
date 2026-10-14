"""
ModernizeAI: Command-Line Interface (CLI)
Automates library upgrades, AST codemod execution, and migration report generation.
"""

from __future__ import annotations

import argparse
import sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from .agent import ModernizeAgent
from .rule_engine import CodemodRuleEngine


def main():
    parser = argparse.ArgumentParser(
        prog="modernize-ai",
        description="Autonomous Breaking Change Migration & AST Codemod CLI",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # 1. Packages command
    subparsers.add_parser("packages", help="List supported migration packages")

    # 2. Plan command
    plan_parser = subparsers.add_parser("plan", help="View planned migration rules for a package")
    plan_parser.add_argument("--package", required=True, help="Target package name (e.g. pydantic, langchain)")
    plan_parser.add_argument("--to", default=None, help="Target version (e.g. 2.0, 0.3)")

    # 3. Apply command
    apply_parser = subparsers.add_parser("apply", help="Execute codemods across codebase")
    apply_parser.add_argument("--package", required=True, help="Target package name")
    apply_parser.add_argument("--to", default=None, help="Target version")
    apply_parser.add_argument("--write", action="store_true", help="Write changes to disk (default: dry-run preview)")
    apply_parser.add_argument("--output", help="Output file for Markdown report")
    apply_parser.add_argument("--dir", default=".", help="Root directory to transform")

    args = parser.parse_args()
    engine = CodemodRuleEngine()

    if args.command == "packages":
        pkgs = engine.list_supported_packages()
        print("[*] Supported ModernizeAI Migration Packages:")
        for p in pkgs:
            print(f"  - {p}")

    elif args.command == "plan":
        plan = engine.get_plan(args.package, target_version=args.to)
        if not plan:
            print(f"[!] No migration rules registered for package '{args.package}'.")
            sys.exit(1)

        print(f"[*] Migration Plan for '{args.package}' to '{plan.to_version}':")
        for idx, r in enumerate(plan.rules, 1):
            print(f"  [{idx}] {r.rule_id} ({r.rule_type.value}):")
            print(f"      {r.description}")
            print(f"      Transform: {r.source_symbol} -> {r.target_symbol}")

    elif args.command == "apply":
        plan = engine.get_plan(args.package, target_version=args.to)
        if not plan:
            print(f"[!] No migration rules registered for package '{args.package}'.")
            sys.exit(1)

        agent = ModernizeAgent(root_dir=args.dir)
        results = agent.execute_plan(plan, write=args.write)
        report = agent.generate_markdown_report(plan, results, write_mode=args.write)

        if args.output:
            with open(args.output, "w", encoding="utf-8") as out:
                out.write(report)
            print(f"[+] Report written to {args.output}")
        else:
            print(report)


if __name__ == "__main__":
    main()
