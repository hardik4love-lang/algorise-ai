# 🛡️ Defensive Architectural Review: Enterprise GraphQL Authorization & Query Cost Controls

**Target Programs:** Enterprise GraphQL Gateways (Shopify, Airbnb, GitLab)  
**Subject Area:** GraphQL Query Complexity, Node Interface Authorization, and Tenant Isolation  
**Assessment Standard:** Defensive Architecture & API Security Hardening  
**Author:** Algorise AI Security Operations Lead (`founder@algorise.ai`)

---

## 1. Executive Summary

Modern enterprise architectures increasingly rely on GraphQL federated gateways (Apollo Federation, GraphQL Ruby, or custom Go/Node gateways) to serve web and mobile clients. While GraphQL offers schema flexibility and declarative data fetching, it introduces distinct security and authorization challenges compared to traditional REST APIs.

This review provides a defensive blueprint analyzing:
1. **Broken Object-Level Authorization (BOLA) in Relay Node Interfaces (`node(id: ID!)`).**
2. **Query Complexity & Depth Limiting to prevent resource exhaustion.**
3. **Field-Level Authorization in DataLoaders & Resolvers.**
4. **Webhook HMAC Signature Verification & Replay Protection.**

---

## 2. Relay Node Interface (`node(id: ID!)`) Authorization Defense

### 2.1 The Global Object Identification Challenge
In standard GraphQL implementations conforming to the Relay specification, clients can query any entity via the global `node` field:

```graphql
query GetResource($id: ID!) {
  node(id: $id) {
    id
    ... on Order {
      totalPrice
      customerEmail
    }
  }
}
```

### 2.2 Security Invariant: Owner/Tenant Scoping
A common vulnerability occurs when the `node` resolver resolves an object solely by its globally unique identifier without verifying that the currently authenticated caller possesses access rights to that specific tenant or organization.

**Defensive Implementation Pattern (Ruby / GraphQL-Ruby / Python Graphene):**

```python
# Secure Node Resolver with Mandatory Tenant Boundary Enforcement
def resolve_node(global_id: str, context: GraphQLContext):
    type_name, internal_id = parse_global_id(global_id)
    current_user = context.current_user
    
    # 1. Reject unauthenticated access for non-public entities
    if not current_user:
        raise AuthenticationRequiredError()
        
    model_class = MODEL_REGISTRY.get(type_name)
    if not model_class:
        raise NotFoundError()

    # 2. Scope query strictly to the current tenant / user organization
    scoped_query = model_class.objects.filter(
        id=internal_id,
        organization_id=current_user.organization_id # Mandatory tenant scope
    )
    
    instance = scoped_query.first()
    if not instance:
        # Return generic NotFound to prevent identifier enumeration
        raise NotFoundError("Resource not found or unauthorized")
        
    return instance
```

---

## 3. Query Complexity & Depth Limiting

### 3.1 Resource Exhaustion via Cyclic Queries
Without query cost calculation, an attacker can submit deeply nested recursive queries (e.g. `user -> friends -> user -> friends ...`) that overwhelm backend database connections.

```
+------------------+      +-----------------------+      +---------------------+
| Incoming GraphQL | ---> | AST Depth & Cost      | ---> | Execution Engine    |
| Query String     |      | Analyzer (Pre-flight) |      | (DB Resolvers)      |
+------------------+      +-----------------------+      +---------------------+
                                     |
                               Exceeds Cost?
                                     |
                                     v
                        [HTTP 400 Bad Request]
                        "Query complexity limit exceeded"
```

### 3.2 Defensive Configuration Parameters:
- **Max Depth Limit:** Restrict query AST depth to a maximum of **7 to 10 levels**.
- **Query Complexity Cost:** Assign point values to fields (e.g., scalar fields = 1 point, connection fields = 5 points $\times$ `first` argument).
- **Hard Cost Cap:** Enforce a maximum cost limit (e.g., **1,000 points** per request).
- **Leaky Bucket Token Algorithm:** Track API points consumed over a rolling time window, returning HTTP 429 when depleted.

---

## 4. Webhook Integrity & Replay Mitigation

Enterprise platforms rely on webhooks for asynchronous order, inventory, and account events. Secure webhook ingestion requires:

1. **HMAC-SHA256 Signature Header:** Every payload must include a signature computed with a shared secret:
   $$\text{Signature} = \text{HMAC-SHA256}(\text{SharedSecret}, \text{RawRequestBody})$$
2. **Timing-Safe Comparison:** Verifying signatures using constant-time comparison (`hmac.compare_digest`) to prevent timing side-channel attacks.
3. **Timestamp Tolerance Window:** Checking the `X-Webhook-Timestamp` header and rejecting events older than **5 minutes** (300 seconds) to mitigate replay attacks.

---

## 5. Security Checklist for Enterprise GraphQL APIs

| Check | Standard Requirement | Verification Method |
|---|---|---|
| **Node Query Isolation** | Tenant scoping enforced in `node` resolver | Unit & Integration Tests |
| **Field-Level Auth** | Sensitive fields require explicit permissions | Resolver Policy Matrix |
| **Depth Limiting** | Max depth $\le 10$ enforced | AST Validation Middleware |
| **Complexity Budget** | Pre-flight cost analysis enabled | Query Complexity Plugin |
| **Introspection Controls** | Disabled in production or gated to partners | Gateway Policy Check |
| **Webhook Signatures** | HMAC-SHA256 with timestamp verification | Ingestion Filter Test |

---
*Published to Algorise Security Research Ledger. All rights reserved.*
