import re

with open('index.html', 'rb') as f:
    raw = f.read().decode('utf-8')

old_pricing_block_pattern = r'<div class="max-w-xl mx-auto">\s*<!-- Surat LeadShield Pro -->[\s\S]*?</div>\s*</div>\s*</section>'

three_tier_pricing_html = '''<div class="grid grid-cols-1 lg:grid-cols-3 gap-6 max-w-6xl mx-auto items-stretch">
      <!-- Tier 1: Comment Shield (₹10,000/mo) -->
      <div class="bg-slate-900/80 border border-slate-800 rounded-3xl p-7 sm:p-8 backdrop-blur-xl flex flex-col justify-between hover:border-slate-700 transition-all shadow-xl">
        <div>
          <div class="text-center mb-6">
            <span class="text-xs font-mono text-slate-400 uppercase tracking-wider font-bold">TIER 1 · COMMENT SHIELD</span>
            <div class="my-4 flex items-baseline justify-center gap-1.5">
              <span class="text-4xl sm:text-5xl font-black text-white font-mono">₹10,000</span>
              <span class="text-xs text-slate-400"> / mo</span>
            </div>
            <p class="text-xs text-slate-300">Public ad comment defense &amp; auto-reply. Protect your paid ads from competitor brokers.</p>
          </div>

          <div class="p-3.5 rounded-xl bg-slate-950/80 border border-slate-800/80 mb-6 text-xs text-slate-300 space-y-1.5">
            <div class="flex items-center gap-2 font-bold text-brand-cyan">
              <i class="fa-solid fa-shield-halved"></i> Ad Comment Automation
            </div>
            <p class="text-[11px] text-slate-400 leading-relaxed">
              Auto-hides comments containing buyer phone numbers in 0.018s and posts instant public AI responses.
            </p>
          </div>

          <ul class="space-y-3 text-xs text-slate-300 mb-8">
            <li class="flex items-center gap-2.5"><i class="fa-solid fa-check text-brand-cyan"></i> <strong>Sub-0.018s Broker Shield</strong> (Auto-Hide Numbers)</li>
            <li class="flex items-center gap-2.5"><i class="fa-solid fa-check text-brand-cyan"></i> <strong>Instant Public AI Comment Reply</strong></li>
            <li class="flex items-center gap-2.5"><i class="fa-solid fa-check text-brand-cyan"></i> <strong>Surati Gujarati, Hindi &amp; English NLP</strong></li>
            <li class="flex items-center gap-2.5"><i class="fa-solid fa-check text-brand-cyan"></i> <strong>Competitor Blacklist &amp; Keyword Filter</strong></li>
            <li class="flex items-center gap-2.5"><i class="fa-solid fa-check text-brand-cyan"></i> 1 Connected Facebook Business Page</li>
            <li class="flex items-center gap-2.5"><i class="fa-solid fa-check text-brand-cyan"></i> Zero Per-Message Fees &amp; Zero Ad Markup</li>
          </ul>
        </div>

        <div>
          <button type="button" onclick="openBookingModal('Tier 1: Comment Shield', 10000, 2000)" class="w-full py-3.5 px-5 rounded-2xl bg-slate-800 hover:bg-slate-700 text-white font-bold text-xs transition-all border border-slate-700 cursor-pointer">
            Deploy Comment Shield (₹2,000 Advance) →
          </button>
          <p class="text-center text-[10px] text-slate-500 mt-3 font-mono">Setup via AnyDesk · ₹2,000 Advance</p>
        </div>
      </div>

      <!-- Tier 2: AI Messenger Sales Desk (₹20,000/mo) -->
      <div class="bg-slate-900/80 border border-slate-800 rounded-3xl p-7 sm:p-8 backdrop-blur-xl flex flex-col justify-between hover:border-slate-700 transition-all shadow-xl">
        <div>
          <div class="text-center mb-6">
            <span class="text-xs font-mono text-brand-cyan uppercase tracking-wider font-bold">TIER 2 · AI CHAT SALES DESK</span>
            <div class="my-4 flex items-baseline justify-center gap-1.5">
              <span class="text-4xl sm:text-5xl font-black text-white font-mono">₹20,000</span>
              <span class="text-xs text-slate-400"> / mo</span>
            </div>
            <p class="text-xs text-slate-300">24/7 AI chat desk on your Facebook Page. Turn organic &amp; ad inquiries into closed buyers.</p>
          </div>

          <div class="p-3.5 rounded-xl bg-slate-950/80 border border-slate-800/80 mb-6 text-xs text-slate-300 space-y-1.5">
            <div class="flex items-center gap-2 font-bold text-emerald-400">
              <i class="fa-solid fa-comments"></i> Full Facebook Page Chat Support
            </div>
            <p class="text-[11px] text-slate-400 leading-relaxed">
              Multi-turn conversational AI directly attached to your Facebook Page inbox for continuous 24/7 customer guidance.
            </p>
          </div>

          <ul class="space-y-3 text-xs text-slate-300 mb-8">
            <li class="flex items-center gap-2.5"><i class="fa-solid fa-check text-brand-cyan"></i> <strong>24/7 Facebook Messenger AI Sales Agent</strong></li>
            <li class="flex items-center gap-2.5"><i class="fa-solid fa-check text-brand-cyan"></i> <strong>Custom Boutique Catalog &amp; Rate Knowledge</strong></li>
            <li class="flex items-center gap-2.5"><i class="fa-solid fa-check text-brand-cyan"></i> <strong>Dialect Handling (Gujarati, Hindi, English)</strong></li>
            <li class="flex items-center gap-2.5"><i class="fa-solid fa-check text-brand-cyan"></i> <strong>BANT Lead Qualification</strong> (Volume, City, MOQs)</li>
            <li class="flex items-center gap-2.5"><i class="fa-solid fa-check text-brand-cyan"></i> Instant Hot Lead Telegram Alerts to Owner</li>
            <li class="flex items-center gap-2.5"><i class="fa-solid fa-check text-brand-cyan"></i> Up to 2 Connected Facebook Pages</li>
          </ul>
        </div>

        <div>
          <button type="button" onclick="openBookingModal('Tier 2: AI Messenger Chat Desk', 20000, 4000)" class="w-full py-3.5 px-5 rounded-2xl bg-brand-cyan/20 hover:bg-brand-cyan/30 text-brand-cyan font-bold text-xs transition-all border border-brand-cyan/40 cursor-pointer">
            Deploy Chat Support (₹4,000 Advance) →
          </button>
          <p class="text-center text-[10px] text-slate-500 mt-3 font-mono">Setup via AnyDesk · ₹4,000 Advance</p>
        </div>
      </div>

      <!-- Tier 3: Omnichannel LeadShield Pro (₹30,000/mo) -->
      <div class="bg-gradient-to-b from-brand-cyan/15 via-slate-900/90 to-brand-violet/10 border-2 border-brand-cyan/60 rounded-3xl p-7 sm:p-8 backdrop-blur-xl flex flex-col justify-between shadow-2xl relative">
        <div class="absolute -top-3.5 left-1/2 -translate-x-1/2 bg-gradient-to-r from-brand-cyan to-brand-violet text-brand-void text-[9px] font-extrabold tracking-widest uppercase px-3.5 py-1 rounded-full shadow-lg whitespace-nowrap">
          MOST POPULAR · COMPLETE OMNICHANNEL
        </div>

        <div>
          <div class="text-center mb-6">
            <span class="text-xs font-mono text-brand-cyan uppercase tracking-wider font-bold">TIER 3 · OMNICHANNEL PRO</span>
            <div class="my-4 flex items-baseline justify-center gap-1.5">
              <span class="text-4xl sm:text-5xl font-black text-white font-mono">₹30,000</span>
              <span class="text-xs text-slate-400"> / mo</span>
            </div>
            <p class="text-xs text-slate-300">Comments + Messenger + Instagram + WhatsApp Catalog. The ultimate end-to-end closer.</p>
          </div>

          <div class="p-3.5 rounded-xl bg-slate-950/80 border border-slate-800 mb-6 text-xs text-slate-300 space-y-1.5">
            <div class="flex items-center gap-2 font-bold text-emerald-400">
              <i class="fa-solid fa-crown"></i> Full LeadShield + Catalog Embedding
            </div>
            <p class="text-[11px] text-slate-400 leading-relaxed">
              When a buyer comments on Facebook or Instagram, we auto-hide their phone number, dispatch a 4K catalog via Messenger, and hand off to WhatsApp.
            </p>
          </div>

          <ul class="space-y-3 text-xs text-slate-200 mb-8">
            <li class="flex items-center gap-2.5"><i class="fa-solid fa-check text-brand-cyan"></i> <strong>Everything in Tier 1 &amp; Tier 2 Included</strong></li>
            <li class="flex items-center gap-2.5"><i class="fa-solid fa-check text-brand-cyan"></i> <strong>Private Messenger DM from Public Comment</strong></li>
            <li class="flex items-center gap-2.5"><i class="fa-solid fa-check text-brand-cyan"></i> <strong>Full Instagram Direct &amp; Ad Comment Defense</strong></li>
            <li class="flex items-center gap-2.5"><i class="fa-solid fa-check text-brand-cyan"></i> <strong>Native WhatsApp Business Catalog Embedding</strong></li>
            <li class="flex items-center gap-2.5"><i class="fa-solid fa-check text-brand-cyan"></i> <strong>Closed-Loop #AG Attribution Tracking</strong></li>
            <li class="flex items-center gap-2.5"><i class="fa-solid fa-check text-brand-cyan"></i> Up to 3 Connected Facebook &amp; Instagram Pages</li>
            <li class="flex items-center gap-2.5"><i class="fa-solid fa-check text-brand-cyan"></i> Dedicated Engineer &amp; 10-Min Concierge Handshake</li>
          </ul>
        </div>

        <div>
          <button type="button" onclick="openBookingModal('Tier 3: Omnichannel LeadShield Pro', 30000, 6000)" class="w-full py-3.5 px-5 rounded-2xl bg-gradient-to-r from-brand-cyan to-brand-violet text-brand-void font-black text-xs transition-all shadow-xl hover:shadow-brand-cyan/50 hover:scale-[1.02] cursor-pointer">
            Deploy Full Suite (₹6,000 Advance) →
          </button>
          <p class="text-center text-[10px] text-slate-400 mt-3 font-mono">
            <i class="fa-solid fa-shield text-emerald-400 mr-1"></i> 100% Commercial Protection Guarantee
          </p>
        </div>
      </div>
    </div>
  </section>'''

raw = re.sub(old_pricing_block_pattern, three_tier_pricing_html, raw)

with open('index.html', 'wb') as f:
    f.write(raw.encode('utf-8'))

print('DONE_THREE_TIERS')
