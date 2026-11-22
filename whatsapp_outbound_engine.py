"""
================================================================================
ALGORISE AI — HYBRID WHATSAPP OUTBOUND ENGINE & COMMAND CENTER (CALIBRATED)
Pricing: ₹250 Live Remote Support | ₹500 Base + Distance for Personal Visit
Integrates Personal Line (+91 92270 95624) & UPI (9227095624@upi)
================================================================================
"""
import sys
import os
import re
import json
import csv
import webbrowser
import urllib.request
import urllib.parse
from datetime import datetime, timezone

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# ==============================================================================
# FOUNDER & PERSONAL VISIT CONFIGURATION
# ==============================================================================
FOUNDER_PHONE = "9227095624"
FOUNDER_PHONE_DISPLAY = "+91 92270 95624"
FOUNDER_E164 = "+919227095624"
FOUNDER_WHATSAPP_LINK = f"https://wa.me/{FOUNDER_PHONE}"
FOUNDER_UPI_VPA = f"{FOUNDER_PHONE}@upi"

COMPANY_NAME = "Algorise AI Solutions"
PAYEE_NAME = "Hardik / Algorise AI"
DEMO_URL = "https://algorise-ai.com/#surat-facebook-agent"

# Calibrated Pricing Constants
REMOTE_SUPPORT_FEE = 250   # Flat ₹250 for Remote AnyDesk / TeamViewer / UltraViewer session
BASE_VISITING_FEE = 500    # Flat ₹500 Base for local / Zone 1 personal visit

