# Algorise AI — Strategic Roadmap

**Position:** B2B social-selling infrastructure for Indian commerce SMBs
**Basis:** Codebase audit of `D:\algorise-ai` (61 Python files, ~13,600 LOC, 77 commits / 17.4 days) plus published India pricing for the competitive set
**Status:** Phase 0 is mandatory and precedes all growth work

---

## 0. Why this roadmap starts with subtraction

The audit found that the product's marketing describes a system materially
wider than the one that runs. That is not a positioning weakness. Under
enterprise security review it is a disqualification, and it makes every
acquisition campaign a liability rather than an asset.

Three verified findings set the agenda:

**Fabricated telemetry in production.** `engine/scheduler.py:73` writes a
`FacebookAgentJob` on every 60-second tick claiming `comments_scanned: 31`
and "3-Page Auto-Update Active" — on the branch taken when no Meta token is
configured. That is ~1,440 rows/day of synthetic activity displayed to clients
as evidence of work. At one paying client this is a billing-integrity issue;
at ten it is a pattern.

**Leaked Telegram bot token.** `REDACTED_ROTATE_VIA_BOTFATHER`
appears 17 times across `dashboard.html`, `dist/dashboard.html`,
`temp_script3.js`, and `engine/telegram_service.py`. It is extractable by any
visitor and permits arbitrary messaging as this bot.

**Regulated claims the code cannot support.** `engine/hero_algorithms.py`
returns literal `"HIPAA-VERIFIED-SHA256-OK"` (line 488) and
`"ZERO_INTERACTIONS_DETECTED"` (line 491) without reading any input;
`"DELAWARE_GENERAL_CORPORATION_LAW"` (line 526) is hardcoded;
`"vrp_algorithm": "Dijkstra_Clark_Wright_Savings"` (line 538) names an
algorithm that does not exist in the codebase; and the education solver
returns `flesch_kincaid = round(11.4, 1)` — a constant presented as a
computed readability score.

Also verified: the benchmark's headline "100% pass rate / 100% safety block
rate" is a string literal (`engine/tuning_engine.py:84`), never derived from
the `safety_verified` boolean two lines above it. `mcp_adapter.py` is
imported by nothing, despite documentation claiming MCP compliance for all
100 tools.

**Consequence.** Healthcare, legal, finance, and clinical positioning must be
withdrawn entirely, not softened. Selling a "HIPAA-verified" product that is
an arithmetic lookup table to a hospital is a liability that survives the
revenue several times over.

---

## Phase 0 — De-risk and disclose (Week 1–2)

Nothing else starts until this is done. It is roughly 3–5 days of work.

| # | Action | Why it is first |
|---|---|---|
| 0.1 | **Rotate the Telegram token** via BotFather, purge it from git history, move all references to env-only | Live compromise. Attacker can message as you today |
| 0.2 | Delete the `else` branch in `scheduler.py` that fabricates run results; make a missing token produce `status="not_configured"` and no row | Removes manufactured evidence |
| 0.3 | Purge `temp_script3.js` (2,109 lines, orphaned, contains the token) | Dead code is a leak surface |
| 0.4 | Strip every compliance literal; make the affected bots return `unsupported` rather than a false attestation | Regulatory exposure |
| 0.5 | Replace `safety_gate_status: "VERIFIED_BLOCKED"` with the actual `safety_verified` boolean | The benchmark must be able to fail |
| 0.6 | Delete or archive `TOP_100_HERO_AI_PRODUCTS_DOSSIER.md` (983 lines) and `SECTOR_PROPRIETARY_BOTS_DIRECTORY.md` (60 bots) — they contradict the 100-bot registry and the code | A technical buyer reads these first |
| 0.7 | Reconcile to three domains, one canonical (`algorise.ai`), one sitemap | Six live domains; `sitemap.xml` points at surge.sh while `CNAME` claims otherwise |
| 0.8 | Rotate hardcoded secrets in `config.py` (`secret_key`, `admin_secret`, `fb_app_secret`, two API keys); fail startup if defaults remain in production | `main.py:52-59` auto-returns the default key outside production |
| 0.9 | Write to Shruhi Collections disclosing the telemetry issue and the token exposure | Contractual integrity before it is discovered |

**Definition of done:** no secret in git; no code path can emit a fact it did
not measure; no product page claims a regulated certification.

---

## 1. Product Differentiation

### 1.1 Abandon breadth as a strategy

The 100-bot catalogue is not a moat. Each solver is closed-form arithmetic on
caller-supplied scalars with hardcoded defaults — the FAO-56 ETo and Arrhenius
Q10 formulas are correct, but they are textbook formulas, not proprietary
technology. A competitor reproduces them in an afternoon. Worse, breadth
across regulated verticals creates liability that concentrates in exactly the
domains where the code is thinnest.

### 1.2 The defensible wedge

The genuine, non-reproducible asset is **operational context for Indian
commerce SMBs on Meta**: a working comment→DM threading integration with
correct `recipient.comment_id` payloads, WhatsApp Cloud API dispatch,
Gujarati/Hindi response templating, and — critically — the sector knowledge
to know that a Surat CVD diamond inquiry and a textile wholesale comment need
structurally different replies. That last part is the moat, and it compounds
with every real conversation handled.

