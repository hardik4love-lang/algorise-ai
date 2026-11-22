"""
================================================================================
SURAT B2B ADVERTISER & MERCHANT PROSPECTING ENGINE (HYBRID CALIBRATED)
Pricing: ₹250 Remote Support | ₹500 Base + Distance for Personal Visit
Direct Engineering & Customer Care: +91 92270 95624 | UPI: 9227095624@upi
================================================================================
"""
import sys
import os
import re
import json
import csv
import urllib.request
import urllib.parse
from datetime import datetime, timezone

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
DEMO_URL = 'https://algorise-ai.com/#surat-facebook-agent'
PITCH_URL = 'https://algorise-ai.com/field_pitch.html'

# Direct Founder & Field Engineer Personal Care Line
FOUNDER_PHONE = '9227095624'
FOUNDER_PHONE_DISPLAY = '+91 92270 95624'
FOUNDER_WHATSAPP_LINK = f'https://wa.me/91{FOUNDER_PHONE}'
FOUNDER_UPI_VPA = f'{FOUNDER_PHONE}@upi'

REMOTE_SUPPORT_FEE = 250
BASE_VISITING_FEE = 500

def get_sector_demo_url(sector: str) -> str:
    s = sector.lower()
    if 'textile' in s or 'saree' in s or 'kurti' in s or 'dress' in s:
        return 'https://algorise-ai.com/industry/textile-saree-wholesale-ai-agent.html'
    if 'diamond' in s or 'cvd' in s:
        return 'https://algorise-ai.com/industry/diamond-cvd-sales-agent.html'
    if 'real estate' in s or 'builder' in s or 'realty' in s:
        return 'https://algorise-ai.com/industry/real-estate-whatsapp-ai.html'
    return 'https://algorise-ai.com/industry/b2b-lead-defense.html'

def generate_upi_payment_link(amount: float, lead_name: str, mode: str = "Visit_Deposit") -> dict:
    """Generates real-time UPI deep-link and QR code URL for instant settlement."""
    tx_note = f"{mode[:10]}_{lead_name.replace(' ', '_')[:12]}"
    params = {
        'pa': FOUNDER_UPI_VPA,
        'pn': 'Algorise AI Personal Care',
        'am': f'{amount:.2f}',
        'cu': 'INR',
        'tn': tx_note
    }
    intent_url = f"upi://pay?{urllib.parse.urlencode(params)}"
    qr_image = f"https://api.qrserver.com/v1/create-qr-code/?size=300x300&data={urllib.parse.quote(intent_url)}"
    return {
        'intent_url': intent_url,
        'qr_image': qr_image,
        'vpa': FOUNDER_UPI_VPA,
        'amount': amount,
        'note': tx_note
    }

def generate_personalized_pitch(biz_name: str, sector: str, phone: str, visiting_charge: int = 500) -> str:
    """Generates tailored Gujarati WhatsApp sales pitch for Surat business owners."""
    return (
        f"નમસ્તે {biz_name} સાહેબ, જય શ્રી કૃષ્ણ 🙏\n\n"
        f"તમે દર મહિને ફેસબુક અને ઇન્સ્ટાગ્રામ એડ્સ પાછળ મોટો ખર્ચ કરો છો, પણ તમારી એડ નીચે ૧૫-૨૦ હોલસેલ વેપારીઓના ભાવ પૂછેલા મેસેજ કલાકો સુધી વગર જવાબે પડ્યા રહે છે! "
        f"બીજા દલાલો કમેન્ટમાં પોતાનો નંબર મૂકીને સીધો તમારો પાકો કસ્ટમર ચોરી જાય છે.\n\n"
        f"અમે ખાસ સુરતના {sector} વેપારીઓ માટે \"Autonomous AI Facebook Sales Agent & Dalal Shield\" લાવ્યા છીએ:\n"
        f"⚡ ૦.૦૫ સેકન્ડમાં જાહેર રિપ્લાય + પ્રાઇવેટ મેસેન્જર ડીએમ\n"
        f"🛡️ બ્રોકર શીલ્ડ: દલાલનો નંબર ૦.૦૨ સેકન્ડમાં ઓટો-હાઈડ\n"
        f"🗣️ અસલ સુરતી વેપારી ભાષા & ભાવમાં ડીલિંગ\n"
        f"📲 ગ્રાહક નંબર આપે કે તરત તમારા Telegram/WhatsApp પર હોટ લીડ એલર્ટ!\n\n"
        f"💼 આજે જ ઉપલબ્ધ ૨ વિકલ્પો:\n"
        f"૧. લાઈવ રીમોટ સપોર્ટ (AnyDesk): માત્ર ₹૨૫૦ ફિક્સ ચાર્જમાં હમણાં જ લાઈવ સોલ્યુશન!\n"
        f"૨. રૂબરૂ પર્સનલ વિઝિટ & ડેમો: હું પોતે તમારી ઓફિસે આવીને સેટઅપ કરી આપીશ (માત્ર ₹{visiting_charge} વિઝિટિંગ ડિપોઝિટ, જે સિસ્ટમ લેવા પર ૧૦૦% બાદ મળશે).\n\n"
        f"👉 ૧૦ સેકન્ડનો લાઈવ ડેમો ચેક કરો: {get_sector_demo_url(sector)}\n\n"
        f"AnyDesk લાઈવ સેટઅપ અથવા પર્સનલ વિઝિટ માટે સીધો મને Call અથવા WhatsApp કરો:\n"
        f"📞 {FOUNDER_PHONE_DISPLAY} (હાર્દિક / એલ્ગોરાઇઝ AI સુરત)\n"
        f"UPI: {FOUNDER_UPI_VPA}"
    )

