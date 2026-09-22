"""
Algorise Proprietary AI Engine
Copyright (c) 2026 Algorise AI Solutions. All rights reserved.
"Rise Above with AI."
"""

from engine.config import Settings, get_settings
from engine.database import db_manager, get_db_session
from engine.logging import get_logger, setup_logging
from engine.metrics import REGISTRY, get_metrics, init_metrics
from engine.models_sqlalchemy import Base
from engine.security import (
    api_key_manager,
    audit_logger,
    encryption_manager,
    input_validator,
    rate_limiter,
    verify_api_key,
    check_rate_limit_middleware,
    validate_request_payload,
    validate_query_string,
    get_security_headers,
    get_cors_config,
    SECURITY_HEADERS,
)
from engine.tracing import get_tracer, init_tracing, instrument_fastapi, instrument_redis, instrument_sqlalchemy

__version__ = "1.0.0"
__brand__ = "Algorise AI Solutions"

__all__ = [
    "Settings",
    "get_settings",
    "db_manager",
    "get_db_session",
    "get_logger",
    "setup_logging",
    "REGISTRY",
    "get_metrics",
    "init_metrics",
    "Base",
    "get_tracer",
    "init_tracing",
    "instrument_fastapi",
    "instrument_redis",
    "instrument_sqlalchemy",
    # Security
    "api_key_manager",
    "audit_logger",
    "encryption_manager",
    "input_validator",
    "rate_limiter",
    "verify_api_key",
    "check_rate_limit_middleware",
    "validate_request_payload",
    "validate_query_string",
    "get_security_headers",
    "get_cors_config",
    "SECURITY_HEADERS",
]