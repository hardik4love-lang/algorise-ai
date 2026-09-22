#!/usr/bin/env python3
import urllib.request
import urllib.parse
import json
import time

BOT_TOKEN = "8961434797:AAHaPPybfby3G-Mj7WeJEXsAtKPna-uSPnw"
CHAT_ID = "8737013099"
URL = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

def send_telegram(text):
    data = urllib.parse.urlencode({
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "HTML"
    }).encode("utf-8")
    req = urllib.request.Request(URL, data=data)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"Error with HTML mode: {e}, falling back to plain text...")
        data = urllib.parse.urlencode({
            "chat_id": CHAT_ID,
            "text": text
        }).encode("utf-8")
        req = urllib.request.Request(URL, data=data)
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))

part1 = """🚀 <b>ALGORISE AI — EXECUTIVE PRESENTATION TO MANAGEMENT</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
<b>PRODUCT: Autonomous AI Facebook Marketing & Sales Agent</b>
<b>Primary Target Market:</b> Surat Business Ecosystem (Textile Mills, Diamond Merchants, Real Estate Developers, Industrial Manufacturers, D2C Brands)

<b>1. THE HUGE PAIN POINT IN SURAT:</b>
Surat businesses spend ₹20,000 to ₹1,00,000/month on Meta/Facebook/Instagram ads.
They receive 50 to 200+ comments daily:
👉 <i>"Price?", "Catalog?", "Wholesale rate?", "10 pieces available?", "Shop location?"</i>

<b>The Disaster:</b>
Comments sit unanswered for 6 to 18 hours because owners and staff are occupied on the factory or shop floor. By the time someone replies, the buyer has already bought from a competing manufacturer.
<b>Result:</b> An average Surat business leaks <b>₹50,000 to ₹3,00,000 in lost orders every month!</b>

<b>2. WHAT THE ALGORISE FACEBOOK AI AGENT DOES:</b>
⚡ <b>0.05-Sec Comment-to-DM Response:</b> Instantly replies publicly ("Sent to your DM! 📩") and immediately fires a private Messenger DM with catalog & pricing.
🗣️ <b>Fluent Gujarati, Hindi & English:</b> Speaks native regional business language naturally without sounding robotic.
🎯 <b>BANT Lead Qualification:</b> Asks quantity, location, requirements, and extracts their verified WhatsApp number.
📱 <b>Telegram 2-Way Command Desk:</b> When a lead is hot, YOUR Telegram pings with a HOT LEAD alert card. You can reply directly in Telegram, and the customer receives it on Facebook!"""

part2 = """💼 <b>PRICING & SUBSCRIPTION TIERS FOR SURAT BUSINESSES:</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Ready to subscribe by every business in Surat:

1️⃣ <b>Starter Merchant — ₹2,499 / Month</b>
• 1 Facebook Business Page
• Up to 1,000 automated comment & DM conversations/mo
• Instant Telegram Hot Lead notifications
• <i>Best for:</i> Retail boutiques, local clinics, cafes, salons

2️⃣ <b>Surat Business Pro — ₹5,999 / Month (MOST POPULAR)</b>
• Unlimited Facebook + Instagram Comments & Messenger DMs
• Native Gujarati + Hindi multi-turn negotiation AI
• Full BANT Lead Qualification (Volume, Budget, WhatsApp)
• 2-Way Telegram Message Proxy (Reply from your mobile)
• <i>Best for:</i> Textile manufacturers (Ring Road), Real Estate builders (Vesu), Cocopeat & Industrial mills

3️⃣ <b>Surat Enterprise / Agency — ₹12,999 / Month</b>
• Up to 5 Brand Pages & Multi-User Desk
• Custom Brand Voice & Catalog RAG
• Priority GPU processing & 24/7 dedicated account manager

🔥 <b>SURAT FOUNDER LIFETIME DEAL (FIRST 25 BUSINESSES):</b>
• <b>₹9,999 ONE-TIME (LIFETIME ACCESS)</b>
• Generates <b>₹2,50,000 in immediate upfront cash!</b>"""

part3 = """🎯 <b>HOW TO START SELLING IN SURAT TODAY (3 STEPS):</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>Step 1: The "Unanswered Comments Audit" Hook</b>
Find 10 Surat textile / saree / kurti / real estate pages on Facebook & Instagram.
Take a screenshot showing 15 comments from last week with NO response.
Send WhatsApp / Voice Note in Gujarati:
👉 <i>"કિરીટભાઈ, તમારી સાડી કલેક્શનની લેટેસ્ટ પોસ્ટ જોઈ. ૧૫ થી વધુ કસ્ટમર્સ ભાવ પૂછી રહ્યા છે પણ કોઈ રિપ્લાય નથી મળ્યો. આ આસાનીથી ₹૮૦,૦૦૦ નું નુકસાન છે. અમારું AI એજન્ટ ૦.૦૫ સેકન્ડમાં ગુજરાતીમાં ભાવ અને કેટેલોગ મોકલી આપે છે. તમારી ફેસબુક પેજ પર ૪૮ કલાકની ફ્રી ટ્રાયલ સેટ કરી આપું?"</i>

<b>Step 2: 48-Hour Zero-Risk Live Trial</b>
Connect their Facebook page in 3 minutes via Meta OAuth. Let them watch verified buyer phone numbers and hot leads arrive directly in their Telegram. When they see 10 hot phone numbers, they will NEVER cancel!

<b>Step 3: Close at ₹5,999/mo or ₹9,999 Lifetime</b>
Just 20 Surat business clients = <b>₹1,20,000/month recurring income!</b>

🌐 <b>Live Platform:</b> https://algorise-ai.surge.sh"""

def main():
    print("Dispatching presentation to Telegram...")
    res1 = send_telegram(part1)
    print("Part 1 dispatched:", res1.get("ok"))
    time.sleep(1)
    res2 = send_telegram(part2)
    print("Part 2 dispatched:", res2.get("ok"))
    time.sleep(1)
    res3 = send_telegram(part3)
    print("Part 3 dispatched:", res3.get("ok"))
    print("\nPresentation successfully delivered to Telegram!")

if __name__ == "__main__":
    main()
