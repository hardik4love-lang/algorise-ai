# 🛡️ High-Throughput Security Research Operations Manual
## Enterprise Workflow Architecture & Solo Researcher Methodology (10 Reports/Day)
**Target Output:** 10 High-Quality, Zero-Dispute Vulnerability Disclosures / Day  
**Operational Scope:** HackerOne, Bugcrowd, and GitHub Open-Source Security  
**Architectural Baseline:** Cloud-Native Automation & Strict Cognitive Separation  
**Maintained by:** Algorise AI Security Operations (`hardik4love-lang/algorise-ai`)

---

## Executive Summary

Reaching a sustained output of **10 actionable vulnerability reports per day** as a solo security researcher is fundamentally an engineering and cognitive optimization problem. Researchers rarely fail due to technical insufficiency; they fail because of **cognitive context fragmentation**, notification fatigue, time mismanagement, and inefficient manual reporting friction.

This manual establishes an industrial-grade operational standard engineered to eliminate task-switching overhead, automate continuous reconnaissance via GitHub Actions, apply a deterministic mathematical target scoring matrix, and maintain an uninterrupted flow-state for deep technical exploitation.

```
+---------------------------------------------------------------------------------------+
|                                24/7 CLOUD CONTROL PLANE                               |
|                  Automated Delta Watcher, Asset Sweeper & TPS Matrix                  |
|                        (.github/workflows/security_ops.yml)                           |
+---------------------------------------------------------------------------------------+
                                           |
                                           v
+---------------------------------------------------------------------------------------+
|                               STANDARDIZED WORKSPACES                                 |
|          Docker Sandbox Containers  •  Burp Project Separation  •  Unified Feed       |
+---------------------------------------------------------------------------------------+
                                           |
       +-----------------------------------+-----------------------------------+
       |                                                                       |
       v                                                                       v
+-----------------------------+                                 +-----------------------------+
|    DEEP-WORK BLOCK 1 & 2    |                                 |    RAPID REPORTING SPRINT   |
|   09:00-11:30 & 12:30-14:30 |                                 |         14:30 - 16:00       |
|  - Manual Target Focus (P0) |  ======[ Scratch Dossier ]====> |  - 10 Modular Reports/Day   |
|  - Zero Inbound Distraction |                                 |  - CVSS v3.1 Deterministic  |
|  - Interactive Verification |                                 |  - One-Click Platform Post  |
+-----------------------------+                                 +-----------------------------+
```

---

## 1. Multi-Platform Workflow Orchestration

Operating concurrently across **HackerOne**, **Bugcrowd**, and **GitHub** creates severe mental fatigue if workspaces and communications are mingled. A solo researcher must treat each target as an isolated compute environment while aggregating all telemetry into a centralized, low-noise control stream.

### 1.1 Environment Isolation & Containerized Workspaces
Never run recon tools, test scripts, or proxy configurations for multiple platforms in a single unsegregated OS shell. Use dedicated containerized workspaces with pre-configured network isolation:

```dockerfile
# devops/Dockerfile.security_workspace
FROM ubuntu:22.04
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl wget git python3 python3-pip jq ca-certificates \
    dnsutils nmap netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install --no-cache-dir requests urllib3 pyjwt cryptography

WORKDIR /workspace
ENTRYPOINT ["/bin/bash"]
```

#### Deterministic Workspace Spawning Protocol:
Spawn an isolated ephemeral container for each active audit target. Mount local evidence storage while routing outbound HTTP through an isolated Burp proxy listener:

```bash
# HackerOne Target Workspace
docker run --rm -it \
  --name audit-h1-shopify \
  -v "D:/audit/h1-shopify/evidence:/workspace/evidence" \
  -e "HTTP_PROXY=http://host.docker.internal:8080" \
  -e "HTTPS_PROXY=http://host.docker.internal:8080" \
  algorise/security-workspace:latest

# Bugcrowd Target Workspace (Separate Upstream Port)
docker run --rm -it \
  --name audit-bc-tesla \
  -v "D:/audit/bc-tesla/evidence:/workspace/evidence" \
  -e "HTTP_PROXY=http://host.docker.internal:8081" \
  -e "HTTPS_PROXY=http://host.docker.internal:8081" \
  algorise/security-workspace:latest
```

