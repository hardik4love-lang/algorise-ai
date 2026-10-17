# 🛡️ Defensive Architectural Review: GitLab CI/CD Variable Security & GraphQL Authorization Boundaries

**Target Program:** GitLab Responsible Disclosure / Bug Bounty Program (HackerOne)  
**Scope Surface:** GitLab Community Edition (`gitlabhq/gitlabhq`) & GitLab CI/CD Infrastructure  
**Subject Area:** CI/CD Pipeline Execution Contexts, Masked Variables, and GraphQL Policy Enforcement  
**Assessment Standard:** Defensive Architecture & Security Hardening Review  
**Author:** Algorise AI Security Operations Lead (`founder@algorise.ai`)

---

## 1. Executive Architecture Overview

GitLab's access control architecture relies on two foundational layers:
1. **DeclarativePolicy Engine:** A custom Ruby policy DSL that evaluates permissions at the model, project, and namespace levels before invoking GraphQL resolvers or REST controllers.
2. **CI/CD Variable & Secret Protection Subsystem:** A multi-tiered boundary ensuring sensitive secrets (tokens, deployment keys, credentials) are delivered only to authorized pipeline jobs and properly masked from output logs.

This audit provides a structured security review of these mechanisms, analyzing common configuration risks, authorization edge cases, and concrete defensive hardening guidelines.

---

## 2. CI/CD Variable Protection & Masking Analysis

### 2.1 Protected vs. Masked Variable Boundaries
GitLab provides two distinct flags for pipeline environment variables:
- **`Protected`**: The variable is passed only to pipelines running on protected branches or protected tags.
- **`Masked`**: The variable value is masked (replaced with `[masked]`) in job execution logs.

```
                    +------------------------------------+
                    |  Triggered CI/CD Pipeline Job      |
                    +------------------------------------+
                                       |
                +----------------------+----------------------+
                |                                             |
        [Branch Type Check]                         [Log Masking Filter]
                |                                             |
       Is Branch Protected?                        Does Value Satisfy
       Yes -> Inject Secret                         Masking Regex?
       No  -> Drop Variable                         Yes -> Filtered in Logs
                                                    No  -> Logged in Plaintext
```

### 2.2 Key Security Invariants & Limitations
1. **Masking Regex Constraints:**
   To prevent denial-of-service in log stream parsing, GitLab requires masked values to adhere to strict character and length constraints (e.g., minimum 8 characters, base64 / alphanumeric characters only). If a secret contains characters outside this set or contains multi-line text, masking cannot be enabled, requiring alternative storage (such as HashiCorp Vault or GitLab Secret Manager).
2. **Untrusted Fork Pipelines:**
   For public open-source projects, merge requests from forks run pipelines in a separate security context. GitLab's secure default prevents protected CI/CD variables from leaking to untrusted fork pipelines. Maintaining the `Prevent pipeline creation on forks` or requiring manual approval for untrusted contributors is a critical defensive baseline.

---

## 3. GraphQL Authorization Review (`declarative_policy`)

### 3.1 Field-Level Authorization in Resolvers
In GitLab's GraphQL implementation, every type and mutation should declare an explicit authorization rule:

```ruby
# Secure Pattern in GitLab GraphQL Type Definition
module Types
  class ProjectVariableType < BaseObject
    graphql_name 'CiProjectVariable'
    authorize :admin_variable # Enforces DeclarativePolicy check

    field :id, GraphQL::Types::ID, null: false
    field :key, GraphQL::Types::String, null: false
    field :masked, GraphQL::Types::Boolean, null: false
    field :protected, GraphQL::Types::Boolean, null: false
    # 'value' field is intentionally omitted or guarded by explicit policy
  end
end
```

### 3.2 Authorization Anti-Patterns to Audit
When auditing GraphQL schemas, reviewers inspect:
1. **Nested Type Traversal:** Ensuring that navigating through parent-child relationships (e.g., `Project -> Environment -> Deployment -> Secrets`) enforces the same authorization checks as top-level queries.
2. **Mutation Input Validation:** Verifying that mutations creating or updating variables (`ciVariableCreate`, `ciVariableUpdate`) validate that the caller holds `:admin_variable` on the target project or group, and that protected branch validation cannot be bypassed by empty branch masks.

---

## 4. Runner Isolation & Execution Boundary Hardening

### 4.1 Shared vs. Dedicated Runners
GitLab Runners execute pipeline jobs within isolated environments (Docker executors, Kubernetes pods, or virtual machines). Key security configurations include:
- **Disabling Privileged Mode:** Unless explicitly required for building container images, Docker executors must not run with `--privileged = true`.
- **Rootless Containers:** Running jobs with non-root user IDs prevents container escape risks and protects the underlying host filesystem.
- **Cache Isolation:** Build caches must be scoped to specific projects to prevent cache poisoning across multi-tenant environments.

---

## 5. Defensive Verification Checklist

| Review Area | Verification Standard | Defensive Status |
|---|---|---|
| **CI/CD Variables** | Protected flags verified on all production secrets | Compliant |
| **Log Masking** | Masking enabled on all qualifying credentials | Compliant |
| **Fork Isolation** | Untrusted fork pipeline approval gated | Recommended |
| **GraphQL Policies** | Explicit `authorize` declarations on all mutation resolvers | Compliant |
| **Runner Security** | Non-privileged execution with dedicated networks | Hardened |

---
*Report published to Algorise Security Research Ledger. All rights reserved.*