# ==============================================================================
# CURATED HIGH-TICKET COMMERCIAL TARGETS WITH DISTANCE-CALIBRATED PRICING
# ==============================================================================
# Distance Model: ₹500 Base (0-6 km) | ₹750 (6-14 km) | ₹1,000 (15+ km)
LEADS_DATABASE = [
    {
        "id": "LEAD-001",
        "name": "Kuberji Textiles (Wholesale Sarees)",
        "contact_person": "Kuberji Sheth / Sales Head",
        "phone": "+91 98251 10928",
        "sector": "Textiles & Sarees",
        "market": "Ring Road, Surat",
        "distance_km": 4,
        "zone": "Zone 1 (Core - 4 km)",
        "remote_fee": REMOTE_SUPPORT_FEE,
        "visiting_charge": 500,  # Base ₹500
        "ad_status": "Active Meta Video Ads (Leads leaking in comments)",
        "priority": "HIGH",
        "notes": "Competitor brokers posting numbers in ad comments; needs Dalal Shield."
    },
    {
        "id": "LEAD-002",
        "name": "Radhe Krishna Silk Mills",
        "contact_person": "Managing Director",
        "phone": "+91 99092 44102",
        "sector": "Textiles & Sarees",
        "market": "Millennium Textile Market, Surat",
        "distance_km": 5,
        "zone": "Zone 1 (Core - 5 km)",
        "remote_fee": REMOTE_SUPPORT_FEE,
        "visiting_charge": 500,  # Base ₹500
        "ad_status": "Active Instagram Reels Campaign",
        "priority": "HIGH",
        "notes": "High comment volume; needs 0.05s automated wholesale price quotes."
    },
    {
        "id": "LEAD-003",
        "name": "Surat CVD Diamonds & Gems",
        "contact_person": "Export Director",
        "phone": "+91 98795 33219",
        "sector": "CVD & Lab-Grown Diamonds",
        "market": "Katargam Diamond Bourse, Surat",
        "distance_km": 11,
        "zone": "Zone 2 (Katargam - 11 km)",
        "remote_fee": REMOTE_SUPPORT_FEE,
        "visiting_charge": 750,  # ₹500 base + ₹250 distance
        "ad_status": "High-Ticket B2B Global Exporter",
        "priority": "VERY HIGH",
        "notes": "Requires secure CRM sync + on-site local network integration."
    },
    {
        "id": "LEAD-004",
        "name": "Shree Ram Creators & Kurti Hub",
        "contact_person": "Proprietor",
        "phone": "+91 98241 88921",
        "sector": "Kurti & Dress Material",
        "market": "Sahara Darwaja, Surat",
        "distance_km": 5,
        "zone": "Zone 1 (Core - 5 km)",
        "remote_fee": REMOTE_SUPPORT_FEE,
        "visiting_charge": 500,  # Base ₹500
        "ad_status": "Catalog Ads Active",
        "priority": "HIGH",
        "notes": "Wants instant Telegram lead alerts on wholesale order inquiries."
    },
    {
        "id": "LEAD-005",
        "name": "Vesu Prime Realty & Infrastructure",
        "contact_person": "Chief Sales Officer",
        "phone": "+91 99250 67114",
        "sector": "Real Estate & Builders",
        "market": "VIP Road, Vesu, Surat",
        "distance_km": 12,
        "zone": "Zone 2 (Vesu - 12 km)",
        "remote_fee": REMOTE_SUPPORT_FEE,
        "visiting_charge": 750,  # ₹500 base + ₹250 distance
        "ad_status": "Active High-Spend Meta Lead Ads",
        "priority": "VERY HIGH",
        "notes": "Lead response lag exceeding 4 hours; sales team needs instant WhatsApp lead routing."
    },
    {
        "id": "LEAD-006",
        "name": "Diamond City Lab-Grown Jewel Hub",
        "contact_person": "Sales Director",
        "phone": "+91 98980 12345",
        "sector": "CVD & Lab-Grown Diamonds",
        "market": "Varachha Main Road, Surat",
        "distance_km": 10,
        "zone": "Zone 2 (Varachha - 10 km)",
        "remote_fee": REMOTE_SUPPORT_FEE,
        "visiting_charge": 750,  # ₹500 base + ₹250 distance
        "ad_status": "Active Meta Campaign",
        "priority": "VERY HIGH",
        "notes": "Needs AnyDesk remote setup or on-site evening consultation."
    },
    {
        "id": "LEAD-007",
        "name": "Mahalaxmi Fabrics & Digital Prints",
        "contact_person": "Commercial Manager",
        "phone": "+91 98250 99881",
        "sector": "Textiles & Sarees",
        "market": "Radharaman Textile Market, Surat",
        "distance_km": 4,
        "zone": "Zone 1 (Core - 4 km)",
        "remote_fee": REMOTE_SUPPORT_FEE,
        "visiting_charge": 500,  # Base ₹500
        "ad_status": "Running Reels Ads",
        "priority": "HIGH",
        "notes": "Brokers stealing catalog clicks; requires Dalal Shield."
    },
    {
        "id": "LEAD-008",
        "name": "Avadh Luxury Living Projects",
        "contact_person": "Head of Marketing",
        "phone": "+91 99099 87654",
        "sector": "Real Estate & Builders",
        "market": "Pal - Adajan, Surat",
        "distance_km": 6,
        "zone": "Zone 1 (Adajan - 6 km)",
        "remote_fee": REMOTE_SUPPORT_FEE,
        "visiting_charge": 500,  # Base ₹500
        "ad_status": "Lead Generation Campaign",
        "priority": "VERY HIGH",
        "notes": "Looking for turnkey on-site team onboarding and CRM lead defense."
    }
]

# ==============================================================================
# DYNAMIC UPI GENERATION ENGINE
# ==============================================================================
def create_upi_bundle(amount: float, lead_name: str, purpose: str) -> dict:
    """Generates real-time UPI deep-links for Google Pay, PhonePe, Paytm, and BHIM."""
    clean_tx = f"{purpose}_{lead_name.replace(' ', '_')[:10]}"
    params = {
        "pa": FOUNDER_UPI_VPA,
        "pn": PAYEE_NAME,
        "am": f"{amount:.2f}",
        "cu": "INR",
        "tn": clean_tx
    }
    intent_url = f"upi://pay?{urllib.parse.urlencode(params)}"
    qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=300x300&data={urllib.parse.quote(intent_url)}"
    
    return {
        "vpa": FOUNDER_UPI_VPA,
        "amount": amount,
        "note": clean_tx,
        "intent_url": intent_url,
        "qr_url": qr_url,
        "display_text": f"UPI: {FOUNDER_UPI_VPA} | Amount: ₹{amount:,.2f}"
    }

