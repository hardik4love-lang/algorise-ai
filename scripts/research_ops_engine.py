#!/usr/bin/env python3
"""
Cybersecurity Research Operations Engine
High-Throughput Vulnerability Target Prioritization & Cloud Orchestration
Optimized for zero-cost, cloud-native execution in GitHub Actions runners.
"""

import os
import sys
import json
import math
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

DEFAULT_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config", "research_targets.json")
DEFAULT_OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "TARGET_PRIORITY_MATRIX.md")
DEFAULT_LEDGER_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "research_ledger.json")

USER_AGENT = "Mozilla/5.0 (compatible; SecurityOpsResearcher/1.0; +https://github.com/hardik4love-lang/algorise-ai)"

def load_targets(config_path: str) -> Dict[str, Any]:
    """Loads target configurations from JSON file."""
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)

def calculate_target_priority_score(target: Dict[str, Any], weights: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
    """
    Computes Target Priority Score (TPS) using the formal weighted formula:
    
    TPS_raw = (V_D * S_B * C_T * R_V * H_Y) / (D_C + 1.0)
    
    Where:
      V_D = Estimated Vulnerability Density (0.1 - 1.0)
      S_B = Scope Breadth (1 - 10)
      C_T = Tech Stack Complexity (1 - 5)
      R_V = Reward Velocity (1 - 10)
      H_Y = Historical Yield (0.5 - 2.0)
      D_C = Duplicate Competition Penalty (0 - 5)
    """
    vars_dict = target.get("variables", {})
    vd = float(vars_dict.get("V_D", 0.5))
    sb = float(vars_dict.get("S_B", 5.0))
    ct = float(vars_dict.get("C_T", 3.0))
    rv = float(vars_dict.get("R_V", 5.0))
    hy = float(vars_dict.get("H_Y", 1.0))
    dc = float(vars_dict.get("D_C", 1.0))

    if weights:
        vd *= float(weights.get("vulnerability_density", 1.0))
        sb *= float(weights.get("scope_breadth", 1.0))
        ct *= float(weights.get("tech_stack_complexity", 1.0))
        rv *= float(weights.get("reward_velocity", 1.0))
        hy *= float(weights.get("historical_yield", 1.0))
        dc *= float(weights.get("duplicate_penalty", 1.0))

    numerator = vd * sb * ct * rv * hy
    denominator = dc + 1.0
    tps_raw = numerator / denominator if denominator > 0 else 0.0

    # Normalized TPS (0.0 to 100.0 scale)
    # Theoretical max raw: (1.0 * 10 * 5 * 10 * 2.0) / 1.0 = 1000.0
    tps_normalized = min(100.0, round((tps_raw / 600.0) * 100.0, 2))

    # Priority Tier assignment
    if tps_normalized >= 45.0:
        tier = "P0 - CRITICAL YIELD"
        recommendation = "Immediate Deep Exploitation (Block 1 / Block 2)"
    elif tps_normalized >= 30.0:
        tier = "P1 - HIGH YIELD"
        recommendation = "Secondary Deep Exploitation / High ROI"
    elif tps_normalized >= 15.0:
        tier = "P2 - MEDIUM YIELD"
        recommendation = "Automated Recon & Delta Watch"
    else:
        tier = "P3 - LOW / BACKLOG"
        recommendation = "Passive Tracking Only"

    return {
        "tps_raw": round(tps_raw, 2),
        "tps_normalized": tps_normalized,
        "tier": tier,
        "recommendation": recommendation,
        "variables": {
            "V_D": vd,
            "S_B": sb,
            "C_T": ct,
            "R_V": rv,
            "H_Y": hy,
            "D_C": dc
        }
    }

def inspect_github_target(repo: str, token: Optional[str] = None) -> Dict[str, Any]:
    """Inspects GitHub repository for latest releases and commit deltas."""
    headers = {"User-Agent": USER_AGENT, "Accept": "application/vnd.github.v3+json"}
    if token:
        headers["Authorization"] = f"token {token}"

    res = {"latest_release": "N/A", "latest_commit": "N/A", "active_issues": 0, "status": "ONLINE"}
    
    # 1. Fetch latest release
    rel_url = f"https://api.github.com/repos/{repo}/releases/latest"
    try:
        req = urllib.request.Request(rel_url, headers=headers)
        with urllib.request.urlopen(req, timeout=4.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            res["latest_release"] = data.get("tag_name", "None")
    except Exception as e:
        res["latest_release"] = "No formal release"

    # 2. Fetch latest commit
    commit_url = f"https://api.github.com/repos/{repo}/commits?per_page=1"
    try:
        req = urllib.request.Request(commit_url, headers=headers)
        with urllib.request.urlopen(req, timeout=4.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data and isinstance(data, list):
                sha = data[0].get("sha", "")[:7]
                date = data[0].get("commit", {}).get("author", {}).get("date", "")[:10]
                res["latest_commit"] = f"{sha} ({date})"
    except Exception as e:
        res["latest_commit"] = "Unknown"

    return res

def inspect_passive_endpoint(url: str) -> Dict[str, Any]:
    """Performs passive HTTP header reconnaissance (CORS, CSP, HSTS, Server)."""
    headers = {"User-Agent": USER_AGENT}
    res = {
        "http_status": 0,
        "server": "Redacted/Hidden",
        "csp": False,
        "hsts": False,
        "cors_wildcard": False,
        "status": "OFFLINE"
    }
    try:
        req = urllib.request.Request(url, headers=headers, method="GET")
        with urllib.request.urlopen(req, timeout=3.5) as resp:
            res["http_status"] = resp.status
            res["status"] = "ONLINE" if resp.status < 400 else "DEGRADED"
            resp_headers = {k.lower(): v for k, v in resp.headers.items()}
            res["server"] = resp_headers.get("server", "N/A")
            res["csp"] = "content-security-policy" in resp_headers
            res["hsts"] = "strict-transport-security" in resp_headers
            res["cors_wildcard"] = resp_headers.get("access-control-allow-origin") == "*"
    except urllib.error.HTTPError as e:
        res["http_status"] = e.code
        res["status"] = "REACHABLE"
    except Exception:
        res["status"] = "TIMEOUT"
    return res

def run_research_ops_cycle(config_path: str, ledger_path: str, mode: str = "full") -> List[Dict[str, Any]]:
    """Runs a complete research operations evaluation cycle."""
    config = load_targets(config_path)
    weights = config.get("scoring_weights", {})
    targets = config.get("targets", [])
    gh_token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")

    evaluated_targets = []

    for t in targets:
        if not t.get("active", True):
            continue

        score_data = calculate_target_priority_score(t, weights)
        
        # Passive recon step
        recon_data = {}
        if mode == "full":
            if t.get("platform") == "github" and t.get("repo"):
                recon_data = inspect_github_target(t["repo"], gh_token)
            elif t.get("asset_endpoints"):
                recon_data = inspect_passive_endpoint(t["asset_endpoints"][0])

        merged = {
            **t,
            "scoring": score_data,
            "recon": recon_data
        }
        evaluated_targets.append(merged)

    # Sort descending by normalized TPS
    evaluated_targets.sort(key=lambda x: x["scoring"]["tps_normalized"], reverse=True)
    return evaluated_targets

def generate_markdown_matrix(evaluated: List[Dict[str, Any]], output_path: str) -> str:
    """Renders the comprehensive Target Priority Matrix markdown report."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    
    p0_count = sum(1 for x in evaluated if "P0" in x["scoring"]["tier"])
    p1_count = sum(1 for x in evaluated if "P1" in x["scoring"]["tier"])
    avg_tps = round(sum(x["scoring"]["tps_normalized"] for x in evaluated) / len(evaluated), 2) if evaluated else 0.0

    lines = []
    lines.append(f"# 🛡️ Security Research Target Priority Matrix (TPS)")
    lines.append(f"**Generated:** `{now}` | **Engine Status:** `ONLINE (Cloud GitHub Actions)` | **Active Targets:** `{len(evaluated)}`\n")
    
    # Executive Summary Cards
    lines.append("## 📊 Operational Throughput Overview")
    lines.append("| Metric | Value | Threshold / SLA |")
    lines.append("|---|---|---|")
    lines.append(f"| **P0 Critical Targets** | `{p0_count}` | Prioritize in Daily Deep Work Block 1 |")
    lines.append(f"| **P1 High Targets** | `{p1_count}` | Allocate to Daily Deep Work Block 2 |")
    lines.append(f"| **Mean Target Priority Score** | `{avg_tps} / 100` | Baseline Health $\\ge 30.0$ |")
    lines.append(f"| **Daily Report Throughput Target** | `10 Valid Reports/Day` | SOP Modular Templates Deployed |")
    lines.append(f"| **Target Environment** | `GitHub Actions (Free)` | $0.00 Infrastructure Spend |\n")

    # High-Throughput Daily Temporal Schedule Mapping
    lines.append("## ⏱️ Daily High-Throughput Schedule Alignment (10 Reports/Day)")
    lines.append("Optimized non-overlapping cognitive windows to eliminate context-switching friction:\n")
    
    t0_name = evaluated[0]["name"] if len(evaluated) > 0 else "N/A"
    t1_name = evaluated[1]["name"] if len(evaluated) > 1 else "N/A"
    t2_name = evaluated[2]["name"] if len(evaluated) > 2 else "N/A"

    lines.append(f"1. **07:00 – 08:30 UTC [Recon Sweep & Diff Triage]**: Passive release tracking, delta monitoring, and queue generation.")
    lines.append(f"2. **09:00 – 11:30 UTC [Deep Exploitation Block 1 (Peak Focus)]**: Focus on `{t0_name}` (Target Priority Rank #1).")
    lines.append(f"3. **11:30 – 12:30 UTC [Strategic Recovery & Nutrition]**: Disconnect to prevent cognitive fatigue.")
    lines.append(f"4. **12:30 – 14:30 UTC [Deep Exploitation Block 2 (Second Peak)]**: Focus on `{t1_name}` and `{t2_name}`.")
    lines.append(f"5. **14:30 – 16:00 UTC [Rapid Reporting Sprint]**: Execute SOP Markdown generation using `.github/ISSUE_TEMPLATE/` advisories.")
    lines.append(f"6. **16:00 – 17:00 UTC [Admin, Triage Responses & Settlement Sync]**: Handle bounty portal responses & payout tracking.\n")

    # Target Ranking Matrix Table
    lines.append("## 🎯 Quantitative Target Priority Score (TPS) Ranking")
    lines.append("| Rank | Target / Platform | Scope Type | TPS (Norm) | Priority Tier | Primary Attack Vectors | Status / Delta |")
    lines.append("|---|---|---|---|---|---|---|")

    for i, t in enumerate(evaluated, 1):
        name = t["name"]
        platform = t["platform"].capitalize()
        scope = t["scope_type"]
        tps = t["scoring"]["tps_normalized"]
        tier = t["scoring"]["tier"]
        tags = ", ".join(f"`{tag}`" for tag in t.get("triage_tags", [])[:3])
        
        recon = t.get("recon", {})
        if t["platform"] == "github":
            status = f"Rel: `{recon.get('latest_release', 'N/A')}`"
        else:
            status = f"HTTP: `{recon.get('http_status', 'N/A')}` ({recon.get('status', 'OK')})"
        
        url = t.get("scope_url", "#")
        lines.append(f"| **#{i}** | [{name}]({url})<br>`({platform})` | `{scope}` | **`{tps}`** | `{tier}` | {tags} | {status} |")

    lines.append("\n## 🔍 Target Handoff & Action Protocols")
    for i, t in enumerate(evaluated[:3], 1):
        lines.append(f"### #{i} {t['name']} (`{t['platform'].capitalize()}`)")
        lines.append(f"- **Scope Reference:** [{t['scope_url']}]({t['scope_url']})")
        lines.append(f"- **Calculated TPS:** `{t['scoring']['tps_normalized']} / 100` (`{t['scoring']['tier']}`)")
        lines.append(f"- **Scoring Formula Breakdown:** $V_D={t['scoring']['variables']['V_D']}, S_B={t['scoring']['variables']['S_B']}, C_T={t['scoring']['variables']['C_T']}, R_V={t['scoring']['variables']['R_V']}, H_Y={t['scoring']['variables']['H_Y']}, D_C={t['scoring']['variables']['D_C']}$")
        lines.append(f"- **Recommended Handoff Action:** {t['scoring']['recommendation']}")
        
        # Code snippet handoff
        if t["platform"] == "github":
            repo = t.get("repo", "")
            lines.append(f"```bash\n# GitHub Target Delta Audit Protocol\ngh repo clone {repo} d:\\audit\\{t['target_id']}\ngit log -n 5 --oneline\n```")
        else:
            first_endpoint = t["asset_endpoints"][0] if t.get("asset_endpoints") else "https://target.com"
            lines.append(f"```bash\n# Web/API Target Interception Handoff\ncurl -ik -s -X GET \"{first_endpoint}\" \\\n  -H \"User-Agent: SecurityOpsResearch/1.0\" \\\n  -x \"http://127.0.0.1:8080\"\n```")
        lines.append("")

    lines.append("---\n*Automated report generated by Algorise Security Research Ops Engine. All rights reserved.*")
    
    content = "\n".join(lines) + "\n"
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)

    return content

def update_research_ledger(evaluated: List[Dict[str, Any]], ledger_path: str):
    """Appends execution record to historical research ledger."""
    os.makedirs(os.path.dirname(ledger_path), exist_ok=True)
    
    history = []
    if os.path.exists(ledger_path):
        try:
            with open(ledger_path, "r", encoding="utf-8") as f:
                history = json.load(f)
        except Exception:
            history = []

    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_targets": len(evaluated),
        "top_targets": [
            {
                "target_id": t["target_id"],
                "name": t["name"],
                "platform": t["platform"],
                "tps_normalized": t["scoring"]["tps_normalized"],
                "tier": t["scoring"]["tier"]
            }
            for t in evaluated[:5]
        ]
    }
    history.append(record)
    # Keep last 100 historical entries
    history = history[-100:]

    with open(ledger_path, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2)

def dispatch_webhook(evaluated: List[Dict[str, Any]], webhook_url: str):
    """Dispatches JSON alert to external webhook (Slack/Discord/Matrix)."""
    if not webhook_url:
        return
    
    top3 = evaluated[:3]
    text_lines = [
        "🛡️ *Security Research Ops Update*",
        f"Top Prioritized Targets ({datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}):"
    ]
    for i, t in enumerate(top3, 1):
        text_lines.append(f"• *#{i} {t['name']}* (`{t['platform']}`) - TPS: `{t['scoring']['tps_normalized']}` ({t['scoring']['tier']})")

    payload = {"text": "\n".join(text_lines)}
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(webhook_url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=5.0) as resp:
            print(f"[WEBHOOK] Notification dispatched successfully: HTTP {resp.status}")
    except Exception as e:
        print(f"[WEBHOOK ERROR] Failed to dispatch webhook: {e}")

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Security Research Operations Engine")
    parser.add_argument("--config", default=DEFAULT_CONFIG_PATH, help="Path to research targets JSON")
    parser.add_argument("--output", default=DEFAULT_OUTPUT_PATH, help="Output Markdown Matrix path")
    parser.add_argument("--ledger", default=DEFAULT_LEDGER_PATH, help="Path to research ledger JSON")
    parser.add_argument("--mode", default="full", choices=["full", "fast"], help="Execution mode")
    parser.add_argument("--webhook", default=os.environ.get("SECURITY_OPS_WEBHOOK", ""), help="Webhook URL")
    parser.add_argument("--summary", action="store_true", help="Print summary to stdout")
    args = parser.parse_args()

    print(f"[*] Starting Security Research Ops Engine (Mode: {args.mode})...")
    evaluated = run_research_ops_cycle(args.config, args.ledger, mode=args.mode)
    print(f"[+] Evaluated {len(evaluated)} active targets.")

    md_content = generate_markdown_matrix(evaluated, args.output)
    print(f"[+] Rendered priority matrix to: {args.output}")

    update_research_ledger(evaluated, args.ledger)
    print(f"[+] Updated research ledger at: {args.ledger}")

    # GitHub Actions Step Summary Support
    step_summary_file = os.environ.get("GITHUB_STEP_SUMMARY")
    if step_summary_file:
        try:
            with open(step_summary_file, "a", encoding="utf-8") as f:
                f.write(md_content)
            print("[+] Exported matrix to $GITHUB_STEP_SUMMARY")
        except Exception as e:
            print(f"[-] Could not write to GITHUB_STEP_SUMMARY: {e}")

    if args.webhook:
        dispatch_webhook(evaluated, args.webhook)

    if args.summary:
        print("\n" + md_content)

    print("[*] Security Research Ops Cycle completed successfully.")

if __name__ == "__main__":
    main()
