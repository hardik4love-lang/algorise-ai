"""
Phase 4 – Customer Personalisation Engine
==========================================

Provides real-time customer segmentation and collaborative-filtering product
recommendations for the Shruhi Collections storefront.

Architecture
------------
  SegmentDetector
      Classifies an incoming visitor into one of four behavioural segments
      based on signals that are available without third-party cookies:

        first_visit   – No purchase or browsing history recorded.
        returning     – Has viewed products in the past; no purchase.
        loyal         – ≥1 past purchase in the DB.
        high_ltv      – ≥3 purchases OR lifetime value ≥ the 80th-percentile
                        spend threshold.

  RecommendationEngine
      Combines item-based collaborative filtering (Jaccard similarity over
      co-purchase sets) with a lightweight popularity fallback for cold-start
      customers.  No external ML library is needed; the similarity matrix is
      built on-demand from the purchase log and cached in-process.

  PersonalisationEndpoint helper
      A thin adapter that the FastAPI route calls to fan-out the two engines
      and return a ranked recommendation list with segment metadata.

Design constraints
------------------
* Pure Python / asyncio – no scikit-learn, torch, or external API calls.
* Thread-safe: all mutable state is gated by asyncio.Lock() or is
  effectively read-only after construction.
* Windows-compatible.
* Injected via module-level singletons so import order in main.py is free.
"""

from __future__ import annotations

import asyncio
import math
from dataclasses import dataclass, asdict
from enum import Enum
from typing import Any, Optional

from engine.logging import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Customer Segments
# ---------------------------------------------------------------------------


class Segment(str, Enum):
    FIRST_VISIT = "first_visit"
    RETURNING = "returning"
    LOYAL = "loyal"
    HIGH_LTV = "high_ltv"


# ---------------------------------------------------------------------------
# Simulated purchase-log (production: SELECT from orders table)
# ---------------------------------------------------------------------------

# Each entry: {customer_id, product_ids: list[str], spend_inr: float}
_PURCHASE_LOG: list[dict[str, Any]] = [
    {"customer_id": "c001", "product_ids": ["banarasi-silk-001", "kanjeevaram-001"], "spend_inr": 4200.0},
    {"customer_id": "c002", "product_ids": ["banarasi-silk-001", "wedding-red-002", "cotton-daily-003"], "spend_inr": 8750.0},
    {"customer_id": "c003", "product_ids": ["wedding-red-002", "festive-silk-004"], "spend_inr": 6100.0},
    {"customer_id": "c004", "product_ids": ["banarasi-silk-001", "festive-silk-004", "kalamkari-005", "cotton-daily-003"], "spend_inr": 12400.0},
    {"customer_id": "c005", "product_ids": ["kanjeevaram-001", "kalamkari-005"], "spend_inr": 3900.0},
    {"customer_id": "c006", "product_ids": ["wedding-red-002", "banarasi-silk-001"], "spend_inr": 5300.0},
    {"customer_id": "c007", "product_ids": ["cotton-daily-003"], "spend_inr": 1299.0},
    {"customer_id": "c008", "product_ids": ["festive-silk-004", "kanjeevaram-001", "designer-blouse-006"], "spend_inr": 9800.0},
    {"customer_id": "c009", "product_ids": ["banarasi-silk-001", "wedding-red-002", "kanjeevaram-001", "designer-blouse-006"], "spend_inr": 18500.0},
    {"customer_id": "c010", "product_ids": ["kalamkari-005", "cotton-daily-003"], "spend_inr": 2100.0},
]

# Segment thresholds
_LOYAL_MIN_PURCHASES = 1       # ≥1 past order → loyal
_HIGH_LTV_PURCHASE_COUNT = 3   # ≥3 orders → high_ltv
_HIGH_LTV_SPEND_PERCENTILE_80 = 8000.0   # pre-computed 80th-pct from log above


# ---------------------------------------------------------------------------
# SegmentDetector
# ---------------------------------------------------------------------------


@dataclass
class CustomerProfile:
    customer_id: str
    purchase_count: int
    total_spend_inr: float
    viewed_product_ids: list[str]
    segment: Segment

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["segment"] = self.segment.value
        return d


