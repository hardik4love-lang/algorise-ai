"""
ContextPR: Command-Line Interface (CLI)
Automates blast-radius computation, interface contract audits, and PR review comments.
"""

import argparse
import os
import subprocess
import sys
from typing import List, Tuple

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from .blast_radius import BlastRadiusAnalyzer
from .invariants import InvariantExtractor
from .models import ChangedSymbol
from .reviewer import PRReviewer
from .synthesizer import PropertyTestSynthesizer


def get_git_diff_files(base_ref: str, head_ref: str) -> List[str]:
    """Retrieves list of modified files using git diff."""
    try:
        cmd = ["git", "diff", "--name-only", f"{base_ref}...{head_ref}"]
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        files = [line.strip() for line in res.stdout.splitlines() if line.strip().endswith(".py")]
        return files
    except Exception:
        # Fallback to local unstaged/staged diff against HEAD~1 or HEAD
        try:
            cmd = ["git", "diff", "--name-only", "HEAD~1"]
            res = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return [line.strip() for line in res.stdout.splitlines() if line.strip().endswith(".py")]
        except Exception:
            return []


def get_file_content_at_ref(ref: str, file_path: str) -> str:
    """Gets file contents at a specific git ref."""
    try:
        norm_path = file_path.replace("\\", "/")
        cmd = ["git", "show", f"{ref}:{norm_path}"]
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return res.stdout
    except Exception:
        return ""


def main():
    parser = argparse.ArgumentParser(
        prog="context-pr",
        description="Autonomous Semantic Blast-Radius & Interface Invariant PR Reviewer",
    )
    parser.add_argument("--base", default="HEAD~1", help="Base git ref for diff comparison (default: HEAD~1)")
    parser.add_argument("--head", default="HEAD", help="Head git ref (default: HEAD)")
    parser.add_argument("--files", nargs="*", help="Explicit list of files to evaluate")
    parser.add_argument("--output", help="Output path for Markdown summary (e.g. $GITHUB_STEP_SUMMARY)")
    parser.add_argument("--strict", action="store_true", help="Exit with code 1 if breaking changes detected")
    parser.add_argument("--dir", default=".", help="Root project directory")

    args = parser.parse_args()

    files = args.files or get_git_diff_files(args.base, args.head)
    if not files:
        print("[*] No Python files modified between base and head. Blast radius is empty.")
        sys.exit(0)

    print(f"[*] ContextPR analyzing {len(files)} modified file(s)...")

    # 1. Invariant analysis
    extractor = InvariantExtractor()
    all_changed_symbols: List[ChangedSymbol] = []

    for f in files:
        old_content = get_file_content_at_ref(args.base, f)
        new_content = ""
        if os.path.exists(f):
            with open(f, "r", encoding="utf-8", errors="ignore") as fp:
                new_content = fp.read()
        else:
            new_content = get_file_content_at_ref(args.head, f)

        symbols = extractor.analyze_diff(f, old_content, new_content)
        all_changed_symbols.extend(symbols)

    # 2. Blast radius calculation
    analyzer = BlastRadiusAnalyzer(root_dir=args.dir)
    report = analyzer.compute_blast_radius(
        changed_files=files,
        changed_symbols=all_changed_symbols,
        base_ref=args.base,
        head_ref=args.head,
    )

    # 3. Property invariant test synthesis
    synthesizer = PropertyTestSynthesizer()
    synthetic_tests = []
    for sym in all_changed_symbols:
        synthetic_tests.extend(synthesizer.synthesize_tests_for_symbol(sym))

    # 4. Generate review
    reviewer = PRReviewer()
    markdown = reviewer.generate_review_markdown(report, synthetic_tests)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as out:
            out.write(markdown)
        print(f"[+] Review written to {args.output}")
    else:
        print(markdown)

    if args.strict and report.breaking_changes_detected > 0:
        print(f"[!] STRICT MODE: {report.breaking_changes_detected} breaking change(s) detected. Gate failed.")
        sys.exit(1)


if __name__ == "__main__":
    main()
