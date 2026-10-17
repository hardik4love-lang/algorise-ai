---
name: "SOP-01: IDOR / Broken Object-Level Authorization (BOLA/BFLA)"
about: "Rapid reporting template for Insecure Direct Object Reference and Function Level Authorization flaws."
title: "[IDOR/BOLA] Unauthorized Access to Sensitive Resource in <Target Endpoint>"
labels: ["vulnerability-advisory", "idor", "p1-high"]
assignees: []
---

## 🛡️ Vulnerability Title
**[IDOR/BOLA] Insecure Direct Object Reference Allows Unauthorized [Read/Modification/Deletion] of [Resource] via `[Endpoint]`**

---

### 1. Executive Summary
An Insecure Direct Object Reference (IDOR) vulnerability was identified in `[Target Program / Subsystem]`. Specifically, the endpoint `[Vulnerable Endpoint]` does not properly validate that the authenticated caller owns or has administrative authorization over the requested `[object_id / resource_identifier]`. An authenticated attacker can manipulate this parameter to access or alter private records belonging to other tenants/users.

---

### 2. Vulnerability & Impact Classification
- **Target Platform:** HackerOne / Bugcrowd / GitHub
- **Asset / URL:** `https://api.target.com/v1/...`
- **Vulnerability Class:** CWE-639: Authorization Bypass Through User-Controlled Key
- **CVSS v3.1 Vector:** `CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:H/A:N`
- **Base Score:** **8.1 (High)**
- **Severity Tier:** High (P1) / Critical (P0)

---

### 3. Authorization Matrix & Actor Setup
| Actor | Role / Permission Tier | Session Token / Identifier |
|---|---|---|
| **Attacker (User A)** | Standard Authenticated User | `Bearer eyJ...A` (User ID: `10029`) |
| **Victim (User B)** | Target Organization / Victim | `Bearer eyJ...B` (User ID: `10084`, Resource ID: `res_98741`) |

---

### 4. Step-by-Step Reproduction Guide
1. Log in as **Attacker (User A)** and generate a valid session token.
2. Identify a private object owned exclusively by **Victim (User B)** (e.g., `resource_id = res_98741`).
3. Send the following HTTP request using User A's authorization token:

```http
POST /api/v2/organizations/res_98741/billing_records HTTP/1.1
Host: api.target.com
Authorization: Bearer <USER_A_TOKEN>
Content-Type: application/json
Accept: application/json

{
  "action": "export_records",
  "scope": "full"
}
```

4. Observe the response:
```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "status": "success",
  "organization_id": "res_98741",
  "owner_email": "victim@enterprise.com",
  "payment_profiles": [...]
}
```
5. Confirm that the application returned User B's private data to User A without verifying tenant ownership.

---

### 5. Curl Proof of Concept
```bash
curl -ik -s -X GET "https://api.target.com/api/v2/organizations/res_98741/billing_records" \
  -H "Authorization: Bearer <ATTACKER_TOKEN>" \
  -H "Accept: application/json"
```

---

### 6. Remediation & Hardening Guidance
Enforce strict server-side ownership validation at the data-access layer rather than trusting client-supplied identifiers:

```python
# Secure Implementation Pattern (FastAPI / SQLAlchemy)
@router.get("/organizations/{org_id}/billing_records")
def get_billing(org_id: str, current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    # Validate membership or ownership
    membership = db.query(OrgMember).filter_by(org_id=org_id, user_id=current_user.id).first()
    if not membership:
        raise HTTPException(status_code=403, detail="Forbidden: Insufficient privileges for target tenant.")
    return db.query(BillingRecord).filter_by(org_id=org_id).all()
```
