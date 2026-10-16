#!/usr/bin/env python3
"""
Autonomous PR & Bounty Settlement Portfolio Monitor
Monitors all 10 active and merged pull requests across target repositories:
- BasedHardware/omi
- calcom/cal.com
- tenstorrent/tt-metal
And tracks the settlement status of Ticket #146152932 (PayPal: shruhicollections@gmail.com).
"""

import sys
import json
import subprocess
from datetime import datetime

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

PORTFOLIO_TARGETS = [
    # --- BATCH 1: MERGED PRS (TICKET #146152932 CLAIM) ---
    {
        "repo": "BasedHardware/omi",
        "pr_number": 21524,
        "title": "fix(ble): retry failed codec reads and prevent defaulting to PCM8 (#20779)",
        "url": "https://github.com/BasedHardware/omi/pull/21524",
        "expected_state": "MERGED",
        "bounty_est": "$50 - $100 USD"
    },
    {
        "repo": "BasedHardware/omi",
        "pr_number": 21811,
        "title": "fix(sync): resolve critical 54h+ sync queue starvation on device disconnect (#21122)",
        "url": "https://github.com/BasedHardware/omi/pull/21811",
        "expected_state": "MERGED",
        "bounty_est": "$100 - $200 USD"
    },
    {
        "repo": "BasedHardware/omi",
        "pr_number": 21768,
        "title": "fix(firmware): parse millivolts battery format and clamp percentage (#21749)",
        "url": "https://github.com/BasedHardware/omi/pull/21768",
        "expected_state": "MERGED",
        "bounty_est": "$50 - $100 USD"
    },
    {
        "repo": "BasedHardware/omi",
        "pr_number": 21521,
        "title": "fix(watch): stop Apple Watch recording on forget (#20780)",
        "url": "https://github.com/BasedHardware/omi/pull/21521",
        "expected_state": "MERGED",
        "bounty_est": "$100 USD"
    },
    {
        "repo": "BasedHardware/omi",
        "pr_number": 21671,
        "title": "fix(deploy): specify --cpu=2 for backend-sync to support 6Gi/8Gi memory (#21668)",
        "url": "https://github.com/BasedHardware/omi/pull/21671",
        "expected_state": "MERGED",
        "bounty_est": "Deployment Fix"
    },
    # --- BATCH 2: ACTIVE OPEN PRS (IN REVIEW / CI QUEUE) ---
    {
        "repo": "BasedHardware/omi",
        "pr_number": 21855,
        "title": "fix(backend): filter soft-deleted entities in recommendations and ensure goal deletion idempotency (#21854)",
        "url": "https://github.com/BasedHardware/omi/pull/21855",
        "expected_state": "OPEN",
        "bounty_est": "$50 USD"
    },
    {
        "repo": "BasedHardware/omi",
        "pr_number": 21876,
        "title": "fix(staged_tasks): filter completed entities in creation dedup and default relevance_score (#21875)",
        "url": "https://github.com/BasedHardware/omi/pull/21876",
        "expected_state": "OPEN",
        "bounty_est": "$50 USD"
    },
    {
        "repo": "calcom/cal.com",
        "pr_number": 30353,
        "title": "fix(oauth2): support space-separated scopes per RFC 6749 (#30348)",
        "url": "https://github.com/calcom/cal.diy/pull/30353",
        "expected_state": "OPEN",
        "bounty_est": "$50 - $100 USD"
    },
    {
        "repo": "tenstorrent/tt-metal",
        "pr_number": 60791,
        "title": "[Bug fix] layernorm_welford: reconfigure unpacker SrcA to dfb_x_welford in compact_fp32_finalizer (#60764)",
        "url": "https://github.com/tenstorrent/tt-metal/pull/60791",
        "expected_state": "OPEN",
        "bounty_est": "$100 - $300 USD"
    },
    {
        "repo": "tenstorrent/tt-metal",
        "pr_number": 60777,
        "title": "[Bug fix] ttnn.sort: pad float32 with max-magnitude NaN to eliminate out-of-range index leak (#60613)",
        "url": "https://github.com/tenstorrent/tt-metal/pull/60777",
        "expected_state": "OPEN",
        "bounty_est": "$100 - $300 USD"
    }
]

def check_pr_status(repo: str, pr_number: int):
    try:
        cmd = [
            "gh", "api", f"repos/{repo}/pulls/{pr_number}",
            "--jq", "{state: .state, merged: .merged, comments: .comments, review_comments: .review_comments, updated_at: .updated_at, mergeable: .mergeable}"
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
    print("=" * 86)
    print(f"[*] REVENUE & BOUNTY PORTFOLIO MONITOR — {datetime.now().isoformat()}")
    print(f"[*] Settlement Routing Destination: PayPal (shruhicollections@gmail.com)")
    print(f"[*] Based Hardware Payout Ticket:   #146152932 [SUBMITTED -> IN REVIEW]")
    print("=" * 86)

    merged_count = 0
    open_count = 0

    for item in PORTFOLIO_TARGETS:
        repo = item["repo"]
        pr_num = item["pr_number"]
        info = check_pr_status(repo, pr_num)

        if "error" in info:
            print(f"\n[!] PR #{pr_num} ({repo}): Error: {info['error']}")
            continue

        state = info.get("state", "UNKNOWN").upper()
        merged = info.get("merged", False)
        if merged:
            status_label = "🎉 MERGED (Ready for Payout / In Claim #146152932)"
            merged_count += 1
        elif state == "OPEN":
            status_label = "🟢 OPEN (In Review / CI Queue)"
            open_count += 1
        else:
            status_label = f"⚪ {state}"

        print(f"\n[•] {repo} #{pr_num} | Est: {item['bounty_est']}")
        print(f"    Title:    {item['title']}")
        print(f"    Status:   {status_label}")
        print(f"    URL:      {item['url']}")
        print(f"    Comments: {info.get('comments', 0)} issue comments | {info.get('review_comments', 0)} review comments")
        print(f"    Updated:  {info.get('updated_at')}")

        comments = get_latest_comments(repo, pr_num)
        if comments:
            latest = comments[-1]
            body_snippet = latest['body'].replace('\n', ' ')[:110]
            print(f"    Latest Note: @{latest['user']} ({latest['created_at']}): {body_snippet}...")

    print("\n" + "=" * 86)
    print(f"[*] Summary: {merged_count} MERGED PRs ($400 - $600+ USD) | {open_count} OPEN PRs ($350 - $850+ USD)")
    print(f"[*] Total Tracked Pipeline Value: $750 - $1,450+ USD")
    print("=" * 86)

if __name__ == "__main__":
    run_monitor_check()
