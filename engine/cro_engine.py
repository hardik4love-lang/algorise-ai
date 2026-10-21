"""
Algorise Autonomous eCommerce CRO Engine (Phase 3 & 4 Autonomous Framework)
Orchestrates autonomous A/B conversion rate experiments, statistical significance testing,
and automated variant promotion/reversion for shruhi-collections storefront.
Learnings are persisted into Agent Semantic Memory for cross-session optimization.
"""

from __future__ import annotations

import json
import math
import os
import sqlite3
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from threading import Lock
from typing import Any, Dict, List, Optional, Tuple

from engine.logging import get_logger
from engine.memory import agent_memory, MemoryType

logger = get_logger(__name__)


class ExperimentStatus(str, Enum):
    DRAFT = "DRAFT"
    RUNNING = "RUNNING"
    CONCLUDED_PROMOTED = "CONCLUDED_PROMOTED"
    CONCLUDED_REVERTED = "CONCLUDED_REVERTED"


@dataclass
class VariantStats:
    variant_id: str
    name: str
    description: str
    impressions: int = 0
    conversions: int = 0
    revenue_inr: float = 0.0

    @property
    def conversion_rate(self) -> float:
        return (self.conversions / self.impressions) if self.impressions > 0 else 0.0

    @property
    def aov_inr(self) -> float:
        return (self.revenue_inr / self.conversions) if self.conversions > 0 else 0.0


@dataclass
class CROExperiment:
    experiment_id: str
    client_id: str
    hypothesis: str
    target_page: str
    target_metric: str  # e.g., "cart_addition", "upi_checkout_click", "whatsapp_inquiry"
    control: VariantStats
    variant: VariantStats
    status: ExperimentStatus = ExperimentStatus.RUNNING
    min_sample_size: int = 100
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    concluded_at: Optional[str] = None
    winning_variant_id: Optional[str] = None
    relative_lift_pct: float = 0.0
    p_value: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["status"] = self.status.value
        return d


def _calculate_two_proportion_z_test(
    count_a: int, total_a: int, count_b: int, total_b: int
) -> Tuple[float, float]:
    """
    Computes two-proportion z-statistic and two-tailed p-value.
    Returns (z_stat, p_value).
    """
    if total_a < 10 or total_b < 10:
        return (0.0, 1.0)

    p1 = count_a / total_a
    p2 = count_b / total_b
    pooled_p = (count_a + count_b) / (total_a + total_b)

    if pooled_p == 0.0 or pooled_p == 1.0:
        return (0.0, 1.0)

    se = math.sqrt(pooled_p * (1.0 - pooled_p) * ((1.0 / total_a) + (1.0 / total_b)))
    if se == 0.0:
        return (0.0, 1.0)

    z = (p2 - p1) / se

    # Normal CDF approximation for two-tailed p-value
    # Erf based standard normal cumulative distribution
    p_val = 2.0 * (1.0 - 0.5 * (1.0 + math.erf(abs(z) / math.sqrt(2.0))))
    return (round(z, 4), round(max(0.0, min(1.0, p_val)), 4))


_CRO_DB_PATH = os.getenv(
    "CRO_EXPERIMENT_DB_PATH",
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "cro_experiments.db")),
)


