import logging
import sys
from typing import Any, Dict

import structlog
from pythonjsonlogger import jsonlogger

from engine.config import get_settings


def setup_logging() -> None:
    settings = get_settings()

    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
    )

    # Configure structlog
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]

    if settings.environment == "development":
        # Pretty console output for development
        processors = shared_processors + [
            structlog.dev.ConsoleRenderer(colors=True),
        ]
    else:
        # JSON output for production
        processors = shared_processors + [
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(),
        ]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Set up JSON formatter for standard logging (for file handlers, etc.)
    json_handler = logging.StreamHandler(sys.stdout)
    json_handler.setFormatter(
        jsonlogger.JsonFormatter(
            fmt="%(timestamp)s %(level)s %(name)s %(message)s",
            rename_fields={"level": "level", "name": "logger"},
        )
    )

    # Replace root handler
    root_logger = logging.getLogger()
    root_logger.handlers = [json_handler]


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)


class LoggingMixin:
    @property
    def logger(self) -> structlog.stdlib.BoundLogger:
        if not hasattr(self, "_logger"):
            self._logger = get_logger(self.__class__.__module__ + "." + self.__class__.__name__)
        return self._logger


def log_execution_time(logger: structlog.stdlib.BoundLogger, operation: str):
    """Decorator to log execution time of async functions."""
    import functools
    import time

    def decorator(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            start = time.perf_counter()
            try:
                result = await func(*args, **kwargs)
                logger.info(
                    f"{operation} completed",
                    operation=operation,
                    duration_ms=round((time.perf_counter() - start) * 1000, 2),
                    success=True,
                )
                return result
            except Exception as e:
                logger.error(
                    f"{operation} failed",
                    operation=operation,
                    duration_ms=round((time.perf_counter() - start) * 1000, 2),
                    success=False,
                    error=str(e),
                    error_type=type(e).__name__,
                )
                raise

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            start = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                logger.info(
                    f"{operation} completed",
                    operation=operation,
                    duration_ms=round((time.perf_counter() - start) * 1000, 2),
                    success=True,
                )
                return result
            except Exception as e:
                logger.error(
                    f"{operation} failed",
                    operation=operation,
                    duration_ms=round((time.perf_counter() - start) * 1000, 2),
                    success=False,
                    error=str(e),
                    error_type=type(e).__name__,
                )
                raise

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator