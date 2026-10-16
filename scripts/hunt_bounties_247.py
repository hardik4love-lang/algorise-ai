#!/usr/bin/env python3
"""
24/7 Autonomous Bounty Hunter & Triage Engine
Continuously hunts for high-yield, unassigned bug bounties and open-source rewards
across GitHub, Algora, and top-tier repositories. Computes Priority Score and ENR.
"""

import os
import sys
import json
import time
import argparse
import subprocess
from datetime import datetime, timezone

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# ---------------------------------------------------------------------------
# Tracked Active Pull Requests
# ---------------------------------------------------------------------------
TRACKED_PRS = [
    {
        "repo": "BasedHardware/omi",
        "pr_number": 21521,
        "title": "fix(watch): stop Apple Watch recording on forget (#20780)",
        "url": "https://github.com/BasedHardware/omi/pull/21521",
        "bounty_est": "$100 - $200",
        "role": "Critical P1 Privacy Defect"
    },
    {
        "repo": "BasedHardware/omi",
        "pr_number": 21524,
        "title": "fix(ble): retry failed codec reads and prevent defaulting to PCM8 (#20779)",
        "url": "https://github.com/BasedHardware/omi/pull/21524",
        "bounty_est": "$50 - $100",
        "role": "Audio Codec Stability"
    },
    {
        "repo": "BasedHardware/omi",
        "pr_number": 21671,
        "title": "fix(deploy): specify --cpu=2 for backend-sync to support 6Gi/8Gi memory (#21668)",
        "url": "https://github.com/BasedHardware/omi/pull/21671",
        "bounty_est": "P0 Hotfix",
        "role": "Main CI Outage Restoration"
    },
    {
        "repo": "tenstorrent/tt-metal",
        "pr_number": 60777,
        "title": "fix(ops): pad float32 with max-magnitude NaN to eliminate out-of-range index leak (#60613)",
        "url": "https://github.com/tenstorrent/tt-metal/pull/60777",
        "bounty_est": "$100 - $300",
        "role": "Hardware Bitonic Sort Op Bugfix"
    },
    {
        "repo": "tenstorrent/tt-metal",
        "pr_number": 60791,
        "title": "fix(ops): reconfigure unpacker SrcA to dfb_x_welford in compact_fp32_finalizer (#60764)",
        "url": "https://github.com/tenstorrent/tt-metal/pull/60791",
        "bounty_est": "$100 - $300",
        "role": "Welford Layernorm LLK Assert Op Bugfix"
    },
    {
        "repo": "BasedHardware/omi",
        "pr_number": 21768,
        "title": "fix(bee): support 3-byte millivolts battery format and clamp legacy percentage (#21749)",
        "url": "https://github.com/BasedHardware/omi/pull/21768",
        "bounty_est": "$50 - $100",
        "role": "Bee Frontier Battery Parser Stability"
    },
    {
        "repo": "BasedHardware/omi",
        "pr_number": 21811,
        "title": "fix(sync): unblock backfill queue with owner deferral and NotFound resilience (#21122)",
        "url": "https://github.com/BasedHardware/omi/pull/21811",
        "bounty_est": "$100 - $200",
        "role": "Critical P1 Production Outage Restoration"
    },
    {
        "repo": "BasedHardware/omi",
        "pr_number": 21855,
        "title": "fix(backend): filter soft-deleted entities in recommendations and ensure goal deletion idempotency (#21854)",
        "url": "https://github.com/BasedHardware/omi/pull/21855",
        "bounty_est": "$50",
        "role": "Canonical Product State Integrity & Goal Deletion Idempotency"
    },
    {
        "repo": "BasedHardware/omi",
        "pr_number": 21876,
        "title": "fix(staged_tasks): filter completed entities in creation dedup and default relevance_score (#21875)",
        "url": "https://github.com/BasedHardware/omi/pull/21876",
        "bounty_est": "$50",
        "role": "Staged Tasks Creation Dedup & Firestore Index Sorting"
    },
    {
        "repo": "BasedHardware/omi",
        "pr_number": 21898,
        "title": "fix(tests): preload calendar_render in calendar unit stubs and adapt to model_text event format (#21897)",
        "url": "https://github.com/BasedHardware/omi/pull/21898",
        "bounty_est": "$50",
        "role": "P0 CI Recovery: Preload calendar_render in Unit Stubs"
    }
]

