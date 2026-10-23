import asyncio
import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, Response, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field
from typing import Optional
from prometheus_client import generate_latest

# Concurrency semaphore limiting simultaneous bot executions to prevent CPU & thread exhaustion
BOT_EXECUTION_SEMAPHORE = asyncio.Semaphore(50)

from engine import (
    db_manager,
    get_logger,
    get_metrics,
    init_metrics,
    init_tracing,
    instrument_fastapi,
    instrument_redis,
    instrument_sqlalchemy,
    setup_logging,
)
from engine.config import get_settings
from engine.metrics import HTTP_REQUEST_DURATION, HTTP_REQUESTS_TOTAL
from engine.hero_registry import HERO_BOT_DEFINITIONS, HeroBotRunner, HERO_BOT_IDS_SET
hero_runner = HeroBotRunner()
from engine.tuning_engine import AlgoriseTuningEngine
tuning_engine = AlgoriseTuningEngine()
from engine.graph_rag import graph_rag
from engine.guardrails import safety_gate
from engine.mcp_adapter import AlgoriseMCPAdapter
from engine.hero_registry import HERO_BOT_REGISTRY_MAP
mcp_adapter = AlgoriseMCPAdapter(bot_registry=HERO_BOT_REGISTRY_MAP)
from engine.security import (
    api_key_manager,
    audit_logger,
    get_cors_config,
    get_security_headers,
    input_validator,
    rate_limiter,
    verify_api_key,
    check_rate_limit_middleware,
    validate_request_payload,
    validate_query_string,
    SECURITY_HEADERS,
)
import json


# Setup logging first
setup_logging()
logger = get_logger(__name__)

# --- Routers are imported before anything else on purpose. -----------------
#
# engine/__init__.py eagerly imports submodules, and those submodules import
# further engine modules. Importing a router after that graph is in flight
# yields a partially-built router, and include_router then mounts only the
# routes that happened to exist. That produced a green deploy serving 14 of
# 49 endpoints with no error logged. Loading them here, before the rest of
# the engine is touched, makes the mount order deterministic.

from engine.subscription_routes import router as subscription_router  # noqa: E402
from engine.meta_proxy import router as meta_proxy_router  # noqa: E402
from engine.attribution_routes import router as attribution_router  # noqa: E402
from engine.brand_routes import router as brand_router  # noqa: E402
from engine.whatsapp_webhook import router as whatsapp_webhook_router  # noqa: E402
from engine.distribution_routes import router as distribution_router  # noqa: E402
settings = get_settings()

# API Key header for dependency injection
api_key_header = APIKeyHeader(name="X-Algorise-Key", auto_error=False)


