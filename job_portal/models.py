"""
Job Placement Ecosystem: Data Models
Defines schemas for employer vacancies, worker profiles, $1/month subscriptions, and AI matching.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class EmploymentType(str, Enum):
    FULL_TIME = "full_time"
    CONTRACT = "contract"
    OPEN_SOURCE_BOUNTY = "open_source_bounty"


class SubscriptionStatus(str, Enum):
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    TRIAL = "trial"


class JobPosting(BaseModel):
    vacancy_id: str = Field(..., description="Unique vacancy identifier")
    employer_id: str = Field(..., description="Enterprise employer tenant ID")
    title: str = Field(..., description="Job title, e.g. Senior DevEx Engineer")
    description: str = Field(..., description="Role description and requirements")
    required_skills: List[str] = Field(default_factory=list, description="Required technical skills/AST proficiencies")
    employment_type: EmploymentType = Field(EmploymentType.FULL_TIME)
    salary_range_usd: Optional[str] = Field(None, description="Compensation range")
    sponsored: bool = Field(False, description="Whether this is a premium sponsored listing")
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    active: bool = Field(True)


class WorkerProfile(BaseModel):
    worker_id: str = Field(..., description="Unique developer/worker ID")
    github_handle: str = Field(..., description="GitHub username")
    skills: List[str] = Field(default_factory=list, description="Verified skill set")
    verified_benchmark_score: float = Field(0.0, ge=0.0, le=100.0, description="Algorise test suite score")
    subscription_status: SubscriptionStatus = Field(SubscriptionStatus.ACTIVE)
    subscription_fee_usd: float = Field(1.00, description="Nominal monthly subscription fee ($1/mo)")
    last_billing_date: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class JobMatch(BaseModel):
    match_id: str = Field(..., description="Unique match identifier")
    vacancy_id: str
    worker_id: str
    match_score: float = Field(..., ge=0.0, le=1.0, description="AI-calculated match percentage")
    matched_skills: List[str] = Field(default_factory=list)
    status: str = Field("suggested", description="suggested, contacted, interviewed, hired")
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
