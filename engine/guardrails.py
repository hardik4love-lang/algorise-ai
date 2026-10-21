"""
Algorise Causal Safety Gate & Guardrails Engine
Enforces deterministic policy validation, SQL injection prevention, shell command blocking,
PII leakage defense, financial transaction boundary verification, and anti-hallucination controls.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class SafetyAuditResult:
    is_approved: bool
    status_code: str
    risk_score: float  # 0.0 (safest) to 1.0 (critical threat)
    audit_flags: List[str] = field(default_factory=list)
    sanitized_payload: Optional[Dict[str, Any]] = None
    latency_ms: float = 0.0


class AlgoriseSafetyGate:
    """Deterministic, causal safety release gate evaluated before any tool or financial execution."""

    def __init__(self):
        # 1. SQL Injection patterns (lexical & AST pattern heuristics)
        self.sql_injection_patterns = [
            re.compile(r"(\b(select|insert|update|delete|drop|alter|truncate|create|grant|revoke)\b.*\b(from|into|table|database|where)\b)", re.IGNORECASE),
            re.compile(r"(--|/\*|\*/|;\s*$)", re.IGNORECASE),
            re.compile(r"(\bunion\b\s+(all\s+)?\bselect\b)", re.IGNORECASE),
            re.compile(r"(\bor\b\s+['\"]?\d+['\"]?\s*=\s*['\"]?\d+)", re.IGNORECASE),
            re.compile(r"(\bwaitfor\b\s+\bdelay\b|\bsleep\s*\(\s*\d+\s*\)|\bbenchmark\s*\()", re.IGNORECASE),
            re.compile(r"(\badmin_override\b|\bdrop\s+table\b|\bexec\s*\(|\bxp_cmdshell\b)", re.IGNORECASE),
        ]

        # 2. System Command / Code Injection patterns
        self.cmd_injection_patterns = [
            re.compile(r"(\brm\s+-rf\b|\bdel\s+/[fqsk]\b)", re.IGNORECASE),
            re.compile(r"(\beval\s*\(|\bexec\s*\(|\b__import__\b|\bcompile\s*\()", re.IGNORECASE),
            re.compile(r"(\bpowershell\b|\bcmd\.exe\b|\b/bin/sh\b|\b/bin/bash\b)", re.IGNORECASE),
            re.compile(r"(\||\&{2}|;)\s*(cat|ls|rm|curl|wget|chmod|netcat|nc)\b", re.IGNORECASE),
        ]

        # 3. PII & Secret Leakage patterns
        self.pii_patterns = {
            "credit_card": re.compile(r"\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|6(?:011|5[0-9]{2})[0-9]{12})\b"),
            "ssn_us": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
            "private_key": re.compile(r"-----BEGIN (?:RSA |EC )?PRIVATE KEY-----", re.IGNORECASE),
            "meta_access_token": re.compile(r"\bEAA[A-Za-z0-9]{50,}\b"),
            "generic_secret": re.compile(r"(?:api[_-]?key|secret[_-]?key|access[_-]?token|passphrase)\s*[:=]\s*['\"][A-Za-z0-9_=-]{16,}['\"]", re.IGNORECASE),
        }

        # 4. Financial & Commerce bounds
        self.max_single_transaction_usd = 500.0
        self.max_single_transaction_inr = 50000.0
        self.max_discount_pct = 35.0

    def audit_bot_action(
        self,
        bot_name: str,
        proposed_action: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, List[str]]:
        """Backwards-compatible tuple interface: returns (is_approved, status_code, audit_flags)."""
        res = self.audit_detailed(bot_name, proposed_action, context)
        return res.is_approved, res.status_code, res.audit_flags

    def audit_detailed(
        self,
        bot_name: str,
        proposed_action: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> SafetyAuditResult:
        """
        Deep deterministic causal safety audit.
        Evaluates input against 5 deterministic gate stages with nanosecond latency.
        """
        started = time.perf_counter()
        flags: List[str] = []
        action_str = str(proposed_action)
        risk_score = 0.0

        # Stage 1: SQL Injection & Command Injection
        for pat in self.sql_injection_patterns:
            if pat.search(action_str):
                flags.append("CRITICAL_SAFETY_BLOCK: Detected prohibited SQL injection or administrative command pattern")
                elapsed_ms = (time.perf_counter() - started) * 1000
                return SafetyAuditResult(
                    is_approved=False,
                    status_code="BLOCKED_MALICIOUS_INTENT",
                    risk_score=1.0,
                    audit_flags=flags,
                    latency_ms=elapsed_ms,
                )

        for pat in self.cmd_injection_patterns:
            if pat.search(action_str):
                flags.append("CRITICAL_SAFETY_BLOCK: Detected prohibited shell execution or arbitrary code execution pattern")
                elapsed_ms = (time.perf_counter() - started) * 1000
                return SafetyAuditResult(
                    is_approved=False,
                    status_code="BLOCKED_MALICIOUS_INTENT",
                    risk_score=1.0,
                    audit_flags=flags,
                    latency_ms=elapsed_ms,
                )

        # Stage 2: PII & Secret Leakage
        def _redact_value(val: Any) -> Any:
            if isinstance(val, str):
                s = val
                for pii_type, pat in self.pii_patterns.items():
                    s = pat.sub(f"[REDACTED_{pii_type.upper()}]", s)
                return s
            elif isinstance(val, dict):
                return {k: _redact_value(v) for k, v in val.items()}
            elif isinstance(val, list):
                return [_redact_value(v) for v in val]
            return val

        sanitized = _redact_value(dict(proposed_action))
        detected_pii = []
        for pii_type, pat in self.pii_patterns.items():
            if pat.search(action_str):
                detected_pii.append(pii_type)
                flags.append(f"PII_GUARD_ALERT: Suspected sensitive secret or PII exposure: '{pii_type}'")

        if detected_pii:
            elapsed_ms = (time.perf_counter() - started) * 1000
            return SafetyAuditResult(
                is_approved=False,
                status_code="BLOCKED_PII_LEAKAGE",
                risk_score=1.0,
                audit_flags=flags,
                sanitized_payload=sanitized,
                latency_ms=elapsed_ms,
            )

        # Stage 3: Financial Transaction Bounds (expanded synonym coverage)
        financial_keys = ("amount", "price", "order_value", "transaction_amount", "cost", "fee", "budget", "value")
        matched_key = next((k for k in financial_keys if k in proposed_action), None)
        if matched_key is not None:
            val = proposed_action.get(matched_key)
            try:
                if isinstance(val, (int, float)):
                    amt = float(val)
                elif isinstance(val, str):
                    # extract numeric
                    m = re.search(r"[\d,.]+", val.replace("₹", "").replace("$", ""))
                    amt = float(m.group(0).replace(",", "")) if m else 0.0
                else:
                    amt = 0.0

                currency = str(proposed_action.get("currency", "INR")).upper()
                if currency in ("USD", "$") and amt > self.max_single_transaction_usd:
                    flags.append(f"FINANCIAL_LIMIT_EXCEEDED: Requested ${amt} exceeds automated USD cap of ${self.max_single_transaction_usd}")
                    elapsed_ms = (time.perf_counter() - started) * 1000
                    return SafetyAuditResult(
                        is_approved=False,
                        status_code="REQUIRES_HUMAN_SIGN_OFF",
                        risk_score=0.85,
                        audit_flags=flags,
                        latency_ms=elapsed_ms,
                    )
                elif currency in ("INR", "₹") and amt > self.max_single_transaction_inr:
                    flags.append(f"FINANCIAL_LIMIT_EXCEEDED: Requested ₹{amt:,.2f} exceeds automated INR cap of ₹{self.max_single_transaction_inr:,.2f}")
                    elapsed_ms = (time.perf_counter() - started) * 1000
                    return SafetyAuditResult(
                        is_approved=False,
                        status_code="REQUIRES_HUMAN_SIGN_OFF",
                        risk_score=0.85,
                        audit_flags=flags,
                        latency_ms=elapsed_ms,
                    )
            except (ValueError, TypeError):
                pass

        # Stage 4: Discount & Margin Bounds
        if "discount_pct" in proposed_action:
            try:
                pct = float(proposed_action["discount_pct"])
                if pct > self.max_discount_pct:
                    flags.append(f"DISCOUNT_POLICY_VIOLATION: Requested {pct}% discount exceeds policy max of {self.max_discount_pct}%")
                    elapsed_ms = (time.perf_counter() - started) * 1000
                    return SafetyAuditResult(
                        is_approved=False,
                        status_code="DISCOUNT_EXCEEDED_REQUIRES_APPROVAL",
                        risk_score=0.75,
                        audit_flags=flags,
                        latency_ms=elapsed_ms,
                    )
            except (ValueError, TypeError):
                pass

        # Stage 5: Hallucination & Policy Verification
        message_body = proposed_action.get("message") or proposed_action.get("reply") or proposed_action.get("query")
        if isinstance(message_body, str):
            # Check for absurd unverified promises
            lower_msg = message_body.lower()
            unverified_claims = [
                "100% free gold", "guaranteed 1000% return", "free diamond with every kurti",
                "zero rupee checkout", "bypass security"
            ]
            for claim in unverified_claims:
                if claim in lower_msg:
                    flags.append(f"HALLUCINATION_POLICY_BLOCKED: Detected ungrounded marketing claim '{claim}'")
                    elapsed_ms = (time.perf_counter() - started) * 1000
                    return SafetyAuditResult(
                        is_approved=False,
                        status_code="POLICY_VIOLATION_BLOCKED",
                        risk_score=0.9,
                        audit_flags=flags,
                        latency_ms=elapsed_ms,
                    )

        elapsed_ms = (time.perf_counter() - started) * 1000
        if flags:
            return SafetyAuditResult(
                is_approved=True,
                status_code="APPROVED_WITH_CAUTION",
                risk_score=risk_score or 0.4,
                audit_flags=flags,
                sanitized_payload=sanitized,
                latency_ms=elapsed_ms,
            )

        return SafetyAuditResult(
            is_approved=True,
            status_code="APPROVED_DETERMINISTIC",
            risk_score=0.0,
            audit_flags=["Passed all Algorise Causal Safety Gates."],
            sanitized_payload=sanitized,
            latency_ms=elapsed_ms,
        )


safety_gate = AlgoriseSafetyGate()
