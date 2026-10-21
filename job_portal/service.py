"""
Job Placement Ecosystem: Subscription & Marketplace Service
Manages the $1/month worker subscriptions, employer vacancy postings, and the matching pipeline.
Zero external dependencies - operates on local JSON persistence for zero-cost operation.
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .models import (
    EmploymentType,
    JobMatch,
    JobPosting,
    SubscriptionStatus,
    WorkerProfile,
)
from .matching_engine import JobMatchingEngine


SUBSCRIPTION_FEE_USD = 1.00


class MarketplaceService:
    """Core service orchestrating the dual-sided job placement marketplace."""

    def __init__(self, data_dir: str = ".algorise/marketplace"):
        self.data_dir = data_dir
        os.makedirs(self.data_dir, exist_ok=True)
        self.vacancies_path = os.path.join(self.data_dir, "vacancies.json")
        self.workers_path = os.path.join(self.data_dir, "workers.json")
        self.matches_path = os.path.join(self.data_dir, "matches.json")
        self.matcher = JobMatchingEngine()

    # -- Persistence helpers ------------------------------------------------
    def _load(self, path: str) -> List[Dict[str, Any]]:
        if not os.path.exists(path):
            return []
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _save(self, path: str, data: List[Dict[str, Any]]) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    # -- Employer side ------------------------------------------------------
    def post_vacancy(
        self,
        employer_id: str,
        title: str,
        description: str,
        required_skills: List[str],
        employment_type: EmploymentType = EmploymentType.FULL_TIME,
        salary_range_usd: Optional[str] = None,
        sponsored: bool = False,
    ) -> JobPosting:
        """Registers a new vacancy from a verified employer tenant."""
        vacancy = JobPosting(
            vacancy_id=f"vac_{uuid.uuid4().hex[:10]}",
            employer_id=employer_id,
            title=title,
            description=description,
            required_skills=required_skills,
            employment_type=employment_type,
            salary_range_usd=salary_range_usd,
            sponsored=sponsored,
        )
        vacancies = self._load(self.vacancies_path)
        vacancies.append(vacancy.model_dump())
        self._save(self.vacancies_path, vacancies)
        return vacancy

    def list_vacancies(self, active_only: bool = True) -> List[JobPosting]:
        vacancies = self._load(self.vacancies_path)
        result = [JobPosting(**v) for v in vacancies]
        if active_only:
            result = [v for v in result if v.active]
        return result

    # -- Worker side -------------------------------------------------------
    def register_worker(
        self,
        worker_id: str,
        github_handle: str,
        skills: List[str],
        verified_benchmark_score: float = 0.0,
    ) -> WorkerProfile:
        """Registers a worker profile and activates their $1/month subscription."""
        worker = WorkerProfile(
            worker_id=worker_id,
            github_handle=github_handle,
            skills=skills,
            verified_benchmark_score=verified_benchmark_score,
            subscription_status=SubscriptionStatus.ACTIVE,
            subscription_fee_usd=SUBSCRIPTION_FEE_USD,
        )
        workers = self._load(self.workers_path)
        workers = [w for w in workers if w.get("worker_id") != worker_id]
        workers.append(worker.model_dump())
        self._save(self.workers_path, workers)
        return worker

    def renew_subscription(self, worker_id: str) -> WorkerProfile:
        """Processes the nominal $1/month renewal."""
        workers = self._load(self.workers_path)
        for w in workers:
            if w["worker_id"] == worker_id:
                w["subscription_status"] = SubscriptionStatus.ACTIVE.value
                w["last_billing_date"] = datetime.now(timezone.utc).isoformat()
                self._save(self.workers_path, workers)
                return WorkerProfile(**w)
        raise KeyError(f"Worker {worker_id} not found")

    def cancel_subscription(self, worker_id: str) -> WorkerProfile:
        """Cancels the subscription (worker loses premium matching access)."""
        workers = self._load(self.workers_path)
        for w in workers:
            if w["worker_id"] == worker_id:
                w["subscription_status"] = SubscriptionStatus.CANCELED.value
                self._save(self.workers_path, workers)
                return WorkerProfile(**w)
        raise KeyError(f"Worker {worker_id} not found")

    def list_workers(self, active_only: bool = False) -> List[WorkerProfile]:
        workers = [WorkerProfile(**w) for w in self._load(self.workers_path)]
        if active_only:
            workers = [w for w in workers if w.subscription_status == SubscriptionStatus.ACTIVE]
        return workers

    # -- Matching pipeline --------------------------------------------------
    def match_vacancy(self, vacancy_id: str, top_n: int = 5) -> List[JobMatch]:
        """Runs the AI matching pipeline for a vacancy against all active subscribers."""
        vacancies = self._load(self.vacancies_path)
        vacancy = next((JobPosting(**v) for v in vacancies if v["vacancy_id"] == vacancy_id), None)
        if vacancy is None:
            raise KeyError(f"Vacancy {vacancy_id} not found")

        workers = self.list_workers(active_only=True)
        matches = self.matcher.find_best_matches(vacancy, workers, top_n=top_n)

        stored = self._load(self.matches_path)
        stored.extend([m.model_dump() for m in matches])
        self._save(self.matches_path, stored)
        return matches

    def get_worker_matches(self, worker_id: str) -> List[JobMatch]:
        matches = self._load(self.matches_path)
        return [JobMatch(**m) for m in matches if m["worker_id"] == worker_id]

    # -- Unit economics -----------------------------------------------------
    def revenue_report(self) -> Dict[str, Any]:
        """Computes the MRR and margin metrics for the $1/month subscription model."""
        workers = self.list_workers()
        active = [w for w in workers if w.subscription_status == SubscriptionStatus.ACTIVE]
        mrr = sum(w.subscription_fee_usd for w in active)
        # Estimated marginal infrastructure cost per active subscriber
        marginal_cost_per_user = 0.08
        total_cost = marginal_cost_per_user * len(active)
        gross_margin = (mrr - total_cost) / mrr if mrr > 0 else 0.0
        return {
            "total_workers": len(workers),
            "active_subscribers": len(active),
            "mrr_usd": round(mrr, 2),
            "arr_run_rate_usd": round(mrr * 12, 2),
            "marginal_cost_usd": round(total_cost, 2),
            "gross_margin_pct": round(gross_margin * 100, 1),
        }