### 1.2 Deterministic Directory Layout & Vault Structure
Structure the local filesystem so that context is completely partitioned by platform and target program:

```
D:\audit\
├── h1-shopify\                  # Platform: HackerOne | Program: Shopify
│   ├── config.json              # Scopes, out-of-scope regex, policy rules
│   ├── targets.txt              # Active assets identified by automation
│   ├── requests\                # Raw HTTP request dumps (.req)
│   ├── evidence\                # Screen captures, logs, execution traces
│   └── scratch.md               # Raw scratch buffer for PoC curl snippets
├── bc-tesla\                    # Platform: Bugcrowd | Program: Tesla
│   ├── config.json
│   ├── targets.txt
│   └── scratch.md
└── gh-tenstorrent\              # Platform: GitHub | Program: Tenstorrent
    ├── repo\                    # Local cloned repository tree
    ├── harness\                 # Local harness reproduction scripts
    └── scratch.md
```

### 1.3 Notification Filtering & Cognitive Gateways
Do not allow email or mobile notifications from HackerOne, Bugcrowd, and GitHub to interrupt active work. Filter notifications into strict tiers:

1. **P0 (Actionable Settlement & Critical Info):** Bounty Awarded, Mediation Required, Critical Scope Update $\rightarrow$ Routed directly to the Telegram Executive Bot (`@Arya_ah_bot`) or dedicated VIP inbox.
2. **P1 (Administrative Triage):** Triaged, Needs More Info, Pending Disclosure $\rightarrow$ Batched for processing strictly during the Administrative Window (16:00–17:00 UTC).
3. **P2 (Noise / Non-Actionable):** Program updates, marketing blasts, general newsletter $\rightarrow$ Silently archived and discarded.

---

## 2. High-Throughput Daily Schedule (The 10-Report Routine)

Sustaining 10 high-quality vulnerability submissions every day requires rigid time-blocking. Cognitive fatigue sets in after 90–120 minutes of intense vulnerability analysis. The schedule enforces non-overlapping blocks for automated recon, deep exploitation, and report generation.

| Time Window (UTC) | Operational Block | Cognitive State | Primary Activity & Deliverables | Focus Mode |
|---|---|---|---|---|
| **07:00 – 08:30** | **Recon & Delta Triage** | Divergent / Analytical | Review automated GitHub Actions diffs, newly resolved endpoints, certificate transparency alerts. Select top 3 targets. | Low Noise |
| **08:30 – 09:00** | **Cognitive Reset** | Rest / Disconnect | Physical warmup, hydration, zero screens. Clear working memory. | Zero Screen |
| **09:00 – 11:30** | **Deep Work Block 1** | Convergent / Intense | **Target #1 (P0 Yield).** Manual verification of complex logic bugs (IDOR, BFLA, Race Conditions, Kernel Unpack Assertions). | **PEAK FLOW** |
| **11:30 – 12:30** | **Decompression & Nutrition** | Recovery | Walking break, lunch, mental detachment. Prevents afternoon slump. | Zero Screen |
| **12:30 – 14:30** | **Deep Work Block 2** | Convergent / Intense | **Targets #2 & #3 (P1 Yield).** Second attack surface sweep (GraphQL introspection, token leakage, auth bypass). | **PEAK FLOW** |
| **14:30 – 16:00** | **Rapid Reporting Sprint** | Execution / Modular | **The 10-Report Factory.** Convert scratch buffer notes into 10 structured Markdown advisories using pre-built modular templates. | High Velocity |
| **16:00 – 17:00** | **Admin & Settlement Sync** | Administrative | Process triage queries, verify PayPal settlement deposits, update research ledger, stage next day crons. | Low Intensity |

### Rules of Engagement:
* **The Zero-Interruption Invariant:** During Deep Work Blocks (09:00–11:30 and 12:30–14:30), all email, chat, and non-essential terminals are strictly terminated.
* **Separation of Exploitation and Reporting:** Never draft a formal submission during an exploitation block. When a bug is verified, dump the raw `curl` string and token trace into `scratch.md` in $<60$ seconds, then immediately continue hunting. All reporting occurs in the dedicated sprint (14:30–16:00).

---

## 3. Dynamic Target Prioritization Matrix (TPS)

Target selection governs 80% of researcher yield. Working on hyper-saturated public web assets yields duplicate reports and disputes. The researcher must algorithmically score every target using the quantitative **Target Priority Score (TPS)** formula before writing a single line of code.