# ==============================================================================
# DUAL-TRACK PITCH GENERATORS (WITH ₹250 REMOTE & ₹500+ VISIT)
# ==============================================================================
def generate_remote_pitch_gujarati(lead: dict) -> str:
    """Track 1: Flat ₹250 Instant Live Remote Support (AnyDesk/UltraViewer)."""
    return (
        f"નમસ્તે {lead['name']} સાહેબ, જય શ્રી કૃષ્ણ 🙏\n\n"
        f"તમે દર મહિને ફેસબુક અને ઇન્સ્ટાગ્રામ એડ્સ પાછળ મોટો ખર્ચ કરો છો, પણ તમારી એડ નીચે ૧૫-૨૦ હોલસેલ વેપારીઓના ભાવ પૂછેલા મેસેજ કલાકો સુધી વગર જવાબે પડ્યા રહે છે! "
        f"બીજા દલાલો કમેન્ટમાં પોતાનો નંબર મૂકીને સીધો તમારો કસ્ટમર ચોરી જાય છે.\n\n"
        f"⚡ અમારું સોલ્યુશન: \"Autonomous AI Facebook Sales Agent & Dalal Shield\"\n"
        f"• ૦.૦૫ સેકન્ડમાં જાહેર રિપ્લાય + પ્રાઇવેટ મેસેન્જર ડીએમ\n"
        f"• બ્રોકર શીલ્ડ: દલાલનો નંબર ૦.૦૨ સેકન્ડમાં ઓટો-હાઈડ\n"
        f"• ગ્રાહક નંબર આપે કે તરત તમારા Telegram/WhatsApp પર હોટ લીડ એલર્ટ!\n\n"
        f"💻 આજે જ લાઈવ રીમોટ સપોર્ટ (AnyDesk / UltraViewer):\n"
        f"👉 માત્ર ₹૨૫૦ ફિક્સ ચાર્જમાં અમારી ટેકનિકલ ટીમ હમણાં જ લાઈવ કનેક્ટ થઈને તમારી સમસ્યા તપાસી સોલ્વ કરી આપશે!\n\n"
        f"👉 ૧૦ સેકન્ડનો લાઈવ વિડીયો ડેમો: {DEMO_URL}\n\n"
        f"૧૫ મિનિટમાં AnyDesk કનેક્ટ કરવા માટે સીધો કૉલ/WhatsApp કરો:\n"
        f"📞 {FOUNDER_PHONE_DISPLAY} (હાર્દિક / Algorise AI)\n"
        f"UPI: {FOUNDER_UPI_VPA} (₹૨૫૦)"
    )

