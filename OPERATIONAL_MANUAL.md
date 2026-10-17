# 🛡️ High-Throughput Security Research Operations Manual
### Enterprise Architecture & Autonomous Workflow Orchestration
**Target Output:** 10 High-Quality Vulnerability Reports / Day  
**Hosting Model:** 100% Cloud-Native via GitHub Actions ($0.00 Infrastructure Spend)  
**Maintained by:** Algorise AI Security Operations Lead (`founder@algorise.ai`)

---

## Executive Overview
This manual defines a battle-tested, high-performance operational framework engineered for a solo cybersecurity researcher. Designed to systematically eliminate cognitive switching friction, it transitions all background monitoring, asset tracking, and mathematical target scoring to automated GitHub Actions workflows, while providing standardized, modular templates for high-velocity triage and reporting.

```
                           +------------------------------------------+
                           |  Cloud-Hosted GitHub Actions Engine      |
                           |  (.github/workflows/security_ops.yml)   |
                           +------------------------------------------+
                                  |                     |
                  (Every 6 Hours) |                     | (Target Ranking)
                                  v                     v
                    +--------------------+    +--------------------+
                    | Passive Recon &    |    | Target Priority    |
                    | Delta Sweeper      |    | Score (TPS) Calc   |
                    +--------------------+    +--------------------+
                                  |                     |
                                  +----------+----------+
                                             |
                                             v
                    +------------------------------------------------+
                    |  TARGET_PRIORITY_MATRIX.md & Ledger (Git Push) |
                    +------------------------------------------------+
                                             |
                   +-------------------------+-------------------------+
                   |                                                   |
                   v                                                   v
+------------------------------------+              +------------------------------------+
| Deep-Work Exploitation Handoff     |              | Rapid Reporting SOP                |
| - Ranked Top 3 Attack Surfaces     |              | - .github/ISSUE_TEMPLATE/          |
| - Pre-generated Curl & Burp Config |              | - One-Click Markdown Export        |
+------------------------------------+              +------------------------------------+
```

---

## Module 1: Multi-Platform Workflow Orchestration
Managing concurrent activities across **HackerOne**, **Bugcrowd**, and **GitHub** without context fragmentation requires environment isolation, centralized data normalization, and unified notification queues.

### 1.1 Cloud-Native Zero-Cost Architecture (GitHub Actions)
Because local hosting introduces daemon management overhead, hardware wear, and connectivity constraints, the entire operational control plane is deployed directly into GitHub:
- **Runner Environment:** GitHub-Hosted Runner (`ubuntu-latest`, 2-core / 7GB RAM, Free Tier).
- **Execution Interval:** Scheduled every 6 hours (`0 */6 * * *`) and on-demand via `workflow_dispatch`.
- **Target Registry:** Version-controlled JSON in `config/research_targets.json`.
- **Audit Ledger:** Auto-persisted in `data/research_ledger.json` and committed with `[skip ci]`.
- **Zero Local Footprint:** The researcher needs only a browser or mobile device to inspect priorities.

### 1.2 Containerized Workspace Isolation (For Local Deep Work)
When manual verification requires running test scripts or local interception, isolate each target using Docker to prevent cross-contamination and token leakage:

```dockerfile
# devops/Dockerfile.workspace
FROM ubuntu:22.04
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl wget git python3 python3-pip jq ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install --no-cache-dir requests urllib3

WORKDIR /workspace
CMD ["/bin/bash"]
```

Launch isolated workspaces with bind-mounted scoped targets:
```bash
docker run --rm -it \
  --name audit-target-h1-shopify \
  -v "D:/audit/h1-shopify:/workspace" \
  -e "HTTP_PROXY=http://host.docker.internal:8080" \
  security-workspace:latest
```

