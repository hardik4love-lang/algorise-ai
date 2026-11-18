# Security Policy - Algorise PayHR

## Zero-Trust Architecture Overview

Algorise PayHR implements a defense-in-depth, zero-trust security model designed for sensitive human resource and financial data.

### 1. Cryptographic PII Protection (AES-256-GCM)
* Statutory employee identity documents (PAN cards, Aadhaar tokens, Universal Account Numbers, Bank Account numbers, and IFSC) are encrypted at rest using **AES-256-GCM** authenticated encryption.
* Nonces are randomly generated (96-bit) per record to prevent chosen-ciphertext attacks.

### 2. Hardware Webhook Anti-Replay Guard (HMAC-SHA256)
* Biometric push endpoints (`/api/v1/attendance/device/push`) require cryptographic signatures using a shared pre-shared key (PSK).
* Replay attacks are blocked using a rolling timestamp window ($\le 300\text{ seconds}$) and nonce de-duplication.

### 3. Anti-Spoofing & Geofence Protection
* Mobile check-in validates:
  1. `is_mock_provider` OS flags (blocks fake GPS apps).
  2. Great-circle distance calculations via Haversine formula against configured branch centroids.
  3. Physical Wi-Fi BSSID (hardware MAC) matches.
  4. Impossible travel velocity detection ($> 150\text{ km/h}$) preventing multi-point punch spoofing.

### 4. Continuous Geofence Sentinel & Auto Cut-Off
* Background heartbeats detect departures from work premises.
* A configurable grace period (default 3 minutes) buffers GPS signal drops.
* If breach persists, the session is auto-terminated (`PUNCH_OUT`), and high-priority alerts are dispatched to supervisors.

### 5. Reporting a Security Vulnerability
If you discover a security vulnerability within Algorise PayHR, please report it privately to `security@algorise.ai`. Do not disclose security vulnerabilities publicly until they have been reviewed and addressed.
