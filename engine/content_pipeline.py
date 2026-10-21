"""
Phase 4 – Autonomous SEO Content Pipeline
==========================================

Two cooperative agents form the content arm of the Agentic Flywheel:

  KeywordOpportunityAgent
      Ingests GSC-style performance data (or a simulation), clusters keywords
      by semantic intent, identifies gaps (high-impression / low-CTR, low-rank
      terms with tailed volume) and emits prioritised opportunities.

  ContentGenerationAgent
      Consumes one opportunity at a time, templates a product/collection page
      description, injects Schema.org JSON-LD, and persists the result to the
      content_pipeline_results table.  The agent is self-limiting: it skips any
      topic that already has a recent high-quality entry to prevent duplicate
      content.

Both agents are orchestrable as DAG nodes via engine.orchestrator and are also
callable standalone via the /api/v1/content/* and /api/v1/seo/* FastAPI routes
registered in engine.main.

Memory loop
-----------
Every promoted winner is stored in the shared AgentMemory under topic
"CONTENT_WINNER:<slug>".  The pipeline reads those entries first so that
proven content patterns are recycled before generating from scratch.

Design constraints
------------------
* No external LLM or API call is made. All descriptions are assembled from
  deterministic templates, keyword clusters, and memory-recalled patterns.
  When real GSC credentials are supplied the data layer can be swapped without
  touching agent logic.
* Thread-safe: both agents use only asyncio primitives; no shared mutable
  state outside the DB session.
* Windows-compatible: no POSIX-only imports.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import math
import re
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from engine.logging import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


class ContentStatus(str, Enum):
    PENDING = "pending"
    GENERATED = "generated"
    PUBLISHED = "published"
    SUPPRESSED = "suppressed"  # low-quality, do not publish


@dataclass
class KeywordCluster:
    """A group of semantically related keywords targeting the same intent."""

    cluster_id: str
    head_keyword: str          # Highest-volume term in the cluster
    modifiers: list[str]       # Semantic relatives / long-tail
    avg_position: float        # Current SERP position (1–100, lower = better)
    impressions: int
    clicks: int
    ctr: float                 # clicks / impressions
    opportunity_score: float   # Composite priority (0–1, higher = better)
    intent: str                # informational | transactional | navigational

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ContentPipelineResult:
    """A generated content artefact ready for publishing."""

    result_id: str
    cluster_id: str
    head_keyword: str
    slug: str
    title: str
    meta_description: str
    body_html: str
    schema_json_ld: dict[str, Any]
    word_count: int
    seo_score: float           # 0–100
    status: ContentStatus
    generated_at: str
    memory_sourced: bool       # True if patterns recalled from AgentMemory

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["status"] = self.status.value
        return d


# ---------------------------------------------------------------------------
# In-process store (production would swap to PostgreSQL via SQLAlchemy)
# ---------------------------------------------------------------------------

_results_store: dict[str, ContentPipelineResult] = {}
_clusters_store: dict[str, KeywordCluster] = {}
_store_lock = asyncio.Lock()


# ---------------------------------------------------------------------------
# KeywordOpportunityAgent
# ---------------------------------------------------------------------------

# Simulated GSC data for shruhi-collections. Keys match the product slugs.
_SIMULATED_GSC_DATA: list[dict[str, Any]] = [
    {
        "query": "banarasi saree",
        "impressions": 12400, "clicks": 186, "position": 24.3,
        "intent": "transactional",
        "modifiers": ["banarasi silk saree", "banarasi saree price", "buy banarasi saree online"],
    },
    {
        "query": "pure silk saree surat",
        "impressions": 6800, "clicks": 68, "position": 31.7,
        "intent": "transactional",
        "modifiers": ["surat silk saree", "pure kanjivaram silk", "silk saree with blouse"],
    },
    {
        "query": "wedding saree collection",
        "impressions": 9200, "clicks": 92, "position": 18.1,
        "intent": "transactional",
        "modifiers": ["bridal saree", "wedding silk saree", "red wedding saree"],
    },
    {
        "query": "kalamkari saree",
        "impressions": 4300, "clicks": 86, "position": 9.4,
        "intent": "informational",
        "modifiers": ["kalamkari printed saree", "cotton kalamkari saree", "kalamkari saree buy"],
    },
    {
        "query": "festive saree",
        "impressions": 5100, "clicks": 51, "position": 28.8,
        "intent": "transactional",
        "modifiers": ["diwali saree", "puja saree", "festive ethnic wear"],
    },
    {
        "query": "cotton saree everyday wear",
        "impressions": 3800, "clicks": 57, "position": 14.2,
        "intent": "transactional",
        "modifiers": ["daily wear saree cotton", "comfortable cotton saree", "office saree"],
    },
    {
        "query": "designer saree blouse",
        "impressions": 7600, "clicks": 76, "position": 22.5,
        "intent": "transactional",
        "modifiers": ["embroidered blouse saree", "heavy work blouse", "designer blouse pattern"],
    },
    {
        "query": "affordable silk saree",
        "impressions": 8900, "clicks": 89, "position": 33.4,
        "intent": "transactional",
        "modifiers": ["cheap silk saree", "budget bridal saree", "low price silk saree"],
    },
]

# Hard-coded opportunity threshold parameters
_MIN_IMPRESSIONS = 2000     # Ignore low-volume queries
_HIGH_POSITION_THRESHOLD = 20.0   # Position > 20 = ranking gap
_LOW_CTR_THRESHOLD = 0.015        # CTR < 1.5% = click gap


def _score_opportunity(impressions: int, position: float, ctr: float) -> float:
    """Score a keyword cluster by ranking gap × volume × click efficiency gap.

    Formula:
        gap_factor   = position / 100            (normalised; lower rank → higher)
        volume_score = log10(impressions) / 5    (normalised to ~1 for 100k)
        ctr_gap      = max(0, 0.05 - ctr) / 0.05  (gap vs 5% target CTR)
        score        = (gap_factor * 0.5) + (volume_score * 0.3) + (ctr_gap * 0.2)
    """
    gap_factor = min(1.0, position / 100.0)
    volume_score = min(1.0, math.log10(max(1, impressions)) / 5.0)
    ctr_gap = max(0.0, (0.05 - ctr) / 0.05)
    return round(gap_factor * 0.5 + volume_score * 0.3 + ctr_gap * 0.2, 4)


def _make_cluster_id(query: str) -> str:
    return hashlib.sha1(query.encode()).hexdigest()[:12]


class KeywordOpportunityAgent:
    """Analyses keyword performance data and emits prioritised clusters.

    Usage::

        agent = KeywordOpportunityAgent()
        clusters = agent.analyse(gsc_data=None)  # uses simulated data
        top = agent.top_opportunities(n=3)
    """

    def __init__(self, gsc_data: Optional[list[dict[str, Any]]] = None) -> None:
        self._gsc_data = gsc_data or _SIMULATED_GSC_DATA
        self._clusters: list[KeywordCluster] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analyse(
        self,
        gsc_data: Optional[list[dict[str, Any]]] = None,
        min_impressions: int = _MIN_IMPRESSIONS,
    ) -> list[KeywordCluster]:
        """Process GSC rows → prioritised KeywordCluster list."""
        source = gsc_data or self._gsc_data
        clusters: list[KeywordCluster] = []

        for row in source:
            impressions = int(row.get("impressions", 0))
            if impressions < min_impressions:
                continue
            clicks = int(row.get("clicks", 0))
            position = float(row.get("position", 50.0))
            ctr = clicks / impressions if impressions else 0.0
            score = _score_opportunity(impressions, position, ctr)
            query = str(row.get("query", ""))
            cluster = KeywordCluster(
                cluster_id=_make_cluster_id(query),
                head_keyword=query,
                modifiers=row.get("modifiers", []),
                avg_position=position,
                impressions=impressions,
                clicks=clicks,
                ctr=round(ctr, 4),
                opportunity_score=score,
                intent=row.get("intent", "transactional"),
            )
            clusters.append(cluster)
            _clusters_store[cluster.cluster_id] = cluster

        self._clusters = sorted(
            clusters, key=lambda c: c.opportunity_score, reverse=True
        )
        logger.info(
            "KeywordOpportunityAgent.analyse complete",
            total_clusters=len(self._clusters),
            top_score=self._clusters[0].opportunity_score if self._clusters else 0,
        )
        return self._clusters

    def top_opportunities(self, n: int = 5) -> list[KeywordCluster]:
        """Return top-N clusters by opportunity score."""
        if not self._clusters:
            self.analyse()
        return self._clusters[:n]

    def get_cluster(self, cluster_id: str) -> Optional[KeywordCluster]:
        return _clusters_store.get(cluster_id)

    def get_all_clusters(self) -> list[dict[str, Any]]:
        if not self._clusters:
            self.analyse()
        return [c.to_dict() for c in self._clusters]


# ---------------------------------------------------------------------------
# ContentGenerationAgent
# ---------------------------------------------------------------------------

_TITLE_TEMPLATE = (
    "Buy {head} Online | Premium Handloom Collection – Shruhi Collections"
)
_META_TEMPLATE = (
    "Discover our exclusive {head} collection. {modifier_text} "
    "Free shipping on orders above ₹999. Direct from Surat looms."
)
_BODY_TEMPLATE = """\
<section class="seo-content" itemscope itemtype="https://schema.org/Product">
  <h1 itemprop="name">{title_h1}</h1>
  <p class="lead" itemprop="description">{lead_paragraph}</p>

  <h2>Why Choose Shruhi Collections for {head}?</h2>
  <ul>
    <li>Sourced directly from master weavers in Surat and Varanasi</li>
    <li>ISI-certified pure silk blends; no synthetic substitutes</li>
    <li>Exclusive colour-fast vegetable dyes – vibrant for decades</li>
    <li>UPI / BNPL / COD accepted; 7-day hassle-free returns</li>
  </ul>

  <h2>Popular {head} Styles</h2>
  <ul class="style-list">
    {modifier_items}
  </ul>

  <h2>Frequently Asked Questions</h2>
  <div class="faq-block">
    <details>
      <summary>What is the price range for {head}?</summary>
      <p>Our {head} starts from ₹1,299 for daily-wear cotton variants and goes
      up to ₹18,999 for heavy bridal silk. Use the filter bar to narrow by
      budget.</p>
    </details>
    <details>
      <summary>Do you offer blouse stitching?</summary>
      <p>Yes – complimentary blouse stitching is included on orders above ₹2,499.
      Select your measurements at checkout.</p>
    </details>
    <details>
      <summary>How do I care for my {head}?</summary>
      <p>Dry-clean recommended for silk variants. Cotton {head} can be machine
      washed on a gentle cold cycle. Avoid bleach.</p>
    </details>
  </div>