### 1.3 Build the three defensible capabilities

**a) Outcome attribution, not activity counting.** Every comment handled,
reply sent, and DM opened should be attributable to a pipeline outcome. This
is the single highest-value feature you can build, because it converts an
activity dashboard into a revenue dashboard. It requires: UTM-tagged deep
links, a WhatsApp Cloud API webhook receiver (you have the dispatcher, not the
inbound path), and a join from `outreach_messages` to `leads` to closed
business. It is also the only credible answer to "what did I get for ₹29,999."

**b) Meta-native comment deflection with reply quality measured.** The
deflection already works. What is missing is measurement of whether replies
are any good. Build a labelled set of real comment/reply pairs with merchant
ratings and report reply acceptance rate. This becomes a benchmark competitors
cannot fabricate — because it comes from your customers, not your code.

**c) Pass-through Meta billing at cost.** See §1.5 — this is a pricing moat
you can implement in a week.

### 1.4 Delete rather than diminish

Retire the 100-bot registry, the tuning benchmark as currently constructed,
the GraphRAG stub (a 95-line `Dict[str, Set[str]]` with two seed entities),
and the five legacy bot classes used only by the unused `mcp_adapter`. Replace
with a single pipeline: comment → classify → reply or escalate → DM →
attribute → report. Fewer components, all real.

### 1.5 Pricing reposition

Current: **₹29,999/mo** (`subscription_routes.py:32-51`), which sits above
WATI Business (₹16,999/mo) before conversation charges.

Published India pricing, verified August 2026:

| Competitor | India list | Meta conversation handling |
|---|---|---|
| Interakt / AiSensy | ₹999/mo | Pass-through |
| ManyChat | ₹2,405–₹12,035/mo (contact-tiered) | Pass-through |
| WATI | ₹2,499 / ₹5,999 / ₹16,999 per month | **Rate card, ~15–20% above Meta** |
| **Algorise** | ₹29,999/mo | Not currently separated |

Meta's India rates: marketing ₹0.76–0.86 per 24-hour conversation, utility
₹0.115–0.152. WATI's documented practices — 15–20% conversation markup,
₹1,299/user/mo extra seats, ₹4.99/mo Shopify add-on — are exactly what SMB
complain about, and migrating teams report them explicitly.

**Recommendation.** Keep the headline at ₹24,999 and publish a transparent
cost model:

- Platform fee, stated
- Meta conversations billed **at Meta's card, no markup** — a claim WATI
  cannot match and can be proven with a sample invoice
- No per-seat charge
- A measurable attribution report, or a refund tied to it

This reframes you from "expensive" to "the only one that shows you the
pipeline and doesn't tax you on top of Meta." That is a defensible position
against WATI. It is not defensible as "100 bots."

---

## 2. User Acquisition

### 2.1 Constraints that shape every channel

- One paying client, one sector, one city. There is no traction to extrapolate from.
- The market is relationship-driven. Surat merchant networks are dense and referral-driven; this is an advantage over ManyChat's self-serve funnel.
- CAC cannot be responsibly forecast yet. It must be measured over the first 10 clients before any channel gets budget.

### 2.2 The loop that actually fits this product

**Attribution is the loop.** When Algorise can show a merchant exactly which
comments became conversations and which conversations became orders, the
merchant shows that dashboard to a peer. That peer is your next customer, at
near-zero acquisition cost, in a market where everyone else is selling
activity metrics.

This is why §1.3(a) precedes acquisition work. Without attribution you have
no loop, only a pitch.

### 2.3 Concrete channels

**Sector association partnerships (highest expected yield).** Surat textile
and diamond associations, wholesale markets, and trade federations have
existing member directories. A member-benefit rate plus a short enablement
session converts a warm list. This is how the first 5–10 clients should be
acquired — not by paid ads.

**Shruhi as a public case study.** With informed consent, publish the real
attribution: comments handled, conversations opened, enquiries that reached
WhatsApp, and what the merchant says the value was. One credible Surat case
study outperforms any ad spend in this market.

**Comparison content that is honest.** `compare/wati-alternative.html` and
`manychat-alternative.html` already exist. Make them accurate rather than
aggressive — quote published prices, name the markup only if you can show
an invoice, and do not fabricate their SLAs. Aggressive comparison pages get
found and discredited by competitors.

**Content in Gujarati.** `field_pitch.html` exists; the document set is thin
and the search competition is near zero. B2B merchants in this segment are not
reading English vendor content.

### 2.4 What to measure

- Activated clients (Meta token connected, ≥50 real comments handled)
- Attribution coverage: share of clients with a working outcome join
- Referral-sourced clients per quarter
- **Payback period and churn** — with one client, churn is the single most
  informative number you do not have

Do not scale spend until activated-client count and churn are both known.

---

## 3. Technical Optimization

### 3.1 What exists and is worth keeping

Real, runnable, and worth building on:

- `facebook_agent.py` — correctly-formed Meta Graph calls with
  comment→DM threading, and it correctly refuses simulated/dev tokens
- `whatsapp_cloud_api.py`, `telegram_service.py` — real dispatchers
- `security.py` (536 lines) — keys, rate limiting, validation, headers, encryption
- `subscription_routes.py` (1,228 lines) — the actual product surface
- `models_sqlalchemy.py` (487 lines, 19 tables) — coherent data model
- Two live job scrapers (Remotive API, WeWorkRemotely RSS)
- SQLite/Postgres dialect fallback — genuine production hardening

### 3.2 Critical gaps, in priority order

**a) CI runs zero tests.** `.github/workflows/ci.yml` only `py_compile`s six
files and asserts 100 definitions import. Meanwhile `pyproject.toml` declares
ruff, black, isort, mypy strict, and `--cov-fail-under=80`. Enable what is
already configured. This is configuration, not engineering.

**b) Two test files contain no assertions.**
`test_advanced_features.py` and `test_realtor_sales_assistant.py` are
`main()` demos that print. 42 tests collect, 40 run, 3 of 5 files assert
nothing.

**c) A live `NameError`.** `main.py:297` references `hero_ids`, which is
never defined — every 404 from `POST /api/v1/bots/execute` returns 500.

**d) Three tables have no migration.** Alembic has one revision covering 16
of 19 tables; `subscriptions`, `leads`, and `facebook_agent_jobs` are created
by `Base.metadata.create_all` at runtime. That is why a production DB cannot
be reconstructed from migrations.

**e) `hero_bots` and `bot_executions` are provably empty.** `HeroBot` is
never instantiated outside tests; `/api/v1/bots/execute` logs to an audit
file, not the database. The flagship tables hold nothing.

**f) Twelve hardcoded secrets, two default API keys returned automatically
outside production**, and admin access via a single query parameter.

**g) Browser-side Meta Graph calls.** `dashboard.html` calls
`graph.facebook.com` directly from the browser including comment-hide and
reply POSTs — so any page visitor's token handling is in scope, and Meta's
domain restrictions apply.

### 3.3 Scaling requirements

For 10 → 100 clients the blocking constraint is the 60-second scheduler
writing a row per client per tick — 144k rows/day at 100 clients. Move
per-client work to a queue with backoff, make the job row a record of
*actual* API calls, and keep idempotency on the Meta side.

---

## 4. Market Expansion

### 4.1 Sequence, not scatter

Expansion should follow evidence, and the evidence base is one client. The
sequence:

1. **Surat textile and CVD diamond** — proven, dense, referral-driven
2. **Adjacent Gujarat clusters you already scraped** — the nursery and
   Surat cluster logic in `nursery_lead_scraper.py` shows the segmentation
   already exists in code
3. **Other Indian commerce hubs on the same Meta-first motion** — Jaipur
   textiles, Ludhiana apparel, Coimbatore, Tiruppur knitwear
4. Only then: verticals, regions

### 4.2 Do not enter these, ever

**Healthcare, clinical, legal, finance.** The code cannot support regulated
attestation, and the liability vastly exceeds the revenue. This is not a
"later" item.

**International.** The WhatsApp conversation pricing advantage that makes
India attractive does not exist in the US or EU, and you would compete against
WATI on its home turf with a worse product.

### 4.3 The data assets worth keeping

`lead_finder.py` and `nursery_lead_scraper.py` work — they scrape YouTube and
DuckDuckGo and extract contacts. But three defects need fixing before they
matter: the pitch is a fixed string with identical performance claims for every
lead; `nursery_lead_scraper.py:189` **fabricates placeholder leads when it
finds nothing** (with fake phone numbers); and `surat_business_scraper.py`
performs no scraping at all — it returns eight hardcoded rows with obviously
placeholder numbers.

That last one is worth stating plainly: a file named `surat_business_scraper.py`
that scrapes nothing will be found. Fix the fabrication first — a tool that
invents data when it finds none is worse than no tool.

---

## What the top 1% actually looks like here

Not 100 bots. Not 10 verticals. Top-1% in this category is a small number of
Indian commerce merchants for whom Algorise is provably the most profitable
comment-to-enquiry system they run — because it shows the pipeline and charges
nothing on top of Meta.

That is a defensible, narrow, high-margin position. It is also reachable from
where you are, which the current positioning is not.

---

## Success criteria

| Phase | Metric | Target |
|---|---|---|
| 0 | Secrets in git history | 0 |
| 0 | Code paths emitting unmeasured facts | 0 |
| 0 | Regulated verticals in marketing | 0 |
| 1 | Attribution coverage | ≥80% of replies joined to an outcome |
| 1 | Meta markup | 0, proven by sample invoice |
| 2 | Activated clients | 10 |
| 2 | Monthly churn | <10% |
| 2 | Referral-sourced clients | ≥30% by client 15 |
| 3 | Tests running in CI | 100% of collected |
| 3 | Coverage gate | ≥80%, actually enforced |
| 4 | Adjacent city launched | 1, on the same playbook |