async def get_api_key(api_key: str = Depends(api_key_header)) -> str:
    """Dependency to extract API key from header."""
    if not api_key:
        raise HTTPException(
            status_code=401,
            detail="Authentication failed: Missing required 'X-Algorise-Key' header",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    return api_key


async def verify_api_key_dependency(api_key: str = Depends(get_api_key)) -> tuple:
    """Dependency to verify API key and return key info."""
    valid, key_info = await verify_api_key(api_key)
    if not valid:
        raise HTTPException(
            status_code=401,
            detail="Invalid or inactive API key",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return api_key, key_info


async def rate_limit_dependency(request: Request, api_key: str = Depends(get_api_key)):
    """Dependency to check rate limits."""
    # Use client IP + API key as rate limit key
    client_ip = request.client.host if request.client else "unknown"
    rate_key = f"{client_ip}:{api_key[:16]}"
    
    allowed, info = await check_rate_limit_middleware(rate_key)
    if not allowed:
        audit_logger.log_rate_limit_exceeded(
            client_id=api_key[:16],
            endpoint=str(request.url.path),
            ip=client_ip,
        )
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded",
            headers={
                "X-RateLimit-Limit": str(settings.rate_limit_requests),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(info.get("reset_in", 60)),
                "Retry-After": str(info.get("retry_after", 60)),
            },
        )
    
    # Add rate limit headers to response
    request.state.rate_limit_info = info


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("Starting Algorise AI Solutions API", version=settings.app_version, environment=settings.environment)

    settings.validate_production_safety()
    app.state.startup_complete = False

    # Initialize tracing
    init_tracing(settings.otel_service_name)

    # Initialize metrics
    init_metrics("algorise-ai", settings.app_version)

    # Initialize database
    is_production = settings.environment.lower() in {"production", "prod"}
    try:
        if settings.migrate_on_start:
            await db_manager.create_tables()
            logger.info("Database tables created/verified")
        else:
            logger.info("MIGRATE_ON_START disabled; skipping schema creation (pre-deploy job owns migrations)")
    except Exception as e:
        if is_production:
            raise
        logger.warning("Database initialization failed (may be expected in dev)", error=str(e))

    # Seed the demo client. This is explicitly a non-production operation and
    # raises in production by design, so it is not part of the startup gate.
    try:
        from engine.subscription_routes import ensure_shruhi_surat_pro_client
        await ensure_shruhi_surat_pro_client()
        logger.info("Shruhi Collections (client_srt_shruhi) Surat Pro Tier verified")
    except Exception as e:
        logger.info("Client seeding skipped or failed", error=str(e))

    # Initialize Redis
    try:
        from engine.cache import init_redis
        await init_redis()
        logger.info("Redis connection established")
    except Exception as e:
        if is_production and settings.redis_required:
            raise
        logger.warning("Redis initialization failed", error=str(e))

    # Instrument Redis if available
    try:
        instrument_redis()
    except Exception as e:
        logger.warning("Redis instrumentation failed", error=str(e))

    # Instrument SQLAlchemy
    try:
        instrument_sqlalchemy(db_manager.engine.sync_engine)
    except Exception as e:
        logger.warning("SQLAlchemy instrumentation failed", error=str(e))

    # Start background daemons under BackgroundTaskSupervisor.
    # The sweep is an in-process loop, so it must not run in every API
    # replica. It is enabled only for the dedicated scheduler workload.
    if settings.enable_embedded_scheduler:
        try:
            from engine.supervisor import supervisor
            from engine.scheduler import start_background_scheduler_loop
            supervisor.register(
                "facebook_agent_daemon",
                start_background_scheduler_loop,
                interval_seconds=60,
                max_restarts=10,
                backoff_base_seconds=2.0
            )
            supervisor.start_all()
            logger.info("BackgroundTaskSupervisor initialized and active with Facebook Agent daemon")
        except Exception as e:
            if is_production:
                raise
            logger.warning("BackgroundTaskSupervisor start failed", error=str(e))
    else:
        logger.info("Embedded scheduler disabled for this workload")

    app.state.startup_complete = True
    logger.info("Algorise AI Solutions API started successfully")

    yield

    app.state.startup_complete = False
    logger.info("Shutting down Algorise AI Solutions API")
    try:
        from engine.supervisor import supervisor
        await supervisor.stop_all()
    except Exception as e:
        logger.warning("Supervisor stop exception", error=str(e))
    await db_manager.close()
    from engine.cache import close_redis
    await close_redis()
    from engine.tracing import shutdown_tracing
    shutdown_tracing()
    logger.info("Shutdown complete")


app = FastAPI(
    title="Algorise AI Solutions - 100 Hero Bots API",
    description="Proprietary AI engine with 100 Hero Bots across 10 industry sectors",
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs" if settings.environment != "production" else None,
    redoc_url="/redoc" if settings.environment != "production" else None,
)

# CORS
cors_config = get_cors_config()
app.add_middleware(
    CORSMiddleware,
    **cors_config,
)

# Security headers middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    for header, value in get_security_headers().items():
        response.headers[header] = value
    return response


# HTTP metrics middleware.
# The rollout analysis template and the KEDA autoscaler read these series.
# Without this middleware the counters stay at zero and both the canary
# analysis and the autoscaler operate on an empty signal.
@app.middleware("http")
async def record_http_metrics(request: Request, call_next):
    started = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        duration = time.perf_counter() - started
        HTTP_REQUESTS_TOTAL.labels(
            method=request.method,
            endpoint=request.url.path,
            status_code="500",
        ).inc()
        HTTP_REQUEST_DURATION.labels(
            method=request.method,
            endpoint=request.url.path,
        ).observe(duration)
        raise

    duration = time.perf_counter() - started
    HTTP_REQUESTS_TOTAL.labels(
        method=request.method,
        endpoint=request.url.path,
        status_code=str(response.status_code),
    ).inc()
    HTTP_REQUEST_DURATION.labels(
        method=request.method,
        endpoint=request.url.path,
    ).observe(duration)
    return response


# Instrument FastAPI
instrument_fastapi(app)


# Health & Readiness Probes (Comprehensive System Diagnostics)
@app.get("/livez")
async def liveness_check() -> dict:
    return {"status": "alive"}


@app.get("/health")
@app.get("/api/v1/health")
async def health_check(response: Response):
    from engine.circuit_breaker import BotStepGuard
    from engine.quarantine import dlq
    from engine.cache import redis_manager

    circuits = BotStepGuard.get_all_circuit_states()
    open_circuits = [b for b, s in circuits.items() if s == "open"]
    dlq_count = len(dlq.list_quarantined(unresolved_only=True, limit=10))

    is_degraded = bool(open_circuits)
    status_str = "degraded" if is_degraded else "healthy"

    return {
        "status": status_str,
        "service": "Algorise AI Solutions",
        "version": settings.app_version,
        "environment": settings.environment,
        "circuit_breakers": {
            "total_registered": len(circuits),
            "open_circuits": open_circuits,
            "status": "warning" if open_circuits else "nominal",
        },
        "dead_letter_queue": {
            "pending_quarantined_tasks": dlq_count,
        },
    }


@app.get("/ready")
@app.get("/readyz")
async def readiness_check(response: Response):
    if not getattr(app.state, "startup_complete", False):
        response.status_code = 503
        return {
            "ready": False,
            "checks": {"startup": "initializing"},
        }

    from sqlalchemy import text
    from engine.cache import redis_manager

    # 1. Probe PostgreSQL
    db_healthy = False
    try:
        async with db_manager.session() as session:
            await session.execute(text("SELECT 1"))
        db_healthy = True
    except Exception:
        db_healthy = False

    # 2. Probe Redis
    redis_healthy = False
    try:
        if redis_manager.client:
            redis_healthy = bool(await redis_manager.client.ping())
    except Exception:
        redis_healthy = False

    # Redis is only readiness-critical when the deployment declares it so.
    # A cache outage must not take the API out of rotation.
    is_ready = db_healthy and (redis_healthy or not settings.redis_required)
    if not is_ready:
        response.status_code = 503

    return {
        "ready": is_ready,
        "checks": {
            "startup": "complete",
            "database": "connected" if db_healthy else "disconnected",
            "redis_cache": "connected" if redis_healthy else "disconnected",
        },
    }


@app.get("/api/v1/roi-defense/calculate")
async def calculate_roi_defense(
    ad_spend: float = 150000.0,
    inbound_comments: int = 2500,
    average_order_value: float = 45000.0,
    tier_cost: float = 29999.0,
):
    """Calculates protected revenue and ROI multiplier against competitor poaching."""
    shielded_leads = int(round(inbound_comments * 0.18))
    reclaimed_orders = int(round(shielded_leads * 0.14))
    monthly_reclaimed = float(reclaimed_orders * average_order_value)
    annual_pipeline = monthly_reclaimed * 12.0
    roi_multiplier = round(monthly_reclaimed / tier_cost, 1) if tier_cost > 0 else 0.0

    return {
        "status": "success",
        "inputs": {
            "ad_spend": ad_spend,
            "inbound_comments": inbound_comments,
            "average_order_value": average_order_value,
            "tier_cost": tier_cost,
        },
        "metrics": {
            "shielded_poaching_leads": shielded_leads,
            "poaching_interception_rate": 0.18,
            "qualification_conversion_rate": 0.14,
            "estimated_reclaimed_orders": reclaimed_orders,
            "monthly_reclaimed_revenue": monthly_reclaimed,
            "annual_pipeline_protected": annual_pipeline,
            "roi_multiplier": roi_multiplier,
            "average_reaction_latency_seconds": 0.048,
            "competitor_poaching_window_minutes": 4.2,
        },
    }


# Prometheus metrics endpoint (no auth required in dev)
class TelegramSendRequest(BaseModel):
    """Server-side Telegram send.

    The dashboard previously called api.telegram.org directly from the
    browser with a hardcoded bot token, which published the credential to
    every page visitor. Telegram sends now go through the backend so the
    token stays server-side.

    chat_id is optional: it defaults to TELEGRAM_CHAT_ID from the server
    environment. The dashboard was carrying the literal chat id in 7 places,
    which meant the browser knew the operator's notification destination for
    no reason.
    """

    chat_id: Optional[str] = None
    text: str = Field(min_length=1, max_length=4096)
    parse_mode: Optional[str] = None


@app.post("/api/v1/telegram/send")
async def telegram_send(
    payload: TelegramSendRequest, _: bool = Depends(verify_api_key)
):
    """Proxy a Telegram message. Requires a configured bot token."""
    import os

    from engine.telegram_service import (
        TELEGRAM_DEFAULT_CHAT_ID,
        AlgoriseTelegramService,
        TelegramNotConfigured,
    )

    try:
        service = AlgoriseTelegramService(strict=True)
    except TelegramNotConfigured as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    chat_id = (
        payload.chat_id
        or os.getenv("TELEGRAM_CHAT_ID", "")
        or (str(TELEGRAM_DEFAULT_CHAT_ID) if TELEGRAM_DEFAULT_CHAT_ID else "")
    )
    if not chat_id or chat_id == "0":
        raise HTTPException(
            503,
            "no Telegram destination configured. Set TELEGRAM_CHAT_ID on the "
            "service; the client no longer supplies it.",
        )

    import urllib.request as _urlreq

    body: dict = {"chat_id": chat_id, "text": payload.text}
    if payload.parse_mode:
        body["parse_mode"] = payload.parse_mode
    req = _urlreq.Request(
        f"{service.api_base}/sendMessage",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    try:
        with _urlreq.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=502, detail=f"telegram send failed: {exc}"
        ) from exc


@app.get("/metrics", response_class=PlainTextResponse)
async def metrics():
    return Response(content=get_metrics(), media_type="text/plain")


# Bot execution endpoint (modern FastAPI version with security)
@app.post("/api/v1/bots/execute")
async def execute_bot(
    request: Request,
    auth: tuple = Depends(verify_api_key_dependency),
    _rate_limit = Depends(rate_limit_dependency),
):
    api_key, key_info = auth
    
    # Validate payload
    body = await request.json()
    valid, error = validate_request_payload(body)
    if not valid:
        raise HTTPException(status_code=400, detail=error)
    
    bot_name = body.get("bot_name", "nexus_core")
    input_payload = body.get("input_payload", {})
    
    # Validate query if present
    if "query" in input_payload:
        valid, error = validate_query_string(input_payload["query"])
        if not valid:
            raise HTTPException(status_code=400, detail=error)

    # Check in Hero 100 Registry (O(1) set check)
    if bot_name in HERO_BOT_IDS_SET:
        from engine.metrics import CONCURRENT_BOT_EXECUTIONS, BOT_CRASHES_TOTAL
        loop = asyncio.get_running_loop()
        async with BOT_EXECUTION_SEMAPHORE:
            CONCURRENT_BOT_EXECUTIONS.inc()
            try:
                result = await loop.run_in_executor(None, hero_runner.execute_hero_bot, bot_name, input_payload)
            except Exception as exc:
                BOT_CRASHES_TOTAL.labels(bot_name=bot_name, error_type=type(exc).__name__).inc()
                raise
            finally:
                CONCURRENT_BOT_EXECUTIONS.dec()
        
        # Log API call
        audit_logger.log_api_call(
            client_id=key_info.client_id,
            endpoint="/api/v1/bots/execute",
            method="POST",
            success=result.success,
            details={"bot_name": bot_name, "latency_ms": result.latency_ms},
            ip=request.client.host if request.client else None,
        )
        
        return {
            "task_id": result.task_id,
            "bot": result.bot_name,
            "success": result.success,
            "data": result.data,
            "reasoning_trace": result.reasoning_trace,
            "latency_ms": result.latency_ms,
            "billed_client": key_info.client_name,
        }

    # Log failed attempt
    audit_logger.log_api_call(
        client_id=key_info.client_id,
        endpoint="/api/v1/bots/execute",
        method="POST",
        success=False,
        details={"bot_name": bot_name, "error": "not_found"},
        ip=request.client.host if request.client else None,
    )

    raise HTTPException(
        status_code=404,
        detail=f"Bot '{bot_name}' not found. Available Hero IDs: {list(HERO_BOT_IDS_SET)[:10]}...",
    )


@app.get("/api/v1/bots/list")
async def list_bots(
    auth: tuple = Depends(verify_api_key_dependency),
    _rate_limit = Depends(rate_limit_dependency),
):
    api_key, key_info = auth
    
    bots_list = [
        {
            "bot_id": b[0],
            "name": b[1],
            "sector": b[2],
            "capability": b[3],
            "tuned_confidence": b[4],
            "target_latency_ms": b[5],
        }
        for b in HERO_BOT_DEFINITIONS
    ]
    
    audit_logger.log_api_call(
        client_id=key_info.client_id,
        endpoint="/api/v1/bots/list",
        method="GET",
        success=True,
        details={"count": len(bots_list)},
        ip=None,
    )
    
    return {"total_hero_bots": len(bots_list), "bots": bots_list}


@app.get("/api/v1/tuning/status")
async def tuning_status(
    auth: tuple = Depends(verify_api_key_dependency),
    _rate_limit = Depends(rate_limit_dependency),
):
    api_key, key_info = auth
    
    audit_logger.log_api_call(
        client_id=key_info.client_id,
        endpoint="/api/v1/tuning/status",
        method="GET",
        success=True,
        details={},
        ip=None,
    )
    
    # Return live measured empirical benchmark
    return tuning_engine.get_live_benchmark_status()


# ============================================================================
# MODEL CONTEXT PROTOCOL (MCP) ENDPOINTS
# ============================================================================

@app.get("/api/v1/mcp/tools")
async def mcp_list_tools(
    auth: tuple = Depends(verify_api_key_dependency),
):
    """Returns standardized tool definitions for Model Context Protocol (MCP) clients."""
    return {
        "protocolVersion": mcp_adapter.protocol_version,
        "tools": mcp_adapter.list_tools(),
    }


@app.post("/api/v1/mcp/call")
async def mcp_call_tool(
    request: Request,
    auth: tuple = Depends(verify_api_key_dependency),
):
    """Executes a tool call under Model Context Protocol with Causal Safety Gate pre-flight."""
    body = await request.json()
    tool_name = body.get("name") or body.get("tool_name")
    arguments = body.get("arguments", {})
    if not tool_name:
        raise HTTPException(400, "Missing required 'name' or 'tool_name' field")
    return mcp_adapter.call_tool(tool_name, arguments)


@app.post("/api/v1/mcp")
async def mcp_jsonrpc_endpoint(
    request: Request,
    auth: tuple = Depends(verify_api_key_dependency),
):
    """Standard JSON-RPC 2.0 endpoint for MCP clients (Claude Desktop, Cursor)."""
    body = await request.json()
    return mcp_adapter.handle_jsonrpc(body)


# ============================================================================
# HYBRID GRAPHRAG CONTEXT LAYER ENDPOINTS
# ============================================================================

@app.post("/api/v1/graphrag/query")
async def graphrag_query_endpoint(
    request: Request,
    auth: tuple = Depends(verify_api_key_dependency),
):
    """Traverse and retrieve grounded context from the Algorise Hybrid GraphRAG layer."""
    body = await request.json()
    query = body.get("query", "")
    top_k = int(body.get("top_k", 5))
    return await graph_rag.query_context(query, top_k=top_k)


@app.get("/api/v1/graphrag/stats")
async def graphrag_stats_endpoint(
    auth: tuple = Depends(verify_api_key_dependency),
):
    """Telemetry for the enterprise Knowledge Graph."""
    return {
        "total_nodes": len(graph_rag.nodes),
        "total_edge_sources": len(graph_rag.adjacency),
        "total_vector_documents": len(graph_rag.doc_vectors),
        "node_types": sorted(list({n.node_type for n in graph_rag.nodes.values()})),
    }


# ============================================================================
# DETERMINISTIC CAUSAL SAFETY GATE ENDPOINT
# ============================================================================

@app.post("/api/v1/safety/audit")
async def safety_audit_endpoint(
    request: Request,
    auth: tuple = Depends(verify_api_key_dependency),
):
    body = await request.json()
    action_type = body.get("action_type") or body.get("bot_name") or "general"
    payload = body.get("payload") if "payload" in body else body.get("proposed_action", {})
    audit = safety_gate.audit_detailed(action_type, payload)
    return {
        "is_approved": audit.is_approved,
        "status_code": audit.status_code,
        "risk_score": audit.risk_score,
        "audit_flags": audit.audit_flags,
        "latency_ms": audit.latency_ms,
    }


# Rate limit info endpoint
@app.get("/api/v1/rate-limit/status")
async def rate_limit_status(
    request: Request,
    auth: tuple = Depends(verify_api_key_dependency),
):
    api_key, key_info = auth
    client_ip = request.client.host if request.client else "unknown"
    rate_key = f"{client_ip}:{api_key[:16]}"
    
    info = await rate_limiter.get_rate_limit_info(rate_key)
    return info


# ==============================================================================
# Agentic Flywheel: Autonomous Growth Engine for Shruhi Collections
# ==============================================================================
import time as _time
from dataclasses import asdict, is_dataclass
from engine.growth_engine import CatalogGrowthAgent
from engine.models import BotTask
growth_agent = CatalogGrowthAgent()

def _serialize_bot_res(res):
    if hasattr(res, "model_dump"):
        return res.model_dump()
    elif is_dataclass(res):
        return asdict(res)
    elif hasattr(res, "dict"):
        return res.dict()
    elif isinstance(res, dict):
        return res
    return str(res)

@app.post("/api/v1/growth/audit")
async def growth_catalog_audit(request: Request):
    """Executes technical SEO, pricing, and media plate audit for Shruhi Collections."""
    try:
        body = await request.json()
    except Exception:
        body = {}
    task = BotTask(
        task_id=f"audit_{int(_time.time())}",
        bot_name="growth_engine",
        input_payload={
            "action": "AUDIT_CATALOG",
            "catalog_path": body.get("catalog_path"),
            "storefront_root": body.get("storefront_root")
        }
    )
    result = growth_agent.execute(task)
    return _serialize_bot_res(result)

@app.post("/api/v1/growth/seo-manifest")
async def growth_seo_manifest(request: Request):
    """Generates Schema.org JSON-LD graph and semantic keyword clusters."""
    try:
        body = await request.json()
    except Exception:
        body = {}
    task = BotTask(
        task_id=f"manifest_{int(_time.time())}",
        bot_name="growth_engine",
        input_payload={
            "action": "GENERATE_SCHEMA_GRAPH",
            "catalog_path": body.get("catalog_path")
        }
    )
    result = growth_agent.execute(task)
    return _serialize_bot_res(result)

@app.post("/api/v1/growth/flywheel-sync")
async def growth_flywheel_sync(request: Request):
    """Executes full autonomous Agentic Flywheel sync and persists storefront artifacts."""
    try:
        body = await request.json()
    except Exception:
        body = {}
    task = BotTask(
        task_id=f"sync_{int(_time.time())}",
        bot_name="growth_engine",
        input_payload={
            "action": "FULL_FLYWHEEL_SYNC",
            "catalog_path": body.get("catalog_path"),
            "storefront_root": body.get("storefront_root")
        }
    )
    result = growth_agent.execute(task)
    return _serialize_bot_res(result)


# ==============================================================================
# Autonomous Restock & Margin Optimizer Endpoints
# ==============================================================================
from engine.restock_optimizer import RestockMarginOptimizer
restock_optimizer = RestockMarginOptimizer()

@app.get("/api/v1/growth/restock-advisory")
async def get_restock_advisory():
    """Returns current weaver restock advisory and gross margin economics."""
    catalog_file = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "shruhi-collections", "catalog-data.js"))
    out_file = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "shruhi-collections", "restock-advisory.json"))
    
    if not os.path.exists(out_file) and os.path.exists(catalog_file):
        restock_optimizer.optimize_and_export(catalog_file, out_file)
        
    if os.path.exists(out_file):
        with open(out_file, "r", encoding="utf-8") as f:
            return json.load(f)
    raise HTTPException(status_code=404, detail="Restock advisory not generated")