def generate_onsite_pitch_hybrid(lead: dict) -> str:
    """Track 2: Physical On-Site Visit (₹500 Base + Distance dependent)."""
    return (
        f"નમસ્તે {lead['name']} સાહેબ, 🙏\n\n"
        f"જો તમારી {lead['market']} સ્થિત ઓફિસ/શોરૂમ પર Facebook Ads Lead Sync, CRM કનેક્શન અથવા નેટવર્ક સંબંધિત સમસ્યા હોય કે તમારે રૂબરૂ પર્સનલ ડેમો અને સેટઅપ જોઈતું હોય, તો હું ૯૦ મિનિટમાં રૂબરૂ હાજર થઈ જઈશ.\n\n"
        f"🛠️ ઓન-સાઇટ સેવાઓ:\n"
        f"૧. તમારી આખી સેલ્સ ટીમ માટે Meta Leads સીધા WhatsApp/Telegram પર લાઈવ સેટઅપ\n"
        f"૨. દલાલ પ્રોટેક્શન શીલ્ડ & AI સેલ્સ રોબોટ ઇન્સ્ટોલેશન\n"
        f"૩. સ્ટાફને રૂબરૂ ટ્રેનિંગ અને ડેશબોર્ડ એક્ટિવેશન\n\n"
        f"📍 વિઝિટિંગ ચાર્જ (પર્સનલ વિઝિટ & કેર ડિપોઝિટ):\n"
        f"👉 માત્ર ₹{lead['visiting_charge']} (બેઝ ₹૫૦૦ + અંતર આધારિત - {lead['zone']})\n"
        f"💡 ખાસ ફાયદો: જો તમે અમારી સિસ્ટમ લેશો, તો આ પૂરેપૂરા ₹{lead['visiting_charge']} તમારા પ્રોડક્ટ બિલમાંથી ૧૦૦% બાદ (Credit) મળશે!\n\n"
        f"પર્સનલ વિઝિટ બુક કરવા અને ૯૦ મિનિટમાં મને મળવા માટે અહીં UPI થી ડિપોઝિટ કરી સ્ક્રીનશોટ મોકલો:\n"
        f"💳 UPI ID: {FOUNDER_UPI_VPA} (₹{lead['visiting_charge']})\n"
        f"📞 ડાયરેક્ટ કોલ: {FOUNDER_PHONE_DISPLAY} (હાર્દિક - Algorise AI Field Lead)"
    )

def generate_english_corporate_pitch(lead: dict) -> str:
    """Track 3: Corporate English Pitch with ₹250 Remote / ₹500+ On-Site."""
    return (
        f"Hello {lead['contact_person']} ({lead['name']}),\n\n"
        f"We noticed your active Meta ad campaigns targeting high-intent buyers in {lead['sector']}. "
        f"Unmonitored comments and competitor broker poaching are resulting in significant lead leakage.\n\n"
        f"Algorise AI provides autonomous lead defense & instantaneous WhatsApp sales triage:\n"
        f"• 0.05-second automated response with verified pricing/catalog\n"
        f"• Instant broker-shield: auto-hiding malicious competitor phone numbers\n"
        f"• Instant Telegram/CRM push for verified wholesale inquiries\n\n"
        f"Transparent Service Pricing Today:\n"
        f"1. Live Remote AnyDesk Support Session: Flat ₹250\n"
        f"2. Priority On-Site Engineering Visit ({lead['market']}): ₹{lead['visiting_charge']} (₹500 Base + Distance travel, 100% credited against your monthly retainer)\n\n"
        f"To schedule an immediate on-site visit or remote session:\n"
        f"Call/WhatsApp: {FOUNDER_PHONE_DISPLAY}\n"
        f"UPI Deposit: {FOUNDER_UPI_VPA}"
    )

# ==============================================================================
# HTML COMMAND CENTER GENERATOR (UPDATED PRICING)
# ==============================================================================
def build_interactive_html_console(leads_data: list, output_path: str):
    """Creates a modern, responsive HTML operations console with calibrated ₹250 / ₹500+ pricing."""
    cards_html = ""
    for lead in leads_data:
        clean_num = "".join(filter(str.isdigit, lead['phone']))
        track1_wa = f"https://wa.me/{clean_num}?text={urllib.parse.quote(lead['pitch_remote_gu'])}"
        track2_wa = f"https://wa.me/{clean_num}?text={urllib.parse.quote(lead['pitch_onsite_gu'])}"
        track3_wa = f"https://wa.me/{clean_num}?text={urllib.parse.quote(lead['pitch_corp_en'])}"
        
        cards_html += f"""
        <div class="bg-gray-800 rounded-xl p-5 border border-gray-700 hover:border-emerald-500 transition-all shadow-lg flex flex-col justify-between">
            <div>
                <div class="flex items-center justify-between mb-2">
                    <span class="text-xs font-mono font-semibold px-2.5 py-0.5 rounded bg-emerald-900 text-emerald-300">{lead['zone']}</span>
                    <span class="text-xs font-mono font-semibold px-2.5 py-0.5 rounded bg-amber-900 text-amber-300">{lead['priority']}</span>
                </div>
                <h3 class="text-lg font-bold text-white mb-1">{lead['name']}</h3>
                <p class="text-sm text-gray-400 mb-1">📍 {lead['market']} (~{lead['distance_km']} km)</p>
                <p class="text-sm text-emerald-400 font-mono mb-3">📱 {lead['phone']} ({lead['contact_person']})</p>
                <div class="bg-gray-900 rounded p-3 text-xs text-gray-300 font-mono mb-4 border border-gray-700 space-y-1">
                    <div class="flex justify-between items-center">
                        <span class="text-gray-400">⚡ Remote AnyDesk:</span>
                        <span class="text-emerald-400 font-bold">₹{lead['remote_fee']} Flat</span>
                    </div>
                    <div class="flex justify-between items-center">
                        <span class="text-gray-400">🚗 On-Site Visit:</span>
                        <span class="text-amber-400 font-bold">₹{lead['visiting_charge']} (₹500 Base + Dist)</span>
                    </div>
                </div>
            </div>

            <div class="space-y-2 pt-2 border-t border-gray-700">
                <a href="{track1_wa}" target="_blank" class="w-full inline-flex items-center justify-center px-4 py-2.5 bg-emerald-600 hover:bg-emerald-500 text-white font-semibold rounded-lg text-sm transition-colors shadow">
                    💻 Track 1: Remote Support (₹250)
                </a>
                <a href="{track2_wa}" target="_blank" class="w-full inline-flex items-center justify-center px-4 py-2.5 bg-blue-600 hover:bg-blue-500 text-white font-semibold rounded-lg text-sm transition-colors shadow">
                    🚗 Track 2: On-Site Visit (₹{lead['visiting_charge']})
                </a>
                <div class="flex items-center justify-between gap-2 pt-1">
                    <a href="{track3_wa}" target="_blank" class="flex-1 text-center py-1.5 bg-gray-700 hover:bg-gray-600 text-gray-200 text-xs rounded transition-colors">
                        📄 Corporate English
                    </a>
                    <a href="{lead['upi_remote']['intent_url']}" class="flex-1 text-center py-1.5 bg-purple-700 hover:bg-purple-600 text-white text-xs rounded transition-colors font-mono" title="₹250 Remote UPI">
                        💳 ₹250 UPI
                    </a>
                    <a href="{lead['upi_visit']['intent_url']}" class="flex-1 text-center py-1.5 bg-indigo-700 hover:bg-indigo-600 text-white text-xs rounded transition-colors font-mono" title="₹{lead['visiting_charge']} Visit UPI">
                        💳 ₹{lead['visiting_charge']} UPI
                    </a>
                    <a href="{lead['upi_remote']['qr_url']}" target="_blank" class="px-2 py-1.5 bg-gray-700 hover:bg-gray-600 text-xs text-gray-300 rounded" title="View ₹250 QR Code">
                        📷 QR
                    </a>
                </div>
            </div>
        </div>
        """

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Algorise AI — Hybrid Outbound & Personal Visit Command Center</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-900 text-gray-100 min-h-screen">
    <!-- Top Header -->
    <header class="bg-gray-800 border-b border-gray-700 sticky top-0 z-50 shadow-md">
        <div class="max-w-7xl mx-auto px-4 py-4 sm:px-6 lg:px-8 flex flex-wrap items-center justify-between gap-4">
            <div class="flex items-center space-x-3">
                <div class="h-10 w-10 bg-emerald-500 rounded-lg flex items-center justify-center font-black text-xl text-gray-900 shadow">A</div>
                <div>
                    <h1 class="text-xl font-bold tracking-tight text-white">Algorise AI — Hybrid Dispatch Console</h1>
                    <p class="text-xs text-gray-400">₹250 Remote Support • ₹500 Base + Distance Personal Visit</p>
                </div>
            </div>
            <!-- Founder Hotline & UPI Pill -->
            <div class="flex flex-wrap items-center gap-3">
                <div class="bg-gray-900 border border-gray-700 rounded-lg px-3 py-1.5 flex items-center space-x-2">
                    <span class="text-xs text-gray-400">Personal Visit & Care:</span>
                    <a href="tel:+919227095624" class="text-sm font-mono font-bold text-emerald-400 hover:underline">{FOUNDER_PHONE_DISPLAY}</a>
                </div>
                <div class="bg-gray-900 border border-gray-700 rounded-lg px-3 py-1.5 flex items-center space-x-2">
                    <span class="text-xs text-gray-400">Primary UPI:</span>
                    <span class="text-sm font-mono font-bold text-amber-400">{FOUNDER_UPI_VPA}</span>
                </div>
                <a href="{FOUNDER_WHATSAPP_LINK}" target="_blank" class="px-3 py-1.5 bg-emerald-500 hover:bg-emerald-400 text-gray-900 font-bold text-xs rounded-lg transition-colors">
                    📱 Direct WhatsApp Me
                </a>
            </div>
        </div>
    </header>

    <!-- Operational Banner -->
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <div class="bg-gradient-to-r from-emerald-950 via-gray-800 to-blue-950 border border-emerald-800/50 rounded-2xl p-6 shadow-xl mb-8">
            <div class="flex flex-col md:flex-row md:items-center justify-between gap-6">
                <div>
                    <span class="inline-block px-3 py-1 bg-emerald-500/20 text-emerald-300 text-xs font-mono font-bold rounded-full mb-2">⚡ CALIBRATED PRICING ACTIVE</span>
                    <h2 class="text-2xl font-black text-white">Surat B2B Direct WhatsApp Dispatcher</h2>
                    <p class="text-gray-300 text-sm mt-1 max-w-2xl">
                        Unbeatable low-barrier pricing: <strong class="text-emerald-400">₹250 for instant AnyDesk remote support</strong> and <strong class="text-amber-400">₹500 Base + Distance for on-site personal visit</strong>. Click any button to send pre-filled WhatsApp messages with your personal number ({FOUNDER_PHONE_DISPLAY})!
                    </p>
                </div>
                <div class="flex flex-col sm:flex-row gap-3">
                    <div class="bg-gray-900/80 border border-gray-700 rounded-xl p-3 text-center min-w-[130px]">
                        <p class="text-xs text-gray-400 font-mono">Remote Support</p>
                        <p class="text-2xl font-black text-emerald-400 font-mono">₹250</p>
                    </div>
                    <div class="bg-gray-900/80 border border-gray-700 rounded-xl p-3 text-center min-w-[130px]">
                        <p class="text-xs text-gray-400 font-mono">On-Site Visit</p>
                        <p class="text-2xl font-black text-amber-400 font-mono">₹500+</p>
                    </div>
                    <div class="bg-gray-900/80 border border-gray-700 rounded-xl p-3 text-center min-w-[110px]">
                        <p class="text-xs text-gray-400 font-mono">Truck-Roll Risk</p>
                        <p class="text-2xl font-black text-blue-400 font-mono">0% Loss</p>
                    </div>
                </div>
            </div>
        </div>

        <!-- Leads Grid -->
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {cards_html}
        </div>

        <!-- Footer Protocol Notice -->
        <div class="mt-12 bg-gray-800/60 border border-gray-700 rounded-xl p-6 text-sm text-gray-400">
            <h4 class="font-bold text-gray-200 mb-2">🛡️ Zero Preventable Loss Operating Rule:</h4>
            <p>1. <strong>Remote Support:</strong> ₹250 flat fee collected via UPI prior to AnyDesk live session initiation.</p>
            <p class="mt-1">2. <strong>Personal On-Site Visit:</strong> Base ₹500 (Ring Road / Millennium / Sahara Darwaja) or ₹750 (Katargam / Varachha / Vesu) paid upfront to <span class="font-mono text-emerald-400">{FOUNDER_UPI_VPA}</span>.</p>
            <p class="mt-1">3. <strong>100% Credit Roll-Over:</strong> Both ₹250 and ₹500+ deposits are 100% credited against any monthly retainer or AI bot subscription!</p>
        </div>
    </div>
