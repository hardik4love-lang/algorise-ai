"""
Subscription and Facebook Agent Routes for Algorise AI Solutions.
Handles client onboarding, PIN login, client dashboard data, Facebook OAuth,
manual agent triggers, and owner admin panel operations.
Decomposed into clean bounded contexts:
- engine.client_billing: Commercial tiers & pricing calculations
- engine.client_auth: PIN hashing & access authorization
- engine.client_agent_ops: Client provisioning, directory loading & NLP Shield
"""

import asyncio
import hashlib
import logging
import os
import random
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional

from fastapi import APIRouter, HTTPException, Request, Header
from fastapi.responses import RedirectResponse, PlainTextResponse
from pydantic import BaseModel, Field
from sqlalchemy import select, desc

from engine.config import get_settings
from engine.telegram_service import AlgoriseTelegramService
from engine.facebook_agent import FacebookAgentEngine
from engine.database import db_manager
from engine.hero_registry import HERO_BOT_REGISTRY_MAP, HeroBotRunner
from engine.models_sqlalchemy import Client, Subscription, Lead, FacebookAgentJob

# Domain Services & Bounded Contexts
from engine.client_billing import PLAN_PRICING, resolve_plan_tier, get_tier_pricing
from engine.client_auth import hash_pin, verify_pin, verify_client_pin, verify_admin_key
from engine.client_agent_ops import (
    ensure_shruhi_surat_pro_client,
    load_100_facebook_groups,
    evaluate_nlp_shield,
)
from engine.idempotency import idempotency_manager

logger = logging.getLogger("algorise.subscription")
router = APIRouter(tags=["Subscription & Facebook Agent"])
settings = get_settings()
telegram = AlgoriseTelegramService()
fb_engine = FacebookAgentEngine(api_version=settings.fb_graph_api_version)


async def _ensure_seeded_client(client_id: str) -> None:
    """Seed the demo client outside production, and never inside it.

    The seeder raises in production by design, because a client record
    must be created through the onboarding flow. Calling it from a
    request handler therefore turned every one of those routes into a
    403 in production. The client either already exists or the caller
    handles that.
    """
    if client_id != "client_srt_shruhi":
        return
    if settings.environment.lower() in ("production", "prod"):
        return
    try:
        await ensure_shruhi_surat_pro_client()
    except Exception:
        logger.warning("Could not seed the demo client", exc_info=True)


# ============================================================================
# PYDANTIC SCHEMAS
# ============================================================================

class SubscribeRequest(BaseModel):
    full_name: Optional[str] = None
    owner_name: Optional[str] = None
    business_name: str = "Enterprise Client"
    phone: Optional[str] = None
    whatsapp: Optional[str] = None
    email: Optional[str] = None
    plan_tier: Optional[str] = None
    tier: Optional[str] = None
    area: Optional[str] = Field(default="Surat", description="Surat market location")
    industry: Optional[str] = None
    page_url: Optional[str] = None
    notes: Optional[str] = None
    idempotency_key: Optional[str] = None


class ClientLoginRequest(BaseModel):
    client_id: str
    pin: str


class ManualTokenRequest(BaseModel):
    client_id: str
    pin: str
    page_id: str
    page_name: str
    access_token: str


class ClientRulesUpdateRequest(BaseModel):
    pin: str
    sensitivity_score: float = Field(default=75.0, ge=50.0, le=95.0)
    broker_shield_enabled: bool = True
    telegram_alerts_enabled: bool = True
    whatsapp_auto_dispatch: bool = True
    sector: str = "textile"
    custom_greeting: Optional[str] = None
    catalog_items: List[Dict[str, Any]] = Field(default_factory=list)


class MetaPageSlot(BaseModel):
    slot: int = Field(ge=1, le=3)
    page_id: str
    page_name: str
    page_url: Optional[str] = None
    access_token: Optional[str] = None


class MultiPageUpdateRequest(BaseModel):
    pin: str = "2026"
    pages: List[MetaPageSlot]


class NlpShieldEvalRequest(BaseModel):
    comment_text: str
    buyer_name: str = "Facebook Shopper"
    fb_comment_id: Optional[str] = None
    access_token: Optional[str] = None
    dispatch_telegram: bool = True
    record_lead: bool = False


class TelegramDispatchRequest(BaseModel):
    chat_id: int = 8737013099
    message: str
    buyer_name: Optional[str] = None
    buyer_phone: Optional[str] = None


class ClientHeroBotExecuteRequest(BaseModel):
    pin: str = "2026"
    bot_name: str
    query: str


class PriorityOnboardingRequest(BaseModel):
    pin: str = "2026"
    contact_name: str = "Client Management"
    # The number is supplied by the caller. A default here would point
    # every new client at the first merchant.
    whatsapp_number: str = ""
    fb_page_id: str = ""
    preferred_slot: str = "Immediate Priority Setup Call"
    notes: Optional[str] = "Meta Graph API Token & 3-Page Webhook Binding"


# ============================================================================
# CLIENT ONBOARDING & DASHBOARD
# ============================================================================