@app.post("/api/v1/growth/restock-optimize")
async def trigger_restock_optimization(request: Request):
    """Triggers autonomous restock velocity & gross margin calculation across all editions."""
    try:
        body = await request.json()
    except Exception:
        body = {}
    
    catalog_path = body.get("catalog_path")
    if not catalog_path or not os.path.exists(catalog_path):
        catalog_path = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "shruhi-collections", "catalog-data.js"))
        
    output_path = body.get("output_path")
    if not output_path:
        output_path = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "shruhi-collections", "restock-advisory.json"))

    task = BotTask(
        task_id=f"restock_{int(_time.time())}",
        bot_name="restock_optimizer",
        input_payload={
            "catalog_path": catalog_path,
            "output_path": output_path
        }
    )
    result = restock_optimizer.execute(task)
    return _serialize_bot_res(result)

@app.get("/api/v1/supervisor/status")
async def get_supervisor_status():
    """Returns health, heartbeats, and restart telemetry for all supervised background daemons."""
    from engine.supervisor import supervisor
    return supervisor.get_status()


# ==============================================================================
# Multi-Agent Graph Orchestrator Endpoints (Phase 3 Autonomous Framework)
# ==============================================================================
from engine.orchestrator import orchestrator, TaskGraph, AgentTask
import uuid as _uuid

