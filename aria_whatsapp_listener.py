"""
================================================================================
ALGORISE AI — ARIA WHATSAPP INBOUND LISTENER (CALIBRATED PRICING)
Pricing: ₹250 Remote AnyDesk Support | ₹500 Base + Distance Personal Visit
Listens for Inbound Inquiries on +91 92270 95624 | UPI: 9227095624@upi
================================================================================
"""
import sys
import os
import re
import json
import urllib.parse
from datetime import datetime, timezone

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

FOUNDER_PHONE = "9227095624"
FOUNDER_PHONE_DISPLAY = "+91 92270 95624"
FOUNDER_UPI_VPA = f"{FOUNDER_PHONE}@upi"

REMOTE_SUPPORT_FEE = 250
BASE_VISIT_FEE = 500

PHYSICAL_KEYWORDS = [
    "network down", "fiber cut", "router", "switch", "lan", "cable",
    "wifi", "printer", "machine", "camera", "cctv", "hardware", "office aavo",
    "rubru", "visit", "office visit", "factory", "personal", "meet"
]

SOFTWARE_KEYWORDS = [
    "facebook", "instagram", "ads", "lead", "pixel", "capi", "token",
    "bot", "anydesk", "teamviewer", "ultraviewer", "api", "dalal", "broker",
    "crm", "hubspot", "salesforce", "webhook", "telegram"
]

