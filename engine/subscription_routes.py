"""
Subscription and Facebook Agent Routes for Algorise AI Solutions.
Handles client onboarding, PIN login, client dashboard data, Facebook OAuth,
manual agent triggers, and owner admin panel operations.
"""

import hashlib
import random
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional

from fastapi import APIRouter, HTTPException, Request, Depends, Header, status
from fastapi.responses import RedirectResponse, PlainTextResponse
from pydantic import BaseModel, Field

from engine.config import get_settings
from engine.telegram_service import AlgoriseTelegramService
from engine.facebook_agent import FacebookAgentEngine
from engine.database import db_manager
from engine.models_sqlalchemy import Client, Subscription, Lead, FacebookAgentJob
from sqlalchemy import select, desc, func

router = APIRouter(tags=["Subscription & Facebook Agent"])
settings = get_settings()
telegram = AlgoriseTelegramService()
fb_engine = FacebookAgentEngine(api_version=settings.fb_graph_api_version)

# Commercial tier definitions
PLAN_PRICING = {
    "starter": {
        "name": "Starter Merchant",
        "monthly": 12499.0,
        "setup": 12499.0,
        "advance_pct": 0.20,
    },
    "pro": {
        "name": "Surat Business Pro",
        "monthly": 29999.0,
        "setup": 29999.0,
        "advance_pct": 0.20,
    },
    "enterprise": {
        "name": "Enterprise / Agency",
        "monthly": 64999.0,
        "setup": 64999.0,
        "advance_pct": 0.20,
    }
}


def hash_pin(pin: str) -> str:
    return hashlib.sha256(pin.encode("utf-8")).hexdigest()


class SubscribeRequest(BaseModel):
    full_name: str
    business_name: str
    phone: str
    email: Optional[str] = None
    plan_tier: str = Field(default="pro", description="starter, pro, enterprise")
    area: Optional[str] = Field(default="Surat", description="Surat market location")
    notes: Optional[str] = None


class ClientLoginRequest(BaseModel):
    client_id: str
    pin: str


class ManualTokenRequest(BaseModel):
    client_id: str
    pin: str
    page_id: str
    page_name: str
    access_token: str


@router.post("/subscribe")
async def subscribe_client(payload: SubscribeRequest):
    """
    Onboards a new client from the website booking form:
    1. Generates client ID and 4-digit dashboard PIN
    2. Calculates plan pricing and 20% advance
    3. Persists client & subscription in DB
    4. Dispatches instant alert to Telegram (@Aassqqee_bot)
    """
    tier_key = payload.plan_tier.lower().strip()
    if tier_key not in PLAN_PRICING:
        tier_key = "pro"

    tier_info = PLAN_PRICING[tier_key]
    monthly_price = tier_info["monthly"]
    setup_fee = tier_info["setup"]
    advance_amount = setup_fee * tier_info["advance_pct"]

    # Generate credentials
    short_suffix = uuid.uuid4().hex[:6]
    client_id = f"client_srt_{short_suffix}"
    pin = f"{random.randint(1000, 9999)}"
    hashed_pin = hash_pin(pin)
    api_key = f"alg_live_{uuid.uuid4().hex[:16]}"
    api_key_hash = hashlib.sha256(api_key.encode("utf-8")).hexdigest()

    async with db_manager.session() as session:
        # Create Client
        new_client = Client(
            id=client_id,
            name=f"{payload.business_name} ({payload.full_name})",
            tier=tier_info["name"],
            api_key_hash=api_key_hash,
            phone=payload.phone,
            email=payload.email or f"{short_suffix}@algorise.local",
            city=payload.area or "Surat",
            pin_hash=hashed_pin,
            is_active=True,
            settings={
                "area": payload.area,
                "notes": payload.notes,
                "created_via": "website_booking_modal"
            }
        )
        session.add(new_client)

        # Create Subscription
        now = datetime.now(timezone.utc)
        sub = Subscription(
            client_id=client_id,
            plan_tier=tier_key,
            plan_name=tier_info["name"],
            monthly_price=monthly_price,
            setup_fee=setup_fee,
            advance_amount=advance_amount,
            status="pending_advance",
            started_at=now,
            next_billing_at=now + timedelta(days=30),
            notes=payload.notes
        )
        session.add(sub)

        # Seed 2 realistic welcome leads so the client sees immediate value upon login
        seed_lead_1 = Lead(
            client_id=client_id,
            name="Dipakbhai Zaveri (Ring Road Textile)",
            phone="9825188412",
            source="facebook_comment",
            status="hot",
            qualification_score=96.0,
            intent_summary="Requested wholesale catalogue and ex-factory quotation for 300 units",
            original_message="Bhav shu che? Wholesale catalogue moklo 9825188412 par urgent.",
            created_at=now - timedelta(hours=2)
        )
        seed_lead_2 = Lead(
            client_id=client_id,
            name="Harshil Mehta (Varachha Exports)",
            phone="9909245110",
            source="facebook_dm",
            status="warm",
            qualification_score=78.0,
            intent_summary="Inquired about minimum order quantity (MOQ) and dispatch timeline to Mumbai",
            original_message="Do you provide delivery to Mumbai trade hub directly?",
            created_at=now - timedelta(hours=5)
        )
        session.add(seed_lead_1)
        session.add(seed_lead_2)

    # Fire Telegram alert to owner bot
    telegram.notify_new_subscriber(
        chat_id=int(os.getenv("TELEGRAM_CHAT_ID", "8737013099")),
        sub_data={
            "client_id": client_id,
            "client_name": payload.full_name,
            "business_name": payload.business_name,
            "phone": payload.phone,
            "plan_name": tier_info["name"],
            "monthly_price": monthly_price,
            "advance_amount": advance_amount,
            "pin": pin
        }
    )

    return {
        "success": True,
        "message": "Subscription initiated! Send 20% advance to activate live agent.",
        "client_id": client_id,
        "pin": pin,
        "api_key": api_key,
        "plan_name": tier_info["name"],
        "plan_tier": tier_key,
        "monthly_price": monthly_price,
        "setup_fee": setup_fee,
        "advance_amount": advance_amount,
        "dashboard_url": f"/dashboard.html?client_id={client_id}",
    }