def get_curated_surat_seed_leads() -> list:
    """Provides high-value verified Surat commercial targets with calibrated pricing."""
    return [
        {
            'name': 'Kuberji Textiles (Wholesale Sarees)',
            'sector': 'Textiles & Sarees',
            'market': 'Ring Road, Surat',
            'phone': '+91 98251 10928',
            'source': 'Ring Road Textile Hub',
            'ad_status': 'Active Meta Advertiser',
            'priority': 'HIGH',
            'visiting_charge': 500,
            'remote_fee': 250,
            'zone': 'Zone 1 (Ring Road - 4 km)'
        },
        {
            'name': 'Radhe Krishna Silk Mills',
            'sector': 'Textiles & Sarees',
            'market': 'Millennium Textile Market, Surat',
            'phone': '+91 99092 44102',
            'source': 'Millennium Market Cluster',
            'ad_status': 'Active Instagram Ads',
            'priority': 'HIGH',
            'visiting_charge': 500,
            'remote_fee': 250,
            'zone': 'Zone 1 (Millennium Market - 5 km)'
        },
        {
            'name': 'Surat CVD Diamonds & Gems',
            'sector': 'CVD & Lab-Grown Diamonds',
            'market': 'Katargam, Surat',
            'phone': '+91 98795 33219',
            'source': 'Katargam Diamond Association',
            'ad_status': 'High-Ticket B2B Exporter',
            'priority': 'VERY HIGH',
            'visiting_charge': 750,
            'remote_fee': 250,
            'zone': 'Zone 2 (Katargam - 11 km)'
        },
        {
            'name': 'Shree Ram Creators & Kurti Hub',
            'sector': 'Kurti & Dress Material',
            'market': 'Sahara Darwaja, Surat',
            'phone': '+91 98241 88921',
            'source': 'Sahara Darwaja Wholesale',
            'ad_status': 'Catalog Ad Running',
            'priority': 'HIGH',
            'visiting_charge': 500,
            'remote_fee': 250,
            'zone': 'Zone 1 (Sahara Darwaja - 5 km)'
        },
        {
            'name': 'Vesu Prime Realty & Infrastructure',
            'sector': 'Real Estate & Builders',
            'market': 'VIP Road, Vesu, Surat',
            'phone': '+91 99250 67114',
            'source': 'Vesu Builder Group',
            'ad_status': 'High Lead Ads Volume',
            'priority': 'VERY HIGH',
            'visiting_charge': 750,
            'remote_fee': 250,
            'zone': 'Zone 2 (Vesu VIP Road - 12 km)'
        },
        {
            'name': 'Diamond City Lab-Grown Jewel Hub',
            'sector': 'CVD & Lab-Grown Diamonds',
            'market': 'Varachha Main Road, Surat',
            'phone': '+91 98980 12345',
            'source': 'Varachha CVD Hub',
            'ad_status': 'Active Meta Campaign',
            'priority': 'VERY HIGH',
            'visiting_charge': 750,
            'remote_fee': 250,
            'zone': 'Zone 2 (Varachha - 10 km)'
        },
        {
            'name': 'Mahalaxmi Fabrics & Digital Prints',
            'sector': 'Textiles & Sarees',
            'market': 'Radharaman Textile Market, Surat',
            'phone': '+91 98250 99881',
            'source': 'Radharaman Market',
            'ad_status': 'Running Reels Ads',
            'priority': 'HIGH',
            'visiting_charge': 500,
            'remote_fee': 250,
            'zone': 'Zone 1 (Radharaman Market - 4 km)'
        },
        {
            'name': 'Avadh Luxury Living Projects',
            'sector': 'Real Estate & Builders',
            'market': 'Pal - Adajan, Surat',
            'phone': '+91 99099 87654',
            'source': 'Adajan Real Estate Syndicate',
            'ad_status': 'Lead Generation Campaign',
            'priority': 'VERY HIGH',
            'visiting_charge': 500,
            'remote_fee': 250,
            'zone': 'Zone 1 (Adajan - 6 km)'
        }
    ]

