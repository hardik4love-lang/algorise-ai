# Aria — Technical System Architecture & Roadmap (Cloud-Only, Zero-Cost)

## 1. Modular Skill Integration Engine
- Skill = Python package with `aria.skill.yaml` manifest + async `execute(task_context)`.
- `SkillRegistry` (SQLite) + hot-load from `~/.aria/skills/` and GitHub releases.
- JSON-schema I/O, semver versioning, capability tags: `swe`, `sysadmin`, `offsec`, `defsec`.
- Isolated subprocess execution with egress allow-list; static scan (bandit/semgrep) + signature verify before activation.
- Declarative DAG composition of skill chains.

## 2. Autonomous Workflow & Orchestration
- Event bus: Redis Streams (free, Upstash) instead of NATS.
- Adapters: IMAP email, GitHub webhooks, API polling → canonical `Event` envelope.
- Zero-loss: idempotency keys + transactional outbox in Postgres (Neon/Supabase free); DLQ with replay.
- Orchestration: GitHub Actions reusable workflows + matrix jobs (free, no Temporal infra).
- State: Upstash Redis (hot), Neon Postgres (durable), pgvector (semantic recall).

## 3. Automated Vulnerability Research Lifecycle
Pipeline as checkpointed Actions jobs:
1. Recon: subdomain enum, port scan, tech fingerprint → Neo4j/Postgres asset graph.
2. Scan: nuclei + semgrep SAST + dependency CVE audit.
3. Verify: PoC harness in ephemeral runner; reproducibility re-run; CVSS 3.1 scoring.
4. Report: templated Markdown/PDF with evidence; auto-file via HackerOne/Bugcrowd or GitHub Security Advisory.
- Scope policy engine: never test out-of-scope; rate-limited, consent-verified targets only.

## 4. Heterogeneous Free Cloud Model Orchestration
- Router priority: Groq free → Google AI Studio free → HuggingFace Inference free → OpenRouter free → Cloudflare Workers AI free.
- Fallback chain on rate-limit; token budget per run; semantic cache in Redis.
- Task-type routing: code→code model, recon→fast small model, exploit analysis→large reasoning model.

## 5. Continuous Evolution & Research Loop
- Weekly scheduled workflow scans HuggingFace trending + GitHub releases + ArXiv.
- Candidate models benchmarked on SWE-bench-lite + custom security tasks.
- Canary pool A/B test; promote if ≥5% improvement, no regression (opens PR).
- Free API registry health-checked with auto-failover.

## 6. Resilience & Self-Correction
- Testing: pytest + Hypothesis; integration tests in Docker compose; chaos via toxiproxy.
- Self-correction: Reflexion retry loop (critique → revised plan → re-execute; max N then escalate).
- Observability: OpenTelemetry + Prometheus + Grafana (free tiers).
- Recovery: circuit breakers, exponential backoff, checkpoint/resume, graceful degradation.
- Human-in-the-loop approval gates for destructive/exploit actions; audit log.

## Multi-Phase Roadmap
- Phase 0 (wk1-2): scaffolding, CI, core abstractions, hello-world skill.
- Phase 1 (wk3-5): ingestion adapters, Redis Streams, zero-loss outbox, dashboard.
- Phase 2 (wk6-9): skill engine, sandboxing, model router, semantic cache.
- Phase 3 (wk10-13): recon/scan/verify/report pipeline, scope policy.
- Phase 4 (wk14-16): evolution loop, benchmark harness, canary promotion.
- Phase 5 (wk17-19): chaos tests, reflexion, observability, HITL gates.
- Phase 6 (wk20+): skill marketplace, multi-tenant isolation.

## GitHub Deployment
- Monorepo `/core /skills /infra /docs`; Actions: lint, test, build, push GHCR, deploy ArgoCD.
- Secrets via GitHub Environments + SOPS; config via `.aria.yaml`.
- Branch protection + required reviews for skill merges.
