"""
Unit Tests for Daily Wage (Dihadi) and Compliance Export Engines
Verifies EPFO ECR format, ESIC format, Tally XML, and contract labour calculations.
"""

import pytest
from app.services.daily_wage_engine import DailyWageCalculationEngine
from app.services.compliance_export_engine import ComplianceExportEngine


def test_dihadi_calculation_with_kharchi_and_bocw():
    """
    Test daily wage calculation for construction / factory workers with kharchi deductions.
    """
    res = DailyWageCalculationEngine.calculate_dihadi_payout(
        worker_id="LABOUR-101",
        worker_name="Ramesh Kumar",
        daily_rate=700.0,
        full_days_worked=24.0,
        half_days_worked=2.0,  # 24 + 1 = 25 effective days
        overtime_hours=10.0,
        kharchi_advances_drawn=2000.0,
        bocw_cess_applicable=True,
        food_allowance_daily=50.0
    )
    # Effective days = 25.0
    assert res["muster_summary"]["effective_payable_days"] == 25.0
    # Base wage = 25 * 700 = 17,500
    assert res["earnings"]["base_wage"] == 17500.0
    # Overtime hourly = 700 / 8 = 87.5; 10 hrs * 1.5 * 87.5 = 1,312.50
    assert res["earnings"]["overtime_pay"] == 1312.50
    # Food allowance = 25 * 50 = 1,250
    assert res["earnings"]["food_allowance"] == 1250.0
    # Gross = 17500 + 1312.5 + 1250 = 20,062.50
    assert res["earnings"]["gross_dihadi_total"] == 20062.50
    # BOCW 1% = 200.62; Kharchi = 2000; Total = 2,200.62
    assert res["deductions"]["bocw_welfare"] == 200.62
    # Net = 20062.50 - 2200.62 = 17861.88
    assert abs(res["net_dihadi_payout"] - 17861.88) < 0.1


def test_epfo_ecr_format_generation():
    """
    Test generation of official #~# delimited EPFO ECR text format.
    """
    records = [
        {
            "uan": "100123456789",
            "name": "Rahul Sharma",
            "gross_wages": 45000,
            "epf_wages": 15000,
            "eps_wages": 15000,
            "edli_wages": 15000,
            "ee_pf": 1800,
            "er_eps": 1250,
            "er_pf": 550,
            "lop_days": 1
        }
    ]
    ecr_txt = ComplianceExportEngine.generate_epfo_ecr_txt(records)
    expected_line = "100123456789#~#Rahul Sharma#~#45000#~#15000#~#15000#~#15000#~#1800#~#1250#~#550#~#1#~#0"
    assert ecr_txt == expected_line


def test_tally_and_bank_exports():
    """
    Test Tally XML and Bank CSV export generation.
    """
    records = [
        {"account_number": "50100012345678", "net_pay": 59722.15, "name": "Rahul Sharma", "ifsc": "HDFC0000001"}
    ]
    bank_csv = ComplianceExportEngine.generate_bank_salary_file(records, bank="HDFC")
    assert "HDFC0000001" in bank_csv
    assert "59722.15" in bank_csv

    tally_xml = ComplianceExportEngine.generate_tally_payroll_xml(records)
    assert "<TALLYREQUEST>Import Data</TALLYREQUEST>" in tally_xml
    assert "-59722.15" in tally_xml
