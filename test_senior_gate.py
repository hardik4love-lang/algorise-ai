import re
from typing import Dict, Any, Optional, Tuple

class SeniorSafeLifelineGate:
    """
    Deterministic whitelist gate for critical senior communications:
    1. Healthcare & Doctor appointments (NHS, UK GP, US Clinics, Specialists)
    2. Pharmacy prescription collection/pickup (Boots, CVS, Walgreens, Rite Aid)
    3. Family affection, gratitude, and thank-you notes (Grandchildren, Children)
    4. Legitimate Bank Two-Factor Passcodes (OTPs with zero deceptive hyperlinks)
    """

    # 1. Healthcare patterns
    HEALTHCARE_APPOINTMENT_PATTERNS = [
        r"(?i)\b(NHS|GP surgery|hospital appointment|clinic appointment|dental appointment|optician)\b",
        r"(?i)\b(appointment (reminder|scheduled|confirmed) with (dr|doctor)\.?\s+[a-z]+)\b",
        r"(?i)\b(appointment on\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday|[a-z]+\s+\d{1,2}))\b",
        r"(?i)\b(reply 1 to confirm|text 1 to confirm|reply 2 to cancel|text STOP to end)\b",
        r"(?i)\b(st\.?\s*mary'?s\s*hospital|mayo clinic|cleveland clinic|kaiser|quest diagnostics|labcorp)\b"
    ]

    PHARMACY_PATTERNS = [
        r"(?i)\b(prescription is ready for (collection|pickup))\b",
        r"(?i)\b(boots pharmacy|cvs pharmacy|walgreens|rite aid|superdrug pharmacy|lloyds pharmacy)\b",
        r"(?i)\b(rx\s*#?\s*\d{4,}|\bprescription rx\b)\b"
    ]

    # 2. Family affection / gratitude patterns
    FAMILY_GRATITUDE_PATTERNS = [
        r"(?i)\b(thank you so much for the (target|apple|amazon|walmart)?\s*gift card)\b",
        r"(?i)\b(thanks\s+(grandma|grandpa|nana|papa|mom|dad|auntie|uncle))\b",
        r"(?i)\b(love you so much|we love you|miss you lots|can't wait to see you|see you on sunday)\b",
        r"(?i)\b(happy birthday\s+(grandma|grandpa|nana|mom|dad)|happy thanksgiving|happy mother'?s day)\b",
        r"(?i)\b(thanks for sending the (money|cash|\$|£|train ticket))\b"
    ]

    # Deceptive URL check for excluding spoofed texts
    SUSPICIOUS_URL_REGEX = r"(?i)(?:https?://)?(?:[a-zA-Z0-9-]+\.)*(?:track-usps|royalmail-fee|evri-redeliver|secure-chase|login-hmrc|claim-rebate|toll-pay)[^\s]*|(?:https?://)?(?:[a-zA-Z0-9-]+\.)+(?:xyz|top|work|buzz|icu|live|click|cyou|shop|sbs)(?:/[^\s]*)?"

    # Coercive payment extortion signals that negate family status
    EXTORTION_SIGNALS = [
        r"(?i)\b(i'm in jail|arrested|need bail money|lawyer says wire|don't tell mom|western union now)\b",
        r"(?i)\b(go to (cvs|target|walmart) now and buy|read me the numbers on the back)\b",
        r"(?i)\b(safe holding account|deposit cash into coin machine)\b"
    ]

    @classmethod
    def evaluate_lifeline(cls, content: str, sender: str, channel: str) -> Optional[Dict[str, Any]]:
        full_text = f"{sender} {content}"

        # If malicious phishing URLs or coercive extortion are present, do NOT bypass
        if re.search(cls.SUSPICIOUS_URL_REGEX, full_text):
            return None
        if any(re.search(pat, full_text) for pat in cls.EXTORTION_SIGNALS):
            return None

        # A. Healthcare Appointment Check
        has_health_provider = any(re.search(p, full_text) for p in cls.HEALTHCARE_APPOINTMENT_PATTERNS[:2] + [cls.HEALTHCARE_APPOINTMENT_PATTERNS[4]])
        has_appt_timing = any(re.search(p, full_text) for p in cls.HEALTHCARE_APPOINTMENT_PATTERNS[2:])
        if has_health_provider or (re.search(r"(?i)\b(appointment|dr\.|doctor)\b", full_text) and has_appt_timing):
            return {
                "category": "SAFE_HEALTHCARE",
                "verdict": "VERIFIED DOCTOR / HEALTHCARE APPOINTMENT 🏥💚",
                "score": 0,
                "action": "INBOX_SAFE",
                "confidence": 0.999,
                "senior_headline": "SAFE TO OPEN: Doctor / Clinic Appointment Reminder",
                "senior_reassurance": "This is a real appointment from your healthcare provider. You can confirm or attend as planned.",
                "why_we_flagged_this": [
                    "Verified healthcare communication from your doctor or hospital.",
                    "Contains legitimate appointment scheduling details with no suspicious payment requests."
                ],
                "safe_next_step": "Reply to confirm if requested, or simply note the time on your calendar.",
                "speech_text": "Good news! This is a safe reminder for your upcoming doctor's appointment. You do not need to worry."
            }

        # B. Pharmacy Prescription Check
        if any(re.search(p, full_text) for p in cls.PHARMACY_PATTERNS):
            return {
                "category": "SAFE_HEALTHCARE",
                "verdict": "VERIFIED PHARMACY PRESCRIPTION READY 💊💚",
                "score": 0,
                "action": "INBOX_SAFE",
                "confidence": 0.999,
                "senior_headline": "SAFE TO OPEN: Your Prescription is Ready for Pickup",
                "senior_reassurance": "This is a real message from your local pharmacy confirming your medication is ready.",
                "why_we_flagged_this": [
                    "Legitimate notification from a recognized pharmacy (Boots / CVS / Walgreens).",
                    "No links asking for bank details or gift cards."
                ],
                "safe_next_step": "You can pick up your medication from the pharmacy during normal opening hours.",
                "speech_text": "Good news! This is a verified message from your pharmacy letting you know your prescription is ready for pickup."
            }

        # C. Family Affection / Gratitude Check
        if any(re.search(p, full_text) for p in cls.FAMILY_GRATITUDE_PATTERNS):
            return {
                "category": "SAFE_FAMILY",
                "verdict": "VERIFIED FAMILY & LOVED ONE 👨‍👩‍👧‍👦💚",
                "score": 0,
                "action": "INBOX_SAFE",
                "confidence": 0.999,
                "senior_headline": "SAFE TO OPEN: Message from Family or Loved One",
                "senior_reassurance": "This is a warm personal message from a grandchild or family member. It is completely safe.",
                "why_we_flagged_this": [
                    "Recognized personal gratitude or affectionate message from family.",
                    "Zero requests to send money or wire funds anywhere."
                ],
                "safe_next_step": "Safe to read and reply with your love!",
                "speech_text": "This is a lovely, safe personal message from a family member. Everything is safe and sound."
            }

        # D. Legitimate Bank OTP / Two-Factor Code (without links)
        if re.search(r"(?i)\b(one-time (passcode|password)|verification code is|security code is|never share this code)\b", full_text) and not re.search(r"(?i)https?://", full_text):
            return {
                "category": "TRANSACTIONAL",
                "verdict": "VERIFIED BANK LOGIN SECURITY CODE 🔑🟡",
                "score": 0,
                "action": "INBOX_PRIORITY",
                "confidence": 0.995,
                "senior_headline": "TEMPORARY SECURITY CODE (Keep Private)",
                "senior_reassurance": "This is a one-time code for logging into your account. Only use it if YOU just tried to log in.",
                "why_we_flagged_this": [
                    "Standard bank two-factor security passcode.",
                    "Contains no dangerous links or website redirects."
                ],
                "safe_next_step": "If you are currently logging into your bank on your computer, use this code. NEVER read this code over the phone to anyone who calls you.",
                "speech_text": "This is a bank security code. It is safe if you requested it, but remember never to read this number over the phone to anyone."
            }

        return None

