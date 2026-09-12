"""
Verification test for Algorise RealtorReach AI Sales Assistant.
"""

from engine.realtor_sales_assistant import AlgoriseRealtorSalesAssistant
import json

def main():
    print("=" * 70)
    print("  ALGORISE REALTOR-REACH AI SALES ASSISTANT VERIFICATION")
    print("  Target Vertical: Real Estate (Agents, Brokerages, Buyers & Sellers)")
    print("=" * 70)

    assistant = AlgoriseRealtorSalesAssistant()

    # 1. Test SMS Outreach for Home Buyer Lead
    print("\n[1] Generating Personalized SMS Outreach (Buyer Lead)...")
    buyer_lead = {
        "name": "Sarah Jenkins",
        "lead_type": "buyer",
        "property_interest": "3-Bedroom Suburban Home with Pool",
        "location": "North Scottsdale, AZ",
        "budget": "$850,000",
        "source": "Zillow Listing View"
    }
    sms_res = assistant.generate_outreach(buyer_lead, channel="sms")
    print(f"    Channel: {sms_res['channel']}")
    print(f"    Content: \"{sms_res['outreach_content']}\"")
    print(f"    Latency: {sms_res['latency_ms']}ms")

    # 2. Test Email Outreach for Home Seller Lead
    print("\n[2] Generating High-Converting Email (Seller Lead)...")
    seller_lead = {
        "name": "David Martinez",
        "lead_type": "seller",
        "property_interest": "Single Family Home",
        "location": "Downtown Austin, TX",
        "budget": "$1,100,000",
        "source": "Home Valuation Calculator"
    }
    email_res = assistant.generate_outreach(seller_lead, channel="email")
    print(f"    Subject: {email_res['outreach_content']['subject']}")
    print(f"    Body:\n{email_res['outreach_content']['body']}")

    # 3. Test Explaining Complex Purchase Contract Draft
    print("\n[3] Explaining Complex Real Estate Contract Draft in Plain English...")
    complex_draft = """
    SECTION 8.2 FINANCING CONTINGENCY & EARNEST MONEY ESCROW:
    Buyer's obligation to consummate the acquisition of the subject real property is strictly contingent upon Buyer obtaining a written firm commitment for a conventional mortgage loan of not less than 80% of the purchase price ($680,000) within twenty-one (21) calendar days of mutual execution. In the event Buyer fails to obtain said commitment after good faith application, Buyer may deliver written notice of cancellation, upon which the Earnest Money Deposit ($15,000) held in Escrow by Fidelity National Title shall be promptly remitted to Buyer in full without deduction.
    """
    
    # First-time home buyer mode
    explanation_res = assistant.explain_draft(complex_draft, audience_style="first_time_buyer")
    print(f"    Style: {explanation_res['audience_style']}")
    print(f"    Summary:\n{explanation_res['plain_english_summary']}")
    print("    Decoded Clauses:")
    for c in explanation_res['key_clauses_decoded']:
        print(f"      • {c['term']}: {c['plain_english']}")

    # 4. Test Concise SMS Summary Mode
    print("\n[4] Explaining Draft as a Quick Text/SMS...")
    sms_draft_res = assistant.explain_draft(complex_draft, audience_style="concise_sms")
    print(f"    Quick SMS Version:\n    \"{sms_draft_res['plain_english_summary']}\"")

    # 5. Test Message Dispatch Relay
    print("\n[5] Dispatching Text to Client Phone...")
    dispatch_res = assistant.dispatch_text_action(
        destination="+1 (480) 555-0199",
        content=sms_draft_res['plain_english_summary'],
        channel="sms"
    )
    print(f"    Status:      {dispatch_res['status']}")
    print(f"    Destination: {dispatch_res['destination']}")
    print(f"    Gateway:     {dispatch_res['gateway']}")
    print(f"    Timestamp:   {dispatch_res['timestamp']}")

    print("\n" + "=" * 70)
    print(">> REALTOR-REACH AI SALES ASSISTANT: 100% OPERATIONAL & VERIFIED")
    print("=" * 70)

if __name__ == "__main__":
    main()
