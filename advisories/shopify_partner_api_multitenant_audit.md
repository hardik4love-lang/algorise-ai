# 🛡️ Defensive Architectural Review: Shopify Multi-Tenant Merchant Isolation & App Bridge Authorization

**Target Program:** Shopify Vulnerability Disclosure Program (HackerOne)  
**Scope Surface:** Shopify Commerce Platform, Admin GraphQL API, & Embedded Partner Apps  
**Subject Area:** Merchant Multi-Tenant Boundaries, App Bridge Session Tokens, and Webhook Integrity  
**Assessment Standard:** Defensive Architecture & API Security Hardening  
**Author:** Algorise AI Security Operations Lead (`founder@algorise.ai`)

---

## 1. Executive Architecture Overview

Shopify’s commerce ecosystem serves millions of independent merchants through a unified multi-tenant architecture. Security boundaries depend on two critical enforcement planes:
1. **Merchant Data Boundary Isolation:** Ensuring that internal identifiers (`shop_id`, `customer_id`, `order_id`) cannot be accessed across tenant boundaries via BOLA (Broken Object Level Authorization) or BFLA (Broken Function Level Authorization).
2. **Embedded App Authentication (Shopify App Bridge):** Transitioning from legacy cookie-based OAuth sessions to cryptographically signed JWT Session Tokens passed in the `Authorization: Bearer <token>` header, eliminating Third-Party Cookie deprecation issues and cross-site request forgery (CSRF).

This review details the mathematical and cryptographic invariants required to guarantee zero-leakage merchant multi-tenancy and webhook integrity.

---

## 2. Shopify App Bridge Session Token Validation

### 2.1 Cryptographic Token Structure
Modern Shopify embedded applications receive a short-lived JSON Web Token (JWT) issued by Shopify and verified by the app backend:

$$\text{JWT} = \text{Base64Url}(\text{Header}) \mathbin{\Vert} \text{Base64Url}(\text{Payload}) \mathbin{\Vert} \text{Base64Url}(\text{Signature})$$

```
+--------------------------------------------------------------------------+
| Header:    {"alg": "HS256", "typ": "JWT"}                                |
| Payload:   {                                                             |
|              "iss": "https://{shop}.myshopify.com/admin",                |
|              "dest": "https://{shop}.myshopify.com",                     |
|              "aud": "{api_key}",                                         |
|              "sub": "{user_id}",                                         |
|              "exp": 1792138800,                                          |
|              "nbf": 1792138740,                                          |
|              "iat": 1792138740,                                          |
|              "jti": "d6e3f19a-9e8c-4f1e-8f2e-0a1b2c3d4e5f",              |
|              "sid": "session_id_hash"                                    |
|            }                                                             |
| Signature: HMAC-SHA256(Header + "." + Payload, ClientSecret)             |
+--------------------------------------------------------------------------+
```

### 2.2 Defensive Verification Invariants
When validating incoming session tokens, backends must verify all 6 security invariants:
1. **Signature Verification:** Verified exclusively with the application's `client_secret` using constant-time comparison.
2. **Algorithm Pinning:** Explicitly restrict allowed algorithms to `HS256`. Reject tokens with `alg: "none"` or asymmetric types.
3. **Audience Matching (`aud`):** The `aud` claim must strictly equal the application's registered Shopify Client ID / API Key.
4. **Issuer Validation (`iss`):** The `iss` claim must match `https://{shop}.myshopify.com/admin`, where `{shop}` matches the expected tenant domain format (`^[a-zA-Z0-9][a-zA-Z0-9\-]*\.myshopify\.com$`).
5. **Lifetime Expiration (`exp` & `nbf`):** Enforce tight expiration windows with a maximum allowable clock skew of $\le 5\text{ seconds}$.
6. **Replay Protection (`jti`):** For critical actions (e.g. billing subscription approvals, inventory dumps), verify that the unique JWT identifier (`jti`) has not been seen within its validity window.

---

## 3. Webhook Integrity & Replay Mitigation