### 3.1 The Formal Scoring Formula

$$\mathbf{TPS}_{\text{raw}} = \frac{V_D \times S_B \times C_T \times R_V \times H_Y}{D_C + 1.0}$$

$$\mathbf{TPS}_{\text{norm}} = \min\left(100.0, \;\frac{\mathbf{TPS}_{\text{raw}}}{600.0} \times 100.0\right)$$

### 3.2 Parameter Definitions & Calibrations

| Parameter | Metric Name | Value Range | Technical Indicator / Criterion |
|---|---|---|---|
| **$V_D$** | Vulnerability Density | $0.1 - 1.0$ | High code churn, polyglot architecture, frequent PR merges, active issue tracker ($0.8 - 1.0$). Static legacy code ($0.2 - 0.4$). |
| **$S_B$** | Scope Breadth | $1.0 - 10.0$ | Wildcard subdomains (`*.domain.com`), microservice meshes, public source code ($8.0 - 10.0$). Single static web page ($1.0 - 2.0$). |
| **$C_T$** | Tech Stack Complexity | $1.0 - 5.0$ | Hardware compute kernels (C++/CUDA), multi-tenant OAuth, distributed state ($4.0 - 5.0$). Standard monolithic web app ($2.0$). |
| **$R_V$** | Reward Velocity | $1.0 - 10.0$ | Critical bounty $\ge \$2,500$ USD with median payout $< 7$ days ($9.0 - 10.0$). Low bounty or slow payout ($1.0 - 3.0$). |
| **$H_Y$** | Historical Yield Multiplier | $0.5 - 2.0$ | Responsive security team, fast triage, high conversion to paid bounty ($1.5 - 2.0$). High dispute / slow triage ($0.5$). |
| **$D_C$** | Duplicate Competition Penalty | $0.0 - 5.0$ | Public program with $> 1,000$ active hackers ($3.0 - 5.0$). Newly launched or high-barrier codebase ($0.0 - 1.0$). |

### 3.3 Target Priority Tiers
* **Tier P0 — Critical Yield ($\mathbf{TPS}_{\text{norm}} \ge 45.0$):** Mandatory target for Deep Work Block 1 (e.g., Tenstorrent TT-Metal Kernel Engine).
* **Tier P1 — High Yield ($30.0 \le \mathbf{TPS}_{\text{norm}} < 45.0$):** Mandatory target for Deep Work Block 2 (e.g., BasedHardware Omi, GitLab CI/CD).
* **Tier P2 — Medium Yield ($15.0 \le \mathbf{TPS}_{\text{norm}} < 30.0$):** Secondary attack surface for automated delta alerts (e.g., Shopify, Uber, Cal.com).
* **Tier P3 — Backlog ($< 15.0$):** Passive asset collection only; no active manual deep work.

---

## 4. Scalable Automation Integration Strategy

Automated vulnerability scanners produce noise, rate-limit bans, and low-severity duplicates. Automation in this framework is strictly utilized as a **continuous asset differencing engine** that feeds actionable attack surface changes into the researcher's staging queue.

### 4.1 Cloud-Native Automated Architecture (GitHub Actions)
The entire recon and delta discovery loop is executed in GitHub Actions runners at zero infrastructure cost:

```
[Cron Trigger: 0 */6 * * *]
            |
            v
+-----------------------------------------------------------+
| GitHub Actions Runner (ubuntu-latest)                    |
| - Pulls config/research_targets.json                      |
| - Executes scripts/research_ops_engine.py                 |
+-----------------------------------------------------------+
            |
            +-----------------------+-----------------------+
            |                                               |
            v                                               v
+-----------------------+                       +-----------------------+
|  GitHub Target Delta  |                       |  Web API Delta Check  |
|  - Tag & Release Diff |                       |  - Endpoint Liveness  |
|  - Git Commit Logs    |                       |  - Header Disclosures |
+-----------------------+                       +-----------------------+
            |                                               |
            +-----------------------+-----------------------+
                                    |
                                    v
+-----------------------------------------------------------+
| Automated Handoff Dossier Generation                      |
| - Commits updated TARGET_PRIORITY_MATRIX.md               |
| - Emits pre-configured curl payloads                      |
| - Dispatches alert to Telegram Bot                        |
+-----------------------------------------------------------+
```