### 1.3 Notification Aggregation & Dashboarding
To eliminate platform-switching fatigue (constantly refreshing HackerOne, Bugcrowd, and GitHub), all events are normalized into a single stream:
1. **GitHub Repository Step Summary:** Every run writes a formatted markdown overview into `$GITHUB_STEP_SUMMARY`.
2. **Webhook Integration:** If `SECURITY_OPS_WEBHOOK` is set in GitHub Repository Secrets, the engine posts structured JSON directly to Slack, Discord, or Matrix:
```json
{
  "text": "🛡️ *Security Research Ops Update*\nTop Prioritized Targets:\n• #1 Tenstorrent TT-Metal (TPS: 45.33, P0)\n• #2 BasedHardware Omi (TPS: 24.34, P2)"
}
```

---

## Module 2: High-Throughput Temporal Architecture
Reaching a sustained velocity of **10 vulnerability reports per day** is not an issue of typing speed; it is an issue of **cognitive energy conservation**. High-load vulnerability discovery cannot be sustained for 8 continuous hours. Instead, the day is divided into strict, non-overlapping temporal windows:

| Time Window (UTC) | Cognitive Mode | Primary Operational Focus | Cognitive Load |
|---|---|---|---|
| **07:00 – 08:30** | Divergent / Passive | Automated Recon Sweep & Delta Triage | Low |
| **08:30 – 09:00** | Reset | Physical warmup, hydration, zero screens | None |
| **09:00 – 11:30** | Convergent / Deep Focus | **Deep Work Block 1: Exploitation** (P0 Target #1) | **PEAK** |
| **11:30 – 12:30** | Recovery | Nutrition & Walking Break (Full Disconnect) | None |
| **12:30 – 14:30** | Convergent / Deep Focus | **Deep Work Block 2: Exploitation** (P1 Targets #2 & #3) | **PEAK** |
| **14:30 – 16:00** | Execution / Modular | **Rapid Reporting Sprint (10 Reports/Day SOP)** | Medium |
| **16:00 – 17:00** | Administrative | Triage responses, payout tracking, ledger sync | Low |

### Rules of Engagement:
- **Zero Interruption Rule:** During Deep Work Blocks (09:00–11:30 and 12:30–14:30), all email, Slack, and social channels must be terminated.
- **Reporting Separation:** Never write reports while exploiting. File reproduction curl strings into temporary scratch buffers, then write all 10 reports in the dedicated Rapid Reporting Sprint.

---

## Module 3: Quantitative Target Prioritization Matrix
Target selection determines 80% of vulnerability discovery yield. Researchers often waste cognitive capital on low-yield, hyper-competitive targets. We apply the **Target Priority Score (TPS)** formula:

$$\mathbf{TPS} = \frac{V_D \times S_B \times C_T \times R_V \times H_Y}{D_C + 1.0}$$

### Variable Definitions & Calibrations:
1. **$V_D$ — Vulnerability Density ($0.1 - 1.0$):**
   - High churn, legacy codebases, rapid PR velocity, polyglot repositories $\rightarrow 0.8 - 1.0$.
   - Mature, audited, static codebases $\rightarrow 0.2 - 0.4$.
2. **$S_B$ — Scope Breadth ($1 - 10$):**
   - Wildcard subdomains (`*.target.com`), public source code, GraphQL schemas $\rightarrow 8 - 10$.
   - Single static brochure page $\rightarrow 1 - 2$.
3. **$C_T$ — Tech Stack Complexity ($1 - 5$):**
   - Distributed microservices, custom C++/CUDA kernels, multi-tenant RBAC $\rightarrow 4 - 5$.
   - Simple static CMS $\rightarrow 1$.
4. **$R_V$ — Reward Velocity & Payout Tier ($1 - 10$):**
   - Critical bounties $\ge \$2,500$ USD with fast median payout $< 7$ days $\rightarrow 9 - 10$.
   - Swag-only or low bounties $\rightarrow 1 - 3$.
5. **$H_Y$ — Historical Yield Multiplier ($0.5 - 2.0$):**
   - Responsive triage team, low dispute rate, fast acceptance $\rightarrow 1.5 - 2.0$.
   - Slow response ($> 30$ days), high false-duplicate rate $\rightarrow 0.5$.
6. **$D_C$ — Duplicate Competition Penalty ($0 - 5$):**
   - Public, highly advertised program with thousands of hunters $\rightarrow 3 - 5$.
   - Private invite or newly launched open-source program $\rightarrow 0 - 1$.

### Score Normalization & Tiers:
$$\mathbf{TPS}_{\text{norm}} = \min\left(100.0, \frac{\mathbf{TPS}_{\text{raw}}}{600.0} \times 100\right)$$
- **$\ge 45.0$ (P0 - CRITICAL YIELD):** Primary target for Deep Work Block 1.
- **$30.0 - 44.9$ (P1 - HIGH YIELD):** Secondary target for Deep Work Block 2.
- **$15.0 - 29.9$ (P2 - MEDIUM YIELD):** Handled via automated delta sweeps.
- **$< 15.0$ (P3 - BACKLOG):** Passive monitoring only.

---

## Module 4: Scalable Automation-to-Manual Pipeline
Automated tools must never be used to spray intrusive scans indiscriminately. Instead, automation serves as an **intel-gathering pre-filter** that hands pre-triaged attack surfaces to manual exploitation.

```
[Target Inventory (config/research_targets.json)]
                       |
                       v
         [GitHub Actions Scheduled Cron]
                       |
        +--------------+--------------+
        |                             |
        v                             v
[GitHub Target Delta]      [Web/API Posture Audit]
- Release tag diffing       - HTTP status & response time
- Commit log delta          - CSP, HSTS, CORS header checks
        |                             |
        +--------------+--------------+
                       |
                       v
     [Automated Handoff Dossier Generation]
     - Pre-configured curl templates
     - Burp Suite interception strings
     - Targeted Git clone commands
```

### CLI Command Specifications (For Local Tooling When Required):
When running active sub-recon tooling on authorized scopes:
- **Subfinder (Passive Subdomain Enumeration):**
  ```bash
  subfinder -d target.com -all -silent -o subdomains.txt
  ```
- **HTTPX (Asset Filtering & Tech Fingerprinting):**
  ```bash
  httpx -l subdomains.txt -silent -status-code -title -tech-detect -o alive_hosts.txt
  ```
- **Burp Suite Proxy Configuration:**
  Ensure all automated validation traffic routes through Burp Suite upstream:
  ```bash
  export HTTP_PROXY="http://127.0.0.1:8080"
  export HTTPS_PROXY="http://127.0.0.1:8080"
  ```

---

## Module 5: Rapid Reporting Standard Operating Procedure (SOP)
To maintain **10 high-quality reports per day**, reporting must be completely modular. Every advisory is generated using standardized templates located in `.github/ISSUE_TEMPLATE/`:

### Standardized Template Library:
1. `01_idor_bfla_advisory.md` — Insecure Direct Object Reference & Broken Function Level Authorization.
2. `02_xss_injection_advisory.md` — Stored, Reflected, and DOM Cross-Site Scripting.
3. `03_rce_command_injection_advisory.md` — Remote Code Execution & Command Injection.
4. `04_broken_access_control_advisory.md` — Broken Access Control & Vertical Privilege Escalation.
5. `05_target_prioritization_intake.md` — Intake form for newly discovered targets.

### Report Quality Invariants (Zero-Dispute Standard):
Every generated advisory must contain:
1. **Accurate CVSS v3.1 Vector:** Defensible base score with exact metric choices.
2. **Actor Privilege Table:** Clear demarcation between Attacker (User A) and Victim (User B).
3. **Copy-Pasteable Reproduction Steps:** Deterministic steps containing exact HTTP requests and curl commands.
4. **Non-Destructive Validation:** Clear verification without altering or deleting production state.
5. **Code-Level Remediation Guidance:** Concrete code snippets (Python, TypeScript, or Go) illustrating the fix.

---

## Verification & Deployment Checklist
- [x] Target registry configured in `config/research_targets.json`.
- [x] Mathematical $TPS$ engine operational in `scripts/research_ops_engine.py`.
- [x] Automated 6-hour cron workflow deployed in `.github/workflows/security_research_ops.yml`.
- [x] Issue templates deployed in `.github/ISSUE_TEMPLATE/`.
- [x] Target Priority Matrix generated in `TARGET_PRIORITY_MATRIX.md`.
- [x] Zero-cost cloud execution verified with zero local hosting dependencies.