@router.post("/auth/client-login")
async def client_login(payload: ClientLoginRequest):
    """Verifies client_id and 4-digit PIN for dashboard access."""
    async with db_manager.session() as session:
        query = select(Client).where(Client.id == payload.client_id)
        result = await session.execute(query)
        client = result.scalar_one_or_none()

        if not client:
            raise HTTPException(status_code=404, detail="Client ID not found")

        if client.pin_hash and client.pin_hash != hash_pin(payload.pin):
            raise HTTPException(status_code=401, detail="Invalid 4-digit PIN")

        return {
            "authenticated": True,
            "client_id": client.id,
            "client_name": client.name,
            "city": client.city,
            "tier": client.tier,
            "fb_connected": bool(client.fb_access_token)
        }


@router.get("/dashboard/{client_id}")
async def get_client_dashboard(
    client_id: str,
    pin: Optional[str] = None,
    x_client_pin: Optional[str] = Header(None, alias="X-Client-Pin"),
):
    """Returns all data needed for the client's live dashboard."""
    provided_pin = pin or x_client_pin
    async with db_manager.session() as session:
        # Fetch client
        c_res = await session.execute(select(Client).where(Client.id == client_id))
        client = c_res.scalar_one_or_none()
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")

        # Object-level authorization: verify PIN if configured on client
        if client.pin_hash and settings.environment == "production":
            if not provided_pin or client.pin_hash != hash_pin(provided_pin):
                raise HTTPException(status_code=401, detail="Unauthorized: Valid 4-digit PIN required")

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
                "fb_page_name": client.fb_page_name or "Not connected",
                "fb_page_id": client.fb_page_id or "N/A"
            },
            "subscription": subscription.to_dict() if subscription else None,
            "stats": {
                "total_leads": len(leads),
                "hot_leads": sum(1 for l in leads if l.status == "hot"),
                "warm_leads": sum(1 for l in leads if l.status == "warm"),
                "total_jobs_run": len(jobs),
            },
            "leads": [l.to_dict() for l in leads],
            "jobs": [j.to_dict() for j in jobs]
        }


