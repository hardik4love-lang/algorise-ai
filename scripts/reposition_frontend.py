"""Reposition index.html to focus 100% on Product #1: Algorise LeadShield with CRLF preservation."""
import re
from pathlib import Path

ROOT = Path(r"C:\Users\om\.gemini\antigravity\scratch\algorise-ai")
index_file = ROOT / "index.html"
raw = index_file.read_bytes().decode("utf-8")

# 1. Update Navigation
old_nav = re.search(r'<nav class="sf-nav" aria-label="Primary">.*?</nav>', raw, re.DOTALL)
new_nav = '''<nav class="sf-nav" aria-label="Primary">
      <a href="#simulation">Live Shield Demo</a>
      <a href="#how-it-works">How It Works</a>
      <a href="#roi-simulator">ROI Calculator</a>
      <a href="#pricing">Pricing</a>
      <a href="dashboard.html" class="text-brand-cyan hover:underline font-bold">Live Console</a>
    </nav>'''.replace("\n", "\r\n")

if old_nav:
    raw = raw.replace(old_nav.group(0), new_nav)
    print("Nav updated")

# 2. Update Hero Section
old_hero = re.search(r'<section class="sf-hero" id="top">.*?</section>', raw, re.DOTALL)
new_hero = '''<section class="sf-hero" id="top">
    <div class="sf-hero-inner">
      <div class="sf-pill">
        <span class="sf-dot"></span> SURAT TEXTILE &amp; SOCIAL COMMERCE DEFENSE · v3.0
      </div>

      <h1 class="sf-h1">
        Stop Competitor Brokers From <span class="sf-grad">Stealing Your Ad Leads</span> in 0.018s.
      </h1>

      <p class="sf-lead">
        When wholesale buyers comment on your Facebook &amp; Instagram ads, rival brokers poach their phone numbers in minutes. Algorise auto-hides comments in sub-second speed, sends instant 4K catalog Messenger DMs, and routes orders straight to your WhatsApp Business app.
      </p>

      <div class="sf-hero-actions">
        <button type="button" onclick="openBookingModal('Surat LeadShield Pro', 2999, 0)" class="sf-btn-primary cursor-pointer border-0">
          Start 7-Day Free Trial <i class="fa-solid fa-chevron-right text-xs"></i>
        </button>
        <a class="sf-btn-ghost" href="#simulation">
          <i class="fa-solid fa-shield-halved text-brand-cyan text-sm"></i> Test Live Shield Simulator
        </a>
      </div>

      <div class="sf-hero-stats">
        <div>
          <b>0.018s</b>
          <span>Auto-Hide SLA</span>
        </div>
        <div>
          <b>100%</b>
          <span>WhatsApp Handoff</span>
        </div>
        <div>
          <b>₹0</b>
          <span>Meta Markup</span>
        </div>
        <div>
          <b>10 Min</b>
          <span>AnyDesk Setup</span>
        </div>
      </div>
    </div>

    <!-- Hero Visual: Orbiting Rings & Core -->
    <div class="sf-hero-visual" aria-hidden="true">
      <div class="sf-ring sf-ring-1"></div>
      <div class="sf-ring sf-ring-2"></div>
      <div class="sf-ring sf-ring-3"></div>

      <div class="sf-core">
        <i class="fa-solid fa-shield-halved text-4xl text-brand-cyan"></i>
      </div>

      <div class="sf-chip sf-chip-a">
        <i class="fa-solid fa-bolt text-brand-cyan"></i> 0.018s Meta Shield
      </div>
      <div class="sf-chip sf-chip-b">
        <i class="fa-solid fa-user-shield text-brand-emerald"></i> Broker Phone Masking
      </div>
      <div class="sf-chip sf-chip-c">
        <i class="fa-brands fa-whatsapp text-brand-emerald"></i> Direct WhatsApp Order
      </div>
    </div>
  </section>'''.replace("\n", "\r\n")

if old_hero:
    raw = raw.replace(old_hero.group(0), new_hero)
    print("Hero updated")