class AutonomousCROEngine:
    """
    Autonomous Conversion Rate Optimization engine for eCommerce growth.
    """

    def __init__(self, db_path: str = _CRO_DB_PATH):
        self.db_path = os.path.abspath(db_path)
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._lock = Lock()
        self._init_db()

    def _init_db(self) -> None:
        with self._lock:
            with sqlite3.connect(self.db_path, timeout=10) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS cro_experiments (
                        experiment_id TEXT PRIMARY KEY,
                        client_id TEXT NOT NULL,
                        target_page TEXT NOT NULL,
                        hypothesis TEXT NOT NULL,
                        target_metric TEXT NOT NULL,
                        control_json TEXT NOT NULL,
                        variant_json TEXT NOT NULL,
                        status TEXT NOT NULL,
                        min_sample_size INTEGER NOT NULL,
                        relative_lift_pct REAL NOT NULL,
                        p_value REAL NOT NULL,
                        winning_variant_id TEXT,
                        created_at TEXT NOT NULL,
                        concluded_at TEXT
                    );
                """)
                conn.commit()

    def create_experiment(
        self,
        client_id: str,
        hypothesis: str,
        target_page: str,
        target_metric: str,
        control_name: str,
        control_desc: str,
        variant_name: str,
        variant_desc: str,
        min_sample_size: int = 100,
    ) -> CROExperiment:
        exp_id = f"exp_{uuid.uuid4().hex[:10]}"
        exp = CROExperiment(
            experiment_id=exp_id,
            client_id=client_id,
            hypothesis=hypothesis,
            target_page=target_page,
            target_metric=target_metric,
            control=VariantStats(variant_id="control", name=control_name, description=control_desc),
            variant=VariantStats(variant_id="variant_b", name=variant_name, description=variant_desc),
            min_sample_size=min_sample_size,
        )
        self._save(exp)
        logger.info(
            "cro_experiment_created",
            experiment_id=exp.experiment_id,
            target_page=target_page,
            hypothesis=hypothesis,
        )
        return exp

    def record_event(
        self,
        experiment_id: str,
        variant_id: str,
        event_type: str,  # "impression" or "conversion"
        revenue_inr: float = 0.0,
    ) -> Optional[CROExperiment]:
        exp = self.get_experiment(experiment_id)
        if not exp or exp.status != ExperimentStatus.RUNNING:
            return None

        target = exp.control if variant_id == "control" else exp.variant
        if event_type == "impression":
            target.impressions += 1
        elif event_type == "conversion":
            target.conversions += 1
            target.revenue_inr += revenue_inr

        # Re-evaluate statistical significance
        self._evaluate_significance(exp)
        self._save(exp)
        return exp

    def _evaluate_significance(self, exp: CROExperiment) -> None:
        total_sample = exp.control.impressions + exp.variant.impressions
        if total_sample < exp.min_sample_size:
            return

        cr_control = exp.control.conversion_rate
        cr_variant = exp.variant.conversion_rate

        if cr_control > 0:
            exp.relative_lift_pct = round(((cr_variant - cr_control) / cr_control) * 100, 2)
        else:
            exp.relative_lift_pct = 0.0

        _, p_val = _calculate_two_proportion_z_test(
            exp.control.conversions, exp.control.impressions,
            exp.variant.conversions, exp.variant.impressions,
        )
        exp.p_value = p_val

        # Auto-decision gates
        # Positive winning variant: p < 0.05 and lift >= +5%
        if exp.p_value <= 0.05 and exp.relative_lift_pct >= 5.0 and exp.variant.impressions >= exp.min_sample_size // 2:
            exp.status = ExperimentStatus.CONCLUDED_PROMOTED
            exp.winning_variant_id = exp.variant.variant_id
            exp.concluded_at = datetime.now(timezone.utc).isoformat()
            logger.info(
                "cro_experiment_promoted_winner",
                experiment_id=exp.experiment_id,
                lift_pct=exp.relative_lift_pct,
                p_value=exp.p_value,
            )
            # Store in semantic memory for compounding learning
            agent_memory.store(
                memory_type=MemoryType.SEMANTIC,
                client_id=exp.client_id,
                topic=f"CRO_WINNER_{exp.target_page}",
                content=(
                    f"A/B Experiment on {exp.target_page} won with +{exp.relative_lift_pct}% lift (p={exp.p_value}). "
                    f"Winning pattern: '{exp.variant.name}' ({exp.variant.description}) outperformed '{exp.control.name}'. "
                    f"Target metric: {exp.target_metric}."
                ),
                metadata=exp.to_dict(),
                confidence_score=0.95,
            )

        # Negative failing variant: p < 0.05 and lift <= -5%
        elif exp.p_value <= 0.05 and exp.relative_lift_pct <= -5.0 and exp.variant.impressions >= exp.min_sample_size // 2:
            exp.status = ExperimentStatus.CONCLUDED_REVERTED
            exp.winning_variant_id = exp.control.variant_id
            exp.concluded_at = datetime.now(timezone.utc).isoformat()
            logger.warning(
                "cro_experiment_reverted_underperformer",
                experiment_id=exp.experiment_id,
                lift_pct=exp.relative_lift_pct,
                p_value=exp.p_value,
            )
            # Store in semantic memory to prevent recurring mistakes
            agent_memory.store(
                memory_type=MemoryType.SEMANTIC,
                client_id=exp.client_id,
                topic=f"CRO_REVERT_{exp.target_page}",
                content=(
                    f"A/B Experiment on {exp.target_page} failed with {exp.relative_lift_pct}% drop (p={exp.p_value}). "
                    f"Rejected pattern: '{exp.variant.name}' ({exp.variant.description}). Kept control."
                ),
                metadata=exp.to_dict(),
                confidence_score=0.90,
            )

    def _save(self, exp: CROExperiment) -> None:
        with self._lock:
            with sqlite3.connect(self.db_path, timeout=10) as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO cro_experiments
                    (experiment_id, client_id, target_page, hypothesis, target_metric, control_json, variant_json, status, min_sample_size, relative_lift_pct, p_value, winning_variant_id, created_at, concluded_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        exp.experiment_id,
                        exp.client_id,
                        exp.target_page,
                        exp.hypothesis,
                        exp.target_metric,
                        json.dumps(asdict(exp.control)),
                        json.dumps(asdict(exp.variant)),
                        exp.status.value,
                        exp.min_sample_size,
                        exp.relative_lift_pct,
                        exp.p_value,
                        exp.winning_variant_id,
                        exp.created_at,
                        exp.concluded_at,
                    ),
                )
                conn.commit()

    def get_experiment(self, experiment_id: str) -> Optional[CROExperiment]:
        with self._lock:
            with sqlite3.connect(self.db_path, timeout=10) as conn:
                conn.row_factory = sqlite3.Row
                r = conn.execute("SELECT * FROM cro_experiments WHERE experiment_id = ?", (experiment_id,)).fetchone()
                if not r:
                    return None
                return CROExperiment(
                    experiment_id=r["experiment_id"],
                    client_id=r["client_id"],
                    target_page=r["target_page"],
                    hypothesis=r["hypothesis"],
                    target_metric=r["target_metric"],
                    control=VariantStats(**json.loads(r["control_json"])),
                    variant=VariantStats(**json.loads(r["variant_json"])),
                    status=ExperimentStatus(r["status"]),
                    min_sample_size=r["min_sample_size"],
                    relative_lift_pct=r["relative_lift_pct"],
                    p_value=r["p_value"],
                    winning_variant_id=r["winning_variant_id"],
                    created_at=r["created_at"],
                    concluded_at=r["concluded_at"],
                )

    def list_experiments(self, client_id: Optional[str] = None) -> List[Dict[str, Any]]:
        query = "SELECT * FROM cro_experiments"
        params = ()
        if client_id:
            query += " WHERE client_id = ?"
            params = (client_id,)
        query += " ORDER BY created_at DESC"

        with self._lock:
            with sqlite3.connect(self.db_path, timeout=10) as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute(query, params).fetchall()
                out = []
                for r in rows:
                    exp = CROExperiment(
                        experiment_id=r["experiment_id"],
                        client_id=r["client_id"],
                        target_page=r["target_page"],
                        hypothesis=r["hypothesis"],
                        target_metric=r["target_metric"],
                        control=VariantStats(**json.loads(r["control_json"])),
                        variant=VariantStats(**json.loads(r["variant_json"])),
                        status=ExperimentStatus(r["status"]),
                        min_sample_size=r["min_sample_size"],
                        relative_lift_pct=r["relative_lift_pct"],
                        p_value=r["p_value"],
                        winning_variant_id=r["winning_variant_id"],
                        created_at=r["created_at"],
                        concluded_at=r["concluded_at"],
                    )
                    out.append(exp.to_dict())
                return out


# Global singleton
cro_engine = AutonomousCROEngine()
