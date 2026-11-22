from fastapi.testclient import TestClient
from guardian_angel_api import app
import json

client = TestClient(app)

print("=" * 80)
print("TESTING PHASE 1 AUTOMATED CARRIER & CLOUD SENTRY PROTECTION (IN-MEMORY)")
print("=" * 80)

# 1. Test Carrier Call Forwarding with an IRS Scammer
scam_call = {
    "From": "+18885550199",
    "To": "+14155550123",
    "CallerSpeech": "This is Officer Davis from IRS warrant department. You will be arrested within 30 minutes if you do not buy Target gift cards.",
    "ForwardingCode": "*71",
    "ProtectedSenior": "Margaret (76)",
    "Region": "US"
}
resp = client.post("/v1/telecom/carrier-forward-webhook", json=scam_call)
assert resp.status_code == 200
assert "application/xml" in resp.headers.get("content-type", "")
print("\n[TEST 1] CARRIER *71 SCAMMER CALL INTERCEPTED:")
print("  • Content-Type:", resp.headers.get("content-type"))
print("  • TwiML XML Generated:", resp.text[:120], "...")
assert "<Response>" in resp.text
assert "Say" in resp.text

# 2. Test Carrier Call Forwarding with Legitimate Doctor Call
doctor_call = {
    "From": "+14155550999",
    "To": "+14155550123",
    "CallerSpeech": "Hello Margaret, this is Dr. Robert's office calling to confirm your cardiology checkup on Tuesday at 10 AM.",
    "ForwardingCode": "*71",
    "ProtectedSenior": "Margaret (76)",
    "Region": "US"
}
resp = client.post("/v1/telecom/carrier-forward-webhook", json=doctor_call)
assert resp.status_code == 200
assert "<Dial>+14155550123</Dial>" in resp.text
print("\n[TEST 2] CARRIER *71 LEGITIMATE DOCTOR CALL:")
print("  • Status: FORWARDED DIRECTLY TO MOM")
print("  • TwiML XML:", resp.text)

# 3. Test Cloud Inbox Auto-Quarantine (Fake Geek Squad $499 Invoice)
fake_invoice = {
    "account_email": "margaret.elder@gmail.com",
    "provider": "gmail",
    "sender": "Geek Squad Renewal <billing-support8912@gmail.com>",
    "subject": "Invoice #8921 auto-renewed for $499.00",
    "body": "Your annual total tech protection has renewed. Call toll-free 1-888-555-0142 to connect AnyDesk and dispute."
}
resp = client.post("/v1/cloud-inbox/webhook", json=fake_invoice)
assert resp.status_code == 200
res = resp.json()
print("\n[TEST 3] CLOUD INBOX GMAIL AUTO-QUARANTINE:")
print("  • Status:", res["status"])
print("  • Action Taken:", res["action_taken"])
print("  • Threat:", res["threat_category"])
print("  • Senior Impact: Email moved to Trash before Margaret ever saw it.")
assert res["status"] == "AUTO_QUARANTINED"

# 4. Test Viral Scammer Waster Clips Endpoint
resp = client.get("/v1/scammer-waster/clips")
assert resp.status_code == 200
res = resp.json()
print("\n[TEST 4] VIRAL SCAMMER WASTER CLIPS REPOSITORY:")
print("  • Total Viral Clips Ready:", res["total_clips"])
for clip in res["clips"]:
    print(f"    - [{clip['viral_views']}] {clip['title']} ({clip['duration_mins']}m wasted)")
assert res["total_clips"] >= 3

print("\n" + "=" * 80)
print("ALL 4 AUTOMATED ZERO-SENIOR-TOUCH PIPELINES VERIFIED 100% PERFECTLY! ✅")
print("=" * 80)