# 3. Update Platform / Bento Cards
old_cards = re.search(r'<div class="sf-feature-grid">.*?</div>\s*</section>', raw, re.DOTALL)
new_cards = '''<div class="sf-feature-grid">
      <!-- Card 1 -->
      <article class="sf-card">
        <div class="sf-card-icon">
          <i class="fa-solid fa-shield-cat text-xl"></i>
        </div>
        <h3>0.018s Meta Ad Shield</h3>
        <p>When buyers drop phone numbers or request rates on your Facebook or Instagram ad posts, competitor brokers scrape them in seconds. Algorise intercepts and auto-hides them in sub-0.05s.</p>
        <a class="sf-card-link" href="#simulation">
          See live test <i class="fa-solid fa-arrow-right text-xs"></i>
        </a>
      </article>

      <!-- Card 2 -->
      <article class="sf-card">
        <div class="sf-card-icon">
          <i class="fa-solid fa-language text-xl"></i>
        </div>
        <h3>Surati Gujarati &amp; Hindi NLP</h3>
        <p>Trained on regional trade dialects. Effortlessly parses "Bhai 500 piece no bhav bolo", "ex-factory rate", "sample courier moko", and diamond/textile industry terminology.</p>
        <a class="sf-card-link" href="#simulation">
          Test dialect demo <i class="fa-solid fa-arrow-right text-xs"></i>
        </a>
      </article>

      <!-- Card 3 -->
      <article class="sf-card">
        <div class="sf-card-icon">
          <i class="fa-brands fa-whatsapp text-xl"></i>
        </div>
        <h3>Direct WhatsApp Business Handoff</h3>
        <p>Buyer is guided straight to your shop's existing WhatsApp Business app with a 1-click order link carrying tracking code (#AG...). Zero extra API setup or per-message fees.</p>
        <a class="sf-card-link" href="#how-it-works">
          Handoff workflow <i class="fa-solid fa-arrow-right text-xs"></i>
        </a>
      </article>

      <!-- Card 4 -->
      <article class="sf-card">
        <div class="sf-card-icon">
          <i class="fa-solid fa-paper-plane text-xl"></i>
        </div>
        <h3>Instant Private Messenger DM</h3>
        <p>Within seconds of a comment, buyer receives a private Messenger DM with your verified 4K digital catalog, ex-factory rates, and ready-to-ship sizes (S to 6XL).</p>
        <a class="sf-card-link" href="#simulation">
          Inspect catalog DM <i class="fa-solid fa-arrow-right text-xs"></i>
        </a>
      </article>

      <!-- Card 5 -->
      <article class="sf-card">
        <div class="sf-card-icon">
          <i class="fa-solid fa-hand-holding-dollar text-xl"></i>
        </div>
        <h3>Zero Meta Ad Markup</h3>
        <p>Pure software infrastructure. We charge zero percentage on your Meta ad spend and zero per-conversation markup. You pay one flat software rate of ₹2,999/mo.</p>
        <a class="sf-card-link" href="#pricing">
          View transparent pricing <i class="fa-solid fa-arrow-right text-xs"></i>
        </a>
      </article>

      <!-- Card 6 -->
      <article class="sf-card">
        <div class="sf-card-icon">
          <i class="fa-solid fa-chart-line text-xl"></i>
        </div>
        <h3>Real-Time Revenue Analytics</h3>
        <p>Monitor pipeline value protected in INR, comment masking latency logs, qualified buyers captured, and ROAS enhancement metrics in your live unified console.</p>
        <a class="sf-card-link" href="dashboard.html">
          Open live console <i class="fa-solid fa-arrow-right text-xs"></i>
        </a>
      </article>
    </div>
  </section>'''.replace("\n", "\r\n")

if old_cards:
    raw = raw.replace(old_cards.group(0), new_cards)
    print("Platform cards updated")

