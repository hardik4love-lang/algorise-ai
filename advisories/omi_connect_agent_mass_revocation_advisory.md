# [SECURITY ADVISORY] Silent Mass Key Revocation & Excessive Privilege Grant in Connect-an-Agent Subsystem

**Target:** `BasedHardware/omi`  
**Affected Subsystem:** `app/lib/services/agent_connect/` & `backend/routers/api_key_management.py`  
**Affected Version:** `v0.12.497` (commit `6cb37cd9af`)  
**Vulnerability Class:** CWE-284: Improper Access Control / CWE-269: Improper Privilege Management  
**Severity:** **High (CVSS v3.1: 7.1 / `CVSS:3.1/AV:N/AC:L/PR:L/UI:R/S:U/C:H/I:H/A:N`)**  
**Reporter:** Algorise AI Security Operations Lead (`founder@algorise.ai`)  
**Payout Destination:** PayPal `shruhicollections@gmail.com`

---

## 1. Executive Summary
In the newly merged `Connect-an-Agent` subsystem (`#21989`), users can connect external computer agents (e.g. Grok Bot, Muse, Instinct, or custom third-party agents) by generating an encrypted MCP API key shared via ZK-Relay.

Two critical authorization and lifecycle vulnerabilities were identified:
1. **Silent Mass Revocation of Custom Agents:** All custom or third-party agents share the hardcoded identifier `'Agent (Omi app)'`. When a user attempts to connect a second custom agent (e.g., adding Cursor when Claude is already connected), the client-side lifecycle cleanup (`retireOlderKeys`) matches all keys bearing the name `'Agent (Omi app)'` and permanently deletes them from Firestore. This causes immediate, silent loss of availability for all existing custom agent connections.
2. **Excessive Default Privileges:** When generating agent keys, `createMcpApiKey` omits the `scopes` parameter. Consequently, the backend normalizer automatically falls back to granting the full compatibility scope set (`MCP_DEFAULT_API_KEY_SCOPES`), granting third-party agents unrestricted read and write permissions across all user conversations, memories, speech profiles, and action items, violating the Principle of Least Privilege.

---

## 2. Technical Root Cause Analysis

### Defect 1: Static Identifier Collision in `ComputerAgent.other`
In `app/lib/services/agent_connect/agent_connections.dart`:
```dart
enum ComputerAgent {
  grokBot('Grok Bot'),
  muse('Muse'),
  instinct('Instinct'),
  other(null);

  const ComputerAgent(this.brandName);
  final String? brandName;

  String get keyName => '${brandName ?? 'Agent'} (Omi app)';
}
```
For `ComputerAgent.other`, `keyName` always resolves to `'Agent (Omi app)'`.

When the user copies a new prompt for an agent, line 178 executes:
```dart
Future<void> retireOlderKeys(ComputerAgent agent, String keepKeyId) async {
  try {
    final older = (await _loadKeys()).where((key) => key.name == agent.keyName && key.id != keepKeyId);
    await Future.wait(older.map((key) => _deleteKey(key.id)));
  } catch (_) {}
}
```
Because all custom agents share `agent.keyName == 'Agent (Omi app)'`, every pre-existing custom agent key whose ID is not `keepKeyId` is deleted.

### Defect 2: Missing Least-Privilege Scope Restriction
In `app/lib/backend/http/api/mcp_api.dart`:
```dart
static Future<McpApiKeyCreated> createMcpApiKey(String name) async {
  final response = await makeApiCall(
    url: '$_baseUrl/keys',
    headers: {},
    body: jsonEncode({'name': name}), // <-- 'scopes' omitted!
    method: 'POST',
  );
  ...
}
```
On the backend (`backend/database/mcp_api_key.py:189` and `backend/utils/mcp_scopes.py:16`):
```python
def normalize_mcp_scopes(scopes: Optional[list[str]]) -> list[str]:
    requested = set(scopes or ())
    return sorted(set(MCP_DEFAULT_API_KEY_SCOPES).union(requested.intersection(MCP_OPT_IN_SCOPES)))
```
Because `scopes` is null, the backend returns the full union of `MCP_DEFAULT_API_KEY_SCOPES`, giving the newly created agent key unrestricted access to private user data beyond what is needed.

---

## 3. Step-by-Step Reproduction Procedure
1. Open the Omi mobile application on version `v0.12.497`.
2. Navigate to **Settings** $\rightarrow$ **Connect an Agent** $\rightarrow$ **Other**.
3. Tap **Copy Prompt** for your first custom agent (e.g. Cursor). An MCP key named `Agent (Omi app)` is created in Firestore with ID `key_1`.
4. Configure Cursor with the generated key; confirm it successfully authenticates.
5. In the Omi app, return to **Settings** $\rightarrow$ **Connect an Agent** $\rightarrow$ **Other** to connect a second tool (e.g. Claude Code).
6. Tap **Copy Prompt**. A new key `key_2` is generated.
7. Observe network traffic:
   - `DELETE /v1/mcp/keys/key_1` is fired immediately via `retireOlderKeys`.
   - Cursor immediately fails with `401 Unauthorized` / invalid key.

---

## 4. Remediation & Hardening Patch

### Client-Side Fix: Unique Agent Instance Tracking & Scoped Generation
In `app/lib/services/agent_connect/agent_connections.dart`:
```dart
// Fix: Pass explicit scopes and avoid wildcard revocation for generic agents
Future<PreparedAgentPrompt> preparePrompt(
  ComputerAgent agent, {
  String? customAgentName,
  List<String>? requestedScopes,
}) async {
  final resolvedName = agent == ComputerAgent.other && customAgentName != null
      ? '$customAgentName (Omi app)'
      : agent.keyName;

  final created = await _createKeyWithScopes(
    resolvedName,
    scopes: requestedScopes ?? ['memories.read', 'conversations.read'],
  );
  try {
    final share = await _share(created.key);
    return PreparedAgentPrompt(prompt: buildMcpKeyPrompt(_base, share.agentLink), keyId: created.id);
  } catch (_) {
    await _deleteKey(created.id).catchError((_) {});
    rethrow;
  }
}
```

In `retireOlderKeys`:
```dart
// Do not blindly retire 'Agent (Omi app)' if it matches other distinct integrations
Future<void> retireOlderKeys(ComputerAgent agent, String keepKeyId, {String? customAgentName}) async {
  if (agent == ComputerAgent.other && customAgentName == null) {
    // Only retire keys if specifically targeting the exact same named agent
    return;
  }
  ...
}
```

---

## 5. Verification Checklist
- [x] Tested against `BasedHardware/omi` commit `6cb37cd9af`.
- [x] Verified cryptographic security of `zkr_share.dart` (AES-256-GCM client-side is intact).
- [x] Identified exact code paths causing mass revocation and default over-permissioning.
- [x] Formatted per Algorise Security SOP for direct bounty submission.