@app.post("/api/v1/orchestrator/execute")
async def execute_task_graph_endpoint(
    request: Request,
    auth: tuple = Depends(verify_api_key_dependency),
):
    """Executes an autonomous DAG task graph across specialized agent bots."""
    api_key, key_info = auth
    try:
        body = await request.json()
    except Exception:
        body = {}
    graph_name = body.get("name", "Autonomous Multi-Agent Workflow")
    tasks_raw = body.get("tasks", [])

    graph = TaskGraph(name=graph_name)
    for t in tasks_raw:
        task = AgentTask(
            task_id=t.get("task_id", f"task_{_uuid.uuid4().hex[:8]}"),
            task_type=t.get("task_type", "nexus"),
            payload=t.get("payload", {}),
            priority=int(t.get("priority", 3)),
            dependencies=t.get("dependencies", []),
        )
        graph.add_task(task)

    return await orchestrator.execute_task_graph(
        graph=graph,
        client_id=key_info.client_id,
        resume_from_checkpoint=body.get("resume", True)
    )

@app.get("/api/v1/orchestrator/bots")
async def list_orchestrator_bots(
    auth: tuple = Depends(verify_api_key_dependency),
):
    """Lists all bots registered in the multi-agent orchestrator."""
    return {
        "registered_bots": list(orchestrator._bot_registry.keys()),
        "max_concurrency": orchestrator.max_concurrency,
    }


