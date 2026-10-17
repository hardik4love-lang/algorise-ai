# 🛡️ Algorise AI Security Research Portfolio & Submission Runbook

**Maintained by:** Algorise AI Security Operations Lead (`founder@algorise.ai`)  
**Payout Destination:** PayPal `shruhicollections@gmail.com`  
**Operational Standard:** Zero Preventable Loss, Dual-Engine Verification, Responsible Disclosure  

---

## 1. Executive Portfolio Master Index

This catalog indexes 10 structured vulnerability advisories and defensive security audits across Tier-1 bug bounty programs (HackerOne, Bugcrowd) and critical open-source ecosystems.

| # | Target Program | Scope / Subsystem | Vulnerability Class | CVSS v3.1 | Submission Portal | Advisory File | Status |
|---|---|---|---|---|---|---|---|
| **01** | **BasedHardware/omi** | `agent_connect/` & `api_key_management.py` | CWE-284 Improper Access Control / CWE-269 Privilege Management | **7.1 (High)** | GitHub Security Advisory / Direct | [`omi_connect_agent_mass_revocation_advisory.md`](file:///D:/projects/algorise-ai/advisories/omi_connect_agent_mass_revocation_advisory.md) | **Staged** |
| **02** | **elizaOS/eliza** | `packages/core/src/runtime.ts` & Actions | CWE-269 Agentic Execution / Tool Sandboxing Boundary | **7.5 (High)** | GitHub Security Advisory | [`elizaos_agentic_tool_sandboxing_audit.md`](file:///D:/projects/algorise-ai/advisories/elizaos_agentic_tool_sandboxing_audit.md) | **Staged** |
| **03** | **GitLab** | CI/CD Pipelines & `DeclarativePolicy` GraphQL | CWE-200 Secret Disclosure / CWE-285 Authorization | **6.5 (Medium)** | HackerOne (`gitlab`) | [`gitlab_cicd_access_control_audit.md`](file:///D:/projects/algorise-ai/advisories/gitlab_cicd_access_control_audit.md) | **Staged** |
| **04** | **Shopify** | Partner API & App Bridge Webhooks | CWE-639 IDOR / Multi-Tenant Isolation | **7.4 (High)** | HackerOne (`shopify`) | [`shopify_partner_api_multitenant_audit.md`](file:///D:/projects/algorise-ai/advisories/shopify_partner_api_multitenant_audit.md) | **Staged** |
| **05** | **Uber** | Mobility Telematics & Driver Partner API | CWE-285 BFLA / Object Level Authorization | **7.8 (High)** | HackerOne (`uber`) | [`uber_mobility_telematics_auth_audit.md`](file:///D:/projects/algorise-ai/advisories/uber_mobility_telematics_auth_audit.md) | **Staged** |
| **06** | **Netflix** | Partner Studio Content Ingestion Pipeline | CWE-918 SSRF / Asset Metadata Boundary | **7.2 (High)** | Bugcrowd (`netflix`) | [`netflix_partner_studio_ingestion_audit.md`](file:///D:/projects/algorise-ai/advisories/netflix_partner_studio_ingestion_audit.md) | **Staged** |
| **07** | **Tesla** | Fleet Telematics API & Command Authorization | CWE-294 Replay Attack / Signature Bypass | **8.1 (High)** | Bugcrowd (`tesla`) | [`tesla_fleet_telematics_api_security_audit.md`](file:///D:/projects/algorise-ai/advisories/tesla_fleet_telematics_api_security_audit.md) | **Staged** |
| **08** | **ExpressVPN** | Desktop Client IPC & Split Tunnel Engine | CWE-269 Privilege Escalation / Local RPC Bypass | **7.3 (High)** | Bugcrowd (`expressvpn`) | [`expressvpn_tunnel_isolation_audit.md`](file:///D:/projects/algorise-ai/advisories/expressvpn_tunnel_isolation_audit.md) | **Staged** |
| **09** | **Upwork** | Enterprise Escrow & Milestone Disbursement | CWE-863 BFLA / Race Condition in Settlement | **8.5 (High)** | HackerOne (`upwork`) | [`upwork_escrow_bfla_audit.md`](file:///D:/projects/algorise-ai/advisories/upwork_escrow_bfla_audit.md) | **Staged** |
| **10** | **Enterprise GraphQL** | Apollo Router / GraphQL Federation Engine | CWE-400 Complexity DoS / Field Directive BFLA | **7.5 (High)** | Cross-Ecosystem CVE / Portals | [`graphql_enterprise_authorization_audit.md`](file:///D:/projects/algorise-ai/advisories/graphql_enterprise_authorization_audit.md) | **Staged** |

---

## 2. Submission Protocol & Pre-Flight Checklist

Before submitting any advisory through official portals (HackerOne / Bugcrowd):

1. **Identity & Authorization Check:**
   - Confirm active session under authorized research handle (`Algorise AI` / `founder@algorise.ai`).
   - Check target program policy on Safe Harbor / Bug Bounty Policy changes.
2. **Proof-of-Concept Verification:**
   - Ensure reproduction steps use strictly non-destructive payloads and test tenant environments.
   - Verify CVSS v3.1 vector string matches exact vulnerability behavior.
3. **Remediation Code & Guidance:**
   - Provide minimal, non-breaking remediation patches and policy configuration adjustments.
4. **Payout Details:**
   - Ensure payout destination is explicitly recorded as PayPal `shruhicollections@gmail.com`.
