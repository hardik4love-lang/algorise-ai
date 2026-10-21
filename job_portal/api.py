"""
Job Placement Ecosystem: HTTP API
FastAPI router exposing employer vacancy posting, worker subscription, and AI matching endpoints.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field

from .models import EmploymentType, JobPosting, SubscriptionStatus, WorkerProfile
from .service import MarketplaceService, SUBSCRIPTION_FEE_USD

router = APIRouter(prefix="/v1/marketplace", tags=["Marketplace"])

_service = MarketplaceService()


def get_service() -> MarketplaceService:
    return _service


class VacancyCreate(BaseModel):
    title: str
    description: str
    required_skills: List[str] = Field(default_factory=list)
    employment_type: EmploymentType = EmploymentType.FULL_TIME
    salary_range_usd: Optional[str] = None
    sponsored: bool = False


class WorkerCreate(BaseModel):
    worker_id: str
    github_handle: str
    skills: List[str] = Field(default_factory=list)
    verified_benchmark_score: float = 0.0


@router.get("/health")
def marketplace_health() -> Dict[str, Any]:
    """Public health check for the marketplace subsystem."""
    return {
        "status": "healthy",
        "service": "algorise-marketplace",
        "subscription_fee_usd": SUBSCRIPTION_FEE_USD,
        "timestamp": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
    }


@router.get("/metrics")
def marketplace_metrics(service: MarketplaceService = Depends(get_service)) -> Dict[str, Any]:
    """Returns MRR and unit economics metrics."""
    return service.revenue_report()


@router.post("/vacancies", status_code=status.HTTP_201_CREATED)
def create_vacancy(
    payload: VacancyCreate,
    x_employer_id: str = Header(..., alias="X-Employer-ID"),
    service: MarketplaceService = Depends(get_service),
) -> Dict[str, Any]:
    """Employer posts a vacancy (requires verified employer tenant ID)."""
    vacancy = service.post_vacancy(
        employer_id=x_employer_id,
        title=payload.title,
        description=payload.description,
        required_skills=payload.required_skills,
        employment_type=payload.employment_type,
        salary_range_usd=payload.salary_range_usd,
        sponsored=payload.sponsored,
    )
    return vacancy.model_dump()


@router.get("/vacancies")
def list_vacancies(
    active_only: bool = True,
    service: MarketplaceService = Depends(get_service),
) -> Dict[str, Any]:
    """Lists all active job vacancies."""
    vacancies = service.list_vacancies(active_only=active_only)
    return {"total": len(vacancies), "vacancies": [v.model_dump() for v in vacancies]}


@router.post("/workers", status_code=status.HTTP_201_CREATED)
def register_worker(
    payload: WorkerCreate,
    service: MarketplaceService = Depends(get_service),
) -> Dict[str, Any]:
    """Registers a worker and activates their $1/month subscription."""
    worker = service.register_worker(
        worker_id=payload.worker_id,
        github_handle=payload.github_handle,
        skills=payload.skills,
        verified_benchmark_score=payload.verified_benchmark_score,
    )
    return worker.model_dump()


@router.post("/workers/{worker_id}/renew")
def renew_subscription(
    worker_id: str,
    service: MarketplaceService = Depends(get_service),
) -> Dict[str, Any]:
    """Processes the nominal $1/month renewal."""
    try:
        worker = service.renew_subscription(worker_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Worker {worker_id} not found")
    return worker.model_dump()


@router.post("/workers/{worker_id}/cancel")
def cancel_subscription(
    worker_id: str,
    service: MarketplaceService = Depends(get_service),
) -> Dict[str, Any]:
    """Cancels a worker's subscription."""
    try:
        worker = service.cancel_subscription(worker_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Worker {worker_id} not found")
    return worker.model_dump()


@router.get("/workers")
def list_workers(
    active_only: bool = False,
    service: MarketplaceService = Depends(get_service),
) -> Dict[str, Any]:
    """Lists registered workers."""
    workers = service.list_workers(active_only=active_only)
    return {"total": len(workers), "workers": [w.model_dump() for w in workers]}


@router.post("/vacancies/{vacancy_id}/match")
def match_vacancy(
    vacancy_id: str,
    top_n: int = 5,
    service: MarketplaceService = Depends(get_service),
) -> Dict[str, Any]:
    """Runs the AI matching pipeline and returns top N worker matches."""
    try:
        matches = service.match_vacancy(vacancy_id, top_n=top_n)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Vacancy {vacancy_id} not found")
    return {"vacancy_id": vacancy_id, "matches": [m.model_dump() for m in matches]}


@router.get("/workers/{worker_id}/matches")
def worker_matches(
    worker_id: str,
    service: MarketplaceService = Depends(get_service),
) -> Dict[str, Any]:
    """Returns all job matches for a specific worker."""
    matches = service.get_worker_matches(worker_id)
    return {"worker_id": worker_id, "matches": [m.model_dump() for m in matches]}
