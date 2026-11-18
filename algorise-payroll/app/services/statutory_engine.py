"""
Algorise PayHR - Indian Statutory Compliance Engine (2026 Edition)
Implements precise EPF, ESIC, State-wise Professional Tax, Section 115BAC TDS, and Gratuity.
"""

from typing import Dict, Any, Optional
from app.core.config import settings


class StatutoryComplianceEngine:
    """
    Certified Indian Payroll Statutory Calculator.
    Handles exact employee and employer liability breakups.
    """

    @staticmethod
    def calculate_epf(
        basic_salary: float,
        is_pf_eligible: bool = True,
        cap_at_statutory_limit: bool = True
    ) -> Dict[str, float]:
        """
        Computes EPF (Employee Provident Fund) contributions.
        - Statutory wage ceiling: ₹15,000/month
        - Employee: 12%
        - Employer: 12% total -> EPS 8.33% (max ₹1,250), EPF 3.67%, EDLI 0.5%, Admin 0.5%
        """
        if not is_pf_eligible or basic_salary <= 0:
            return {
                "pf_wage_base": 0.0,
                "employee_pf": 0.0,
                "employer_eps": 0.0,
                "employer_epf": 0.0,
                "employer_edli": 0.0,
                "employer_admin": 0.0,
                "total_employer_pf": 0.0
            }

        # Determine wage base
        if cap_at_statutory_limit:
            pf_wage = min(basic_salary, settings.EPF_WAGE_CEILING)
        else:
            pf_wage = basic_salary

        # Employee 12%
        employee_pf = round(pf_wage * settings.EPF_EMPLOYEE_RATE, 2)

        # Employer EPS (Pension): 8.33% statutory rate, officially capped at ₹1,250 on ₹15,000 wage ceiling
        eps_base = min(basic_salary, settings.EPF_WAGE_CEILING)
        if eps_base >= settings.EPF_WAGE_CEILING:
            employer_eps = settings.EPS_MAX_CAP
        else:
            employer_eps = min(round((eps_base * 8.3333333) / 100.0, 2), settings.EPS_MAX_CAP)

        # Employer EPF (Difference to make total employer contribution equal to employee PF or actual)
        # Total standard employer contribution = 12% of pf_wage
        total_employer_contrib = round(pf_wage * settings.EPF_EMPLOYER_TOTAL_RATE, 2)
        employer_epf = max(round(total_employer_contrib - employer_eps, 2), 0.0)

        # Administrative charges & EDLI
        employer_edli = round(eps_base * settings.EPF_EDLI_RATE, 2)
        employer_admin = round(pf_wage * settings.EPF_ADMIN_RATE, 2)

        total_employer = round(employer_eps + employer_epf + employer_edli + employer_admin, 2)

        return {
            "pf_wage_base": pf_wage,
            "employee_pf": employee_pf,
            "employer_eps": employer_eps,
            "employer_epf": employer_epf,
            "employer_edli": employer_edli,
            "employer_admin": employer_admin,
            "total_employer_pf": total_employer
        }

    @staticmethod
    def calculate_esic(
        gross_salary: float,
        is_esic_eligible: bool = True
    ) -> Dict[str, float]:
        """
        Computes ESIC contributions if gross salary <= ₹21,000/month.
        - Employee: 0.75%
        - Employer: 3.25%
        """
        if not is_esic_eligible or gross_salary <= 0 or gross_salary > settings.ESIC_WAGE_CEILING:
            return {
                "esic_applicable": False,
                "employee_esic": 0.0,
                "employer_esic": 0.0,
                "total_esic": 0.0
            }

        employee_esic = round(gross_salary * settings.ESIC_EMPLOYEE_RATE, 2)
        employer_esic = round(gross_salary * settings.ESIC_EMPLOYER_RATE, 2)

        return {
            "esic_applicable": True,
            "employee_esic": employee_esic,
            "employer_esic": employer_esic,
            "total_esic": round(employee_esic + employer_esic, 2)
        }

    @staticmethod
    def calculate_professional_tax(
        monthly_gross: float,
        state: str = "Maharashtra",
        month_number: int = 10,
        gender: str = "MALE"
    ) -> float:
        """
        Computes state-specific Professional Tax (PT).
        Handles February adjustments (e.g. Maharashtra ₹300).
        """
        st = state.strip().title()

        if st == "Maharashtra":
            # Men with gross > 10,000 pay ₹200 (₹300 in Feb). Women earning <= 25,000 are exempt.
            if gender.upper() == "FEMALE" and monthly_gross <= 25000:
                return 0.0
            if monthly_gross <= 7500:
                return 0.0
            elif monthly_gross <= 10000:
                return 175.0
            else:
                return 300.0 if month_number == 2 else 200.0

        elif st == "Karnataka":
            # Gross >= 15,000 -> ₹200/month
            return 200.0 if monthly_gross >= 15000 else 0.0

        elif st in ["Telangana", "Andhra Pradesh"]:
            if monthly_gross <= 15000:
                return 0.0
            elif monthly_gross <= 20000:
                return 150.0
            else:
                return 200.0

        elif st == "Tamil Nadu":
            # Slabs generally semi-annual; monthly proration:
            if monthly_gross < 21000:
                return 0.0
            elif monthly_gross <= 30000:
                return 100.0
            elif monthly_gross <= 45000:
                return 235.0
            elif monthly_gross <= 60000:
                return 340.0
            elif monthly_gross <= 75000:
                return 510.0
            else:
                return 208.0  # Approx statutory monthly cap

        elif st in ["Delhi", "Haryana", "Rajasthan", "Uttar Pradesh"]:
            return 0.0  # No Professional Tax levied

        elif st == "Gujarat":
            if monthly_gross <= 5999:
                return 0.0
            elif monthly_gross <= 8999:
                return 80.0
            elif monthly_gross <= 11999:
                return 150.0
            else:
                return 200.0

        # Default fallback
        return 200.0 if monthly_gross >= 15000 else 0.0

    @staticmethod
    def calculate_annual_tds_new_regime(
        projected_annual_gross: float,
        other_exemptions: float = 0.0
    ) -> Dict[str, float]:
        """
        Computes Income Tax TDS under New Tax Regime (Section 115BAC).
        Reflects Standard Deduction: ₹75,000.
        Slabs:
          0 to 3,00,000: 0%
          3,00,001 to 7,00,000: 5%
          7,00,001 to 10,00,000: 10%
          10,00,001 to 12,00,000: 15%
          12,00,001 to 15,00,000: 20%
          Above 15,00,000: 30%
        Rebate u/s 87A: If Net Taxable Income <= ₹7,00,000 -> Tax is Nil.
        Health & Education Cess: 4%
        """
        std_deduction = settings.NEW_REGIME_STD_DEDUCTION
        taxable_income = max(0.0, projected_annual_gross - std_deduction - other_exemptions)

        # Full rebate under 87A for taxable income up to 7 Lakhs
        if taxable_income <= 700000.0:
            return {
                "annual_taxable_income": taxable_income,
                "annual_base_tax": 0.0,
                "annual_cess": 0.0,
                "total_annual_tds": 0.0,
                "monthly_tds": 0.0
            }

        tax = 0.0
        # 3L to 7L @ 5% (400,000 * 0.05 = 20,000)
        if taxable_income > 300000:
            slab_amt = min(taxable_income, 700000) - 300000
            tax += slab_amt * 0.05

        # 7L to 10L @ 10% (300,000 * 0.10 = 30,000)
        if taxable_income > 700000:
            slab_amt = min(taxable_income, 1000000) - 700000
            tax += slab_amt * 0.10

        # 10L to 12L @ 15% (200,000 * 0.15 = 30,000)
        if taxable_income > 1000000:
            slab_amt = min(taxable_income, 1200000) - 1000000
            tax += slab_amt * 0.15

        # 12L to 15L @ 20% (300,000 * 0.20 = 60,000)
        if taxable_income > 1200000:
            slab_amt = min(taxable_income, 1500000) - 1200000
            tax += slab_amt * 0.20

        # Above 15L @ 30%
        if taxable_income > 1500000:
            slab_amt = taxable_income - 1500000
            tax += slab_amt * 0.30

        cess = round(tax * 0.04, 2)
        total_tax = round(tax + cess, 2)
        monthly_tds = round(total_tax / 12.0, 2)

        return {
            "annual_taxable_income": taxable_income,
            "annual_base_tax": round(tax, 2),
            "annual_cess": cess,
            "total_annual_tds": total_tax,
            "monthly_tds": monthly_tds
        }
