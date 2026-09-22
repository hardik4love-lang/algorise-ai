import logging
from typing import Optional

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

from engine.config import get_settings


_tracer_provider: Optional[TracerProvider] = None


def init_tracing(service_name: Optional[str] = None) -> TracerProvider:
    global _tracer_provider

    settings = get_settings()
    service = service_name or settings.otel_service_name

    # Create resource
    resource = Resource.create({
        "service.name": service,
        "service.version": settings.app_version,
        "deployment.environment": settings.environment,
    })

    # Create tracer provider
    provider = TracerProvider(resource=resource)

    # Add OTLP exporter if endpoint configured
    if settings.otel_endpoint:
        otlp_exporter = OTLPSpanExporter(
            endpoint=settings.otel_endpoint,
            insecure=True,
        )
        provider.add_span_processor(BatchSpanProcessor(otlp_exporter))

    # Add console exporter for development
    if settings.environment == "development":
        console_exporter = ConsoleSpanExporter()
        provider.add_span_processor(BatchSpanProcessor(console_exporter))

    # Set as global tracer provider
    trace.set_tracer_provider(provider)
    _tracer_provider = provider

    return provider


def get_tracer(name: str) -> trace.Tracer:
    return trace.get_tracer(name)


def instrument_fastapi(app) -> None:
    settings = get_settings()
    FastAPIInstrumentor.instrument_app(
        app,
        tracer_provider=_tracer_provider,
        excluded_urls="health,metrics,ready",
    )


def instrument_redis() -> None:
    RedisInstrumentor().instrument(tracer_provider=_tracer_provider)


def instrument_sqlalchemy(engine) -> None:
    SQLAlchemyInstrumentor().instrument(
        engine=engine,
        tracer_provider=_tracer_provider,
    )


def shutdown_tracing() -> None:
    global _tracer_provider
    if _tracer_provider:
        _tracer_provider.shutdown()
        _tracer_provider = None


# Custom span attributes for Algorise
class SpanAttributes:
    BOT_ID = "algorise.bot.id"
    BOT_NAME = "algorise.bot.name"
    BOT_SECTOR = "algorise.bot.sector"
    CLIENT_ID = "algorise.client.id"
    CLIENT_TIER = "algorise.client.tier"
    TASK_ID = "algorise.task.id"
    LATENCY_MS = "algorise.latency.ms"
    SUCCESS = "algorise.success"
    SAFETY_CLEARANCE = "algorise.safety.clearance"
    AUTO_FLOW_ID = "algorise.autoflow.id"
    PIPELINE_ID = "algorise.pipeline.id"