### 3.1 HMAC-SHA256 Signature Verification
Every webhook dispatch from Shopify includes the `X-Shopify-Hmac-Sha256` header, calculated as the Base64-encoded HMAC-SHA256 hash of the raw HTTP request body:

$$\text{Calculated HMAC} = \text{Base64}\Big(\text{HMAC-SHA256}\big(\text{RawRequestBody},\, \text{AppSharedSecret}\big)\Big)$$

```python
import hmac
import hashlib
import base64
import time

def verify_shopify_webhook(raw_body: bytes, hmac_header: str, shared_secret: str) -> bool:
    """
    Verifies Shopify webhook signature using constant-time comparison
    on the raw byte stream prior to JSON deserialization.
    """
    if not hmac_header or not raw_body:
        return False
        
    calculated_digest = hmac.new(
        shared_secret.encode('utf-8'),
        raw_body,
        hashlib.sha256
    ).digest()
    
    calculated_b64 = base64.b64encode(calculated_digest).decode('utf-8')
    
    # Constant-time comparison prevents timing side-channel attacks
    return hmac.compare_digest(calculated_b64, hmac_header)
```

### 3.2 Defensive Replay Defense via Webhook ID
To prevent malicious network actors or compromised middleboxes from replaying captured webhook payloads:
- Extract the `X-Shopify-Webhook-Id` header.
- Store processed webhook IDs in a Redis set with a 24-hour TTL:
  $$\text{SETNX}(\text{key} = \text{webhook\_id}, \text{ttl} = 86400)$$
- If the ID already exists in the set, drop the request and return `HTTP 200 OK` (acknowledging receipt without re-executing state transitions).

---

## 4. GraphQL Admin API Cost Calculation & Leaky Bucket Protection

### 4.1 Cost Point Budgeting
Shopify protects its GraphQL infrastructure using an explicit query cost model:
- Every tenant store is allocated a leak rate of **50 points per second** and a maximum capacity of **1,000 points**.
- Incoming queries calculate their cost prior to execution based on requested fields and connection pagination sizes (`first: N`).

```graphql
query DefensiveInventoryQuery($first: Int!) {
  products(first: $first) { # Cost = 2 + ($first * 1)
    edges {
      node {
        id
        title
        variants(first: 5) {  # Cost multiplier: $first * (2 + 5 * 1)
          edges {
            node {
              id
              price
              inventoryQuantity
            }
          }
        }
      }
    }
  }
}
```

### 4.2 Throttling Mitigation Guidelines for Apps
1. **Requested vs. Actual Cost Accounting:** Track `extensions.cost.actualQueryCost` in response payloads to dynamically adjust pagination page sizes.
2. **Exponential Backoff with Jitter:** When throttled (`HTTP 429` / `MAX_COST_EXCEEDED`), parse `extensions.cost.throttleStatus.restoreRate` to sleep exactly until sufficient points have leaked:
   $$T_{\text{wait}} = \frac{\text{RequestedCost} - \text{CurrentlyAvailable}}{\text{RestoreRate}} + \mathcal{U}(0.05, 0.20)$$

---

## 5. Defensive Verification Checklist

| Security Control | Implementation Standard | Defensive Status |
|---|---|---|
| **Session Token Verification** | JWT signature validated with `client_secret` via constant-time compare | Compliant |
| **Issuer & Domain Guard** | Strict regex check on `myshopify.com` domain format | Compliant |
| **Raw Body Webhook HMAC** | Verification computed directly on raw bytes before JSON parse | Compliant |
| **Webhook Replay Idempotency** | `X-Shopify-Webhook-Id` tracked in Redis cache with 24h TTL | Hardened |
| **Multi-Tenant DB Query Scoping** | All database queries strictly parameterized with `shop_id` filter | Verified |
| **GraphQL Cost Management** | Dynamic page sizing with jittered backoff on leaky bucket depletion | Compliant |

---
*Report published to Algorise Security Research Ledger. All rights reserved.*
