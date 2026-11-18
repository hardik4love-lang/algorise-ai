# 📋 Algorise PeopleOS: Commercial Proposal & Service Level Agreement (SLA)

**Document Reference:** `PROP-2026-ALGORISE-ENTERPRISE`  
**Prepared By:** Algorise AI Solutions  
**Client Target:** Manufacturing Plants, Textile Mills, Diamond Units, IT Tech Parks, and Commercial Enterprises  
**Product:** Algorise PeopleOS (Hardware-Free CCTV AI Workforce & Statutory Payroll Operating System)  
**Live Platform:** [https://algorise-ai.com/algorise-payroll/](https://algorise-ai.com/algorise-payroll/)  
**Public Code Verification:** [hardik4love-lang/algorise-payroll](https://github.com/hardik4love-lang/algorise-payroll) (31/31 Passing Tests)

---

## 1. Executive Summary & Value Proposition

Indian enterprises face an average **4.2% undetected payroll leakage** resulting from:
1. **Buddy-Punching & Proxy Attendance:** Colleagues swiping cards or punching biometrics for absent workers.
2. **Biometric Hardware Failure:** Optical fingerprint sensors continually clogged by factory dust, oil, or humidity.
3. **Perimeter Drift:** Employees clocking in at 9:00 AM, leaving the factory grounds for non-work errands, and returning hours later with zero tracking.
4. **Statutory Non-Compliance:** Tedious manual adjustments for FY 2025–26 New Tax Regime slabs, EPF caps, ESIC thresholds, and daily wage (Dihadi) Kharchi advances.

**The Solution:**  
Algorise PeopleOS eliminates 100% of biometric hardware replacement costs by turning your **existing CCTV cameras** into multi-point facial recognition terminals, enforces a **50m Perimeter Sentinel** departure cut-off with automated admin alerts, and runs an unhackable **SHA-256 Merkle audit trail** with 1-click EPFO, ESIC, and TallyPrime generation.

---

## 2. Scope of Delivery

| Component | Technical Delivery Specification |
| :--- | :--- |
| **Multi-Camera CCTV RTSP Ingest** | Ingests up to 16 RTSP streams (Hikvision, CP Plus, Dahua, Uniview) simultaneously with 3D liveness detection (sub-50ms latency). |
| **50m Perimeter Sentinel** | Real-time coordinate boundary monitoring. Triggers 180s grace countdown, auto punch-out, and admin WhatsApp dispatch on departure. |
| **2026 Statutory Payroll Core** | 100% compliant with FY 2025–26: ₹75k standard deduction, Sec 87A rebate, EPF ₹15,000 ceiling, ESIC ₹21,000 limit, and State PT. |
| **Blue-Collar & Dihadi Engine** | Daily wage calculations, piece-rate tracking, Kharchi advance ledger, 2x overtime multipliers, and 1% state BOCW welfare cess. |
| **1-Click Compliance Filing** | Generates official EPFO ECR text format (`#~#`), ESIC CSV, HDFC/ICICI bulk payout files, and Tally ERP 9 / TallyPrime XML journals. |
| **Unhackable Merkle Audit** | SHA-256 cryptographic block chaining across all punches and deductions, rendering internal database tampering mathematically detectable. |
| **Disaster Recovery Sovereignty** | Nightly local AES-256-GCM encrypted database dumps automatically dispatched to client's Gmail inbox + Cloudflare R2 (10GB free offsite storage). |

---

## 3. Commercial Rate Card & Subscription Packages

All packages include full access to all 17 modules, zero per-module add-on charges, and full source code sovereignty.

```
┌────────────────────────┬────────────────────────┬────────────────────────┐
│      SME STARTER       │      FACTORY PRO       │    ENTERPRISE SCALE    │
│    ₹14,999 / month     │    ₹34,999 / month     │    ₹79,999 / month     │
├────────────────────────┼────────────────────────┼────────────────────────┤
│ • Up to 100 Employees  │ • Up to 500 Employees  │ • Unlimited Employees  │
│ • 2 CCTV Camera Feeds  │ • 6 CCTV Camera Feeds  │ • Unlimited Cameras    │
│ • 50m Perimeter Guard  │ • Multi-Gate Sentinel  │ • Multi-Branch Roster  │
│ • Statutory Core 2026  │ • Dihadi & Kharchi     │ • Dedicated Edge Server│
│ • Email / WhatsApp SLA │ • Tally XML Integration│ • Custom ERP Webhooks  │
│ • Standard Backups     │ • Nightly Gmail Encrypt│ • 24x7 Dedicated SRE   │
└────────────────────────┴────────────────────────┴────────────────────────┘
```

*One-Time On-Site Setup & Calibration Fee:* ₹15,000 (Waived on Annual Prepaid Subscriptions).

---

## 4. Demonstrable ROI & Payback Guarantee

```
  Example Analysis for a 300-Employee Manufacturing Unit:
  ─────────────────────────────────────────────────────────────
  Average Monthly Gross Salary:             ₹28,000 / employee
  Total Monthly Payroll:                    ₹84,00,000
  Conservative Payroll Leakage (3.5%):      ₹2,94,000 / month
  Annual Cash Bleed to Proxy/Time-Theft:    ₹35,28,000 / year
  ─────────────────────────────────────────────────────────────
  Algorise Factory Pro Annual Subscription: ₹4,19,988 / year
  NET ANNUAL CLIENT SAVINGS:                ₹31,08,012 / year
  PAYBACK PERIOD:                           Under 6.2 Weeks
```

> **The Algorise Performance Guarantee:**  
> If Algorise PeopleOS does not recover at least 2.5x the subscription fee in avoided time-theft leakage during the first 90 days of operation, Algorise will refund 100% of the platform software fee.

---

## 5. Service Level Agreement (SLA) & Data Sovereignty

1. **Uptime Guarantee:** 99.9% availability for the cloud attendance engine and API endpoints.
2. **Edge Resilience:** If factory internet connectivity goes down, CCTV edge nodes continue buffering facial punches locally and re-sync upon reconnection with cryptographic timestamp verification.
3. **Data Security & Privacy:** All employee biometric templates are stored as irreversibly hashed 512-dimension mathematical vectors, never raw images. PII (PAN, Bank Accounts) is encrypted with AES-256-GCM.
4. **Client Data Ownership:** The client retains 100% ownership of employee databases. Encrypted dumps are delivered directly to the client's own Google Mail and Cloudflare R2 bucket.

---

## 6. Implementation Timeline (48-Hour Rapid Rollout)

* **Hour 0 – 2:** RTSP camera IP mapping and edge credentials handshake (Hikvision / Dahua / CP Plus).
* **Hour 2 – 12:** Employee master roster & face template bulk enrollment (via employee selfie upload or HR web console).
* **Hour 12 – 24:** 50m Perimeter Sentinel boundary calibration and Wi-Fi mesh SSID configuration.
* **Hour 24 – 36:** Statutory shift policy mapping (Rotational shifts, overtime multipliers, Dihadi advances).
* **Hour 36 – 48:** End-to-end dry run: Punch-to-Payslip automated generation & Tally XML ledger verification.

---

## 7. Commercial Acceptance & Sign-Off

To accept this proposal and begin the 48-Hour On-Site CCTV Integration Pilot:

**Client Representative:**  
Name: ___________________________  
Title: ___________________________  
Signature: _______________________  
Date: ___________________________  

**Algorise AI Solutions:**  
Representative: Hardik / Algorise AI  
Title: Enterprise Solutions Director  
Date: 27 October 2026  
Online Booking Reference: [https://algorise-ai.com/algorise-payroll/](https://algorise-ai.com/algorise-payroll/)  