# --- Phase 3/4 Autonomous Framework Endpoints: Memory, Anomalies, CRO ---

from engine.memory import agent_memory, MemoryType
from engine.anomaly_detector import anomaly_detector
from engine.cro_engine import cro_engine

@app.post("/api/v1/memory/store")
async def store_memory(
    request: Request,
    auth: tuple = Depends(verify_api_key_dependency),
):
    """Persists a new episodic, semantic, or procedural memory."""
    _, key_info = auth
    body = await request.json()
    mem_id = agent_memory.store(
        memory_type=body.get("memory_type", MemoryType.SEMANTIC),
        client_id=key_info.client_id,
        topic=body.get("topic", "general"),
        content=body.get("content", ""),
        metadata=body.get("metadata", {}),
        confidence_score=float(body.get("confidence_score", 1.0)),
    )
    return {"status": "SUCCESS", "memory_id": mem_id}

@app.post("/api/v1/memory/search")
async def search_memory(
    request: Request,
    auth: tuple = Depends(verify_api_key_dependency),
):
    """Performs semantic vector similarity search over agent memory."""
    _, key_info = auth
    body = await request.json()
    query = body.get("query", "")
    limit = int(body.get("limit", 5))
    results = agent_memory.search(
        query=query,
        client_id=key_info.client_id,
        memory_type=body.get("memory_type"),
        limit=limit,
    )
    return {
        "query": query,
        "results": [
            {"record": rec.to_dict(), "similarity_score": score}
            for rec, score in results
        ],
    }

