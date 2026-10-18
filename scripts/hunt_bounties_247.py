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
        "repo": "limitlessprojects/Go-Hybrid",
        "pr_number": 497,
        "title": "fix(tools): decode checker JSON as UTF-8 independently of host locale (#492)",
        "url": "https://github.com/limitlessprojects/Go-Hybrid/pull/497",
        "bounty_est": "$75 - $100",
        "role": "Corpus Harness UTF-8 Decoder (MERGED upstream)",
        "is_merged": True
    },
    {
        "repo": "limitlessprojects/Go-Hybrid",
        "pr_number": 569,
        "title": "spike(w008): settlement regions for own-handle tasks (#257)",
        "url": "https://github.com/limitlessprojects/Go-Hybrid/pull/569",
        "bounty_est": "$250 - $500",
        "role": "Wildcard W-008 Settlement Region Spike",
        "is_merged": False
    },
    {
        "repo": "limitlessprojects/Go-Hybrid",
        "pr_number": 413,
        "title": "fix(check): type-check receive operands and reject non-channel values (#409)",
        "url": "https://github.com/limitlessprojects/Go-Hybrid/pull/413",
        "bounty_est": "$75 - $100",
        "role": "Soundness Type Checker (Recv Operand)"
    },
    {
        "repo": "limitlessprojects/Go-Hybrid",
        "pr_number": 427,
        "title": "fix(check): type-check for-in iterable operands and reject non-iterables (#411)",
        "url": "https://github.com/limitlessprojects/Go-Hybrid/pull/427",
        "bounty_est": "$75 - $100",
        "role": "Soundness Type Checker (For-In Iterable)"
    },
    {
        "repo": "limitlessprojects/Go-Hybrid",
        "pr_number": 430,
        "title": "fix(check): type-check operand types for conditions, index, slice, call, and builtins (#425)",
        "url": "https://github.com/limitlessprojects/Go-Hybrid/pull/430",
        "bounty_est": "$75 - $100",
        "role": "Soundness Type Checker (Operand Types & Builtins)"
    },
    {
        "repo": "BasedHardware/omi",
        "pr_number": 21999,
        "title": "fix(sync): sequenced stale job recovery and atomic lease renewal (#21998)",
        "url": "https://github.com/BasedHardware/omi/pull/21999",
        "bounty_est": "$100 - $200",
        "role": "Critical Queue Sync Stability"
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
        "repo": "calcom/cal.diy",
        "pr_number": 30353,
        "title": "fix(oauth2): support space-separated scopes per RFC 6749 (#30348)",
        "url": "https://github.com/calcom/cal.diy/pull/30353",
        "bounty_est": "$50 - $100",
        "role": "RFC 6749 OAuth 2.0 Scope Delimiter Parser"
    },
    {
        "repo": "calcom/cal.diy",
        "pr_number": 30355,
        "title": "fix(docker): bind ports to 127.0.0.1 in docker-compose (#30351)",
        "url": "https://github.com/calcom/cal.diy/pull/30355",
        "bounty_est": "$50 - $100",
        "role": "Security Localhost Port Isolation"
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
        "repo": "tenstorrent/tt-metal",
        "pr_number": 61086,
        "title": "fix(host): resolve symbol resolution and build warnings",
        "url": "https://github.com/tenstorrent/tt-metal/pull/61086",
        "bounty_est": "$100 - $200",
        "role": "Host Runtime Symbol Fix"
    }
]

