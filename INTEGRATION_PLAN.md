# Algorise AI — Technical & Operational Integration Plan

**Scope:** Unification of products first, agents second.
**Basis:** Measured surface inventory (`scripts/inventory_surfaces.py`, `scripts/inventory_api_calls.py`) against `D:\algorise-ai` at commit `0e21e0d`.
**Status:** Plan plus executable rollback tooling. Nothing in this plan has been deployed.

---

## 0. P0 blocker, ahead of every phase

**The leaked Telegram bot token has not been rotated.**

The credential was purged from the repository and its entire git history
(verified: 0 blobs across `master`, `main`, `gh-pages`,
`backup-freelancer-all`). That removed the exposure surface. It did **not**
invalidate the credential. Anyone who read the repository before
2026-10-02 still holds a working bot token.

Rotation is a two-minute action in @BotFather and cannot be automated.
**No phase below should be deployed before it is done**, because each phase
pushes a new build to a public origin, and a compromised credential plus a
fresh deploy is a worse combination than either alone.

Rotation procedure:

1. @BotFather → `/revoke` on the affected bot, or delete and recreate it
2. `TELEGRAM_BOT_TOKEN` in the deployment environment only
3. Confirm: `curl -s "https://api.telegram.org/bot<new>/getMe"` returns `ok: true`
4. Confirm the **old** token now returns 401

Then delete the local backup bundle, which still contains the old history:

```powershell
Remove-Item D:\algorise-ai\pre-rewrite-backup-*.bundle
```

---

## 1. Measured current state

These are counts from the inventory scripts, not estimates.

### 1.1 Product fragmentation

| Surface | `fetch()` calls | API base declared | Notes |
|---|---|---|---|
| `dashboard.html` | 35 | **two, competing** | `localhost:8000` + `onrender.com`, with a fallback chain |
| `creator_studio.html` | 1 | **`localhost`, hardcoded** | Cannot work in production |
| `index.html` | 2 | none | 20 relative calls resolve at runtime |
| `admin.html` | 2 | none | template-built URLs |
| `realtor_sales_console.html` | 0 | — | static |
| `cocopeat.html` | 0 | — | static e-commerce page |
| `field_pitch.html` | 0 | — | Gujarati pitch, static |
| `compare/*.html` (2) | 0 | — | SEO/comparison pages |
| `industry/*.html` (2) | 0 | — | vertical landing pages |

**Six of eleven surfaces are static. Five are interactive, and those five do
not agree on where the API lives.**

### 1.2 Client-side external calls

`dashboard.html` calls `graph.facebook.com` **7 times directly from the
browser** (comment-hide, replies, page fetch). Consequences:

- Meta app domain restrictions apply to page origins, not your server
- Any page visitor's session carries your page's Meta permissions
- The backend has no record of those operations, so `bot_executions` and the
  audit trail stay empty — which is why the flagship tables hold nothing

### 1.3 Build divergence

`dist/` is a hand-maintained copy, not a build artifact. **5 of 11 mirrors
have diverged from source**, meaning the served page and the repository page
are different documents:

`dashboard.html`, `compare/manychat-alternative.html`,
`compare/wati-alternative.html`, `industry/diamond-cvd-sales-agent.html`,
`industry/textile-saree-wholesale-ai-agent.html`

### 1.4 Domain fragmentation

Six live domains: `algorise-ai.com` (CNAME), `algorise-ai.surge.sh`
(sitemap + robots + all hardcoded links), `algorise.surge.sh`
(`deploy_cloud.bat`), `algorise.ai` (all docs), the Render backend, and
GitHub Pages. `sitemap.xml` advertises surge.sh while `CNAME` claims
algorise-ai.com.

### 1.5 Hardcoded identifiers in client code

38 phone numbers and 5 Telegram chat IDs in `dashboard.html`; `wa.me` deep
links in three surfaces. These are merchant-specific and will be wrong for
every client but the first.

---

## 2. Phase plan

Six phases. Each has a measurable exit criterion, an explicit rollback, and a
revenue guard.

### Phase 1 — Single API contract

**Why first.** Nothing else can be verified while surfaces disagree about
where the API is. `creator_studio.html` is broken in production today.

| # | Change | Measure |
|---|---|---|
| 1.1 | One `config.js` generated at build time from `API_BASE_URL`, `API_VERSION`, `BUILD_SHA` | 1 file, 0 hardcoded hosts |
| 1.2 | `dashboard.html` drops its `LOCAL_API`/`CLOUD_API` fallback chain | fallback chain removed |
| 1.3 | `creator_studio.html` `localhost` → injected config | 0 `localhost` in any surface |
| 1.4 | Config injected from environment at build; never committed | `.env` not in git |

**Exit:** `grep -r "localhost:8000" *.html` returns 0.
**Rollback:** revert the commit. Surfaces fall back to their previous
hardcoded values; no data migration involved.
**Revenue guard:** none required — no schema, no client-visible change.