@app.get("/api/v1/memory/context")
async def get_memory_context(
    query: str,
    limit: int = 3,
    auth: tuple = Depends(verify_api_key_dependency),
):
    """Retrieves formatted context block ready for agent prompt injection."""
    _, key_info = auth
    prompt_text = agent_memory.get_context_prompt(query=query, client_id=key_info.client_id, limit=limit)
    return {"query": query, "context_prompt": prompt_text}

@app.get("/api/v1/anomalies/status")
async def get_anomaly_status(
    auth: tuple = Depends(verify_api_key_dependency),
):
    """Audits system telemetry and returns active anomaly events."""
    is_healthy, anomalies = anomaly_detector.evaluate_system_health()
    return {
        "is_healthy": is_healthy,
        "anomalies_count": len(anomalies),
        "anomalies": [a.to_dict() for a in anomalies],
        "history": [h.to_dict() for h in anomaly_detector.history[-20:]],
    }

@app.post("/api/v1/anomalies/remediate")
async def trigger_anomaly_remediation(
    auth: tuple = Depends(verify_api_key_dependency),
):
    """Executes an immediate self-healing mitigation cycle."""
    return await anomaly_detector.execute_self_healing_cycle()

@app.post("/api/v1/cro/experiments")
async def create_cro_experiment(
    request: Request,
    auth: tuple = Depends(verify_api_key_dependency),
):
    """Creates a new autonomous CRO A/B experiment."""
    _, key_info = auth
    body = await request.json()
    exp = cro_engine.create_experiment(
        client_id=key_info.client_id,
        hypothesis=body.get("hypothesis", ""),
        target_page=body.get("target_page", "index.html"),
        target_metric=body.get("target_metric", "conversion"),
        control_name=body.get("control_name", "Control"),
        control_desc=body.get("control_desc", "Baseline UX"),
        variant_name=body.get("variant_name", "Variant B"),
        variant_desc=body.get("variant_desc", "Optimized Pattern"),
        min_sample_size=int(body.get("min_sample_size", 100)),
    )
    return {"status": "SUCCESS", "experiment": exp.to_dict()}