TARGET_REPOS = [
    "BasedHardware/omi",
    "tenstorrent/tt-metal",
    "calcom/cal.com",
    "twentyhq/twenty",
    "elizaOS/eliza"
]

def run_cmd(cmd: list) -> str:
    try:
        res = subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL)
        return res.strip()
    except Exception:
        return ""

def check_active_prs():
    print("\n" + "=" * 80)
    print(f"[*] 📡 ACTIVE PORTFOLIO TRIAGE STATUS — {datetime.now(timezone.utc).isoformat()}")
    print("=" * 80)
    for pr in TRACKED_PRS:
        repo = pr["repo"]
        num = pr["pr_number"]
        out = run_cmd(["gh", "api", f"repos/{repo}/pulls/{num}", "--jq", "{state: .state, merged: .merged, comments: .comments}"])
        if out:
            data = json.loads(out)
            state_str = "🟣 MERGED" if data.get("merged") else ("🟢 OPEN" if data.get("state") == "open" else "🔴 CLOSED")
            print(f"  • PR #{num} [{pr['bounty_est']}]: {state_str}")
            print(f"    Title: {pr['title']}")
            print(f"    URL:   {pr['url']}")
            print(f"    Comments count: {data.get('comments', 0)}")
        else:
            print(f"  • PR #{num}: Unable to fetch status")
    print("-" * 80)

def search_repo_bounties(repo: str) -> list:
    results = []
    raw = run_cmd(["gh", "issue", "list", "--repo", repo, "--state", "open", "--limit", "20", "--json", "number,title,labels,createdAt,url"])
    if not raw:
        return []
    try:
        issues = json.loads(raw)
        for iss in issues:
            title = iss.get("title", "")
            labels = [lbl.get("name", "") if isinstance(lbl, dict) else str(lbl) for lbl in iss.get("labels", [])]
            is_bounty = any("bounty" in l.lower() for l in labels) or "bounty" in title.lower() or "$" in title
            is_p1 = "p1" in labels or "critical" in title.lower() or "bug" in labels or "p0" in title.lower()
            if is_bounty or is_p1 or len(issues) <= 5:
                iss_num = iss.get("number")
                # Fast check for PRs referencing this issue
                prs_raw = run_cmd(["gh", "pr", "list", "--repo", repo, "--search", str(iss_num), "--state", "all", "--json", "number"])
                pr_count = len(json.loads(prs_raw)) if prs_raw else 0
                results.append({
                    "repo": repo,
                    "number": iss_num,
                    "title": title,
                    "url": iss.get("url"),
                    "created_at": iss.get("createdAt"),
                    "labels": labels,
                    "competing_prs": pr_count,
                    "is_bounty": is_bounty,
                    "is_critical": is_p1
                })
    except Exception as e:
        print(f"Error parsing issues for {repo}: {e}")
    return results

def search_global_bounties() -> list:
    results = []
    raw = run_cmd(["gh", "search", "issues", "bounty", "--state", "open", "--sort", "created", "--order", "desc", "--limit", "15", "--json", "number,title,labels,createdAt,url,repository"])
    if not raw:
        return []
    try:
        items = json.loads(raw)
        for iss in items:
            repo_info = iss.get("repository", {})
            repo_name = repo_info.get("nameWithOwner", "unknown")
            labels = [lbl.get("name", "") if isinstance(lbl, dict) else str(lbl) for lbl in iss.get("labels", [])]
            results.append({
                "repo": repo_name,
                "number": iss.get("number"),
                "title": iss.get("title", ""),
                "url": iss.get("url"),
                "created_at": iss.get("createdAt"),
                "labels": labels,
                "competing_prs": 0,
                "is_bounty": True,
                "is_critical": False
            })
    except Exception as e:
        print(f"Error parsing global bounties: {e}")
    return results

