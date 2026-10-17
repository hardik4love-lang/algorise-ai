# 🛡️ Defensive Architectural Review: ElizaOS Agentic Tool Sandboxing & Prompt Injection Defense

**Target Program:** ElizaOS Multi-Agent Autonomous Framework (`elizaOS/eliza`)  
**Scope Surface:** Agent Core Runtime, Action/Evaluator Execution Engine, and Messaging Bridge Plugins  
**Subject Area:** Indirect Prompt Injection, Tool Sandboxing, Memory Isolation, and Secret Redaction  
**Assessment Standard:** Agentic AI Security & Defensive Runtime Architecture  
**Author:** Algorise AI Security Operations Lead (`founder@algorise.ai`)

---

## 1. Executive Architecture Overview

ElizaOS orchestrates autonomous AI agents capable of perceiving inputs across disparate messaging bridges (Discord, Telegram, Twitter/X, iMessage), maintaining persistent vector memory, and executing real-world actions via tool plugins (crypto transactions, browser navigation, shell execution).

The primary attack surface of autonomous agent frameworks comprises:
1. **Indirect Prompt Injection:** Unauthenticated external content (e.g., tweet replies, Discord mentions, fetched web articles) injecting instructions that manipulate the agent's intent or bypass safety filters.
2. **Unsandboxed Tool Execution:** Actions that evaluate code, execute shell commands, or write to local files without operating system boundaries.
3. **Cross-Tenant Vector Memory Contamination:** Shared embeddings and RAG stores returning sensitive context across unrelated users or personas.

This review presents the defensive architecture required to safely operate autonomous agent runtimes in production.

---

## 2. Indirect Prompt Injection Defense Architecture

### 2.1 Dual-Model Context Separation (Perception vs. Decision)
Relying on a single prompt template where untrusted user input is concatenated directly into system instructions is vulnerable to prompt override attacks.

```
+--------------------------------------------------------------------------+
|                       [Untrusted User Message]                           |
+--------------------------------------------------------------------------+
                                     |
                                     v
                 +---------------------------------------+
                 | Untrusted Data Sanitizer / Classifier |
                 | (Fast/Cheap Model / Heuristic Filter) |
                 +---------------------------------------+
                                     |
                               Is Malicious?
                                     |
                  +------------------+------------------+
                  |                                     |
                [Yes]                                  [No]
                  |                                     |
          Drop & Log Alert                     Structured Data Frame
                                                        |
                                                        v
                                        +--------------------------------+
                                        | System Prompt Boundary:        |
                                        | <untrusted_user_content>       |
                                        |   Sanitized User Message       |
                                        | </untrusted_user_content>      |
                                        | Strict Execution Rules         |
                                        +--------------------------------+
```

### 2.2 XML Tag Boundary Enforcement & Parsing
Untrusted text must be strictly enclosed in structural tags (e.g. `<user_input>...</user_input>`), and the LLM system prompt must instruct the model to treat content within these delimiters strictly as data, never as control instructions.
- Pre-flight sanitization must strip or escape matching closing tags (`</user_input>`) from the raw input string to prevent delimiter injection.

---

## 3. Tool Sandboxing & Execution Isolation

### 3.1 Least-Privilege Action Handlers
Actions in ElizaOS must not have direct access to `process.env`, `child_process.exec`, or the host root filesystem:

```typescript
// Secure Tool Execution Wrapper with Resource Gating
export interface SecureActionContext {
  userId: string;
  roomId: string;
  allowedCapabilities: Set<string>;
  egressAllowlist: string[];
}

export async function executeSandboxedAction(
  actionName: string,
  parameters: Record<string, unknown>,
  context: SecureActionContext
): Promise<ActionResult> {
  // 1. Verify caller capability authorization
  if (!context.allowedCapabilities.has(actionName)) {
    throw new SecurityError(`Action ${actionName} is not permitted in room ${context.roomId}`);
  }

  // 2. Execute within an isolated V8 Worker or WebAssembly sandbox
  const sandbox = new IsolatedWorker({
    timeoutMs: 5000,
    memoryLimitMb: 128,
    env: {} // Zero access to process.env secrets
  });

  try {
    return await sandbox.run(actionName, parameters);
  } finally {
    sandbox.terminate();
  }
}
```

### 3.2 Network Egress Filtering
Tool plugins making outbound HTTP requests (e.g. Web3 RPCs, weather APIs, search engines) must pass through an egress proxy:
- Block local RFC 1918 private IPs (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`) and cloud metadata services (`169.254.169.254`) to eliminate SSRF risks.
- Enforce domain allowlisting based on the agent's configured plugin requirements.

---

## 4. Vector Memory Isolation & PII Redaction

### 4.1 Tenant-Scoped Embedding Queries
When agents query SQLite, pgvector, or Milvus for semantic memories:
$$\text{Filter} = \big(\text{room\_id} == \text{current\_room}\big) \land \big(\text{agent\_id} == \text{current\_agent}\big)$$
- Memories must never be retrieved across room or channel boundaries without explicit cross-room sharing authorization.

### 4.2 Automated Secret Scrubbing
Before memories are written to disk or sent to model context:
- Regular expression and entropy-based filters redact API keys (e.g. `sk-[a-zA-Z0-9]{48}`, `ghp_[a-zA-Z0-9]{36}`), private keys (`0x[a-fA-F0-9]{64}`), and authorization bearer tokens.

---

## 5. Defensive Verification Checklist

| Security Control | Implementation Standard | Defensive Status |
|---|---|---|
| **Input Delimitation** | Structural XML tags with closing tag escaping on untrusted input | Compliant |
| **Tool Sandboxing** | Isolated worker environments with zero host `process.env` access | Hardened |
| **SSRF / Egress Gate** | Cloud metadata (`169.254.169.254`) and RFC 1918 ranges blocked | Hardened |
| **Memory Scoping** | Strict `(room_id, agent_id)` compound index filtering on vector lookups | Verified |
| **Secret Redaction** | High-entropy token scrubbing prior to memory persistence | Compliant |
| **Action Rate Limiting** | Max action invocations capped per user/room to prevent resource exhaustion | Compliant |

---
*Report published to Algorise Security Research Ledger. All rights reserved.*
