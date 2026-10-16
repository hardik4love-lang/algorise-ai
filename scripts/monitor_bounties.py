#!/usr/bin/env python3
"""
Autonomous PR & Bounty Triage Monitor
Continuously or periodically monitors open pull requests on BasedHardware/omi
and outputs real-time alerts when maintainers review, comment, or merge.
"""

import sys
import json
import time
import subprocess
from datetime import datetime

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

PR_TARGETS = [
    {
        "repo": "BasedHardware/omi",
        "pr_number": 21521,
        "title": "fix(watch): stop Apple Watch recording on forget (#20780)",
        "url": "https://github.com/BasedHardware/omi/pull/21521"
    },
    {
        "repo": "BasedHardware/omi",
        "pr_number": 21524,
        "title": "fix(ble): retry failed codec reads and prevent defaulting to PCM8 (#20779)",
        "url": "https://github.com/BasedHardware/omi/pull/21524"
    },
    {
        "repo": "BasedHardware/omi",
        "pr_number": 21671,
        "title": "fix(deploy): specify --cpu=2 for backend-sync to support 6Gi/8Gi memory (#21668)",
        "url": "https://github.com/BasedHardware/omi/pull/21671"
    }
]

def check_pr_status(repo: str, pr_number: int):
    try:
        cmd = [
            "gh", "api", f"repos/{repo}/pulls/{pr_number}",
            "--jq", "{state: .state, merged: .merged, comments: .comments, review_comments: .review_comments, updated_at: .updated_at}"
        ]
        res = subprocess.check_output(cmd, text=True).strip()
        return json.loads(res)
    except Exception as e:
        return {"error": str(e)}

def get_latest_comments(repo: str, pr_number: int):
    try:
        cmd = [
            "gh", "api", f"repos/{repo}/issues/{pr_number}/comments",
            "--jq", "[.[] | {user: .user.login, body: .body, created_at: .created_at}]"
        ]
        res = subprocess.check_output(cmd, text=True).strip()
        return json.loads(res)
    except Exception:
        return []

def run_monitor_check():
    print("=" * 80)
    print(f"[*] Bounty PR Triage Monitor Check — {datetime.now().isoformat()}")
    print("=" * 80)

    for item in PR_TARGETS:
        repo = item["repo"]
        pr_num = item["pr_number"]
        info = check_pr_status(repo, pr_num)

        if "error" in info:
            print(f"[!] PR #{pr_num} ({item['title']}): Error checking status: {info['error']}")
            continue

        state = info.get("state", "UNKNOWN").upper()
        merged = info.get("merged", False)
        status_label = "🎉 MERGED!" if merged else (f"🟢 {state}")

        print(f"\n[•] PR #{pr_num}: {item['title']}")
        print(f"    URL:      {item['url']}")
        print(f"    Status:   {status_label}")
        print(f"    Comments: {info.get('comments', 0)} issue comments | {info.get('review_comments', 0)} review comments")
        print(f"    Updated:  {info.get('updated_at')}")

        comments = get_latest_comments(repo, pr_num)
        if comments:
            print("    Recent Review Comments:")
            for c in comments[-3:]:
                body_snippet = c['body'].replace('\n', ' ')[:100]
                print(f"      - @{c['user']} ({c['created_at']}): {body_snippet}...")
        else:
            print("    No comments yet — awaiting maintainer triage.")

    print("\n" + "=" * 80)

if __name__ == "__main__":
    run_monitor_check()