def triage_inbound_message(sender_phone: str, sender_name: str, message_text: str, location_text: str = "Ring Road") -> dict:
    """
    Evaluates incoming WhatsApp message to determine if it requires:
    - Mode 1: Instant AnyDesk Remote Session (₹250 Flat)
    - Mode 2: Physical On-Site Visit (₹500 Base + Distance)
    """
    text_lower = message_text.lower()
    
    physical_hits = sum(1 for kw in PHYSICAL_KEYWORDS if kw in text_lower)
    software_hits = sum(1 for kw in SOFTWARE_KEYWORDS if kw in text_lower)
    
    # Calculate OnSiteNecessityScore (S)
    if "visit" in text_lower or "rubru" in text_lower or "office aavo" in text_lower or physical_hits >= 2:
        on_site_score = 0.90
    elif physical_hits > 0 and software_hits == 0:
        on_site_score = 0.75
    elif software_hits > 0 and physical_hits == 0:
        on_site_score = 0.15
    else:
        on_site_score = 0.45
        
    # Distance-based visiting fee: ₹500 for Zone 1 (0-6 km), ₹750 for Zone 2 (6-14 km)
    if any(k in location_text.lower() for k in ["vesu", "katargam", "varachha", "vip road"]):
        visiting_fee = 750  # ₹500 base + ₹250 distance travel
        zone = "Zone 2 (Katargam / Vesu / Varachha)"
    elif any(k in location_text.lower() for k in ["sachin", "hazira", "palsana", "kamrej"]):
        visiting_fee = 1000  # ₹500 base + ₹500 extended industrial
        zone = "Zone 3 (Extended Industrial Belt)"
    else:
        visiting_fee = 500  # Base ₹500
        zone = "Zone 1 (Ring Road / Millennium / Adajan)"

    if on_site_score >= 0.70:
        mode = "ON_SITE_PHYSICAL_DISPATCH"
        tx_note = f"VisitDep_{sender_name.replace(' ', '_')[:10]}"
        upi_url = f"upi://pay?pa={FOUNDER_UPI_VPA}&pn=AlgoriseAI&am={visiting_fee}&cu=INR&tn={tx_note}"
        qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=300x300&data={urllib.parse.quote(upi_url)}"
        
        reply = (
            f"નમસ્તે {sender_name} સાહેબ, 🙏\n"
            f"તમારી વિનંતી બદલ આભાર. હું (હાર્દિક - Algorise AI) પોતે તમારી {location_text} સ્થિત ઓફિસે પર્સનલ વિઝિટ માટે ૯૦ મિનિટમાં આવી શકું છું.\n\n"
            f"📍 વિઝિટિંગ ચાર્જ: માત્ર ₹{visiting_fee} (બેઝ ₹૫૦૦ + અંતર આધારિત - {zone})\n"
            f"💡 ૧૦૦% ક્રેડિટ: જો તમે અમારી સિસ્ટમ લેશો, તો આ પૂરેપૂરી રકમ તમારા બિલમાંથી બાદ મળશે!\n\n"
            f"ટેકનિશિયન સ્લોટ કન્ફર્મ કરવા નીચે આપેલા UPI પર ડિપોઝિટ કરી સ્ક્રીનશોટ મોકલો:\n"
            f"💳 UPI ID: {FOUNDER_UPI_VPA} (₹{visiting_fee})\n"
            f"🔗 ડાયરેક્ટ પેમેન્ટ લિંક: {upi_url}\n"
            f"📞 સીધો સંપર્ક: {FOUNDER_PHONE_DISPLAY}"
        )
    else:
        mode = "INSTANT_REMOTE_ANYDESK"
        tx_note = f"Remote250_{sender_name.replace(' ', '_')[:10]}"
        upi_url = f"upi://pay?pa={FOUNDER_UPI_VPA}&pn=AlgoriseAI&am={REMOTE_SUPPORT_FEE}&cu=INR&tn={tx_note}"
        reply = (
            f"નમસ્તે {sender_name} સાહેબ, 🙏\n"
            f"તમારો પ્રશ્ન હમણાં જ લાઈવ AnyDesk અથવા TeamViewer દ્વારા સોલ્વ કરી આપીએ છીએ.\n\n"
            f"⚡ લાઈવ AnyDesk સપોર્ટ (માત્ર ₹૨૫૦ ફિક્સ ચાર્જ):\n"
            f"૧. નીચે આપેલા UPI પર ₹૨૫૦ પે કરી AnyDesk નો ૯-અંકનો નંબર અહીં મોકલો.\n"
            f"૨. અમારી ટીમ ૧૫ મિનિટમાં કનેક્ટ થઈ તમારી એડ્સ/સિસ્ટમ સેટ કરી આપશે.\n"
            f"💳 UPI ID: {FOUNDER_UPI_VPA} (₹૨૫૦)\n"
            f"🔗 UPI Link: {upi_url}\n\n"
            f"રૂબરૂ પર્સનલ વિઝિટ જોઈતી હોય તો પણ જણાવશો (બેઝ ₹૫૦૦ + અંતર). સંપર્ક: {FOUNDER_PHONE_DISPLAY}"
        )

    return {
        "sender_phone": sender_phone,
        "sender_name": sender_name,
        "on_site_score": on_site_score,
        "mode": mode,
        "location": location_text,
        "fee": visiting_fee if on_site_score >= 0.70 else REMOTE_SUPPORT_FEE,
        "auto_reply": reply
    }

if __name__ == "__main__":
    print("Testing Inbound Triage with Calibrated Pricing...")
    sample_remote = triage_inbound_message(
        sender_phone="+91 98251 10928",
        sender_name="Kuberji Textiles",
        message_text="Facebook ad comment ma dalal number nakhe chhe, anydesk par check karo",
        location_text="Ring Road, Surat"
    )
    print(f"\n[Test 1] Mode: {sample_remote['mode']} | Fee: ₹{sample_remote['fee']}")
    print(sample_remote['auto_reply'])
    
    sample_visit = triage_inbound_message(
        sender_phone="+91 98795 33219",
        sender_name="Surat CVD Diamonds",
        message_text="Katargam office par aavi ne badhu rubru set kari aapo",
        location_text="Katargam, Surat"
    )
    print(f"\n[Test 2] Mode: {sample_visit['mode']} | Fee: ₹{sample_visit['fee']}")
    print(sample_visit['auto_reply'])
