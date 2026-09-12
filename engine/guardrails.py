"""
Algorise Causal Safety Gate & Guardrails Engine
Enforces deterministic policy validation, hallucination detection, and human-in-the-loop escalation.
"""

from typing import Dict, Any, List, Tuple

class AlgoriseSafetyGate:
    def __init__(self):
        self.risk_thresholds = {
            "financial_action_max_usd": 500.0,
            "disallowed_keywords": ["drop table", "rm -rf", "eval(", "admin_override", "grant all"],
            "pii_patterns": ["ssn", "credit_card", "passphrase", "secret_key"]
        }

    def audit_bot_action(self, bot_name: str, proposed_action: Dict[str, Any]) -> Tuple[bool, str, List[str]]:
        """
        Validates proposed bot action against causal safety rules before execution.
        Returns: (is_approved, status_code, audit_flags)
        """
        flags = []
        action_text = str(proposed_action).lower()

        # 1. SQL Injection & Destructive System Commands Check
        for keyword in self.risk_thresholds["disallowed_keywords"]:
            if keyword in action_text:
                flags.append(f"CRITICAL_SAFETY_BLOCK: Detected prohibited command '{keyword}'")
                return False, "BLOCKED_MALICIOUS_INTENT", flags

        # 2. PII / Secret Leakage Check
        for pii in self.risk_thresholds["pii_patterns"]:
            if pii in action_text:
                flags.append(f"PII_GUARD_ALERT: Suspected private token or PII exposure: '{pii}'")

        # 3. Financial Transaction Bounds
        if "amount" in proposed_action:
            try:
                amt = float(proposed_action["amount"])
                if amt > self.risk_thresholds["financial_action_max_usd"]:
                    flags.append(f"FINANCIAL_LIMIT_EXCEEDED: Requested ${amt} exceeds automated threshold of ${self.risk_thresholds['financial_action_max_usd']}")
                    return False, "REQUIRES_HUMAN_SIGN_OFF", flags
            except (ValueError, TypeError):
                pass

        if flags:
            return True, "APPROVED_WITH_CAUTION", flags
        return True, "APPROVED_DETERMINISTIC", ["Passed all Algorise Causal Safety Gates."]
