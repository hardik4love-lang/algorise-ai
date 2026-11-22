import sys
sys.path.insert(0, r"C:\Users\om\.gemini\antigravity\scratch\algorise-ai")
from guardian_angel_api import OmnichannelTriageRouter, TriageItem

benchmarks = [
    {
        "name": "Benchmark 1: NHS Doctor Appointment (UK)",
        "item": TriageItem(
            channel="TEXT",
            sender="NHS-NoReply",
            content="NHS appointment reminder with Dr. Smith at St Mary's Hospital on Tuesday at 10:30am. Please reply 1 to confirm or 2 to cancel.",
            region="UK"
        ),
        "expected_category": "SAFE_HEALTHCARE",
        "expected_score": 0,
        "expected_safe": True
    },
    {
        "name": "Benchmark 2: CVS Pharmacy Prescription Pickup (US)",
        "item": TriageItem(
            channel="TEXT",
            sender="+18005550199",
            content="CVS Pharmacy: Your prescription Rx #482910 is ready for pickup at 124 Main St.",
            region="US"
        ),
        "expected_category": "SAFE_HEALTHCARE",
        "expected_score": 0,
        "expected_safe": True
    },
    {
        "name": "Benchmark 3: Grandchild Gift Card Thank-You (Family)",
        "item": TriageItem(
            channel="TEXT",
            sender="+15552345678",
            content="Hi Grandma, thank you so much for the Target gift card you sent for my birthday! Love you so much - Emma",
            region="US"
        ),
        "expected_category": "SAFE_FAMILY",
        "expected_score": 0,
        "expected_safe": True
    },
    {
        "name": "Benchmark 4: Chase 2FA Passcode (Transactional)",
        "item": TriageItem(
            channel="TEXT",
            sender="24273",
            content="Chase: Your one-time passcode is 482910. Do not share this code with anyone. We will never call to ask for it.",
            region="US"
        ),
        "expected_category": "TRANSACTIONAL",
        "expected_score": 0,
        "expected_safe": True
    },
    {
        "name": "Benchmark 5: Fake IRS Arrest Warrant (Critical Fraud Call)",
        "item": TriageItem(
            channel="CALL",
            sender="+18885550199",
            content="This is the IRS Internal Revenue Service. An arrest warrant has been issued in your name. Call 1-888-555-0199 immediately with Target gift cards to clear bail.",
            region="US"
        ),
        "expected_category": "CRITICAL_FRAUD",
        "expected_score_min": 70,
        "expected_safe": False
    }
]

print("=" * 80)
print("RUNNING 5 GOLD-STANDARD SENIOR ACCURACY BENCHMARKS")
print("=" * 80)

passed = 0
for b in benchmarks:
    res = OmnichannelTriageRouter.triage(b["item"])
    cat_ok = (res.category == b["expected_category"])
    score_ok = (res.threat_score == b.get("expected_score")) if "expected_score" in b else (res.threat_score >= b["expected_score_min"])
    safe_ok = (res.senior_safe == b["expected_safe"])

    if cat_ok and score_ok and safe_ok:
        passed += 1
        status = "PASSED ✅"
    else:
        status = f"FAILED ❌ (Got cat={res.category}, score={res.threat_score}, safe={res.senior_safe})"

    print(f"\n[{status}] {b['name']}")
    print(f"  • Category: {res.category} (Score: {res.threat_score}%)")
    print(f"  • Senior Headline: {res.senior_headline}")
    print(f"  • Reassurance: {res.senior_reassurance}")
    print(f"  • Why Flagged / Reason: {res.why_we_flagged_this[0] if res.why_we_flagged_this else 'None'}")
    print(f"  • Safe Step: {res.safe_next_step}")
    print(f"  • Voice Speech: {res.speech_text}")

print("\n" + "=" * 80)
print(f"BENCHMARK SUMMARY: {passed} / {len(benchmarks)} TEST CASES PASSED PERFECTLY")
print("=" * 80)