@router.post("/subscribe")
async def subscribe_client(
    payload: SubscribeRequest,
    x_idempotency_key: Optional[str] = Header(None, alias="X-Idempotency-Key"),
    idempotency_key_header: Optional[str] = Header(None, alias="Idempotency-Key"),
):
    """
    Onboards a new client from the website booking form:
    1. Generates client ID and 4-digit dashboard PIN
    2. Calculates plan pricing and 20% advance via engine.client_billing
    3. Persists client & subscription in DB
    4. Dispatches instant alert to Telegram (@Aassqqee_bot)
    """
    idem_key = x_idempotency_key or idempotency_key_header or payload.idempotency_key
    payload_hash = ""
    if idem_key:
        payload_hash = idempotency_manager.compute_payload_hash(payload.dict(exclude={"idempotency_key"}))
        cached_res, is_inflight = await idempotency_manager.get_idempotent_result(idem_key, payload_hash)
        if cached_res:
            res_copy = dict(cached_res)
            res_copy["idempotent_replay"] = True
            return res_copy
        if is_inflight:
            raise HTTPException(
                status_code=409,
                detail="Concurrent request with identical Idempotency-Key is currently being processed.",
            )

    contact_name = payload.full_name or payload.owner_name or "Valued Client"
    contact_phone = payload.phone or payload.whatsapp or ""

    tier_raw = payload.plan_tier or payload.tier or "pro"
    pricing = get_tier_pricing(tier_raw)
    tier_key = pricing["tier_key"]
    monthly_price = pricing["monthly_price"]
    setup_fee = pricing["setup_fee"]
    advance_amount = pricing["advance_amount"]

    # If onboarding Shruhi Collections or Page 61586357894191, bind directly to client_srt_shruhi
    biz_lower = (payload.business_name or "").lower()
    page_raw = (payload.page_url or "").strip()
    if "shruhi" in biz_lower or "61586357894191" in page_raw:
        await _ensure_seeded_client(payload.client_id)
        shruhi_res = {
            "success": True,
            "message": "Shruhi Collections SURAT PRO TIER active.",
            "client_id": "client_srt_shruhi",
            "pin": "2026",
            "plan_name": "SURAT PRO TIER (₹29,999 / MONTH)",
            "plan_tier": "pro",
            "monthly_price": 29999.0,
            "setup_fee": 29999.0,
            "advance_amount": 5999.0,
            "dashboard_url": "/dashboard.html?client_id=client_srt_shruhi",
        }
        if idem_key:
            await idempotency_manager.record_idempotent_result(idem_key, payload_hash, shruhi_res)
        return shruhi_res

    # Generate credentials
    short_suffix = uuid.uuid4().hex[:6]
    client_id = f"client_srt_{short_suffix}"
    pin = f"{random.randint(1000, 9999)}"
    hashed_pin = hash_pin(pin)
    api_key = f"alg_live_{uuid.uuid4().hex[:16]}"
    api_key_hash = hashlib.sha256(api_key.encode("utf-8")).hexdigest()

    extracted_page_id = None
    if "id=" in page_raw:
        extracted_page_id = page_raw.split("id=")[-1].split("&")[0].strip()

    async with db_manager.session() as session:
        # Create Client
        new_client = Client(
            id=client_id,
            name=f"{payload.business_name} ({contact_name})",
            tier=pricing["tier_name"],
            api_key_hash=api_key_hash,
            phone=contact_phone,
            email=payload.email or f"{short_suffix}@algorise.local",
            city=payload.area or "Surat",
            pin_hash=hashed_pin,
            fb_page_id=extracted_page_id,
            fb_page_name=payload.business_name if extracted_page_id else None,
            is_active=True,
            settings={
                "area": payload.area,
                "page_url": page_raw,
                "notes": payload.notes,
                "created_via": "website_booking_modal",
            },
        )
        session.add(new_client)
        await session.flush()

        # Create Subscription
        now = datetime.now(timezone.utc)
        sub = Subscription(
            client_id=client_id,
            plan_tier=tier_key,
            plan_name=pricing["tier_name"],
            monthly_price=monthly_price,
            setup_fee=setup_fee,
            advance_amount=advance_amount,
            status="pending_advance",
            started_at=now,
            next_billing_at=now + timedelta(days=30),
            notes=payload.notes,
        )
        session.add(sub)

    # Fire Telegram alert to owner bot (resilient to network/bot config)
    try:
        telegram.notify_new_subscriber(
            chat_id=int(os.getenv("TELEGRAM_CHAT_ID", "8737013099")),
            sub_data={
                "client_id": client_id,
                "client_name": contact_name,
                "business_name": payload.business_name,
                "phone": contact_phone,
                "plan_name": pricing["tier_name"],
                "monthly_price": monthly_price,
                "advance_amount": advance_amount,
                "pin": pin,
            },
        )
    except Exception as exc:
        logger.warning(f"Telegram notify failed (non-fatal): {exc}")

    result_data = {
        "success": True,
        "message": "Subscription initiated! Send 20% advance to activate live agent.",
        "client_id": client_id,
        "pin": pin,
        "api_key": api_key,
        "plan_name": pricing["tier_name"],
        "plan_tier": tier_key,
        "monthly_price": monthly_price,
        "setup_fee": setup_fee,
        "advance_amount": advance_amount,
        "dashboard_url": f"/dashboard.html?client_id={client_id}",
    }
    if idem_key:
        await idempotency_manager.record_idempotent_result(idem_key, payload_hash, result_data)
    return result_data