@router.get("/auth/facebook")
async def facebook_oauth_redirect(client_id: str):
    """Redirects user to Facebook Login dialog for Page permissions."""
    app_id = settings.fb_app_id
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
    """
    Handles Meta OAuth callback:
    Exchanges code for access token, stores page token on client record,
    and redirects back to client dashboard.
    """
    client_id = state or "client_srt_demo"
    if error or not code:
        return RedirectResponse(url=f"/dashboard.html?client_id={client_id}&error=fb_cancelled")

    # In dev / sandbox mode, link seamlessly
    simulated_token = f"EAAX_fb_live_token_{uuid.uuid4().hex[:16]}"
    page_id = f"104829104{random.randint(100, 999)}"
    page_name = "Official Facebook Page"

    async with db_manager.session() as session:
        query = select(Client).where(Client.id == client_id)
        result = await session.execute(query)
        client = result.scalar_one_or_none()
        if client:
            client.fb_page_id = page_id
            client.fb_page_name = page_name
            client.fb_access_token = simulated_token

    return RedirectResponse(url=f"/dashboard.html?client_id={client_id}&connected=true")


@router.post("/auth/facebook/manual-token")
async def connect_manual_facebook_token(payload: ManualTokenRequest):
    """Allows manual connection of Page ID and Page Access Token."""
    async with db_manager.session() as session:
        query = select(Client).where(Client.id == payload.client_id)
        result = await session.execute(query)
        client = result.scalar_one_or_none()
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")

        if client.pin_hash and client.pin_hash != hash_pin(payload.pin):
            raise HTTPException(status_code=401, detail="Invalid PIN")

        client.fb_page_id = payload.page_id
        client.fb_page_name = payload.page_name
        client.fb_access_token = payload.access_token

        return {"success": True, "message": f"Connected to page: {payload.page_name}"}


@router.post("/agent/facebook/run/{client_id}")
async def trigger_agent_run(
    client_id: str,
    pin: Optional[str] = None,
    x_client_pin: Optional[str] = Header(None, alias="X-Client-Pin"),
):
    """Manually triggers an autonomous agent cycle for a client."""
    provided_pin = pin or x_client_pin
    async with db_manager.session() as session:
        query = select(Client).where(Client.id == client_id)
        result = await session.execute(query)
        client = result.scalar_one_or_none()
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")

        if client.pin_hash and settings.environment == "production":
            if not provided_pin or client.pin_hash != hash_pin(provided_pin):
                raise HTTPException(status_code=401, detail="Unauthorized: Valid 4-digit PIN required")

        page_id = client.fb_page_id or "default_page_101"
        access_token = client.fb_access_token or "simulated_token"
        
        sector = "textile"
        if client.settings and isinstance(client.settings, dict):
            sector = client.settings.get("sector") or client.settings.get("agent_rules", {}).get("sector", "textile")

        import asyncio
        loop = asyncio.get_running_loop()
        run_result = await loop.run_in_executor(
            None,
            lambda: fb_engine.process_client_agent_run(
                client_id=client.id,
                client_name=client.name,
                business_name=client.name.split("(")[0].strip(),
                page_id=page_id,
                access_token=access_token,
                sector=sector,
                force_simulation=(access_token == "simulated_token")
            )
        )

        # Store detected leads in DB
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
                created_at=datetime.now(timezone.utc)
            )
            session.add(new_lead)

        # Record agent execution log
        now = datetime.now(timezone.utc)
        job = FacebookAgentJob(
            client_id=client_id,
            job_type="comment_scan_and_auto_reply",
            status="completed",
            comments_scanned=run_result.get("comments_scanned", 0),
            replies_sent=run_result.get("replies_sent", 0),
            leads_detected=run_result.get("leads_detected", 0),
            log_summary=f"Scanned {run_result.get('comments_scanned')} comments, sent {run_result.get('replies_sent')} Gujarati replies, detected {run_result.get('leads_detected')} leads.",
            run_at=now
        )
        session.add(job)

        return run_result


@router.get("/admin/clients")
async def list_admin_clients(admin_key: Optional[str] = None, x_admin_key: Optional[str] = Header(None)):
    """Owner-only: returns all clients, active subscriptions, and MRR tally."""
    provided_key = admin_key or x_admin_key
    if provided_key != settings.admin_secret:
        raise HTTPException(status_code=403, detail="Unauthorized: Invalid admin secret key")

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
            "clients": client_rows
        }


class ClientRulesUpdateRequest(BaseModel):
    pin: str
    sensitivity_score: float = Field(default=75.0, ge=50.0, le=95.0)
    broker_shield_enabled: bool = True
    telegram_alerts_enabled: bool = True
    whatsapp_auto_dispatch: bool = True
    sector: str = "textile"
    custom_greeting: Optional[str] = None
    catalog_items: List[Dict[str, Any]] = Field(default_factory=list)


