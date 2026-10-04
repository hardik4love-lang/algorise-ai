"""
Algorise Proprietary AI Engine
Copyright (c) 2026 Algorise AI Solutions. All rights reserved.
"Rise Above with AI."

Exports are resolved lazily (PEP 562).

This module used to import every submodule eagerly. That made `import
engine.anything` re-enter this package while it was still initialising, so a
router module reached by `engine.main` could be only partially built when
`app.include_router()` consumed it. FastAPI then mounted whichever routes
happened to exist at that instant.

The failure was invisible: the build succeeded, uvicorn started, /health
answered 200, and the deployment served 14 of 49 endpoints. Thirty-five routes
- Meta proxy, attribution, brand, WhatsApp webhook, distribution - were simply
absent, with nothing logged.

Lazy attribute access breaks the cycle at its source: nothing is imported until
something actually asks for it, so no submodule can observe this package
half-built. `from engine.security import verify_api_key` and
`engine.security.verify_api_key` both still work.
"""

from typing import Any

__version__ = "1.0.0"
__brand__ = "Algorise AI Solutions"

# Attribute name -> submodule that provides it.
_EXPORTS: dict[str, str] = {
    "Settings": "engine.config",
    "get_settings": "engine.config",
    "db_manager": "engine.database",
    "get_db_session": "engine.database",
    "get_logger": "engine.logging",
    "setup_logging": "engine.logging",
    "REGISTRY": "engine.metrics",
    "get_metrics": "engine.metrics",
    "init_metrics": "engine.metrics",
    "Base": "engine.models_sqlalchemy",
    "get_tracer": "engine.tracing",
    "init_tracing": "engine.tracing",
    "instrument_fastapi": "engine.tracing",
    "instrument_redis": "engine.tracing",
    "instrument_sqlalchemy": "engine.tracing",
    "api_key_manager": "engine.security",
    "audit_logger": "engine.security",
    "encryption_manager": "engine.security",
    "input_validator": "engine.security",
    "rate_limiter": "engine.security",
    "verify_api_key": "engine.security",
    "check_rate_limit_middleware": "engine.security",
    "validate_request_payload": "engine.security",
    "validate_query_string": "engine.security",
    "get_security_headers": "engine.security",
    "get_cors_config": "engine.security",
    "SECURITY_HEADERS": "engine.security",
}

__all__ = [*_EXPORTS, "__version__", "__brand__"]


def __getattr__(name: str) -> Any:
    module_name = _EXPORTS.get(name)
    if module_name is None:
        raise AttributeError(f"module 'engine' has no attribute {name!r}")
    from importlib import import_module

    module = import_module(module_name)
    value = getattr(module, name)
    # Cache on the package so the import happens once.
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(__all__)