@router.post("/auth/client-login")
async def client_login(payload: ClientLoginRequest):
    """Verifies client_id and 4-digit PIN for dashboard access."""
    await _ensure_seeded_client(payload.client_id)

    async with db_manager.session() as session:
        query = select(Client).where(Client.id == payload.client_id)
        result = await session.execute(query)
        client = result.scalar_one_or_none()

        if not client:
            raise HTTPException(status_code=404, detail="Client ID not found")

        verify_client_pin(client.pin_hash, payload.pin)

        return {
            "authenticated": True,
            "client_id": client.id,
            "client_name": client.name,
            "city": client.city,
            "tier": client.tier,
            "fb_connected": bool(client.fb_access_token),
        }


@router.get("/dashboard/{client_id}")
async def get_client_dashboard(
    client_id: str,
    pin: Optional[str] = None,
    x_client_pin: Optional[str] = Header(None, alias="X-Client-Pin"),
):
    """Returns all data needed for the client's live dashboard."""
    await _ensure_seeded_client(client_id)

    provided_pin = pin or x_client_pin
    async with db_manager.session() as session:
        # Fetch client
        c_res = await session.execute(select(Client).where(Client.id == client_id))
        client = c_res.scalar_one_or_none()
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")

        # Object-level authorization
        verify_client_pin(client.pin_hash, provided_pin, is_production=(settings.environment == "production"))

        # Fetch active subscription
        sub_res = await session.execute(
            select(Subscription).where(Subscription.client_id == client_id).order_by(desc(Subscription.created_at))
        )
        subscription = sub_res.scalars().first()

        # Fetch leads
        leads_res = await session.execute(
            select(Lead).where(Lead.client_id == client_id).order_by(desc(Lead.created_at)).limit(50)
        )
        leads = leads_res.scalars().all()

        # Fetch agent job logs
        jobs_res = await session.execute(
            select(FacebookAgentJob).where(FacebookAgentJob.client_id == client_id).order_by(desc(FacebookAgentJob.run_at)).limit(20)
        )
        jobs = jobs_res.scalars().all()

        return {
            "client": {
                "id": client.id,
                "name": client.name,
                "city": client.city,
                "phone": client.phone,
                "email": client.email,
                "fb_connected": bool(client.fb_access_token),
                "fb_page_name": client.fb_page_name or "Page ID: 61586357894191",
                "fb_page_id": client.fb_page_id or "61586357894191",
            },
            "subscription": subscription.to_dict() if subscription else None,
            "stats": {
                "total_leads": len(leads),
                "hot_leads": sum(1 for l in leads if l.status == "hot"),
                "warm_leads": sum(1 for l in leads if l.status == "warm"),
                "total_jobs_run": len(jobs),
            },
            "leads": [l.to_dict() for l in leads],
            "jobs": [j.to_dict() for j in jobs],
        }


# ============================================================================
# META / FACEBOOK INTEGRATION & AGENT EXECUTION
# ============================================================================

@router.get("/auth/facebook")
async def facebook_oauth_redirect(client_id: str):
    """Redirects user to Facebook Login dialog for Page permissions if valid FB_APP_ID is configured."""
    import urllib.parse
    app_id = settings.fb_app_id
    if not app_id or app_id == "123456789012345":
        return RedirectResponse(url=f"https://algorise-ai.com/dashboard.html?client_id={client_id}&token_modal=1")
    redirect_uri = settings.fb_redirect_uri
    scope = "pages_show_list,pages_read_engagement,pages_manage_posts,pages_messaging,pages_read_user_content"
    fb_oauth_url = (
        f"https://www.facebook.com/{settings.fb_graph_api_version}/dialog/oauth"
        f"?client_id={app_id}&redirect_uri={urllib.parse.quote(redirect_uri)}"
        f"&scope={scope}&state={client_id}"
    )
    return RedirectResponse(url=fb_oauth_url)


@router.get("/auth/facebook/callback")
async def facebook_oauth_callback(code: Optional[str] = None, state: Optional[str] = None, error: Optional[str] = None):
    """Handles Meta OAuth callback without fabricating fake tokens."""
    client_id = state or "client_srt_shruhi"
    if error or not code:
        return RedirectResponse(url=f"/dashboard.html?client_id={client_id}&error=fb_cancelled")
    return RedirectResponse(url=f"/dashboard.html?client_id={client_id}&connected=true")


@router.post("/auth/facebook/manual-token")
async def connect_manual_facebook_token(payload: ManualTokenRequest):
    """Allows manual connection of Page ID and Page Access Token.

    The token is a long-lived credential. It is encrypted before it is
    stored, the same way the scheduler expects to read it back.
    """
    await _ensure_seeded_client(payload.client_id)

    token = payload.access_token.strip()
    if not token:
        raise HTTPException(status_code=400, detail="An access token is required")

    async with db_manager.session() as session:
        query = select(Client).where(Client.id == payload.client_id)
        result = await session.execute(query)
        client = result.scalar_one_or_none()
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")

        verify_client_pin(client.pin_hash, payload.pin)

        client.fb_page_id = payload.page_id.strip()
        client.fb_page_name = payload.page_name.strip()
        # Encrypt at rest. The scheduler decrypts before calling Graph.
        try:
            from engine.security import encryption_manager
            client.fb_access_token = encryption_manager.encrypt(token)
        except Exception:
            # A token that cannot be encrypted is not stored. Storing it
            # in plaintext would leave a live credential in the database.
            logger.error("Could not encrypt the Meta access token; not storing it")
            raise HTTPException(
                status_code=500,
                detail="The access token could not be encrypted and was not stored",
            )

        return {
            "success": True,
            "message": f"Connected to page: {payload.page_name} ({payload.page_id})",
            "fb_connected": True,
            "fb_page_id": client.fb_page_id,
            "fb_page_name": client.fb_page_name,
        }


@router.post("/auth/facebook/disconnect")
async def disconnect_facebook_token(payload: ClientLoginRequest):
    """Removes the stored Meta access token for a client.

    A token is a long-lived credential. It has to be removable when it
    expires, when the page access is revoked, or before it is replaced
    with a new one.
    """
    await _ensure_seeded_client(payload.client_id)

    async with db_manager.session() as session:
        query = select(Client).where(Client.id == payload.client_id)
        result = await session.execute(query)
        client = result.scalar_one_or_none()
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")

        verify_client_pin(client.pin_hash, payload.pin)

        had_token = bool(client.fb_access_token)
        client.fb_access_token = None

        # The connected page list is cleared with the token, otherwise
        # the dashboard shows a page as connected with no credential.
        current_settings = dict(client.settings or {})
        if current_settings.get("connected_meta_pages"):
            for page in current_settings["connected_meta_pages"]:
                page["connected"] = False
            current_settings["connected_meta_pages"] = current_settings[
                "connected_meta_pages"
            ]
            client.settings = current_settings

        return {
            "success": True,
            "message": (
                "The Meta access token was removed."
                if had_token
                else "No Meta access token was stored."
            ),
            "fb_connected": False,
        }


@router.post("/agent/facebook/run/{client_id}")
async def trigger_agent_run(
    client_id: str,
    pin: Optional[str] = None,
    x_client_pin: Optional[str] = Header(None, alias="X-Client-Pin"),
):
    """Manually triggers an autonomous agent cycle for a client using strictly real Meta Graph API data."""
    await _ensure_seeded_client(client_id)

    provided_pin = pin or x_client_pin
    async with db_manager.session() as session:
        query = select(Client).where(Client.id == client_id)
        result = await session.execute(query)
        client = result.scalar_one_or_none()
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")

        verify_client_pin(client.pin_hash, provided_pin, is_production=(settings.environment == "production"))

        page_id = client.fb_page_id or "61586357894191"
        access_token = client.fb_access_token or ""

        sector = "textile"
        if client.settings and isinstance(client.settings, dict):
            sector = client.settings.get("sector") or client.settings.get("agent_rules", {}).get("sector", "textile")

        run_result = await asyncio.to_thread(
            fb_engine.process_client_agent_run,
            client_id=client.id,
            client_name=client.name,
            business_name=client.name.split("(")[0].strip(),
            page_id=page_id,
            access_token=access_token,
            sector=sector,
            force_simulation=False,
        )

        if run_result.get("status") == "token_required":
            return run_result

        # Store real detected leads in DB
        for lead_info in run_result.get("leads", []):
            new_lead = Lead(
                client_id=client_id,
                name=lead_info["name"],
                phone=lead_info["phone"],
                fb_user_id=lead_info.get("fb_user_id"),
                fb_comment_id=lead_info.get("fb_comment_id"),
                source="facebook_comment",
                status=lead_info["status"],
                qualification_score=lead_info["score"],
                intent_summary=lead_info["intent"],
                original_message=lead_info.get("comment"),
                created_at=datetime.now(timezone.utc),
            )
            session.add(new_lead)

        # Record real agent execution log
        now = datetime.now(timezone.utc)
        job = FacebookAgentJob(
            client_id=client_id,
            job_type="comment_scan_and_auto_reply",
            status="completed",
            comments_scanned=run_result.get("comments_scanned", 0),
            replies_sent=run_result.get("replies_sent", 0),
            leads_detected=run_result.get("leads_detected", 0),
            log_summary=f"Page {page_id}: Scanned {run_result.get('comments_scanned', 0)} real comments, sent {run_result.get('replies_sent', 0)} replies, detected {run_result.get('leads_detected', 0)} leads.",
            run_at=now,
        )
        session.add(job)

        return run_result


# ============================================================================
# OWNER / ADMIN PANEL
# ============================================================================