### Phase 2 — Single build pipeline

| # | Change | Measure |
|---|---|---|
| 2.1 | `npm run build` produces `dist/` deterministically; `dist/` git-ignored | 1 build command |
| 2.2 | Adopt the diverged mirrors into source, then regenerate | 0 divergence |
| 2.3 | CI runs the build on every PR | build is enforced |
| 2.4 | Deploy copies an immutable artifact named by SHA | rollback by SHA, not by rebuild |

**Exit:** `git ls-files dist/` returns nothing; a fresh checkout plus one
command produces the deployable tree.
**Rollback:** every previous release is retained as a SHA-named artifact.
Rollback is redeploying a previous SHA — minutes, no rebuild.
**Revenue guard:** the client portal must stay reachable throughout. Deploy
to a new path first, verify, then switch.

### Phase 3 — Canonical domain

| # | Change | Measure |
|---|---|---|
| 3.1 | Pick one canonical domain | 1 |
| 3.2 | Canonical → others 301, preserve query strings | all redirect |
| 3.3 | `sitemap.xml` and `robots.txt` generated from the canonical list | 0 drift |
| 3.4 | `CNAME`, `deploy_cloud.bat`, and every hardcoded link reconciled | 1 domain in source |

**Exit:** all six resolve to one canonical; no internal link names another.
**Rollback:** DNS is not changed until step 3.5 passes. Restore the previous
CNAME and redeploy the previous SHA.
**Revenue guard:** SEO pages (`compare/`, `industry/`) must keep their paths.
Redirect, never move. A moved URL loses accumulated ranking.

### Phase 4 — Proxy browser-side Meta calls

**Why it matters beyond tidiness.** Seven browser-side calls mean the
backend cannot audit, rate-limit, or attribute any of it. This is the
technical cause of the empty `bot_executions` table.

| # | Change | Measure |
|---|---|---|
| 4.1 | Backend endpoints for page fetch, comment list, comment hide, reply | 4 endpoints |
| 4.2 | Dashboard calls those instead of `graph.facebook.com` | 0 browser-side Meta calls |
| 4.3 | Every proxy call writes a `bot_executions` row | table non-empty |
| 4.4 | Server-side token only; never returned to the browser | 0 tokens in client |

**Exit:** no surface contains `graph.facebook.com`. `bot_executions` gains
rows on first real use.
**Rollback:** revert; the browser falls back to direct calls. Slightly
worse security, fully functional.
**Revenue guard:** this changes the write path for comment handling. Enable
per client behind a flag, verify on Shruhi, then widen.

### Phase 5 — Agent consolidation *(deferred, per your direction)*

Only after Phases 1–4 are stable. Proposed order:

1. `facebook_agent` — the one agent with real, verified integrations
2. WhatsApp Cloud dispatcher — inbound webhook, which does not yet exist
3. `realtor_sales_assistant` — reuse for other merchant verticals
4. Telegram — alerting only, not a product surface

The 100-bot Hero registry stays a sandboxed demo. Its benchmarks cannot fail
by construction and its regulated verticals now return `supported: false`.
It should not be wired into production as if it were working.

### Phase 6 — Observability *(deferred)*

Metrics, alerts, and the accuracy dashboard depend on Phase 4's audit trail.
Building them before then produces dashboards over empty tables.

---

## 3. Operational workflows

### 3.1 Release procedure (canonical, enforced by tooling)

```
build (immutable, SHA-named)
  → verify (health + smoke + surface checks)
  → canary (5% traffic or single client)
  → promote
  → monitor (15 min)
  → or rollback (previous SHA)
```

No step may be skipped manually. `scripts/release.py` is the only sanctioned
path.

### 3.2 Configuration propagation

| Layer | Source of truth | Propagated by | Never |
|---|---|---|---|
| API base URL | Deployment env var | Build-time injection into `config.js` | Hardcoded in HTML |
| Secrets | Platform secret store | Runtime env only | In any file under version control |
| Client IDs / phone numbers | Database | API response | Hardcoded per merchant |
| Calculation config | — | n/a | n/a |

The hardcoded-identifier inventory must return zero merchant-specific values
in client code before a second client is onboarded.

### 3.3 Client onboarding SOP

The current product works for exactly one client because merchant specifics
are baked into the pages. Onboarding a second requires:

1. Client record in `clients` (exists, works)
2. Subscription record (exists, works)
3. Meta access token via OAuth — **not yet implemented**; the token is
   currently read from config for one page
4. Sector selection driving reply templates
5. Remove that merchant's numbers from `dashboard.html`

Steps 3–5 are the gap. Step 5 is the tell: if a second merchant's data
requires editing HTML, the product is not multi-tenant yet.

### 3.4 Incident severity

