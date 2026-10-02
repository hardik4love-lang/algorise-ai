# Algorise AI — Strategic Analysis, Revision 2

**Supersedes:** `STRATEGIC_ROADMAP.md` (written before Phases 0–4)
**Date:** 2026-10-02, after commit `44229d7`
**Reason for revision:** the infrastructure thesis in Revision 1 has been executed. The *business* thesis has not changed, and the gap between them is now the whole story.

---

## What changed since Revision 1

Revision 1 recommended narrowing before scaling. That narrowing has **not** happened — the 100-bot catalogue, the ten verticals, and the regulated positioning are all still in the product. What has happened is that the *engineering* underneath is now sound enough to build on:

| Phase | Delivered |
|---|---|
| 0 | Leaked Telegram token purged from code and full git history; fabricated telemetry removed; regulated compliance literals stripped; benchmark made able to fail |
| 1 | Single API contract; `creator_studio.html` no longer points at a dead localhost port |
| 2 | `dist/` is generated, untracked, drift-checked in CI |
| 3 | One canonical domain; sitemap generated from real surfaces |
| 4 | Meta Graph proxied server-side; no Meta token in the browser; every operation now writes `bot_executions` |

Release gates: **7 of 8 passing**. The eighth needs Render access.

---

## 1. Product Differentiation

### 1.1 The moat has moved, and it is not where the marketing says

Revision 1 argued the defensible asset was operational context for Indian commerce SMBs on Meta. That assessment holds, and the moat is now **stronger in substance and weaker in presentation**.

Stronger: `engine/meta_proxy.py` means comment handling runs server-side with an audit trail. A competitor cannot replicate that in an afternoon — it required fixing an architecture where the browser held the credential and the backend saw nothing. `bot_executions` stops being an empty table.

Weaker: the product still *claims* a hundred bots across ten verticals, and still prices at ₹29,999/month against a competitor floor of ₹999. Nothing in the last five commits moved that.

### 1.2 The three capabilities that would constitute a real moat

**a) Attribution — the whole game**

`OutreachMessage`, `Lead`, and `BotExecution` tables all exist. Nothing joins them. The missing artefact is a chain: `comment → reply (bot_executions) → DM (outreach_messages) → lead (leads) → outcome`.

Until that chain exists, the product sells activity. `WATI`, `ManyChat`, `Interakt` and `AiSensy` all sell activity, and they have distribution, brand recognition, and engineering teams. ₹29,999/month against Interakt's ₹999 cannot be defended on features.

This is the single highest-value build available, and Phase 4 just made it possible by giving the backend visibility it never had.

**b) Reply quality as a measured benchmark**

The dashboard already scores and classifies comments (`classify_lead_intent`, `select_auto_reply`). What it lacks is an outcome label. Build a merchant-rated set of comment/reply pairs — even 200 of them — and report acceptance rate.

This is defensible because it comes from customers, not from code. It cannot be fabricated, which is precisely why it cannot be copied by a competitor with more engineers.

**c) Pass-through Meta billing at cost**

`WATI` marks up Meta conversation rates ~15–20%, sells extra seats at ₹1,299/user/month, and charges ₹4.99/month for the Shopify add-on. Migrating customers report all three as the reasons they left. Meta's India card is marketing ₹0.76–0.86 and utility ₹0.115–0.152 — published, verifiable, and passable through at cost.

This is a wedge that is provable with a sample invoice. It costs one accounting decision, not an engineering quarter.

### 1.3 What must be retired, not softened

`hero_algorithms.py` now returns `supported: false` for Healthcare, Finance and Legal. That is correct and it is not enough: the product catalogue, the pricing page, and the comparison pages still sell those verticals. A competitor or a prospect who reads the code and then reads the marketing finds a contradiction, and the contradiction is worse than the absence.

Retire the verticals from the site. Keep the guardrails.

### 1.4 Price reposition

Current: **₹29,999/month** — above `WATI` Business (₹16,999) before conversation charges.

Recommended: ₹24,999 headline, published cost model, Meta billed at Meta's card with no markup, no per-seat charge, refund tied to a measurable attribution report.

This reframes the pitch from "more features" to "the only one that shows you the pipeline and doesn't tax you on top of Meta." Both halves are provable.

---

## 2. User Acquisition

### 2.1 The blocker is not marketing, it is multi-tenancy

`dashboard.html` contains **34 hardcoded phone numbers** and **4 `wa.me` deep links**. Onboarding a second merchant requires editing HTML.

That is not a marketing problem to be solved later — it is a hard ceiling on revenue. Until client-specific data comes from the database, growth is capped at one client by construction.

### 2.2 The loop

**Attribution is the loop.** When Algorise can show a merchant precisely which comments became conversations and which became orders, the merchant shows that dashboard to a peer. That peer is the next client at near-zero acquisition cost, in a market where every competitor's pitch is a feature comparison.

Attribution precedes acquisition. Without it there is a pitch, not a loop.

### 2.3 Channels, in order of expected yield

**Sector associations and wholesale markets (Surat first).** Textile and CVD-diamond associations have member directories. A member rate plus an enablement session converts a warm list. This is how the next 5–10 clients should be acquired — not by paid ads.

