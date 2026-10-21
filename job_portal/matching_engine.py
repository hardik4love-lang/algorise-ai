"""
Job Placement Ecosystem: AI Matching Engine
Correlates employer vacancy requirements with verified worker profiles and AST benchmark metrics.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from .models import JobPosting, WorkerProfile, JobMatch
import uuid


class JobMatchingEngine:
    """Calculates compatibility scores between job vacancies and platform workers."""

    def __init__(self):
        pass

    def calculate_match(self, vacancy: JobPosting, worker: WorkerProfile) -> JobMatch:
        """Computes a weighted match score based on skill overlap and benchmark performance."""
        vacancy_skills = {s.lower() for s in vacancy.required_skills}
        worker_skills = {s.lower() for s in worker.skills}

        if not vacancy_skills:
            skill_overlap_ratio = 1.0
            matched_skills = []
        else:
            intersection = vacancy_skills.intersection(worker_skills)
            skill_overlap_ratio = len(intersection) / len(vacancy_skills)
            matched_skills = list(intersection)

        # Benchmark weight factor (0.0 to 1.0)
        benchmark_factor = min(1.0, max(0.0, worker.verified_benchmark_score / 100.0))

        # Final composite score (70% skill overlap, 30% benchmark verification)
        composite_score = round((skill_overlap_ratio * 0.7) + (benchmark_factor * 0.3), 4)

        return JobMatch(
            match_id=f"match_{uuid.uuid4().hex[:8]}",
            vacancy_id=vacancy.vacancy_id,
            worker_id=worker.worker_id,
            match_score=composite_score,
            matched_skills=matched_skills,
            status="suggested",
        )

    def find_best_matches(
        self,
        vacancy: JobPosting,
        workers: List[WorkerProfile],
        top_n: int = 5,
        min_match_score: float = 0.35,
    ) -> List[JobMatch]:
        """Finds top N best matching workers for a specific vacancy.

        Only active subscribers are considered. Matches below ``min_match_score``
        are discarded so that employers are not shown irrelevant candidates.
        """
        eligible_workers = [w for w in workers if w.subscription_status.value == "active"]
        matches = [
            self.calculate_match(vacancy, w)
            for w in eligible_workers
            if self.calculate_match(vacancy, w).match_score >= min_match_score
        ]
        # Sort by match score descending
        matches.sort(key=lambda m: m.match_score, reverse=True)
        return matches[:top_n]