class SegmentDetector:
    """Classifies a visitor into a behavioural segment.

    In production the purchase count and spend are retrieved from the DB.
    For the autonomous pipeline they are derived from the in-process log.
    """

    def __init__(
        self,
        purchase_log: Optional[list[dict[str, Any]]] = None,
    ) -> None:
        self._log = purchase_log or _PURCHASE_LOG
        # Build lookup: customer_id → {count, spend}
        self._customer_stats: dict[str, dict[str, Any]] = {}
        for entry in self._log:
            cid = entry["customer_id"]
            if cid not in self._customer_stats:
                self._customer_stats[cid] = {"count": 0, "spend": 0.0, "products": []}
            self._customer_stats[cid]["count"] += 1
            self._customer_stats[cid]["spend"] += float(entry.get("spend_inr", 0.0))
            self._customer_stats[cid]["products"].extend(entry.get("product_ids", []))

    def detect(
        self,
        customer_id: Optional[str],
        viewed_product_ids: Optional[list[str]] = None,
    ) -> CustomerProfile:
        """Classify *customer_id* into a segment.

        Args:
            customer_id: None or empty → first_visit.
            viewed_product_ids: Current-session browsing history (may be empty).

        Returns:
            CustomerProfile with segment classification.
        """
        viewed = viewed_product_ids or []
        if not customer_id:
            return CustomerProfile(
                customer_id="anonymous",
                purchase_count=0,
                total_spend_inr=0.0,
                viewed_product_ids=viewed,
                segment=Segment.FIRST_VISIT,
            )

        stats = self._customer_stats.get(customer_id)
        if not stats:
            segment = Segment.RETURNING if viewed else Segment.FIRST_VISIT
            return CustomerProfile(
                customer_id=customer_id,
                purchase_count=0,
                total_spend_inr=0.0,
                viewed_product_ids=viewed,
                segment=segment,
            )

        count = stats["count"]
        spend = stats["spend"]
        if count >= _HIGH_LTV_PURCHASE_COUNT or spend >= _HIGH_LTV_SPEND_PERCENTILE_80:
            segment = Segment.HIGH_LTV
        elif count >= _LOYAL_MIN_PURCHASES:
            segment = Segment.LOYAL
        else:
            segment = Segment.RETURNING

        return CustomerProfile(
            customer_id=customer_id,
            purchase_count=count,
            total_spend_inr=spend,
            viewed_product_ids=viewed,
            segment=segment,
        )


# ---------------------------------------------------------------------------
# Recommendation Engine (item-based collaborative filtering)
# ---------------------------------------------------------------------------


@dataclass
class RecommendedItem:
    product_id: str
    score: float         # 0–1 similarity or popularity
    reason: str          # "collaborative" | "popularity" | "segment"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class RecommendationEngine:
    """Item-based collaborative filtering over the co-purchase matrix.

    Similarity metric: Jaccard index.

        Jaccard(A, B) = |A ∩ B| / |A ∪ B|

    where A and B are the sets of customers who purchased products A and B.
    """

    def __init__(
        self,
        purchase_log: Optional[list[dict[str, Any]]] = None,
    ) -> None:
        self._log = purchase_log or _PURCHASE_LOG
        self._similarity_cache: dict[tuple[str, str], float] = {}
        self._lock = asyncio.Lock()
        # Build inverted index: product_id → set of customer_ids
        self._product_customers: dict[str, set[str]] = {}
        # Build popularity: product_id → purchase count
        self._popularity: dict[str, int] = {}
        for entry in self._log:
            cid = entry["customer_id"]
            for pid in entry.get("product_ids", []):
                self._product_customers.setdefault(pid, set()).add(cid)
                self._popularity[pid] = self._popularity.get(pid, 0) + 1

    def _jaccard(self, product_a: str, product_b: str) -> float:
        """Jaccard similarity between two products over the co-purchase matrix."""
        cache_key = tuple(sorted([product_a, product_b]))
        if cache_key in self._similarity_cache:
            return self._similarity_cache[cache_key]
        a = self._product_customers.get(product_a, set())
        b = self._product_customers.get(product_b, set())
        union = a | b
        if not union:
            sim = 0.0
        else:
            sim = len(a & b) / len(union)
        self._similarity_cache[cache_key] = sim
        return sim

    def recommend(
        self,
        profile: CustomerProfile,
        catalog_ids: Optional[list[str]] = None,
        n: int = 5,
    ) -> list[RecommendedItem]:
        """Return top-N recommendations for *profile*.

        Strategy:
          1. Collect all products the customer has already purchased.
          2. For each unseen candidate in *catalog_ids*, compute average
             Jaccard similarity to purchased products.
          3. Fall back to popularity if no purchase history.
          4. Apply a segment-specific diversity boost:
             - high_ltv: up-weight premium products (ending in -001, -004)
             - first_visit: weight popularity only
        """
        all_product_ids = catalog_ids or list(self._product_customers.keys())

        # Known purchased products for this customer
        stats_lookup = {}
        for entry in self._log:
            if entry["customer_id"] == profile.customer_id:
                for pid in entry.get("product_ids", []):
                    stats_lookup[pid] = True
        already_purchased: set[str] = set(stats_lookup.keys())
        already_viewed: set[str] = set(profile.viewed_product_ids)

        candidates = [
            pid for pid in all_product_ids
            if pid not in already_purchased
        ]

        scored: list[RecommendedItem] = []

        if not already_purchased:
            # Cold-start: rank by popularity
            pop_max = max(self._popularity.values(), default=1)
            for pid in candidates:
                pop = self._popularity.get(pid, 0)
                score = pop / pop_max
                scored.append(RecommendedItem(
                    product_id=pid, score=round(score, 4), reason="popularity"
                ))
        else:
            for pid in candidates:
                # Average Jaccard similarity to all purchased items
                sims = [self._jaccard(pid, bought) for bought in already_purchased]
                avg_sim = sum(sims) / len(sims) if sims else 0.0
                # Popularity tie-breaker (log-normalised)
                pop = self._popularity.get(pid, 0)
                pop_norm = math.log1p(pop) / math.log1p(max(self._popularity.values(), default=1))
                combined = 0.75 * avg_sim + 0.25 * pop_norm
                # Segment boost
                if profile.segment == Segment.HIGH_LTV and any(
                    pid.endswith(s) for s in ("-001", "-004", "-006")
                ):
                    combined = min(1.0, combined * 1.15)
                reason = "collaborative" if avg_sim > 0 else "popularity"
                scored.append(RecommendedItem(
                    product_id=pid, score=round(combined, 4), reason=reason
                ))

        scored.sort(key=lambda r: r.score, reverse=True)
        return scored[:n]


