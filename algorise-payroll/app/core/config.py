"""
Algorise PayHR - Core Configuration
Enterprise Grade Settings & Statutory Thresholds
"""

from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    # Brand & System Identity
    PROJECT_NAME: str = "Algorise PayHR"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "production"
    DEBUG: bool = False

    # Security & Cryptography
    # 256-bit AES master key for encrypting sensitive PII (PAN, Bank Account, Aadhaar)
    PII_ENCRYPTION_KEY: str = Field(
        default="0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
        description="64-char hex string representing 32-byte AES-GCM key"
    )
    JWT_SECRET_KEY: str = Field(
        default="algorise-super-secure-jwt-secret-key-change-in-production-min-32-chars",
        description="Secret key for signing JWT tokens"
    )
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 8  # 8 hours
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # Hardware & Camera Webhook Authentication
    DEVICE_HMAC_SECRET: str = Field(
        default="algorise-device-hmac-secret-key-2026",
        description="Shared secret for validating biometric/CCTV webhook signatures"
    )
    HMAC_TIMESTAMP_TOLERANCE_SECONDS: int = 300  # 5 minutes replay window

    # Database & Cache
    DATABASE_URL: str = "postgresql+asyncpg://algorise:algorise_secure_pass@localhost:5432/algorise_payroll"
    SYNC_DATABASE_URL: str = "postgresql://algorise:algorise_secure_pass@localhost:5432/algorise_payroll"
    REDIS_URL: str = "redis://localhost:6379/0"

    # CORS & Allowed Hosts
    ALLOWED_HOSTS: List[str] = ["*"]
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "https://payroll.algorise.ai"]

    # Indian Statutory Payroll Constants (2026)
    EPF_WAGE_CEILING: float = 15000.00          # Mandatory EPF ceiling ₹15,000/mo
    EPF_EMPLOYEE_RATE: float = 0.12             # 12%
    EPF_EMPLOYER_TOTAL_RATE: float = 0.12       # 12%
    EPS_EMPLOYER_RATE: float = 0.0833           # 8.33% capped at ₹1,250
    EPS_MAX_CAP: float = 1250.00
    EPF_EDLI_RATE: float = 0.005                # 0.5%
    EPF_ADMIN_RATE: float = 0.005               # 0.5%

    ESIC_WAGE_CEILING: float = 21000.00         # ₹21,000/mo
    ESIC_EMPLOYEE_RATE: float = 0.0075          # 0.75%
    ESIC_EMPLOYER_RATE: float = 0.0325          # 3.25%

    GRATUITY_FACTOR: float = 15.0 / 26.0

    # Default New Tax Regime Standard Deduction (Section 115BAC)
    NEW_REGIME_STD_DEDUCTION: float = 75000.00
    OLD_REGIME_STD_DEDUCTION: float = 50000.00

    # Attendance & Geofencing Guard
    DEFAULT_GEOFENCE_RADIUS_METERS: float = 50.0
    GEOFENCE_BREACH_BUFFER_SECONDS: int = 180    # 3-minute grace period before cutoff
    MAX_ALLOWABLE_SPEED_KMH: float = 120.0       # Anti-teleportation velocity check

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True, extra="ignore")


settings = Settings()