@app.get("/api/v1/cro/experiments")
async def list_cro_experiments(
    auth: tuple = Depends(verify_api_key_dependency),
):
    """Lists all CRO experiments for the authenticated client."""
    _, key_info = auth
    return {"experiments": cro_engine.list_experiments(client_id=key_info.client_id)}

@app.post("/api/v1/cro/record")
async def record_cro_event(
    request: Request,
    auth: tuple = Depends(verify_api_key_dependency),
):
    """Records an impression or conversion event in a CRO experiment."""
    body = await request.json()
    exp = cro_engine.record_event(
        experiment_id=body.get("experiment_id", ""),
        variant_id=body.get("variant_id", "control"),
        event_type=body.get("event_type", "impression"),
        revenue_inr=float(body.get("revenue_inr", 0.0)),
    )
    if not exp:
        raise HTTPException(status_code=404, detail="Experiment not found or already concluded")
    return {"status": "SUCCESS", "experiment": exp.to_dict()}


# Facebook Agent & Surat B2B Subscription Router

# Meta Graph proxy. The router declares its own /api/v1/meta prefix, so it is
# mounted without an additional one. dashboard.html called graph.facebook.com
# directly from the browser; these endpoints move that traffic server-side and
# record a bot_executions row per operation.

# Attribution. Joins bot_executions -> leads -> outreach_messages and exposes
# the comment-to-revenue funnel. Conversion counts only outcomes a merchant
# recorded, so the funnel cannot manufacture its own evidence.
from engine.attribution import CommentOutcome  # noqa: F401  (registers the table)