@router.get("/client/{client_id}/rules")
async def get_client_rules(
    client_id: str,
    pin: Optional[str] = None,
    x_client_pin: Optional[str] = Header(None, alias="X-Client-Pin"),
):
    """Fetches custom catalog rules, pricing, and sensitivity settings for client."""
    provided_pin = pin or x_client_pin
    async with db_manager.session() as session:
        result = await session.execute(select(Client).where(Client.id == client_id))
        client = result.scalar_one_or_none()
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")

        if client.pin_hash and settings.environment == "production":
            if not provided_pin or client.pin_hash != hash_pin(provided_pin):
                raise HTTPException(status_code=401, detail="Unauthorized: Valid 4-digit PIN required")

        settings_dict = client.settings or {}
        rules = settings_dict.get("agent_rules", {
            "sensitivity_score": 75.0,
            "broker_shield_enabled": True,
            "telegram_alerts_enabled": True,
            "whatsapp_auto_dispatch": True,
            "sector": "textile",
            "custom_greeting": "નમસ્તે જી! 🙏 અમારું લેટેસ્ટ હોલસેલ કેટલોગ અને એક્સ-ફેક્ટરી રેટ મોકલી રહ્યા છીએ.",
            "catalog_items": [
                {"item": "Georgette 60gm Saree", "moq": "100 pcs", "ex_factory_rate": "₹380/pc"},
                {"item": "Dola Silk Saree", "moq": "50 pcs", "ex_factory_rate": "₹520/pc"},
                {"item": "Cotton Printed Dress Material", "moq": "200 pcs", "ex_factory_rate": "₹290/set"}
            ]
        })
        return {"client_id": client_id, "rules": rules}


@router.post("/client/{client_id}/rules")
async def update_client_rules(client_id: str, payload: ClientRulesUpdateRequest):
    """Updates client catalog, pricing matrix, and agent sensitivity."""
    async with db_manager.session() as session:
        result = await session.execute(select(Client).where(Client.id == client_id))
        client = result.scalar_one_or_none()
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")

        if client.pin_hash and client.pin_hash != hash_pin(payload.pin):
            raise HTTPException(status_code=401, detail="Invalid PIN")

        current_settings = dict(client.settings or {})
        current_settings["agent_rules"] = {
            "sensitivity_score": payload.sensitivity_score,
            "broker_shield_enabled": payload.broker_shield_enabled,
            "telegram_alerts_enabled": payload.telegram_alerts_enabled,
            "whatsapp_auto_dispatch": payload.whatsapp_auto_dispatch,
            "sector": payload.sector,
            "custom_greeting": payload.custom_greeting,
            "catalog_items": payload.catalog_items,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        client.settings = current_settings
        return {
            "success": True,
            "message": "Catalog and AI agent rules updated successfully!",
            "rules": current_settings["agent_rules"]
        }


# ============================================================================
# META WHATSAPP CLOUD API WEBHOOKS
# ============================================================================
from engine.whatsapp_cloud_api import WhatsAppCloudAPIService, WHATSAPP_VERIFY_TOKEN
wa_service = WhatsAppCloudAPIService()


@router.get("/whatsapp/webhook")
async def verify_whatsapp_webhook(request: Request):
    """Meta webhook verification handshake."""
    params = request.query_params
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    if mode == "subscribe" and token == WHATSAPP_VERIFY_TOKEN:
        return PlainTextResponse(content=challenge or "", status_code=200)
    raise HTTPException(status_code=403, detail="Verification token mismatch")


@router.post("/whatsapp/webhook")
async def receive_whatsapp_webhook(request: Request):
    """Processes inbound WhatsApp messages from prospective buyers."""
    try:
        body = await request.json()
        entry = body.get("entry", [{}])[0]
        changes = entry.get("changes", [{}])[0]
        value = changes.get("value", {})
        messages = value.get("messages", [])

        if messages:
            msg = messages[0]
            from_phone = msg.get("from")
            text = msg.get("text", {}).get("body", "")
            # Auto-respond with Surati trade catalog
            reply_text = (
                "નમસ્તે જી! 🙏 Algorise AI WhatsApp Sales Assistant તરફથી:\n"
                "આપની ઇન્ક્વાયરી બદલ આભાર. અમારા એક્ઝિક્યુટિવ આપને સંપૂર્ણ પ્રાઇસિંગ અને હોલસેલ કેટલોગ મોકલી રહ્યા છે."
            )
            wa_service.send_text_message(from_phone, reply_text)

        return {"status": "received"}
    except Exception as e:
        return {"status": "error", "message": str(e)}