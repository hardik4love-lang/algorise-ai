"""
Algorise DevEx Platform: Commercial Metering Gateway API (TECH-203, TECH-301, TECH-302)
Provides multi-tenant REST endpoints for centralized flaky test quarantine,
AST blast radius telemetry, role-based access control (RBAC), and autonomous incident healing mesh.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from autotest_sentinel.models import (
    FlakeCategory,
    FlakinessReport,
    RootCauseHypothesis,
)
from autotest_sentinel.quarantine import QuarantineManager
from context_pr.blast_radius import BlastRadiusAnalyzer

# ---------------------------------------------------------------------------
# Multi-Tenant Auth, Scopes & RBAC Registry (TECH-301)
# ---------------------------------------------------------------------------

ALL_SCOPES = [
    "quarantine:read",
    "quarantine:write",
    "blast_radius:read",
    "incident:heal",
    "usage:read",
    "admin:*",
]

TENANT_REGISTRY: Dict[str, Dict[str, Any]] = {
    "alg_live_test_key_9981": {
        "client": "Acme Corp",
        "tier": "Enterprise Tier",
        "role": "admin",
        "scopes": ALL_SCOPES,
        "quota": 50000,
        "requests_used": 0,
    },
    "alg_demo_client_key_001": {
        "client": "Starlight Labs",
        "tier": "Growth Tier",
        "role": "developer",
        "scopes": ["quarantine:read", "quarantine:write", "blast_radius:read", "usage:read"],
        "quota": 10000,
        "requests_used": 0,
    },
    "alg_readonly_key_002": {
        "client": "Observer Team",
        "tier": "Viewer Tier",
        "role": "viewer",
        "scopes": ["quarantine:read", "blast_radius:read", "usage:read"],
        "quota": 5000,
        "requests_used": 0,
    },
}

# Allow injecting custom API key via environment
_env_key = os.environ.get("ALGORISE_API_KEY")
if _env_key and _env_key not in TENANT_REGISTRY:
    TENANT_REGISTRY[_env_key] = {
        "client": "Environment Admin",
        "tier": "Enterprise Custom",
        "role": "admin",
        "scopes": ALL_SCOPES,
        "quota": 100000,
        "requests_used": 0,
    }


def authenticate_api_key(
    x_algorise_api_key: Optional[str] = Header(None, alias="X-Algorise-API-Key"),
    authorization: Optional[str] = Header(None, alias="Authorization"),
) -> Dict[str, Any]:
    """Validates API Key from X-Algorise-API-Key header or Bearer token."""
    key = x_algorise_api_key
    if not key and authorization:
        if authorization.lower().startswith("bearer "):
            key = authorization[7:].strip()
        else:
            key = authorization.strip()

    if not key or key not in TENANT_REGISTRY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized: Invalid or missing X-Algorise-API-Key header.",
        )

    tenant = TENANT_REGISTRY[key]
    tenant["requests_used"] += 1
    if tenant["requests_used"] > tenant["quota"]:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Usage quota exceeded for current billing cycle. Please upgrade your seat tier.",
        )
    return tenant


def require_scope(required_scope: str) -> Callable:
    """Enforces fine-grained permission scope check (RBAC) on endpoints."""
    def scope_checker(tenant: Dict[str, Any] = Depends(authenticate_api_key)) -> Dict[str, Any]:
        scopes = tenant.get("scopes", [])
        if "admin:*" in scopes or required_scope in scopes:
            return tenant
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Forbidden: Insufficient privileges. Required scope: '{required_scope}'.",
        )
    return scope_checker


# ---------------------------------------------------------------------------
# FastAPI Application & Request Models
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Algorise DevEx Commercial Metering Gateway",
    version="1.0.0",
    description="Enterprise API Gateway for AutoTest Sentinel, ContextPR, and Autonomous Healing Mesh.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def metering_headers_middleware(request: Request, call_next):
    response = await call_next(request)
    # Check if request has an authorized tenant key
    key = request.headers.get("x-algorise-api-key")
    if not key and request.headers.get("authorization"):
        auth = request.headers.get("authorization", "")
        if auth.lower().startswith("bearer "):
            key = auth[7:].strip()
        else:
            key = auth.strip()

    if key and key in TENANT_REGISTRY:
        tenant = TENANT_REGISTRY[key]
        response.headers["X-Algorise-Tenant"] = tenant["client"]
        response.headers["X-Algorise-Tier"] = tenant["tier"]
        response.headers["X-Algorise-Role"] = tenant.get("role", "developer")
        response.headers["X-Algorise-Requests-Used"] = str(tenant["requests_used"])
        response.headers["X-Algorise-Quota-Remaining"] = str(
            max(0, tenant["quota"] - tenant["requests_used"])
        )
    return response


class QuarantineAddRequest(BaseModel):
    test_id: str = Field(..., description="Unique pytest test node ID, e.g. tests/test_api.py::test_flaky")
    file_path: str = Field(..., description="Relative or absolute file path to the test")
    flakiness_score: float = Field(0.85, ge=0.0, le=1.0, description="Evaluated flakiness score")
    root_cause: str = Field("TIMING_RACE", description="Root cause hypothesis string")
    failure_rate: float = Field(0.30, ge=0.0, le=1.0, description="Historical failure frequency")
    reason: Optional[str] = Field(None, description="Human or automated reason for quarantine")
    ttl_days: int = Field(14, ge=1, le=90, description="Time-to-live before re-evaluating in days")


class BlastRadiusRequest(BaseModel):
    changed_files: List[str] = Field(..., description="List of modified file paths in the commit/PR")
    base_ref: Optional[str] = Field("master", description="Target base branch reference")
    head_ref: Optional[str] = Field("HEAD", description="Source head branch reference")
    root_dir: Optional[str] = Field(None, description="Root directory to analyze. Defaults to current directory.")


class IncidentHealRequest(BaseModel):
    incident_id: str = Field(..., description="Unique incident identifier, e.g. INC-901")
    service_name: str = Field("core-engine", description="Affected microservice name")
    error_type: str = Field(..., description="Exception type, e.g. KeyError, ZeroDivisionError, AttributeError")
    error_message: str = Field(..., description="Exception error message string")
    stack_trace: str = Field(..., description="Raw formatted Python exception traceback")
    root_dir: Optional[str] = Field(None, description="Repository root directory")
    auto_stage: bool = Field(False, description="Whether to apply and stage hotfix immediately")


# ---------------------------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------------------------

@app.get("/v1/health")
def health_check() -> Dict[str, Any]:
    """Public health-check endpoint for load balancers and orchestrators."""
    return {
        "status": "healthy",
        "service": "algorise-devex-gateway",
        "version": "1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "engines": {
            "autotest_sentinel": "OPERATIONAL",
            "context_pr": "OPERATIONAL",
            "modernize_ai": "OPERATIONAL",
            "trace_root_ai": "OPERATIONAL",
            "healing_mesh": "OPERATIONAL",
            "revenue_engine": "OPERATIONAL",
        },
    }


@app.get("/v1/usage")
def get_usage_metrics(tenant: Dict[str, Any] = Depends(require_scope("usage:read"))) -> Dict[str, Any]:
    """Returns seat consumption and rate limit quota for the authenticated tenant."""
    return {
        "client": tenant["client"],
        "tier": tenant["tier"],
        "role": tenant.get("role", "developer"),
        "scopes": tenant.get("scopes", []),
        "quota": tenant["quota"],
        "requests_used": tenant["requests_used"],
        "quota_remaining": max(0, tenant["quota"] - tenant["requests_used"]),
    }


@app.get("/v1/quarantine")
def list_quarantined_tests(
    active_only: bool = True,
    manifest_path: Optional[str] = None,
    tenant: Dict[str, Any] = Depends(require_scope("quarantine:read")),
) -> Dict[str, Any]:
    """Retrieves all quarantined test records from the registry."""
    qm = QuarantineManager(manifest_path=manifest_path)
    if active_only:
        active_ids = qm.get_quarantined_ids()
        records = {k: v for k, v in qm.manifest.quarantined_tests.items() if k in active_ids}
    else:
        records = qm.manifest.quarantined_tests

    return {
        "version": qm.manifest.version,
        "updated_at": qm.manifest.updated_at,
        "total_quarantined": len(records),
        "quarantined_tests": records,
        "pytest_deselect_args": qm.generate_pytest_deselection_args(),
    }


@app.post("/v1/quarantine", status_code=status.HTTP_201_CREATED)
def add_to_quarantine(
    payload: QuarantineAddRequest,
    manifest_path: Optional[str] = None,
    tenant: Dict[str, Any] = Depends(require_scope("quarantine:write")),
) -> Dict[str, Any]:
    """Declares a test as quarantined to prevent CI pipeline blockage."""
    qm = QuarantineManager(manifest_path=manifest_path)

    try:
        cause_enum = RootCauseHypothesis(payload.root_cause)
    except ValueError:
        cause_enum = RootCauseHypothesis.TIMING_RACE

    report = FlakinessReport(
        test_id=payload.test_id,
        file_path=payload.file_path,
        flakiness_score=payload.flakiness_score,
        category=FlakeCategory.FLAKY_HIGH if payload.flakiness_score >= 0.7 else FlakeCategory.FLAKY_MEDIUM,
        root_cause=cause_enum,
        total_runs=10,
        failure_rate=payload.failure_rate,
        duration_jitter=0.05,
        recommended_action="Quarantine test and notify owner",
        remediation_notes=payload.reason or "Quarantined via DevEx Gateway API",
    )

    is_new = qm.quarantine_test(report=report, reason=payload.reason, ttl_days=payload.ttl_days)

    return {
        "success": True,
        "is_new": is_new,
        "test_id": payload.test_id,
        "quarantined_entry": qm.manifest.quarantined_tests.get(payload.test_id),
    }


@app.delete("/v1/quarantine/{test_id:path}")
def remove_from_quarantine(
    test_id: str,
    manifest_path: Optional[str] = None,
    tenant: Dict[str, Any] = Depends(require_scope("quarantine:write")),
) -> Dict[str, Any]:
    """Removes a healed test from quarantine, restoring it to standard CI execution."""
    qm = QuarantineManager(manifest_path=manifest_path)
    removed = qm.unquarantine_test(test_id)
    if not removed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Test ID '{test_id}' not found in active quarantine registry.",
        )
    return {
        "success": True,
        "removed_test_id": test_id,
        "remaining_quarantined": len(qm.get_quarantined_ids()),
    }


@app.post("/v1/blast-radius")
def evaluate_blast_radius(
    payload: BlastRadiusRequest,
    tenant: Dict[str, Any] = Depends(require_scope("blast_radius:read")),
) -> Dict[str, Any]:
    """
    Computes transitive downstream impact graph and risk tier using AST caching.
    """
    root_dir = payload.root_dir or "."
    analyzer = BlastRadiusAnalyzer(root_dir=root_dir)
    report = analyzer.compute_blast_radius(
        changed_files=payload.changed_files,
        base_ref=payload.base_ref or "master",
        head_ref=payload.head_ref or "HEAD",
    )

    impacted_files = [
        {
            "file_path": node.file_path,
            "direct_dependency": node.direct_dependency,
            "imported_symbols": node.imported_symbols,
            "depth": node.depth,
        }
        for node in report.impacted_downstream_files
    ]

    return {
        "base_ref": report.base_ref,
        "head_ref": report.head_ref,
        "risk_level": report.risk_level.value,
        "risk_score": report.risk_score,
        "total_files_changed": report.total_files_changed,
        "impacted_files_count": len(impacted_files),
        "impacted_downstream_files": impacted_files,
        "breaking_changes_detected": report.breaking_changes_detected,
        "high_risk_reasons": report.high_risk_reasons,
        "cache_telemetry": {
            "cache_hits": analyzer.cache_hits,
            "cache_misses": analyzer.cache_misses,
        },
    }


@app.post("/v1/incidents/heal")
def heal_production_incident(
    payload: IncidentHealRequest,
    tenant: Dict[str, Any] = Depends(require_scope("incident:heal")),
) -> Dict[str, Any]:
    """
    TECH-302: Distributed Autonomous Healing Mesh
    Correlates incident telemetry, synthesizes localized AST hotfix, and validates blast radius.
    """
    from trace_root_ai.mesh import AutonomousHealingMesh
    from trace_root_ai.models import IncidentPayload

    incident = IncidentPayload(
        incident_id=payload.incident_id,
        service_name=payload.service_name,
        error_type=payload.error_type,
        error_message=payload.error_message,
        raw_stack_trace=payload.stack_trace,
    )

    mesh = AutonomousHealingMesh(root_dir=payload.root_dir or ".")
    result = mesh.process_incident(incident=incident, auto_stage=payload.auto_stage)
    return result.model_dump()