TARGET_REPOS = [
    "limitlessprojects/Go-Hybrid",
    "BasedHardware/omi",
    "tenstorrent/tt-metal",
    "calcom/cal.diy",
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
            is_merged = data.get("merged", False) or pr.get("is_merged", False)
            state_str = "🟣 MERGED" if is_merged else ("🟢 OPEN" if data.get("state") == "open" else "🔴 CLOSED")
            pr["status_str"] = state_str
            print(f"  • PR #{num} [{pr['bounty_est']}]: {state_str}")
            print(f"    Title: {pr['title']}")
            print(f"    URL:   {pr['url']}")
            print(f"    Comments count: {data.get('comments', 0)}")
        else:
            pr["status_str"] = "🟣 MERGED" if pr.get("is_merged") else "🟢 OPEN"
            print(f"  • PR #{num}: {pr['status_str']} (cached)")
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
            is_p1 = "p1" in labels or "critical" in title.lower() or "bug" in labels or "p0" in title.lower() or "soundness" in title.lower()
            if is_bounty or is_p1 or len(issues) <= 5:
                iss_num = iss.get("number")
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
    return round((enr * 0.40) + (urgency * 0.20) - (risk * 0.25) - (cost_penalty * 0.15), 2)

def load_security_targets() -> list:
    cfg_path = os.path.join(os.path.dirname(__file__), "..", "config", "research_targets.json")
    if not os.path.exists(cfg_path):
        return []
    try:
        with open(cfg_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("targets", [])
    except Exception:
        return []

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

    deduped.sort(key=lambda x: (x["competing_prs"], -x["priority_score"]))

    # Group into platforms:
    platform_1_algora = [o for o in deduped if "Go-Hybrid" not in o.get("repo", "")]
    platform_2_gohybrid = [o for o in deduped if "Go-Hybrid" in o.get("repo", "")]
    platform_3_security = load_security_targets()

    # Generate Markdown Radar Report
    radar_md = [
        f"# 🎯 ARIA Multi-Platform Bounty Radar & Execution Matrix",
        f"**Generated:** `{datetime.now(timezone.utc).isoformat()}` | **Status:** `ACTIVE 24/7 DAEMON`",
        "",
        "## 📡 Tracked Fleet Portfolio",
        "| PR | Target Repo | Role | Status | Bounty Est. |",
        "|---|---|---|---|---|"
    ]
    for pr in TRACKED_PRS:
        status = pr.get("status_str", "🟢 OPEN")
        radar_md.append(f"| [#{pr['pr_number']}]({pr['url']}) | `{pr['repo']}` | {pr['role']} | `{status}` | **{pr['bounty_est']}** |")

    radar_md.extend([
        "",
        "---",
        "## 🌐 Platform 1: Algora / GitHub Open Source Opportunities",
        "| Repo | Issue | Title | Competing PRs | Priority Score | Action |",
        "|---|---|---|---|---|---|"
    ])
    for t in platform_1_algora[:6]:
        title_clean = t['title'][:55].replace('|', '-')
        radar_md.append(f"| `{t['repo']}` | [#{t['number']}]({t['url']}) | {title_clean} | {t['competing_prs']} | `{t['priority_score']}` | [Inspect]({t['url']}) |")

    radar_md.extend([
        "",
        "---",
        "## ⚡ Platform 2: Go-Hybrid Soundness Bounties & Wildcards",
        "| Repo | Issue | Title | Competing PRs | Priority Score | Action |",
        "|---|---|---|---|---|---|"
    ])
    for t in platform_2_gohybrid[:6]:
        title_clean = t['title'][:55].replace('|', '-')
        radar_md.append(f"| `{t['repo']}` | [#{t['number']}]({t['url']}) | {title_clean} | {t['competing_prs']} | `{t['priority_score']}` | [Inspect]({t['url']}) |")

    radar_md.extend([
        "",
        "---",
        "## 🛡️ Platform 3: Coordinated Vulnerability Disclosure (HackerOne / Bugcrowd)",
        "| Target | Platform | Scope URL | Avg Payout | Tier | Focus Vectors |",
        "|---|---|---|---|---|---|"
    ])
    for sec in platform_3_security[:6]:
        sec_name = sec.get("name", "Unknown")[:45]
        sec_plat = sec.get("platform", "").upper()
        sec_url = sec.get("scope_url", "")
        sec_pay = f"${sec.get('average_bounty_usd', 1000):.0f}"
        sec_tier = sec.get("bounty_tier", "high").upper()
        sec_tags = ", ".join(sec.get("triage_tags", [])[:3])
        radar_md.append(f"| {sec_name} | `{sec_plat}` | [Scope]({sec_url}) | **{sec_pay}** | `{sec_tier}` | `{sec_tags}` |")

    report_path = os.path.join(os.getcwd(), "bounty_radar.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(radar_md))

    # Save structured JSON ledger
    ledger_path = os.path.join(os.getcwd(), "bounty_radar.json")
    with open(ledger_path, "w", encoding="utf-8") as f:
        json.dump({
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "tracked_prs": TRACKED_PRS,
            "platform_1_algora": platform_1_algora[:10],
            "platform_2_gohybrid": platform_2_gohybrid[:10],
            "platform_3_security": platform_3_security[:10]
        }, f, indent=2)

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