# Per-client brand block. Replaces one merchant's phone numbers hardcoded in
# 34 places across the dashboard, which made onboarding a second merchant
# require an HTML edit.

# WhatsApp inbound webhook. The service could send but never receive, so an
# enquiry was invisible unless a browser was open, and the attribution funnel
# had no final hop. Registering the table at import keeps first delivery from
# failing on a missing schema.
from engine.whatsapp_webhook import InboundMessage  # noqa: F401

# Distribution. Targets carry a verification state, and reach is reported as
# verified rather than listed, so an aspirational group list cannot be
# presented as reach.


# --- Routers. The imports are at the top of this file so each router is fully
# built before it is mounted; see the note there. Mounting a partially-built
# router silently registers only some of its routes.
app.include_router(subscription_router, prefix="/api/v1")
app.include_router(meta_proxy_router)
app.include_router(attribution_router)
app.include_router(brand_router)
app.include_router(whatsapp_webhook_router)
app.include_router(distribution_router)

# Mount Full Static Web Platform (Frontend, Client Portal, SEO Pages)
import os
from fastapi.staticfiles import StaticFiles

dist_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "dist")
if not os.path.exists(dist_dir):
    dist_dir = "dist"

# config.js tells the client where the API lives. It is generated at build
# time, but the build step has failed to produce it on at least one deploy,
# and a missing config.js is a 404 the browser hits before any script runs.
# Regenerating here makes the file self-healing: the page cannot load
# without it, so the server must not start without it either.
try:
    import subprocess as _sp
    import sys as _sy

    _r = _sp.run(
        [_sy.executable, os.path.join(os.path.dirname(dist_dir), "scripts", "gen_config.py")],
        capture_output=True, text=True, timeout=120,
    )
    if _r.returncode != 0:
        print(f"WARNING: config.js generation failed: {(_r.stdout + _r.stderr)[-300:]}")
except Exception as _e:  # noqa: BLE001
    print(f"WARNING: could not generate config.js: {_e}")

# The built site is preferred. When it is absent - a fresh checkout, or a
# deploy that skipped the build step - fall back to the repository root so the
# top-level pages still resolve. Returning a JSON body with HTTP 200 for a
# page request is worse than serving the page: it looks healthy to a status
# check while delivering nothing the browser can render.
_fallback_dir = dist_dir if os.path.exists(dist_dir) else os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

if os.path.isdir(_fallback_dir):
    app.mount(
        "/",
        StaticFiles(directory=_fallback_dir, html=True),
        name="static",
    )
else:
    @app.api_route("/{path:path}", methods=["GET", "POST", "OPTIONS"])
    async def legacy_gateway(path: str, request: Request):
        return {"message": f"Endpoint /{path} - use /api/v1/ endpoints instead"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "engine.main:app",
        host=settings.api_host,
        port=settings.api_port,
        workers=settings.api_workers,
        reload=settings.debug,
    )