"""
Algorise PayHR - Core Payroll & Gross-to-Net Engine
Prorates earnings by attendance muster (Payable Days, LOP, Overtime),
applies statutory compliance, and computes exact Net Pay.
"""

from typing import Dict, Any, Optional
from app.services.statutory_engine import StatutoryComplianceEngine


class PayrollCalculationEngine:
    """
    Executes end-to-end gross-to-net computation with LOP and Overtime.
    """

    @classmethod
    def compute_employee_payslip(
        cls,
        employee_id: str,
        employee_name: str,
        total_month_days: int,
        lop_days: float,
        overtime_hours: float,
        monthly_basic: float,
        monthly_hra: float,
        monthly_special_allowance: float,
        monthly_other_allowance: float = 0.0,
        state_for_pt: str = "Maharashtra",
        month_number: int = 10,
        gender: str = "MALE",
        tax_regime: str = "NEW",
        is_pf_eligible: bool = True,
        pf_capped: bool = True,
        is_esic_eligible: bool = True
    ) -> Dict[str, Any]:
        """
        Computes itemized monthly payslip for an employee.
        """
        payable_days = max(0.0, float(total_month_days) - float(lop_days))
        proration_ratio = payable_days / float(total_month_days) if total_month_days > 0 else 0.0

        # 1. Prorated Earnings based on actual days worked
        earned_basic = round(monthly_basic * proration_ratio, 2)
        earned_hra = round(monthly_hra * proration_ratio, 2)
        earned_special = round(monthly_special_allowance * proration_ratio, 2)
        earned_other = round(monthly_other_allowance * proration_ratio, 2)

        # 2. Overtime Payout (Factories Act standard: 2x hourly rate based on 26 days * 8 hrs)
        hourly_rate = (monthly_basic / (26.0 * 8.0)) if monthly_basic > 0 else 0.0
        overtime_pay = round(hourly_rate * 2.0 * overtime_hours, 2) if overtime_hours > 0 else 0.0

        total_gross_earnings = round(
            earned_basic + earned_hra + earned_special + earned_other + overtime_pay, 2
        )

        # 3. Statutory Deductions
        # A. EPF
        epf_data = StatutoryComplianceEngine.calculate_epf(
            basic_salary=earned_basic,
            is_pf_eligible=is_pf_eligible,
            cap_at_statutory_limit=pf_capped
        )
        employee_pf = epf_data["employee_pf"]

        # B. ESIC (Based on full monthly gross equivalent or earned gross)
        esic_data = StatutoryComplianceEngine.calculate_esic(
            gross_salary=total_gross_earnings,
            is_esic_eligible=is_esic_eligible
        )
        employee_esic = esic_data["employee_esic"]

        # C. Professional Tax
        pt = StatutoryComplianceEngine.calculate_professional_tax(
            monthly_gross=total_gross_earnings,
            state=state_for_pt,
            month_number=month_number,
            gender=gender
        )

        # D. TDS (Income Tax)
        # Annual projected taxable earnings
        projected_annual_gross = total_gross_earnings * 12.0
        tds_data = StatutoryComplianceEngine.calculate_annual_tds_new_regime(
            projected_annual_gross=projected_annual_gross
        )
        monthly_tds = tds_data["monthly_tds"]

        # 4. Total Deductions & Net Take-Home Pay
        total_deductions = round(employee_pf + employee_esic + pt + monthly_tds, 2)
        net_take_home = round(total_gross_earnings - total_deductions, 2)

        # 5. Employer Cost & Contributions
        employer_pf_total = epf_data["total_employer_pf"]
        employer_esic = esic_data["employer_esic"]
        # Gratuity provision (approx 4.81% of basic)
        monthly_gratuity_provision = round((earned_basic * 15.0) / (26.0 * 12.0), 2)
        total_employer_cost = round(
            total_gross_earnings + employer_pf_total + employer_esic + monthly_gratuity_provision, 2
        )

        return {
            "employee_id": employee_id,
            "employee_name": employee_name,
            "attendance_summary": {
                "total_calendar_days": total_month_days,
                "payable_days": payable_days,
                "lop_days": lop_days,
                "overtime_hours": overtime_hours
            },
            "earnings": {
                "basic": earned_basic,
                "hra": earned_hra,
                "special_allowance": earned_special,
                "other_allowance": earned_other,
                "overtime_pay": overtime_pay,
                "total_gross": total_gross_earnings
            },
            "deductions": {
                "employee_pf": employee_pf,
                "employee_esic": employee_esic,
                "professional_tax": pt,
                "tds_income_tax": monthly_tds,
                "total_deductions": total_deductions
            },
            "net_pay": net_take_home,
            "employer_contributions": {
                "employer_epf_total": employer_pf_total,
                "employer_eps": epf_data["employer_eps"],
                "employer_esic": employer_esic,
                "gratuity_provision": monthly_gratuity_provision,
                "total_company_cost": total_employer_cost
            }
        }