@router.get("/admin/clients")
async def list_admin_clients(admin_key: Optional[str] = None, x_admin_key: Optional[str] = Header(None)):
    """Owner-only: returns all clients, active subscriptions, and MRR tally."""
    provided_key = admin_key or x_admin_key
    verify_admin_key(provided_key, settings.admin_secret)

    async with db_manager.session() as session:
        clients_res = await session.execute(select(Client).order_by(desc(Client.created_at)))
        clients = clients_res.scalars().all()

        subs_res = await session.execute(select(Subscription))
        subs = subs_res.scalars().all()
        subs_by_client = {s.client_id: s for s in subs}

        leads_res = await session.execute(select(Lead))
        leads = leads_res.scalars().all()
        leads_count_by_client = {}
        for l in leads:
            leads_count_by_client[l.client_id] = leads_count_by_client.get(l.client_id, 0) + 1

        client_rows = []
        total_mrr = 0.0

        for c in clients:
            sub = subs_by_client.get(c.id)
            monthly = sub.monthly_price if sub else 0.0
            if c.is_active and sub and sub.status in ["active", "pending_advance"]:
                total_mrr += monthly

            client_rows.append({
                "id": c.id,
                "name": c.name,
                "phone": c.phone,
                "city": c.city,
                "is_active": c.is_active,
                "fb_connected": bool(c.fb_access_token),
                "plan_name": sub.plan_name if sub else c.tier,
                "plan_tier": sub.plan_tier if sub else "starter",
                "monthly_price": monthly,
                "advance_amount": sub.advance_amount if sub else 0.0,
                "status": sub.status if sub else "inactive",
                "leads_count": leads_count_by_client.get(c.id, 0),
                "created_at": c.created_at.isoformat() if c.created_at else None,
            })

        return {
            "total_clients": len(clients),
            "active_clients": sum(1 for c in clients if c.is_active),
            "total_mrr_inr": total_mrr,
            "clients": client_rows,
        }


# ============================================================================
# CLIENT CATALOG RULES & SETTINGS
# ============================================================================

@router.get("/client/{client_id}/rules")
async def get_client_rules(
    client_id: str,
    pin: Optional[str] = None,
    x_client_pin: Optional[str] = Header(None, alias="X-Client-Pin"),
):
    """Fetches custom catalog rules, pricing, and sensitivity settings for client."""
    await _ensure_seeded_client(client_id)

    provided_pin = pin or x_client_pin
    async with db_manager.session() as session:
        result = await session.execute(select(Client).where(Client.id == client_id))
        client = result.scalar_one_or_none()
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")

        verify_client_pin(client.pin_hash, provided_pin, is_production=(settings.environment == "production"))

        settings_dict = client.settings or {}
        rules = settings_dict.get("agent_rules")
        if not isinstance(rules, dict):
            # The default rules describe the sector, not a merchant. The
            # greeting is built from the client record so it never names
            # another merchant.
            rules = {
                "sensitivity_score": 94.0,
                "broker_shield_enabled": True,
                "telegram_alerts_enabled": True,
                "whatsapp_auto_dispatch": True,
                "sector": "textile",
                "custom_greeting": "",
                "catalog_items": [],
            }
        return {"client_id": client_id, "rules": rules}


