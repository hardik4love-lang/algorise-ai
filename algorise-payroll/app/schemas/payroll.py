"""
Algorise PayHR - Payroll API Schemas
"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class SalaryStructureCreate(BaseModel):
    annual_ctc: float = Field(..., gt=0.0)
    monthly_basic: float = Field(..., gt=0.0)
    monthly_hra: float = Field(..., ge=0.0)
    monthly_special_allowance: float = Field(..., ge=0.0)
    monthly_other_allowance: float = Field(default=0.0, ge=0.0)
    pf_applicable: bool = True
    pf_capped: bool = True
    esic_applicable: bool = True
    pt_applicable: bool = True


class CalculatePayslipRequest(BaseModel):
    employee_id: str
    employee_name: str
    total_month_days: int = Field(default=30, ge=28, le=31)
    lop_days: float = Field(default=0.0, ge=0.0)
    overtime_hours: float = Field(default=0.0, ge=0.0)
    monthly_basic: float = Field(..., gt=0.0)
    monthly_hra: float = Field(..., ge=0.0)
    monthly_special_allowance: float = Field(..., ge=0.0)
    monthly_other_allowance: float = Field(default=0.0, ge=0.0)
    state_for_pt: str = Field(default="Maharashtra")
    month_number: int = Field(default=10, ge=1, le=12)
    gender: str = Field(default="MALE", pattern="^(MALE|FEMALE|OTHER)$")
    tax_regime: str = Field(default="NEW", pattern="^(NEW|OLD)$")
    is_pf_eligible: bool = True
    pf_capped: bool = True
    is_esic_eligible: bool = True


class PayrollRunBatchRequest(BaseModel):
    month: int = Field(..., ge=1, le=12)
    year: int = Field(..., ge=2024)
    auto_fetch_muster: bool = True