### 4.2 Seamless Automated-to-Manual Handoff Pipeline
When an automated delta is flagged, the system automatically generates an exploitation dossier containing exact commands for manual inspection:

```bash
# Example Automated Dossier Output: Target #1 Tenstorrent
# Generated by research_ops_engine.py at 07:15 UTC

# 1. Clone repository delta:
git clone --depth 20 https://github.com/tenstorrent/tt-metal.git d:\audit\gh-tenstorrent\repo
cd d:\audit\gh-tenstorrent\repo
git diff v0.79.0..v0.80.0 -- tt_metal/impl/buffers/

# 2. Pre-configured memory bounds check command:
pytest tests/ttnn/unit_tests/operations/test_matmul.py -k "test_fp32_unpack"
```

The researcher does not spend 30 minutes configuring tests. They copy the pre-built command, execute it inside their containerized workspace, and immediately begin manual probe analysis.

---

## 5. Standardized High-Velocity Reporting & Submission Pipeline

Writing 10 unique, high-quality vulnerability reports every single day requires a standardized manufacturing line. Reports must be deterministic, mathematically defensible, and structured to prevent triage disputes.

### 5.1 Standardized Advisory Library (`.github/ISSUE_TEMPLATE/`)
Every submission is compiled from battle-tested markdown templates:
1. `01_idor_bfla_advisory.md` — Object-level & function-level authorization bypasses.
2. `02_xss_injection_advisory.md` — Contextual HTML/JS script injection.
3. `03_rce_command_injection_advisory.md` — Shell breakout and unsanitized system calls.
4. `04_broken_access_control_advisory.md` — Tenant isolation failure & privilege escalation.
5. `05_target_prioritization_intake.md` — Intake specification for newly scoped programs.

### 5.2 The 5 Invariants of an Uncontestable Report
Every report submitted to HackerOne, Bugcrowd, or GitHub must contain all five components:

1. **Defensible CVSS v3.1 Vector:** Clear metric selection with no artificial inflation.
2. **Attacker vs. Victim Actor Matrix:** Exact privilege demarcation:
   * *Attacker:* Unauthenticated / Low-Privilege Tenant (User A, Org 1).
   * *Victim:* High-Privilege Tenant / System Admin (User B, Org 2).
3. **Deterministic, Non-Destructive PoC:** Exact `curl` commands using harmless test entities.
4. **Impact Evidence:** Raw HTTP request and response pairs demonstrating unauthorized state access.
5. **Code-Level Remediation Patch:** Concrete fix snippet (Python, TypeScript, or Go) enabling the engineering team to resolve the issue immediately.

### 5.3 One-Click Multi-Platform Submission Protocol
During the **Rapid Reporting Sprint (14:30–16:00)**:
1. Open the target program submission form.
2. Copy the pre-rendered Markdown from `.github/ISSUE_TEMPLATE/` populated during Deep Work.
3. Attach the sanitized screen recording or Burp HTTP log.
4. Submit report and record submission timestamp in `data/research_ledger.json`.
5. Move immediately to the next report. (Target cadence: **9 minutes per report = 10 reports in 90 minutes**).

---

## 6. Implementation Verification & Repository Links

All components of this operational architecture are deployed and maintained in the root of our GitHub repository:

* **Operational Manual:** [`SECURITY_RESEARCH_OPERATIONS_MANUAL.md`](file:///D:/projects/algorise-ai/SECURITY_RESEARCH_OPERATIONS_MANUAL.md)
* **Mathematical TPS Engine:** [`scripts/research_ops_engine.py`](file:///D:/projects/algorise-ai/scripts/research_ops_engine.py)
* **Target Registry & Calibration:** [`config/research_targets.json`](file:///D:/projects/algorise-ai/config/research_targets.json)
* **Cloud Scheduled Workflow:** [`.github/workflows/security_research_ops.yml`](file:///D:/projects/algorise-ai/.github/workflows/security_research_ops.yml)
* **Live Target Matrix:** [`TARGET_PRIORITY_MATRIX.md`](file:///D:/projects/algorise-ai/TARGET_PRIORITY_MATRIX.md)
* **Modular Issue Templates:** [`.github/ISSUE_TEMPLATE/`](file:///D:/projects/algorise-ai/.github/ISSUE_TEMPLATE/)