| Severity | Definition | Response | Rollback |
|---|---|---|---|
| **S1** | Client portal unreachable, or comment handling stopped | immediate | automatic |
| **S2** | Degraded performance, or Meta API errors | 15 min | on-call decision |
| **S3** | Cosmetic, or a non-client surface broken | next release | no |
| **S4** | Documentation drift | backlog | no |

---

## 4. Risk register

| # | Risk | Likelihood | Impact | Mitigation | Rollback |
|---|---|---|---|---|---|
| R1 | **Unrotated token exploited** | Medium | High — account abuse, reputational | Rotate now (P0). Already purged from repo | Revoke token; disable Telegram surface |
| R2 | **Comment handling breaks on deploy** | Medium | **High — direct revenue loss** | Phase 4 behind a per-client flag; canary on one client | Redeploy previous SHA; flag off restores old path |
| R3 | Canonical domain migration loses SEO | Medium | Medium | Redirect only, never move. Preserve paths | Restore CNAME |
| R4 | Build pipeline change breaks deploy | Low | High | Immutable artifacts; deploy and build are separate steps | Previous SHA artifact |
| R5 | Proxy adds latency to Meta calls | Medium | Medium | Timeouts with fallback to direct call | Flag off |
| R6 | Second merchant still requires HTML edits | **High** | High — blocks growth | Make 3–5 in SOP 3.3 a Phase 5 gate | n/a |
| R7 | `dist/` divergence silently serves stale UI | **High** | Medium | Phase 2 removes hand-maintained mirrors | n/a |
| R8 | Render free tier sleeps, client perceives outage | High | Medium | Uptime pings keep it warm; paid tier when MRR justifies | n/a |
| R9 | Six domains drift further apart | High | Medium | Phase 3.4 | n/a |
| R10 | Removing Hero bots is read as losing the product | Medium | Medium | Position as narrowing, with the roadmap as evidence | Restore registry from `backup-freelancer-all` |

R6 and R7 are marked high-likelihood because they are **present tense**, not
future risks.

---

## 5. Post-deployment monitoring

### 5.1 Checklist before each release

**Build**
- [ ] `npm run build` succeeds from a clean checkout
- [ ] `git ls-files dist/` is empty
- [ ] No `localhost` in any surface
- [ ] No token, chat ID, or page ID in any surface
- [ ] No merchant phone number in any surface

**Contract**
- [ ] `GET /health` returns 200
- [ ] `GET /api/v1/health` returns 200
- [ ] Every endpoint referenced by every surface responds
- [ ] Auth enforced when `VEDIC_API_KEY` is set

**Content**
- [ ] `sitemap.xml` lists only canonical URLs
- [ ] All internal links resolve
- [ ] Redirects from legacy domains work

**Data**
- [ ] Migration applied to a copy, verified, then applied to production
- [ ] Backup taken and restore rehearsed

**Rollback**
- [ ] Previous artifact identified and retrievable
- [ ] Rollback rehearsed on staging this release cycle

### 5.2 KPIs

**Availability**

| KPI | Target | Source |
|---|---|---|
| Portal uptime | ≥99.5% monthly | external ping |
| API p95 latency | <400 ms | `/metrics` |
| Error rate | <1% of requests | `/metrics` |

**Revenue-critical** *(measure these before optimising anything else)*

| KPI | Definition | Why |
|---|---|---|
| Comments scanned/day | per client | the unit of work sold |
| Reply rate | replies ÷ comments scanned | product value |
| Reply acceptance | merchant-approved replies ÷ replies sent | quality |
| **Enquiries to WhatsApp** | DM opens ÷ comments scanned | the conversion clients pay for |
| Leads captured | `leads` rows ÷ comments scanned | pipeline |
| **Client retention** | logo retention, monthly | **the number you do not have** |

**System health**

| KPI | Target |
|---|---|
| `bot_executions` rows per day | grows after Phase 4 |
| `facebook_agent_jobs` rows with `status=not_configured` | falls to 0 once tokens are configured |
| Queue depth per client | <1 pending job |
| Facebook API error rate | <1% |

**Honesty KPIs** *(unique to this product)*

| KPI | Target |
|---|---|
| Claims on public pages with no backing counter | 0 |
| Client-visible metrics not derived from stored data | 0 |
| Telemetry rows not corresponding to a real API call | 0 |

The last row is there because the product previously manufactured its own
evidence. If it ever rises, something has regressed into that failure mode.

---

## 6. What this plan does not cover

- **Agent consolidation** (Phase 5) — deferred per your direction
- **Acquisition and pricing** — covered in `STRATEGIC_ROADMAP.md`
- **Attribution infrastructure** — depends on Phase 4's audit trail
- **Anything requiring the Telegram rotation** — P0, manual, blocking

Two things in this plan are marked high-likelihood risk because they are
already true: onboarding a second merchant still requires editing HTML, and
the `dist/` mirror has already diverged on five surfaces. Both are growth
blockers, and both are fixed by Phases 2 and 5 respectively.