</body>
</html>
    """
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)

# ==============================================================================
# MAIN EXECUTION ROUTINE
# ==============================================================================
def run_hybrid_outbound_engine():
    print("=" * 80)
    print("  ALGORISE AI — CALIBRATED HYBRID WHATSAPP OUTBOUND ENGINE")
    print(f"  Remote: ₹{REMOTE_SUPPORT_FEE} | On-Site: ₹{BASE_VISITING_FEE}+ (Distance-dependent)")
    print(f"  Founder Personal Line: {FOUNDER_PHONE_DISPLAY} | UPI: {FOUNDER_UPI_VPA}")
    print("=" * 80)

    base_dir = os.path.dirname(os.path.abspath(__file__))
    leads_dir = os.path.join(base_dir, "leads")
    os.makedirs(leads_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_file = os.path.join(leads_dir, f"outbound_dispatch_{timestamp}.csv")
    html_file = os.path.join(base_dir, "outbound_command_center.html")

    enriched_leads = []
    print(f"\n[+] Processing {len(LEADS_DATABASE)} Curated High-Ticket Accounts...")

    for i, lead in enumerate(LEADS_DATABASE, 1):
        lead['pitch_remote_gu'] = generate_remote_pitch_gujarati(lead)
        lead['pitch_onsite_gu'] = generate_onsite_pitch_hybrid(lead)
        lead['pitch_corp_en'] = generate_english_corporate_pitch(lead)

        # Generate UPI bundles for both ₹250 Remote and ₹500+ Visit
        lead['upi_remote'] = create_upi_bundle(float(lead['remote_fee']), lead['name'], "Remote_250")
        lead['upi_visit'] = create_upi_bundle(float(lead['visiting_charge']), lead['name'], "Visit_Deposit")

        clean_phone = "".join(filter(str.isdigit, lead['phone']))
        lead['whatsapp_url_remote'] = f"https://wa.me/{clean_phone}?text={urllib.parse.quote(lead['pitch_remote_gu'])}"
        lead['whatsapp_url_onsite'] = f"https://wa.me/{clean_phone}?text={urllib.parse.quote(lead['pitch_onsite_gu'])}"

        enriched_leads.append(lead)

        print(f"\n[{i}/{len(LEADS_DATABASE)}] {lead['name']}")
        print(f"  📍 Cluster:       {lead['market']} ({lead['zone']})")
        print(f"  📱 Owner Phone:   {lead['phone']}")
        print(f"  ⚡ Remote Fee:    ₹{lead['remote_fee']} (UPI: {FOUNDER_UPI_VPA})")
        print(f"  🚗 On-Site Fee:   ₹{lead['visiting_charge']} (UPI: {FOUNDER_UPI_VPA})")
        print(f"  🔗 1-Click WA:    {lead['whatsapp_url_remote'][:65]}...")

    # Write CSV
    fieldnames = [
        "id", "name", "contact_person", "phone", "sector", "market", "zone",
        "distance_km", "remote_fee", "visiting_charge", "ad_status", "priority",
        "whatsapp_url_remote", "whatsapp_url_onsite"
    ]
    with open(csv_file, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(enriched_leads)

    # Build Interactive HTML Console
    build_interactive_html_console(enriched_leads, html_file)

    print("\n" + "=" * 80)
    print(f"✅ Real-Time Outbound CSV generated:  {csv_file}")
    print(f"🚀 Interactive Command Console built: {html_file}")
    print(f"📞 Inbound Personal Care Line:        {FOUNDER_PHONE_DISPLAY}")
    print(f"💳 Active Merchant UPI:               {FOUNDER_UPI_VPA}")
    print("=" * 80)

    try:
        webbrowser.open(f"file:///{html_file.replace(os.sep, '/')}")
        print("🌐 Opened Outbound Command Center in your default web browser!")
    except Exception:
        pass

if __name__ == "__main__":
    run_hybrid_outbound_engine()