# 4. Replace 100 Hero Bots section with "How It Works"
old_bots = re.search(r'<section class="sf-section" id="bots">.*?</section>', raw, re.DOTALL)
new_how_it_works = '''<section class="sf-section" id="how-it-works">
    <div class="sf-section-head">
      <span class="sf-eyebrow">03 — HOW LEADSHIELD WORKS</span>
      <h2>The Complete Closed-Loop Lead Recovery in 3 Steps.</h2>
      <p>Engineered specifically for Surat textile manufacturers, saree &amp; kurti wholesalers, and D2C brands advertising on Meta.</p>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
      <!-- Step 1 -->
      <div class="bg-slate-900/60 border border-slate-800 hover:border-brand-cyan/40 rounded-2xl p-6 backdrop-blur-md transition-all">
        <div class="w-12 h-12 rounded-xl bg-brand-cyan/15 border border-brand-cyan/30 text-brand-cyan flex items-center justify-center text-xl font-black mb-5">
          1
        </div>
        <h4 class="text-lg font-bold text-white mb-2">0.018s Broker-Shield</h4>
        <p class="text-xs text-slate-400 leading-relaxed mb-4">
          When a buyer leaves a comment with a phone number or buying intent ("PP?", "Bhav bolo"), Algorise automatically calls Meta Graph API to hide the comment in sub-second speed. Competitors and rival brokers see an empty post.
        </p>
        <div class="p-3 rounded-xl bg-slate-950 border border-slate-800/80 text-[11px] font-mono text-emerald-400">
          <i class="fa-solid fa-check-circle mr-1"></i> Phone Auto-Masked (< 0.05s)
        </div>
      </div>

      <!-- Step 2 -->
      <div class="bg-slate-900/60 border border-slate-800 hover:border-brand-violet/40 rounded-2xl p-6 backdrop-blur-md transition-all">
        <div class="w-12 h-12 rounded-xl bg-brand-violet/15 border border-brand-violet/30 text-brand-violet flex items-center justify-center text-xl font-black mb-5">
          2
        </div>
        <h4 class="text-lg font-bold text-white mb-2">Instant 4K Catalog DM</h4>
        <p class="text-xs text-slate-400 leading-relaxed mb-4">
          A private Messenger DM is automatically dispatched to the buyer within seconds, containing your official 4K product photos, ex-factory rates, and ready-to-ship sizes (S to 6XL) in their regional dialect.
        </p>
        <div class="p-3 rounded-xl bg-slate-950 border border-slate-800/80 text-[11px] font-mono text-cyan-400">
          <i class="fa-solid fa-check-circle mr-1"></i> 4K Catalog Sent in Gujarati/Hindi
        </div>
      </div>

      <!-- Step 3 -->
      <div class="bg-slate-900/60 border border-slate-800 hover:border-brand-emerald/40 rounded-2xl p-6 backdrop-blur-md transition-all">
        <div class="w-12 h-12 rounded-xl bg-brand-emerald/15 border border-brand-emerald/30 text-brand-emerald flex items-center justify-center text-xl font-black mb-5">
          3
        </div>
        <h4 class="text-lg font-bold text-white mb-2">WhatsApp Order Handoff</h4>
        <p class="text-xs text-slate-400 leading-relaxed mb-4">
          The DM contains a 1-click WhatsApp deep link with an embedded attribution code (#AG...). Tapping it opens your normal WhatsApp Business app on your phone with the buyer ready to confirm payment.
        </p>
        <div class="p-3 rounded-xl bg-slate-950 border border-slate-800/80 text-[11px] font-mono text-emerald-400">
          <i class="fa-solid fa-check-circle mr-1"></i> Chat Dings on Your WhatsApp App
        </div>
      </div>
    </div>

    <div class="text-center mt-10">
      <button type="button" onclick="openBookingModal('Surat LeadShield Pro', 2999, 0)" class="sf-btn-primary cursor-pointer border-0">
        <i class="fa-solid fa-shield-halved text-slate-950 mr-1.5"></i> Start 7-Day Free Trial (10-Min Setup)
      </button>
    </div>
  </section>'''.replace("\n", "\r\n")

if old_bots:
    raw = raw.replace(old_bots.group(0), new_how_it_works)
    print("How-It-Works section updated")