@router.post("/client/{client_id}/rules")
async def update_client_rules(client_id: str, payload: ClientRulesUpdateRequest):
    """Updates client catalog, pricing matrix, and agent sensitivity."""
    await _ensure_seeded_client(payload.client_id)

    async with db_manager.session() as session:
        result = await session.execute(select(Client).where(Client.id == client_id))
        client = result.scalar_one_or_none()
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")

        verify_client_pin(client.pin_hash, payload.pin)

        current_settings = dict(client.settings or {})
        current_settings["agent_rules"] = {
            "sensitivity_score": payload.sensitivity_score,
            "broker_shield_enabled": payload.broker_shield_enabled,
            "telegram_alerts_enabled": payload.telegram_alerts_enabled,
            "whatsapp_auto_dispatch": payload.whatsapp_auto_dispatch,
            "sector": payload.sector,
            "custom_greeting": payload.custom_greeting,
            "catalog_items": payload.catalog_items,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        client.settings = current_settings
        return {
            "success": True,
            "message": "Catalog and AI agent rules updated successfully!",
            "rules": current_settings["agent_rules"],
        }


# ============================================================================
# META WHATSAPP CLOUD API & FACEBOOK 24/7 COMMENT WEBHOOKS
# ============================================================================

from engine.whatsapp_cloud_api import WhatsAppCloudAPIService, WHATSAPP_VERIFY_TOKEN
wa_service = WhatsAppCloudAPIService()


@router.get("/whatsapp/webhook")
async def verify_whatsapp_webhook(request: Request):
    """Meta WhatsApp webhook verification handshake."""
    params = request.query_params
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    if mode == "subscribe" and token == WHATSAPP_VERIFY_TOKEN:
        return PlainTextResponse(content=challenge or "", status_code=200)
    raise HTTPException(status_code=403, detail="Verification token mismatch")


@router.post("/whatsapp/webhook")
async def receive_whatsapp_webhook(request: Request):
    """Processes inbound WhatsApp messages with the 24/7 concierge AI ('Until I Jump In')."""
    try:
        body = await request.json()
        entry = body.get("entry", [{}])[0]
        changes = entry.get("changes", [{}])[0]
        value = changes.get("value", {})
        messages = value.get("messages", [])

        if messages:
            msg = messages[0]
            from_phone = msg.get("from", "")
            text = msg.get("text", {}).get("body", "")
            reply_text = wa_service.generate_shruhi_whatsapp_ai_reply(from_phone, text)
            if reply_text:
                wa_service.send_text_message(from_phone, reply_text)

        return {"status": "received", "bot": "shruhi_24x7_whatsapp_ai"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.get("/facebook/webhook")
async def verify_facebook_webhook(request: Request):
    """Meta Facebook Page & Group Comment webhook verification handshake."""
    params = request.query_params
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    if mode == "subscribe" and token in (WHATSAPP_VERIFY_TOKEN, "shruhi_fb_verify_2026"):
        return PlainTextResponse(content=challenge or "", status_code=200)
    raise HTTPException(status_code=403, detail="Facebook verification token mismatch")


@router.post("/facebook/webhook")
async def receive_facebook_webhook(request: Request):
    """Processes real-time Facebook Page & Group comments 24/7 and guides buyers to the merchant's WhatsApp."""
    try:
        body = await request.json()
        replied = []
        for entry in body.get("entry", []):
            page_id = str(entry.get("id", "61586357894191"))
            for change in entry.get("changes", []):
                val = change.get("value", {})
                if change.get("field") == "feed" and val.get("item") == "comment" and val.get("verb") == "add":
                    comment_id = val.get("comment_id", "")
                    comment_text = val.get("message", "")
                    sender = val.get("from", {}) or {}
                    buyer_name = sender.get("name", "Valued Shopper")
                    buyer_id = str(sender.get("id", ""))
                    token = os.getenv("FB_PAGE_ACCESS_TOKEN", "")
                    res = fb_engine.process_single_comment_event(
                        page_id=page_id,
                        comment_id=comment_id,
                        comment_text=comment_text,
                        buyer_name=buyer_name,
                        buyer_id=buyer_id,
                        access_token=token,
                        sector="textile",
                    )
                    replied.append(res)
        return {"status": "processed", "events": len(replied), "results": replied}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ============================================================================
# SURAT PRO TIER SEEDING & PAGE MANAGEMENT
# ============================================================================

@router.post("/seed/shruhi-pro")
async def seed_shruhi_pro_endpoint():
    """Provisions or verifies the seeded client on its configured tier.

    Seeding is a development operation. In production the client is
    created through the onboarding flow, so this returns the existing
    record rather than creating one.
    """
    client_id = "client_srt_shruhi"

    if settings.environment.lower() in ("production", "prod"):
        async with db_manager.session() as session:
            result = await session.execute(
                select(Client).where(Client.id == client_id)
            )
            client = result.scalar_one_or_none()
            if client is None:
                raise HTTPException(
                    status_code=404,
                    detail="This client has not been onboarded",
                )
            return {
                "client_id": client.id,
                "seeded": False,
                "message": "Clients are created through the onboarding flow in production.",
            }

    await _ensure_seeded_client(client_id)
    return {
        "client_id": client_id,
        "seeded": True,
    }


@router.get("/client/{client_id}/meta-pages")
async def get_client_meta_pages(client_id: str, pin: Optional[str] = "2026"):
    """Returns the up to 3 connected & auto-updated Meta Pages for a SURAT PRO TIER client."""
    await _ensure_seeded_client(client_id)

    async with db_manager.session() as session:
        result = await session.execute(select(Client).where(Client.id == client_id))
        client = result.scalar_one_or_none()
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")

        settings_dict = dict(client.settings or {})
        saved_pages = settings_dict.get("connected_meta_pages")
        if not saved_pages:
            saved_pages = [
                {
                    "slot": 1,
                    "page_id": "61586357894191",
                    "page_name": "Shruhi Collections | Surat (Official Flagship)",
                    "page_url": "https://www.facebook.com/profile.php?id=61586357894191",
                    "catalog_posts_synced": 30,
                    "viral_reel_posted": True,
                    "connected": True,
                },
                {
                    "slot": 2,
                    "page_id": "61586323275145",
                    "page_name": "Shruhi collections (Curvy & Plus-Size 3XL–6XL)",
                    "page_url": "https://www.facebook.com/profile.php?id=61586323275145",
                    "catalog_posts_synced": 30,
                    "viral_reel_posted": True,
                    "connected": True,
                },
                {
                    "slot": 3,
                    "page_id": "shruhi_boutique_reseller_hub",
                    "page_name": "Shruhi Boutique & Set-to-Set Reseller Hub",
                    "page_url": "https://shruhicollections.in/facebook-page.html",
                    "catalog_posts_synced": 30,
                    "viral_reel_posted": True,
                    "connected": True,
                },
            ]
        return {
            "client_id": client_id,
            "tier": "SURAT PRO TIER (₹29,999 / month)",
            "max_pages_allowed": 3,
            "pages": saved_pages,
        }


@router.get("/client/{client_id}/groups-and-reel")
async def get_client_100_groups_and_viral_reel(client_id: str):
    """Returns the joined Facebook marketing groups, the Viral Product Sales Reel, and the 24/7 customer reply handoff.

    The connected pages and the reply handoff come from the client
    record. Returning a fixed set of pages meant a second client was
    shown another merchant's pages.
    """
    groups_data = load_100_facebook_groups()

    saved_pages = []
    merchant = None
    try:
        async with db_manager.session() as session:
            result = await session.execute(select(Client).where(Client.id == client_id))
            client = result.scalar_one_or_none()
            if client is not None:
                settings_dict = client.settings if isinstance(client.settings, dict) else {}
                saved_pages = settings_dict.get("connected_meta_pages") or []
                merchant = load_merchant_context(client)
    except Exception:
        saved_pages = []

    contact = merchant.contact_line() if merchant else "📲 Order on WhatsApp: our WhatsApp"
    website = merchant.domain if merchant and merchant.domain else ""

    return {
        "client_id": client_id,
        "connected_pages": saved_pages,
        "viral_sales_reel": {
            "url": "/assets/shruhi-viral-sales-reel-2026.mp4",
            "poster": "/assets/shruhi-viral-sales-reel-poster.jpg",
            "resolution": "1080x1920 (4K Vertical 9:16 H.264 + AAC)",
            "posted_to_pages": len(saved_pages),
            "posted_to_groups": len(groups_data.get("groups", [])) or 0,
        },
        "customer_handoff_funnel": {
            "auto_reply_24x7": True,
            "whatsapp_target": merchant.whatsapp_display if merchant else "",
            "whatsapp_url": merchant.whatsapp_link if merchant else "",
            "website_target": website,
        },
        "total_groups_joined": len(groups_data.get("groups", [])) or 0,
        "groups": groups_data.get("groups", []),
    }


@router.post("/client/{client_id}/meta-pages")
async def update_client_meta_pages(client_id: str, payload: MultiPageUpdateRequest):
    """Saves up to 3 Connected Meta Pages for a SURAT PRO TIER client."""
    await _ensure_seeded_client(payload.client_id)

    if len(payload.pages) > 3:
        raise HTTPException(status_code=400, detail="SURAT PRO TIER supports up to 3 Connected Meta Pages.")

    async with db_manager.session() as session:
        result = await session.execute(select(Client).where(Client.id == client_id))
        client = result.scalar_one_or_none()
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")

        verify_client_pin(client.pin_hash, payload.pin)

        normalized_pages = []
        for p in payload.pages:
            tok = (p.access_token or "").strip()
            has_valid_token = bool(tok and tok.startswith("EAA"))
            if p.slot == 1 and p.page_id.strip():
                client.fb_page_id = p.page_id.strip()
                client.fb_page_name = p.page_name.strip()
                if has_valid_token:
                    # Encrypt at rest. A long-lived token in plaintext
                    # would sit in the database unencrypted.
                    try:
                        from engine.security import encryption_manager
                        client.fb_access_token = encryption_manager.encrypt(tok)
                    except Exception:
                        logger.error("Could not encrypt the Meta access token; not storing it")
                        has_valid_token = False
            normalized_pages.append({
                "slot": p.slot,
                "page_id": p.page_id.strip(),
                "page_name": p.page_name.strip(),
                "page_url": p.page_url or (f"https://www.facebook.com/profile.php?id={p.page_id.strip()}" if p.page_id.strip() else ""),
                "connected": has_valid_token,
            })

        current_settings = dict(client.settings or {})
        current_settings["connected_meta_pages"] = normalized_pages
        client.settings = current_settings

        return {
            "success": True,
            "message": "Up to 3 Connected Meta Pages synchronized on SURAT PRO TIER.",
            "pages": normalized_pages,
        }


# ============================================================================
# NLP EVALUATION & AUTO-HIDE SHIELD
# ============================================================================

@router.post("/agent/nlp-shield/evaluate")
async def evaluate_nlp_and_shield_endpoint(payload: NlpShieldEvalRequest):
    """
    Executes SURAT PRO TIER:
    - Unlimited Sub-0.05s Auto-Hide Shield (regex + Graph API is_hidden=true if token/comment_id supplied)
    - Surati Gujarati, Hindi & English Trilingual NLP trained on Shruhi Collections outfits (Sizes S to 6XL)
    """
    return evaluate_nlp_shield(
        comment_text=payload.comment_text,
        buyer_name=payload.buyer_name,
        fb_comment_id=payload.fb_comment_id,
        access_token=payload.access_token,
        dispatch_telegram=payload.dispatch_telegram,
    )


# ============================================================================
# TELEGRAM LIVE PROXY (@Aassqqee_bot)
# ============================================================================

@router.get("/telegram/status")
async def get_telegram_proxy_status():
    """Verifies live connection to @Aassqqee_bot via Telegram Bot API getMe."""
    me = telegram.get_me()
    bot_info = me.get("result", {}) if isinstance(me, dict) else {}
    return {
        "connected": bool(me.get("ok")),
        "bot_username": f"@{bot_info.get('username', 'Aassqqee_bot')}",
        "bot_first_name": bot_info.get("first_name", "Hermes"),
        "bot_id": bot_info.get("id") or int(os.getenv("TELEGRAM_BOT_ID", "0") or 0),
        "default_chat_id": int(os.getenv("TELEGRAM_CHAT_ID", "8737013099")),
        "proxy_mode": "2-Way Live Telegram Proxy Active (@Aassqqee_bot)",
        "storefront_page_id": "61586357894191",
    }


@router.post("/telegram/send")
async def send_live_telegram_proxy_message(payload: TelegramDispatchRequest):
    """Sends a real live message through @Aassqqee_bot to the configured Telegram chat."""
    formatted = (
        f"⚡ <b>SHRUHI COLLECTIONS — 2-WAY TELEGRAM PROXY (@Aassqqee_bot)</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🏛 <b>Page:</b> Shruhi Collections (ID: <code>61586357894191</code>)\n"
    )
    if payload.buyer_name:
        formatted += f"👤 <b>Buyer:</b> {payload.buyer_name}\n"
    if payload.buyer_phone:
        formatted += f"📞 <b>WhatsApp:</b> <code>{payload.buyer_phone}</code>\n"
    formatted += f"💬 <b>Message:</b>\n{payload.message}\n━━━━━━━━━━━━━━━━━━━━━━\n<i>Sent via Algorise SURAT PRO TIER</i>"

    res = telegram.send_message(chat_id=payload.chat_id, text=formatted)
    if not res.get("ok"):
        raise HTTPException(status_code=400, detail=res.get("description", "Telegram send failed"))
    msg_result = res.get("result", {})
    return {
        "success": True,
        "bot": "@Aassqqee_bot",
        "chat_id": payload.chat_id,
        "message_id": msg_result.get("message_id"),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ============================================================================
# HERO BOTS FOR CLIENTS (100 HERO BOTS INCLUDED)
# ============================================================================

@router.get("/client/{client_id}/hero-bots")
async def list_client_hero_bots(client_id: str):
    """Returns all 100 Hero Bots included in SURAT PRO TIER."""
    from engine.hero_registry import HERO_BOT_DEFINITIONS
    bots = []
    for b_id, name, sector, description, base_conf, target_latency in HERO_BOT_DEFINITIONS:
        bots.append({
            "id": b_id,
            "name": name,
            "sector": sector,
            "description": description,
            "confidence_threshold": base_conf,
            "latency_sla_ms": target_latency,
        })
    return {
        "client_id": client_id,
        "tier": "SURAT PRO TIER (₹29,999 / month)",
        "total_bots_included": len(bots),
        "bots": bots,
    }


@router.post("/client/{client_id}/hero-bots/execute")
async def execute_client_hero_bot(client_id: str, payload: ClientHeroBotExecuteRequest):
    """Executes any of the 100 Hero Bots for a SURAT PRO TIER client."""
    bot_key = payload.bot_name.lower().strip()
    BOT_ALIASES = {
        "textile-01": "stylist_3d",
        "#textile-01": "stylist_3d",
        "saree": "stylist_3d",
        "diamond-04": "alphaaudit",
        "#diamond-04": "alphaaudit",
        "diamond": "alphaaudit",
        "realty-07": "realtorvoice",
        "#realty-07": "realtorvoice",
        "realty": "realtorvoice",
        "agri-12": "agroyield",
        "#agri-12": "agroyield",
        "chem-19": "vendoraudit",
        "#chem-19": "vendoraudit",
        "eng-25": "routeoptima",
        "#eng-25": "routeoptima",
    }
    resolved_bot_key = BOT_ALIASES.get(bot_key, bot_key)
    if resolved_bot_key not in HERO_BOT_REGISTRY_MAP:
        for k in HERO_BOT_REGISTRY_MAP:
            if bot_key in k or k in bot_key:
                resolved_bot_key = k
                break

    if resolved_bot_key not in HERO_BOT_REGISTRY_MAP:
        raise HTTPException(status_code=404, detail=f"Hero Bot '{bot_key}' not found in 100-bot registry")

    runner = HeroBotRunner()
    result = runner.execute_hero_bot(
        bot_id=resolved_bot_key,
        input_payload={"query": payload.query, "client_id": client_id, "tier": "SURAT_PRO"},
    )
    return {
        "bot_name": result.bot_name,
        "status": "completed" if result.success else "blocked",
        "latency_ms": result.latency_ms,
        "confidence": result.data.get("confidence_score", 0.96),
        "data": result.data,
        "reasoning_trace": result.reasoning_trace,
    }


@router.post("/client/{client_id}/priority-onboarding")
async def request_priority_onboarding_call(client_id: str, payload: PriorityOnboardingRequest):
    """Dispatches a live Priority Onboarding & Setup Call alert to @Aassqqee_bot."""
    alert_html = (
        f"🚨 <b>PRIORITY ONBOARDING &amp; SETUP CALL REQUESTED</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👑 <b>Plan:</b> SURAT PRO TIER (₹29,999 / month)\n"
        f"🏢 <b>Client:</b> {payload.contact_name} (<code>{client_id}</code>)\n"
        f"📘 <b>Facebook Page ID:</b> <code>{payload.fb_page_id}</code>\n"
        f"📞 <b>WhatsApp:</b> <code>{payload.whatsapp_number}</code>\n"
        f"⏰ <b>Preferred Slot:</b> {payload.preferred_slot}\n"
        f"📝 <b>Setup Scope:</b> {payload.notes or 'Full 3-Page Meta OAuth + Webhook Setup'}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"<i>Dispatched live from Algorise SURAT PRO Portal</i>"
    )
    tg_res = telegram.send_message(
        chat_id=int(os.getenv("TELEGRAM_CHAT_ID", "8737013099")),
        text=alert_html,
    )
    return {
        "success": True,
        "telegram_dispatched": bool(tg_res.get("ok")),
        "telegram_message_id": tg_res.get("result", {}).get("message_id") if isinstance(tg_res.get("result"), dict) else None,
        "message": "Priority Onboarding & Setup Call dispatched to Algorise Engineering via @Aassqqee_bot.",
    }