**Shruhi as a public case study**, with informed consent and *real* attribution numbers. One credible Surat case study outperforms any ad spend in this segment.

**Comparison pages that are accurate.** `compare/manychat-alternative.html` and `compare/wati-alternative.html` exist. Make them defensible — quote published prices, name the markup only if you can produce an invoice, fabricate no competitor SLA. Aggressive comparison pages get discredited by the competitor, and that is a good outcome only if your own claims survive the same scrutiny.

**Gujarati content.** `field_pitch.html` exists; the content set is thin and search competition is near zero. The target segment does not read English vendor material.

### 2.4 Do not scale spend until these are known

Activated clients (token connected, ≥50 real comments handled) · churn · referral-sourced clients per quarter · payback period.

With one client, churn is the most informative number you do not have, and it is the one that determines whether acquisition spending is worth anything.

---

## 3. Technical Optimization

### 3.1 What is now solid

The unification phases removed the structural problems. Seven of eight gates pass, the release path is rehearsed (13/13 checks), and CI runs tests and the build. `dist/` cannot drift. The API contract cannot fork. Credentials cannot sit in client code without a gate failing.

**What remains is genuinely blocked, not unfinished:** deploy drift needs Render access, and the leaked Telegram token needs rotation via BotFather.

### 3.2 Engineering requirements for the next stage of growth

**Attribution schema and pipeline.** The tables exist; the join does not. Add a `comment_outcome` table keyed on `fb_comment_id` with `outcome`, `outcome_value_inr`, `recorded_at`. Populate it from a merchant-facing control in the dashboard. Every downstream KPI depends on this.

**Multi-tenant data removal.** Replace all 34 hardcoded phone numbers and 4 deep links with values from the `clients` and `leads` tables. Add a gate so the count cannot regress. This is the difference between one client and many.

**Queue-backed scheduler.** The scheduler writes per client per tick; at 100 clients that is ~144k rows/day. Move work to a queue with backoff and idempotency. Keep it a record of real API calls — the fabrication fix must survive this rewrite.

**Per-client feature flags.** Meta proxy behaviour changed the comment-handling write path. It needs to be togglable per client so a regression can be isolated without a rollback.

### 3.3 The architectural commitment worth making now

**Webhooks, not polling.** The inbound path does not exist. `whatsapp_cloud_api.py` can dispatch but cannot receive. Without an inbound webhook, every enquiry requires the browser to be open. Polling is what produced 1,440 fabricated rows per day in the first place — it produces activity even when nothing happened.

### 3.4 Risk register, updated

| Risk | Status |
|---|---|
| Unrotated token | **OPEN** — yours; two minutes in BotFather |
| Deploy ordering | Meta proxy and dashboard must ship together, or comment handling breaks for the live client |
| Telemetry regression | `not_configured` status will look like an outage to a client; announce it |
| Second-client ceiling | 34 hardcoded numbers; blocks all growth |
| Single-client risk | No churn data; no second reference customer |
| Render free-tier sleeps | Latency spike on first request after idle |

---

## 4. Market Expansion

### 4.1 Sequence follows evidence, and the evidence is one client

1. **Surat textile and CVD diamond** — proven, dense, referral-driven
2. **Adjacent Gujarat clusters** — the segmentation already exists in `nursery_lead_scraper.py`
3. **Other Indian commerce hubs on the same Meta-first motion** — Jaipur textiles, Ludhiana apparel, Coimbatore, Tiruppur knitwear
4. Only then: verticals, then regions

### 4.2 Do not enter

**Healthcare, clinical, legal, finance.** The code cannot support regulated attestation. The liability vastly exceeds the revenue. Not a "later" item.

**International.** The WhatsApp conversation pricing advantage that makes India attractive does not exist in the US or EU, and you would meet `WATI` on its home turf with a weaker product.

### 4.3 The data assets worth keeping

`lead_finder.py` and `nursery_lead_scraper.py` genuinely scrape. Three defects block them:

- The pitch is a fixed string with identical performance claims for every lead
- Fabricated placeholder leads — **fixed in Phase 0**, now reports failure honestly
- `surat_business_scraper.py` performs no scraping; it returns eight hardcoded rows with placeholder phone numbers, and its filename implies otherwise

That last one is a reputational liability in a market where your prospects are local merchants who can check. Fix the name and the behaviour.

---

## What top 1% means here

Not 100 bots. Not ten verticals. Top-1% in this category is a small number of Indian commerce merchants for whom Algorise is provably the most profitable comment-to-enquiry system they run — because it shows the pipeline and charges nothing on top of Meta.

That is narrow, defensible, high-margin, and reachable from where you are.

The gap between Revision 1 and now is not strategic. It is that five phases of engineering have made the honest strategy *executable*, while the dishonest one — hundred bots, ten verticals — is still what's on the website.

---

## Success criteria

| Metric | Target |
|---|---|
| Comment → enquiry attribution coverage | ≥80% |
| Reply acceptance rate (merchant-rated) | measured, then improved |
| Meta markup charged to clients | 0, provable by invoice |
| Hardcoded merchant values in client code | 0 |
| Activated clients | 10 |
| Monthly churn | <10% |
| Referral-sourced clients | ≥30% by client 15 |
| Release gates passing | 8/8 |