# 5. Update Pricing Section
old_pricing = re.search(r'<div class="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-6xl mx-auto">.*?</div>\s*</section>', raw, re.DOTALL)
new_pricing = '''<div class="max-w-xl mx-auto">
      <!-- Surat LeadShield Pro -->
      <div class="bg-gradient-to-b from-brand-cyan/15 via-slate-900/90 to-brand-violet/10 border-2 border-brand-cyan/60 rounded-3xl p-8 sm:p-10 backdrop-blur-xl shadow-2xl relative">
        <div class="absolute -top-3.5 left-1/2 -translate-x-1/2 bg-gradient-to-r from-brand-cyan to-brand-violet text-brand-void text-[10px] font-extrabold tracking-widest uppercase px-4 py-1.5 rounded-full shadow-lg">
          SURAT COMMERCE FOUNDER CHOICE
        </div>

        <div class="text-center mb-6">
          <span class="text-xs font-mono text-brand-cyan uppercase tracking-wider font-bold">SURAT LEADSHIELD PRO</span>
          <div class="my-4 flex items-baseline justify-center gap-2">
            <span class="text-5xl font-black text-white font-mono">₹2,999</span>
            <span class="text-sm text-slate-400"> / month</span>
          </div>
          <p class="text-xs text-slate-300">Billed quarterly (₹8,997). Includes 7-day free concierge setup via AnyDesk with zero advance payment.</p>
        </div>

        <div class="p-4 rounded-xl bg-slate-950/80 border border-slate-800 mb-6 text-xs text-slate-300 space-y-2">
          <div class="flex items-center gap-2 font-bold text-emerald-400">
            <i class="fa-solid fa-gift"></i> 7-Day Free Concierge AnyDesk Setup
          </div>
          <p class="text-[11px] text-slate-400 leading-relaxed">
            We connect your Meta Facebook Page on AnyDesk in 10 minutes. Test it live on your own ad posts. If it doesn't shield at least 50 leads in 7 days, you pay nothing.
          </p>
        </div>

        <ul class="space-y-3.5 text-xs text-slate-200 mb-8">
          <li class="flex items-center gap-2.5"><i class="fa-solid fa-check text-brand-cyan"></i> <strong>Unlimited Meta Facebook &amp; Instagram Page Protection</strong></li>
          <li class="flex items-center gap-2.5"><i class="fa-solid fa-check text-brand-cyan"></i> <strong>Sub-0.05s Auto-Hide Shield</strong> on all public ad comments</li>
          <li class="flex items-center gap-2.5"><i class="fa-solid fa-check text-brand-cyan"></i> <strong>Native Surati Gujarati &amp; Hindi Intent NLP</strong></li>
          <li class="flex items-center gap-2.5"><i class="fa-solid fa-check text-brand-cyan"></i> <strong>Instant Private Messenger DM</strong> with 4K Digital Catalog</li>
          <li class="flex items-center gap-2.5"><i class="fa-solid fa-check text-brand-cyan"></i> <strong>Direct WhatsApp Business App Handoff</strong> (Runs on your phone)</li>
          <li class="flex items-center gap-2.5"><i class="fa-solid fa-check text-brand-cyan"></i> <strong>Closed-Loop Attribution &amp; Lead Recovery Dashboard</strong></li>
          <li class="flex items-center gap-2.5"><i class="fa-solid fa-check text-brand-cyan"></i> <strong>Zero Per-Message Fees &amp; Zero Meta Ad Markup</strong></li>
        </ul>

        <button type="button" onclick="openBookingModal('Surat LeadShield Pro', 2999, 0)" class="w-full py-4 px-6 rounded-2xl bg-gradient-to-r from-brand-cyan to-brand-violet text-brand-void font-black text-sm transition-all shadow-xl hover:shadow-brand-cyan/50 hover:scale-[1.02] cursor-pointer">
          Claim 7-Day Free Trial (10-Min Setup) →
        </button>

        <p class="text-center text-[11px] text-slate-400 mt-4">
          <i class="fa-solid fa-shield text-emerald-400 mr-1"></i> No credit card required. 100% money-back satisfaction guarantee.
        </p>
      </div>
    </div>
  </section>'''.replace("\n", "\r\n")

if old_pricing:
    raw = raw.replace(old_pricing.group(0), new_pricing)
    print("Pricing section updated")

# 6. Update Booking Modal Copy
raw = raw.replace(
    "modalPlanAdvance.textContent = `₹${adv.toLocaleString()} to Book`;",
    "modalPlanAdvance.textContent = adv > 0 ? `₹${adv.toLocaleString()} to Book` : '7 Days Free Trial';"
)
raw = raw.replace(
    "Confirm Booking with ₹5,999 Advance",
    "Start 7-Day Free Concierge Trial →"
)
raw = raw.replace(
    "By submitting, your booking token is created and sent to our live Render API. Our engineering desk will connect via WhatsApp within 15 minutes to configure your Meta token.",
    "By submitting, our engineering desk will reach out via WhatsApp within 10 minutes to setup your Facebook Page on AnyDesk (Takes 10 minutes, zero technical knowledge required)."
)

index_file.write_bytes(raw.encode("utf-8"))
print("index.html rewrite with exact CRLF complete!")
