import re

with open('index.html', 'rb') as f:
    raw = f.read().decode('utf-8')

# 1. Hero CTA
raw = re.sub(
    r"onclick=\"openBookingModal\('Surat LeadShield Pro',\s*2999,\s*0\)\" class=\"sf-btn-primary cursor-pointer border-0\">\s*Start 7-Day Free Trial",
    "onclick=\"openBookingModal('Surat LeadShield Pro', 29999, 5999)\" class=\"sf-btn-primary cursor-pointer border-0\">\n          Deploy LeadShield Pro",
    raw
)

# 2. Card 5 zero ad markup text
raw = raw.replace(
    "flat software rate of ₹2,999/mo.",
    "flat commercial rate of ₹29,999/mo."
)

# 3. Step 3 CTA
raw = re.sub(
    r"onclick=\"openBookingModal\('Surat LeadShield Pro',\s*2999,\s*0\)\" class=\"sf-btn-primary cursor-pointer border-0\">\s*<i class=\"fa-solid fa-shield-halved text-slate-950 mr-1.5\"></i>\s*Start 7-Day Free Trial \(10-Min Setup\)",
    "onclick=\"openBookingModal('Surat LeadShield Pro', 29999, 5999)\" class=\"sf-btn-primary cursor-pointer border-0\">\n        <i class=\"fa-solid fa-shield-halved text-slate-950 mr-1.5\"></i> Deploy LeadShield Pro (Direct AnyDesk Setup)",
    raw
)

# 4. Pricing card
old_pricing_pattern = r'<span class="text-5xl font-black text-white font-mono">₹2,999</span>\s*<span class="text-sm text-slate-400">\s*/ month</span>\s*</div>\s*<p class="text-xs text-slate-300">[^<]+</p>\s*</div>\s*<div class="p-4 rounded-xl bg-slate-950/80 border border-slate-800 mb-6 text-xs text-slate-300 space-y-2">[\s\S]*?</div>\s*<p class="text-\[11px\] text-slate-400 leading-relaxed">[\s\S]*?</p>\s*</div>'

new_pricing_block = '''<span class="text-5xl font-black text-white font-mono">₹29,999</span>
            <span class="text-sm text-slate-400"> / month</span>
          </div>
          <p class="text-xs text-slate-300">Full commercial enterprise license. Direct engineering setup via AnyDesk with ₹5,999 booking advance.</p>
        </div>

        <div class="p-4 rounded-xl bg-slate-950/80 border border-slate-800 mb-6 text-xs text-slate-300 space-y-2">
          <div class="flex items-center gap-2 font-bold text-emerald-400">
            <i class="fa-solid fa-bolt"></i> 10-Minute Direct Engineering Handshake
          </div>
          <p class="text-[11px] text-slate-400 leading-relaxed">
            Our engineers connect your Meta Facebook &amp; Instagram Pages via AnyDesk within 10 minutes. Zero free trials — immediate sub-0.05s broker interception and verified WhatsApp lead delivery.
          </p>
        </div>'''

raw = re.sub(old_pricing_pattern, new_pricing_block, raw)

# 5. Pricing CTA button
raw = re.sub(
    r"onclick=\"openBookingModal\('Surat LeadShield Pro',\s*2999,\s*0\)\" class=\"w-full py-4 px-6 rounded-2xl bg-gradient-to-r from-brand-cyan to-brand-violet text-brand-void font-black text-sm transition-all shadow-xl hover:shadow-brand-cyan/50 hover:scale-\[1\.02\] cursor-pointer\">\s*Claim 7-Day Free Trial \(10-Min Setup\) →",
    "onclick=\"openBookingModal('Surat LeadShield Pro', 29999, 5999)\" class=\"w-full py-4 px-6 rounded-2xl bg-gradient-to-r from-brand-cyan to-brand-violet text-brand-void font-black text-sm transition-all shadow-xl hover:shadow-brand-cyan/50 hover:scale-[1.02] cursor-pointer\">\n          Deploy LeadShield Pro (₹5,999 Advance) →",
    raw
)

# 6. Pricing guarantee footnote
raw = raw.replace(
    '<i class="fa-solid fa-shield text-emerald-400 mr-1"></i> No credit card required. 100% money-back satisfaction guarantee.',
    '<i class="fa-solid fa-shield text-emerald-400 mr-1"></i> 100% Commercial Protection Guarantee. Dedicated Engineer Assigned.'
)

# 7. Modal submit text
raw = raw.replace(
    '<span id="bookingSubmitText">Start 7-Day Free Concierge Trial →</span>',
    '<span id="bookingSubmitText">Confirm Booking with ₹5,999 Advance →</span>'
)

# Any other remaining 2999, 0
raw = raw.replace("openBookingModal('Surat LeadShield Pro', 2999, 0)", "openBookingModal('Surat LeadShield Pro', 29999, 5999)")

with open('index.html', 'wb') as f:
    f.write(raw.encode('utf-8'))

print('DONE_REPOSITION')
