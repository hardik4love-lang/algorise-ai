"""
Unit Tests for Statutory Compliance Engine
Verifies Indian EPF, ESIC, Professional Tax, and Section 115BAC Income Tax.
"""

import pytest
from app.services.statutory_engine import StatutoryComplianceEngine


def test_epf_calculation_capped():
    """
    Test standard EPF calculation with statutory wage ceiling of ₹15,000.
    """
    basic_salary = 30000.0  # Above ₹15,000 ceiling
    epf = StatutoryComplianceEngine.calculate_epf(
        basic_salary=basic_salary,
        is_pf_eligible=True,
        cap_at_statutory_limit=True
    )
    # 12% of 15000 = 1800
    assert epf["employee_pf"] == 1800.0
    # EPS capped at 1250
    assert epf["employer_eps"] == 1250.0
    # EPF difference = 1800 - 1250 = 550
    assert epf["employer_epf"] == 550.0


def test_esic_eligibility():
    """
    Test ESIC is only applied if gross wage <= ₹21,000.
    """
    # Under limit
    esic_eligible = StatutoryComplianceEngine.calculate_esic(gross_salary=20000.0)
    assert esic_eligible["esic_applicable"] is True
    assert esic_eligible["employee_esic"] == 150.0  # 0.75% of 20,000
    assert esic_eligible["employer_esic"] == 650.0  # 3.25% of 20,000

    # Over limit
    esic_ineligible = StatutoryComplianceEngine.calculate_esic(gross_salary=35000.0)
    assert esic_ineligible["esic_applicable"] is False
    assert esic_ineligible["employee_esic"] == 0.0


def test_professional_tax_states():
    """
    Test Professional Tax across different states.
    """
    # Maharashtra standard month (> 10k)
    pt_mh = StatutoryComplianceEngine.calculate_professional_tax(
        monthly_gross=45000.0,
        state="Maharashtra",
        month_number=10
    )
    assert pt_mh == 200.0

    # Maharashtra February adjustment
    pt_mh_feb = StatutoryComplianceEngine.calculate_professional_tax(
        monthly_gross=45000.0,
        state="Maharashtra",
        month_number=2
    )
    assert pt_mh_feb == 300.0

    # Delhi (No PT)
    pt_delhi = StatutoryComplianceEngine.calculate_professional_tax(
        monthly_gross=80000.0,
        state="Delhi"
    )
    assert pt_delhi == 0.0


def test_tds_section_115bac():
    """
    Test Section 115BAC New Tax Regime with 87A rebate and standard deduction.
    """
    # Annual gross of ₹7,50,000:
    # Taxable = 7,50,000 - 75,000 (std deduction) = 6,75,000.
    # Since <= 7,00,000, Section 87A rebate makes tax zero.
    tds_rebate = StatutoryComplianceEngine.calculate_annual_tds_new_regime(
        projected_annual_gross=750000.0
    )
    assert tds_rebate["total_annual_tds"] == 0.0

    # Annual gross of ₹12,00,000:
    # Taxable = 12,00,000 - 75,000 = 11,25,000.
    # 0 to 3L: 0
    # 3L to 7L (4L @ 5%): 20,000
    # 7L to 10L (3L @ 10%): 30,000
    # 10L to 11.25L (1.25L @ 15%): 18,750
    # Total Base Tax = 68,750.
    # Cess 4% = 2,750.
    # Total Tax = 71,500.
    tds = StatutoryComplianceEngine.calculate_annual_tds_new_regime(
        projected_annual_gross=1200000.0
    )
    assert tds["annual_base_tax"] == 68750.0
    assert tds["annual_cess"] == 2750.0
    assert tds["total_annual_tds"] == 71500.0