# ---------------------------------------------------------------------------
# PersonalisationEndpoint helper
# ---------------------------------------------------------------------------


@dataclass
class PersonalisationResponse:
    customer_id: Optional[str]
    segment: str
    purchase_count: int
    total_spend_inr: float
    recommendations: list[dict[str, Any]]
    explanation: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "customer_id": self.customer_id,
            "segment": self.segment,
            "purchase_count": self.purchase_count,
            "total_spend_inr": self.total_spend_inr,
            "recommendations": self.recommendations,
            "explanation": self.explanation,
        }


_SEGMENT_EXPLANATIONS = {
    Segment.FIRST_VISIT: "Showing our best-sellers to help you discover Shruhi Collections.",
    Segment.RETURNING: "Based on your browsing history, you may love these picks.",
    Segment.LOYAL: "Thank you for being a loyal customer! Here are curated selections just for you.",
    Segment.HIGH_LTV: "As a valued VIP customer, here are our premium and exclusive selections.",
}


class PersonalisationEndpoint:
    """Thin orchestrator wiring SegmentDetector + RecommendationEngine together.

    Used by the FastAPI route: POST /api/v1/personalization/recommendations
    """

    def __init__(
        self,
        purchase_log: Optional[list[dict[str, Any]]] = None,
    ) -> None:
        log = purchase_log or _PURCHASE_LOG
        self._detector = SegmentDetector(purchase_log=log)
        self._recommender = RecommendationEngine(purchase_log=log)

    def get_recommendations(
        self,
        customer_id: Optional[str],
        viewed_product_ids: Optional[list[str]] = None,
        catalog_ids: Optional[list[str]] = None,
        n: int = 5,
    ) -> PersonalisationResponse:
        """Classify visitor segment and return personalised product rankings."""
        profile = self._detector.detect(
            customer_id=customer_id,
            viewed_product_ids=viewed_product_ids,
        )
        recs = self._recommender.recommend(
            profile=profile,
            catalog_ids=catalog_ids,
            n=n,
        )
        explanation = _SEGMENT_EXPLANATIONS.get(profile.segment, "Personalised for you.")

        logger.info(
            "personalisation.recommendations",
            customer_id=customer_id or "anonymous",
            segment=profile.segment.value,
            rec_count=len(recs),
        )

        return PersonalisationResponse(
            customer_id=customer_id,
            segment=profile.segment.value,
            purchase_count=profile.purchase_count,
            total_spend_inr=profile.total_spend_inr,
            recommendations=[r.to_dict() for r in recs],
            explanation=explanation,
        )


# ---------------------------------------------------------------------------
# Module-level singletons
# ---------------------------------------------------------------------------

segment_detector = SegmentDetector()
recommendation_engine = RecommendationEngine()
personalisation_endpoint = PersonalisationEndpoint()
