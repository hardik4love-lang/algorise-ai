"""
Algorise PayHR - V1 API Router Aggregator
"""

from fastapi import APIRouter
from app.api.v1.attendance import router as attendance_router
from app.api.v1.payroll import router as payroll_router

api_router = APIRouter()
api_router.include_router(attendance_router)
api_router.include_router(payroll_router)