def compute_priority(opp: dict) -> float:
    gross_rev = 100.0 if opp.get("is_critical") else 50.0
    cost = 0.0  # Zero cost guardrail
    enr = gross_rev - cost
    urgency = 0.9 if opp.get("is_critical") else 0.5
    competition_penalty = opp.get("competing_prs", 0) * 0.3
    risk = 0.2 + competition_penalty
    cost_penalty = 0.0
    # priority_score = (enr * 0.40) + (urgency * 0.20) - (risk * 0.25) - (cost_penalty * 0.15)
    return round((enr * 0.40) + (urgency * 0.20) - (risk * 0.25) - (cost_penalty * 0.15), 2)

def hunt_cycle():
    check_active_prs()
    print("\n[*] 🏹 HUNTING NEW HIGH-ALPHA BOUNTY OPPORTUNITIES...")
    all_opps = []
    
    # 1. Target Repos
    for r in TARGET_REPOS:
        opps = search_repo_bounties(r)
        for o in opps:
            o["priority_score"] = compute_priority(o)
            all_opps.append(o)

    # 2. Global Bounties
    global_opps = search_global_bounties()
    for o in global_opps:
        o["priority_score"] = compute_priority(o)
        all_opps.append(o)

    # Deduplicate by url
    seen_urls = set()
    deduped = []
    for o in all_opps:
        u = o.get("url")
        if u and u not in seen_urls:
            seen_urls.add(u)
            deduped.append(o)

    # Sort descending by priority score and ascending by competing PRs
    deduped.sort(key=lambda x: (x["competing_prs"], -x["priority_score"]))

    print(f"[+] Total opportunities scanned: {len(deduped)}")
    print(f"[+] Opportunities with 0 competing PRs: {sum(1 for o in deduped if o['competing_prs'] == 0)}")

    # Generate Markdown Radar Report
    radar_md = [
        f"# 🎯 Autonomous Bounty Radar — {datetime.now(timezone.utc).isoformat()}",
        "",
        "## Active Tracked PRs",
        "| PR | Target Repo | Role | Status | Bounty Est. |",
        "|---|---|---|---|---|"
    ]
    for pr in TRACKED_PRS:
        radar_md.append(f"| [#{pr['pr_number']}]({pr['url']}) | `{pr['repo']}` | {pr['role']} | `OPEN` | **{pr['bounty_est']}** |")

    radar_md.extend([
        "",
        "## Top Unassigned Bounty Targets (0 Competing PRs)",
        "| Repo | Issue | Title | Competing PRs | Priority Score | Action |",
        "|---|---|---|---|---|---|"
    ])

    top_targets = [o for o in deduped if o["competing_prs"] == 0][:15]
    for t in top_targets:
        title_clean = t['title'][:55].replace('|', '-')
        radar_md.append(f"| `{t['repo']}` | [#{t['number']}]({t['url']}) | {title_clean} | {t['competing_prs']} | `{t['priority_score']}` | [Inspect]({t['url']}) |")

    report_path = os.path.join(os.getcwd(), "bounty_radar.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(radar_md))

    # Save JSON ledger
    ledger_path = os.path.join(os.getcwd(), "bounty_radar.json")
    with open(ledger_path, "w", encoding="utf-8") as f:
        json.dump(deduped, f, indent=2)

    print(f"[✓] Bounty radar generated: {report_path}")
    print(f"[✓] Bounty ledger updated: {ledger_path}")

def main():
    parser = argparse.ArgumentParser(description="24/7 Bounty Hunter Engine")
    parser.add_argument("--loop", type=int, default=0, help="Run continuously with N seconds interval (e.g. 1800)")
    args = parser.parse_args()

    if args.loop > 0:
        print(f"[*] Starting 24/7 Bounty Hunter Daemon (Interval: {args.loop}s)...")
        while True:
            try:
                hunt_cycle()
            except Exception as e:
                print(f"[!] Error in hunt cycle: {e}")
            print(f"[*] Sleeping for {args.loop}s until next hunt cycle...")
            time.sleep(args.loop)
    else:
        hunt_cycle()

if __name__ == "__main__":
    main()