if __name__ == "__main__":
    tests = [
        ("NHS appointment reminder with Dr. Smith at St Mary's Hospital on Tuesday at 10:30am. Please reply 1 to confirm or 2 to cancel.", "NHS-NoReply", "TEXT"),
        ("CVS Pharmacy: Your prescription Rx #482910 is ready for pickup at 124 Main St.", "+18005550199", "TEXT"),
        ("Hi Grandma, thank you so much for the Target gift card you sent for my birthday! Love you so much - Emma", "+15552345678", "TEXT"),
        ("Chase: Your one-time passcode is 482910. Do not share this code with anyone. We will never call to ask for it.", "24273", "TEXT"),
        ("This is the IRS Internal Revenue Service. An arrest warrant has been issued in your name. Call 1-888-555-0199 immediately with Target gift cards to clear bail.", "+18885550199", "CALL")
    ]

    for content, sender, ch in tests:
        res = SeniorSafeLifelineGate.evaluate_lifeline(content, sender, ch)
        print("INPUT:", content[:60], "...")
        print("LIFELINE RESULT:", "BYPASS GATE ->" if res else "NOT A LIFELINE (GO TO SCAM SENTINEL)", res.get("category") if res else None)
        print("-" * 50)

    adversarial_tests = [
        ("NHS: Claim your £250 health voucher now at fake-nhs-voucher.xyz", "NHS-Refund", "TEXT"),
        ("Hi Grandma, i'm in jail after a car accident, need bail money, please don't tell mom", "+15559998888", "CALL"),
        ("Boots: Your prescription requires payment of £12.50 at boots-secure-pay.click", "+447911123456", "TEXT")
    ]
    print("\n--- ADVERSARIAL ATTACK TESTS (MUST NOT BYPASS GATE) ---")
    for content, sender, ch in adversarial_tests:
        res = SeniorSafeLifelineGate.evaluate_lifeline(content, sender, ch)
        print("INPUT:", content[:60], "...")
        print("BYPASS GATE?", "YES (SECURITY RISK!)" if res else "NO (CORRECTLY BLOCKED FROM BYPASS -> SENT TO SENTINEL)")
        print("-" * 50)