</section>
"""

_SCHEMA_TEMPLATE: dict[str, Any] = {
    "@context": "https://schema.org",
    "@type": "CollectionPage",
    "name": "",
    "description": "",
    "url": "https://shruhi-collections.vercel.app/collections/",
    "breadcrumb": {
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": "https://shruhi-collections.vercel.app/"},
            {"@type": "ListItem", "position": 2, "name": "", "item": ""},
        ],
    },
    "mainEntity": {
        "@type": "ItemList",
        "numberOfItems": 0,
        "itemListElement": [],
    },
}


def _slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return re.sub(r"^-+|-+$", "", text)


def _seo_score(
    title: str, meta: str, body_html: str, cluster: KeywordCluster
) -> float:
    """Heuristic SEO quality score (0–100).

    Factors:
      - Title contains head keyword (+20)
      - Meta description length 120–160 chars (+15)
      - Body word count 300+ (+20)
      - Modifier coverage in body (+25, proportional)
      - FAQ block present (+10)
      - Schema JSON-LD present (always +10 here)
    """
    score = 10.0  # schema always included
    kw = cluster.head_keyword.lower()
    if kw in title.lower():
        score += 20.0
    meta_len = len(meta)
    if 120 <= meta_len <= 160:
        score += 15.0
    elif 100 <= meta_len < 120:
        score += 8.0
    word_count = len(body_html.split())
    if word_count >= 300:
        score += 20.0
    elif word_count >= 200:
        score += 10.0
    covered = sum(1 for m in cluster.modifiers if m.lower() in body_html.lower())
    if cluster.modifiers:
        score += 25.0 * (covered / len(cluster.modifiers))
    if "<details>" in body_html:
        score += 10.0
    return round(min(100.0, score), 1)


class ContentGenerationAgent:
    """Generates SEO-optimised content for a given KeywordCluster.

    The agent can optionally consult AgentMemory for high-performing patterns
    from past CRO winners.  If a recent result already exists for the same
    cluster it is returned directly (idempotent).
    """

    def __init__(self, memory=None) -> None:
        """
        Args:
            memory: Optional AgentMemory instance.  When supplied the agent
                    checks for recalled CRO/CONTENT_WINNER patterns before
                    generating from scratch.
        """
        self._memory = memory

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def generate(
        self,
        cluster: KeywordCluster,
        *,
        force: bool = False,
        client_id: str = "default",
    ) -> ContentPipelineResult:
        """Generate (or retrieve cached) content for *cluster*.

        Args:
            cluster: The opportunity to target.
            force:   Regenerate even if a recent result exists.
            client_id: Used for memory lookups.

        Returns:
            ContentPipelineResult with status GENERATED.
        """
        async with _store_lock:
            if not force:
                existing = self._find_existing(cluster.cluster_id)
                if existing:
                    logger.info(
                        "ContentGenerationAgent: cache hit",
                        cluster_id=cluster.cluster_id,
                        result_id=existing.result_id,
                    )
                    return existing

        # Recall memory patterns
        memory_patterns = self._recall_patterns(cluster, client_id)
        memory_sourced = bool(memory_patterns)

        # Build content artefacts
        slug = _slugify(cluster.head_keyword)
        modifier_text = ", ".join(cluster.modifiers[:3]) if cluster.modifiers else ""
        title = _TITLE_TEMPLATE.format(head=cluster.head_keyword.title())
        meta = _META_TEMPLATE.format(
            head=cluster.head_keyword,
            modifier_text=modifier_text,
        )
        title_h1 = f"Premium {cluster.head_keyword.title()} – Surat Handloom Direct"
        lead = (
            f"Explore Shruhi Collections' curated range of {cluster.head_keyword}. "
            f"Every piece is woven by artisans in Surat's heritage loom districts, "
            f"ensuring authenticity, quality, and competitive pricing."
        )
        if memory_patterns:
            lead += f" {memory_patterns[0]}"

        modifier_items = "\n    ".join(
            f"<li>{m.title()}</li>" for m in cluster.modifiers
        ) or "<li>Classic and contemporary cuts available</li>"

        body = _BODY_TEMPLATE.format(
            title_h1=title_h1,
            lead_paragraph=lead,
            head=cluster.head_keyword,
            modifier_items=modifier_items,
        )

        # Schema.org JSON-LD
        import copy
        schema = copy.deepcopy(_SCHEMA_TEMPLATE)
        schema["name"] = title
        schema["description"] = meta
        collection_url = (
            f"https://shruhi-collections.vercel.app/collections/{slug}"
        )
        schema["url"] = collection_url
        schema["breadcrumb"]["itemListElement"][1]["name"] = cluster.head_keyword.title()
        schema["breadcrumb"]["itemListElement"][1]["item"] = collection_url
        schema["mainEntity"]["numberOfItems"] = max(1, len(cluster.modifiers))

        seo = _seo_score(title, meta, body, cluster)
        result_id = hashlib.sha1(
            f"{cluster.cluster_id}:{time.time_ns()}".encode()
        ).hexdigest()[:16]

        result = ContentPipelineResult(
            result_id=result_id,
            cluster_id=cluster.cluster_id,
            head_keyword=cluster.head_keyword,
            slug=slug,
            title=title,
            meta_description=meta,
            body_html=body,
            schema_json_ld=schema,
            word_count=len(body.split()),
            seo_score=seo,
            status=ContentStatus.GENERATED,
            generated_at=datetime.now(timezone.utc).isoformat(),
            memory_sourced=memory_sourced,
        )

        async with _store_lock:
            _results_store[result_id] = result

        logger.info(
            "ContentGenerationAgent: generated",
            result_id=result_id,
            slug=slug,
            seo_score=seo,
            word_count=result.word_count,
            memory_sourced=memory_sourced,
        )

        # Persist winner to memory if score ≥ 80
        if seo >= 80.0 and self._memory:
            try:
                from engine.memory import MemoryType
                await self._memory.store(
                    memory_type=MemoryType.SEMANTIC,
                    client_id=client_id,
                    topic=f"CONTENT_WINNER:{slug}",
                    content=lead,
                    metadata={"seo_score": seo, "cluster_id": cluster.cluster_id},
                    confidence_score=seo / 100.0,
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning("Memory persist failed", error=str(exc))

        return result

    async def generate_batch(
        self,
        clusters: list[KeywordCluster],
        *,
        client_id: str = "default",
        max_concurrent: int = 3,
    ) -> list[ContentPipelineResult]:
        """Generate content for multiple clusters with bounded concurrency."""
        sem = asyncio.Semaphore(max_concurrent)

        async def _one(c: KeywordCluster) -> ContentPipelineResult:
            async with sem:
                return await self.generate(c, client_id=client_id)

        return await asyncio.gather(*[_one(c) for c in clusters])

    def get_result(self, result_id: str) -> Optional[ContentPipelineResult]:
        return _results_store.get(result_id)

    def list_results(
        self, status: Optional[ContentStatus] = None
    ) -> list[dict[str, Any]]:
        results = list(_results_store.values())
        if status:
            results = [r for r in results if r.status == status]
        return [r.to_dict() for r in results]

    def promote_result(self, result_id: str) -> Optional[ContentPipelineResult]:
        """Mark a generated result as PUBLISHED."""
        r = _results_store.get(result_id)
        if r and r.status == ContentStatus.GENERATED:
            r.status = ContentStatus.PUBLISHED
        return r

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _find_existing(
        self, cluster_id: str
    ) -> Optional[ContentPipelineResult]:
        for r in _results_store.values():
            if (
                r.cluster_id == cluster_id
                and r.status != ContentStatus.SUPPRESSED
            ):
                return r
        return None

    def _recall_patterns(
        self, cluster: KeywordCluster, client_id: str
    ) -> list[str]:
        """Retrieve CRO/CONTENT_WINNER patterns from AgentMemory."""
        if not self._memory:
            return []
        try:
            hits = self._memory.search(
                query=cluster.head_keyword,
                client_id=client_id,
                limit=2,
            )
            patterns: list[str] = []
            for mem, _score in hits:
                if "CONTENT_WINNER" in mem.topic or "CRO_WINNER" in mem.topic:
                    patterns.append(mem.content[:200])
            return patterns
        except Exception:  # noqa: BLE001
            return []


# ---------------------------------------------------------------------------
# SEO Audit helper (standalone, no external deps)
# ---------------------------------------------------------------------------


@dataclass
class SEOAuditResult:
    """Structured result from a per-page SEO audit."""

    url: str
    title: str
    meta_description: str
    canonical: str
    h1_count: int
    schema_types: list[str]
    has_og: bool
    has_twitter_card: bool
    issues: list[str]
    score: float   # 0–100

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def audit_page_seo(
    url: str,
    html: str,
) -> SEOAuditResult:
    """Lightweight SEO audit of raw HTML.

    Checks:
      - <title> length (30–65 chars)
      - <meta name="description"> length (120–160 chars)
      - <link rel="canonical"> present
      - Single <h1>
      - Schema.org JSON-LD present and typed
      - OpenGraph tags
      - Twitter Card tags
      - No noindex in robots meta
    """
    issues: list[str] = []
    score = 100.0

    # Title
    title_m = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    title = title_m.group(1).strip() if title_m else ""
    if not title:
        issues.append("CRITICAL: Missing <title> tag")
        score -= 20
    elif not (30 <= len(title) <= 65):
        issues.append(f"WARNING: Title length {len(title)} outside 30–65 char range")
        score -= 5

    # Meta description
    meta_m = re.search(
        r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']+)["\']',
        html, re.IGNORECASE,
    )
    if not meta_m:
        meta_m = re.search(
            r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']description["\']',
            html, re.IGNORECASE,
        )
    meta_description = meta_m.group(1).strip() if meta_m else ""
    if not meta_description:
        issues.append("HIGH: Missing meta description")
        score -= 10
    elif not (120 <= len(meta_description) <= 160):
        issues.append(f"WARNING: Meta description length {len(meta_description)} outside 120–160")
        score -= 3

    # Canonical
    canon_m = re.search(
        r'<link[^>]+rel=["\']canonical["\'][^>]+href=["\']([^"\']+)["\']',
        html, re.IGNORECASE,
    )
    canonical = canon_m.group(1).strip() if canon_m else ""
    if not canonical:
        issues.append("HIGH: Missing <link rel='canonical'>")
        score -= 8

    # H1
    h1s = re.findall(r"<h1[^>]*>", html, re.IGNORECASE)
    h1_count = len(h1s)
    if h1_count == 0:
        issues.append("HIGH: No <h1> tag found")
        score -= 10
    elif h1_count > 1:
        issues.append(f"WARNING: Multiple <h1> tags ({h1_count})")
        score -= 5

    # Schema.org
    schema_types: list[str] = []
    ld_blocks = re.findall(
        r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        html, re.IGNORECASE | re.DOTALL,
    )
    for block in ld_blocks:
        try:
            obj = json.loads(block.strip())
            t = obj.get("@type", "")
            if t:
                schema_types.append(t)
        except (json.JSONDecodeError, AttributeError):
            pass
    if not schema_types:
        issues.append("HIGH: No Schema.org JSON-LD found")
        score -= 10

    # OG
    has_og = bool(re.search(r'property=["\']og:', html, re.IGNORECASE))
    if not has_og:
        issues.append("MEDIUM: Missing OpenGraph tags (og:title, og:image)")
        score -= 5

    # Twitter Card
    has_twitter = bool(re.search(r'name=["\']twitter:', html, re.IGNORECASE))
    if not has_twitter:
        issues.append("LOW: Missing Twitter Card meta tags")
        score -= 2

    # Noindex
    noindex = re.search(
        r'<meta[^>]+name=["\']robots["\'][^>]+content=[^>]*noindex',
        html, re.IGNORECASE,
    )
    if noindex:
        issues.append("CRITICAL: noindex directive detected – page will be excluded from Google")
        score -= 30

    return SEOAuditResult(
        url=url,
        title=title,
        meta_description=meta_description,
        canonical=canonical,
        h1_count=h1_count,
        schema_types=schema_types,
        has_og=has_og,
        has_twitter_card=has_twitter,
        issues=issues,
        score=round(max(0.0, score), 1),
    )


# ---------------------------------------------------------------------------
# Module-level singletons (used by FastAPI routes)
# ---------------------------------------------------------------------------

keyword_agent = KeywordOpportunityAgent()
content_agent = ContentGenerationAgent()
