"""
Algorise PayHR - Daily Wage (Dihadi) & Contract Labour Engine
Specialized for Construction, Real Estate, Manufacturing & BOCW Compliance:
- Daily rate calculation (per-shift / half-day / piece-rate)
- Kharchi (daily advance cash payouts) deduction tracking
- Overtime (OT) multi-shift tracking
- BOCW (Building and Other Construction Workers) Cess & welfare deductions
"""

from typing import Dict, Any, List, Optional
from datetime import date


class DailyWageCalculationEngine:
    """
    Computes daily muster wages, kharchi deductions, and contract labour payouts.
    """

    @staticmethod
    def calculate_dihadi_payout(
        worker_id: str,
        worker_name: str,
        daily_rate: float,
        full_days_worked: float,
        half_days_worked: float,
        overtime_hours: float,
        kharchi_advances_drawn: float = 0.0,
        bocw_cess_applicable: bool = True,
        food_allowance_daily: float = 0.0
    ) -> Dict[str, Any]:
        """
        Calculates net weekly/monthly settlement for site labour and dihadi workers.
        """
        # Effective days = Full days + (0.5 * Half days)
        effective_days = float(full_days_worked) + (0.5 * float(half_days_worked))
        
        # Base wage earned
        base_earned_wage = round(effective_days * daily_rate, 2)
        
        # Overtime calculation: Standard hourly rate = daily_rate / 8 hrs
        hourly_rate = (daily_rate / 8.0) if daily_rate > 0 else 0.0
        # Overtime under Factories Act / Contract Labour: 1.5x or 2x
        overtime_pay = round(hourly_rate * 1.5 * overtime_hours, 2)
        
        # Food / Site allowance
        total_food_allowance = round(effective_days * food_allowance_daily, 2)
        
        gross_dihadi_earnings = round(base_earned_wage + overtime_pay + total_food_allowance, 2)
        
        # BOCW Welfare Fund (typically 1% deduction where enacted)
        bocw_deduction = round(gross_dihadi_earnings * 0.01, 2) if bocw_cess_applicable else 0.0
        
        # Kharchi (mid-week daily cash advances taken by worker)
        total_deductions = round(kharchi_advances_drawn + bocw_deduction, 2)
        net_payable_amount = round(gross_dihadi_earnings - total_deductions, 2)

        return {
            "worker_id": worker_id,
            "worker_name": worker_name,
            "muster_summary": {
                "full_days": full_days_worked,
                "half_days": half_days_worked,
                "effective_payable_days": effective_days,
                "overtime_hours": overtime_hours
            },
            "rates": {
                "daily_rate": daily_rate,
                "hourly_rate": round(hourly_rate, 2)
            },
            "earnings": {
                "base_wage": base_earned_wage,
                "overtime_pay": overtime_pay,
                "food_allowance": total_food_allowance,
                "gross_dihadi_total": gross_dihadi_earnings
            },
            "deductions": {
                "kharchi_advances": kharchi_advances_drawn,
                "bocw_welfare": bocw_deduction,
                "total_deductions": total_deductions
            },
            "net_dihadi_payout": max(0.0, net_payable_amount)
        }
