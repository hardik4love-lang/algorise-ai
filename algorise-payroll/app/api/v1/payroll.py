"""
Algorise PayHR - Payroll Execution API Endpoints
Computes itemized payslips, batch payroll cycles, and statutory compliance reports.
"""

from fastapi import APIRouter, HTTPException, status
from typing import Dict, Any, List

from app.schemas.payroll import CalculatePayslipRequest, PayrollRunBatchRequest
from app.services.payroll_engine import PayrollCalculationEngine
from app.services.statutory_engine import StatutoryComplianceEngine

router = APIRouter(prefix="/payroll", tags=["Payroll"])


@router.post("/calculate-payslip", summary="Compute Individual Prorated Payslip")
async def calculate_single_payslip(payload: CalculatePayslipRequest):
    """
    Computes an exact gross-to-net payslip breakdown prorated by LOP and Overtime.
    """
    try:
        payslip = PayrollCalculationEngine.compute_employee_payslip(
            employee_id=payload.employee_id,
            employee_name=payload.employee_name,
            total_month_days=payload.total_month_days,
            lop_days=payload.lop_days,
            overtime_hours=payload.overtime_hours,
            monthly_basic=payload.monthly_basic,
            monthly_hra=payload.monthly_hra,
            monthly_special_allowance=payload.monthly_special_allowance,
            monthly_other_allowance=payload.monthly_other_allowance,
            state_for_pt=payload.state_for_pt,
            month_number=payload.month_number,
            gender=payload.gender,
            tax_regime=payload.tax_regime,
            is_pf_eligible=payload.is_pf_eligible,
            pf_capped=payload.pf_capped,
            is_esic_eligible=payload.is_esic_eligible
        )
        return payslip
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Payroll calculation error: {str(e)}"
        )


@router.get("/statutory-rates", summary="Get Current Indian Statutory Rules")
async def get_statutory_rates():
    """
    Returns verified statutory slabs for EPF, ESIC, State PT, and TDS Section 115BAC.
    """
    return {
        "regime": "Indian Statutory Rules 2026",
        "epf": {
            "wage_ceiling": 15000.0,
            "employee_rate": "12%",
            "employer_eps_rate": "8.33% (Max ₹1,250)",
            "employer_epf_rate": "3.67%",
            "edli_rate": "0.5%",
            "admin_rate": "0.5%"
        },
        "esic": {
            "wage_ceiling": 21000.0,
            "employee_rate": "0.75%",
            "employer_rate": "3.25%"
        },
        "tds_new_regime_sec_115bac": {
            "standard_deduction": 75000.0,
            "sec_87a_rebate_limit": 700000.0,
            "slabs": [
                {"range": "0 - 3,00,000", "rate": "Nil"},
                {"range": "3,00,001 - 7,00,000", "rate": "5%"},
                {"range": "7,00,001 - 10,00,000", "rate": "10%"},
                {"range": "10,00,001 - 12,00,000", "rate": "15%"},
                {"range": "12,00,001 - 15,00,000", "rate": "20%"},
                {"range": "Above 15,00,000", "rate": "30%"}
            ],
            "cess": "4%"
        }
    }
