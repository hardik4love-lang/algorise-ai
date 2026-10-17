---
name: "SOP-05: Target Prioritization Intake & Re-Scoring"
about: "Intake request to evaluate and add a new bounty program or repository into the Target Priority Matrix."
title: "[TARGET INTAKE] <Target Name> (<Platform>)"
labels: ["target-intake", "tps-evaluation"]
assignees: []
---

## 🎯 Target Intake Dossier

### 1. Target Metadata
- **Target Name:** `[Target Company / Repository]`
- **Platform:** `HackerOne / Bugcrowd / GitHub`
- **Scope URL:** `https://...`
- **Scope Type:** `web_api / source_code / mobile_backend / cloud_infrastructure`
- **Primary Asset Endpoints / Repos:**
  - `https://api.target.com`
  - `target-org/target-repo`

### 2. Variable Estimates for Target Priority Score (TPS)
$$TPS = \frac{V_D \times S_B \times C_T \times R_V \times H_Y}{D_C + 1.0}$$

- **Vulnerability Density ($V_D$, 0.1 - 1.0):** `0.7` (e.g. rapid churn, legacy code)
- **Scope Breadth ($S_B$, 1 - 10):** `8.0` (e.g. wildcard domains, comprehensive APIs)
- **Tech Stack Complexity ($C_T$, 1 - 5):** `4.0` (e.g. polyglot microservices, GraphQL)
- **Reward Velocity ($R_V$, 1 - 10):** `9.0` (e.g. fast payouts, high bounty table)
- **Historical Yield ($H_Y$, 0.5 - 2.0):** `1.5` (e.g. responsive security team)
- **Duplicate Competition ($D_C$, 0 - 5):** `1.0` (e.g. private invite or niche stack)

### 3. Attack Vector Focus
- [ ] IDOR / Broken Object-Level Authorization (BOLA)
- [ ] Cross-Site Scripting (XSS)
- [ ] Broken Access Control (BAC)
- [ ] Remote Code Execution / Command Injection (RCE)
- [ ] Server-Side Request Forgery (SSRF)
- [ ] Business Logic Flaws & Race Conditions