def run_prospecting_sweep():
    print('=' * 80)
    print('  ALGORISE AI — SURAT B2B PROSPECTING & HYBRID OUTBOUND ENGINE')
    print('  Pricing: ₹250 Remote Support | ₹500 Base + Distance Personal Visit')
    print(f'  Direct Line & Care: {FOUNDER_PHONE_DISPLAY} | UPI: {FOUNDER_UPI_VPA}')
    print('=' * 80)
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    local_leads_dir = os.path.join(base_dir, 'leads')
    os.makedirs(local_leads_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    csv_file = os.path.join(local_leads_dir, f'surat_hybrid_targets_{timestamp}.csv')
    
    leads = get_curated_surat_seed_leads()
    print(f'\n[+] Loaded {len(leads)} High-Ticket Verified Surat Commercial Targets')
    
    for i, lead in enumerate(leads, 1):
        lead['whatsapp_pitch'] = generate_personalized_pitch(
            biz_name=lead['name'],
            sector=lead['sector'],
            phone=lead['phone'],
            visiting_charge=lead['visiting_charge']
        )
        clean_digits = ''.join(filter(str.isdigit, lead['phone']))
        lead['direct_whatsapp_link'] = f"https://wa.me/{clean_digits}?text={urllib.parse.quote(lead['whatsapp_pitch'])}"
        
        # Pre-compute UPI visit deposit link
        upi_info = generate_upi_payment_link(lead['visiting_charge'], lead['name'], "Visit_Deposit")
        lead['upi_intent_url'] = upi_info['intent_url']
        lead['upi_qr_image'] = upi_info['qr_image']
        
        print(f"\n--- [{i}/{len(leads)}] {lead['name']} ({lead['sector']}) ---")
        print(f"  📍 Location:       {lead['market']} [{lead['zone']}]")
        print(f"  📱 Client Phone:   {lead['phone']}")
        print(f"  ⚡ Remote AnyDesk: ₹{lead['remote_fee']} Flat")
        print(f"  🚗 Visiting Fee:   ₹{lead['visiting_charge']} (UPI: {FOUNDER_UPI_VPA})")
        print(f"  🔗 1-Click Pitch:  {lead['direct_whatsapp_link'][:65]}...")
        
    fieldnames = [
        'name', 'sector', 'market', 'zone', 'phone', 'remote_fee', 'visiting_charge', 'source',
        'ad_status', 'priority', 'direct_whatsapp_link', 'upi_intent_url', 'upi_qr_image', 'whatsapp_pitch'
    ]
    with open(csv_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(leads)
        
    print('\n' + '=' * 80)
    print(f'✅ Saved all targets with calibrated pricing to:')
    print(f'   {csv_file}')
    print(f'📞 Your Personal Visit & Care Line: {FOUNDER_PHONE_DISPLAY}')
    print(f'⚡ Direct Client-to-You WhatsApp:  {FOUNDER_WHATSAPP_LINK}')
    print('=' * 80)

if __name__ == '__main__':
    run_prospecting_sweep()
