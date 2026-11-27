"""
Guardian Angel™ — Cloud Sentinel, URL/OCR Threat Triage, Family Alerts & Order Checkout API.

Mounted onto engine.main at /api/v1/guardian/* so the live Render deployment serves real
persisted threat inspection, telemetry metrics, Telegram family alerts, and real order/UPI
or Stripe checkout creation alongside the standalone local sentinel.
"""

from __future__ import annotations

import hashlib
import html
import json
import os
import re
import sqlite3
import time
import urllib.parse
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field

from engine.logging import get_logger
from engine.telegram_service import AlgoriseTelegramService

logger = get_logger("algorise.guardian")
router = APIRouter(prefix="/api/v1/guardian", tags=["Guardian Angel Sentinel"])

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
TELEMETRY_DB_PATH = DATA_DIR / "guardian_telemetry.db"

TELEGRAM_BOT = AlgoriseTelegramService()


def _init_guardian_db() -> None:
    """Initializes local SQLite storage for scans, orders, and analytics events."""
    try:
        with sqlite3.connect(TELEMETRY_DB_PATH) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS guardian_scans (
                    scan_id TEXT PRIMARY KEY,
                    created_at REAL,
                    channel TEXT,
                    region TEXT,
                    threat_score INTEGER,
                    category TEXT,
                    impersonation TEXT,
                    url_count INTEGER
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS guardian_orders (
                    order_id TEXT PRIMARY KEY,
                    created_at REAL,
                    plan_tier TEXT,
                    billing_cycle TEXT,
                    region TEXT,
                    amount REAL,
                    currency TEXT,
                    customer_name TEXT,
                    customer_email TEXT,
                    caregiver_phone TEXT,
                    senior_name TEXT,
                    payment_method TEXT,
                    payment_mode TEXT,
                    status TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS guardian_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at REAL,
                    event_name TEXT,
                    surface TEXT,
                    meta_json TEXT
                )
                """
            )
            conn.commit()
    except Exception as exc:
        logger.warning("guardian_db_init_warning", error=str(exc))


_init_guardian_db()


# ==============================================================================
# 1. REQUEST & RESPONSE SCHEMAS
# ==============================================================================


class GuardianTriageRequest(BaseModel):
    channel: str = Field("TEXT", max_length=20)  # CALL, MAIL, TEXT, URL, OCR
    sender: str = Field("Unknown", max_length=250)
    subject: str = Field("", max_length=500)
    content: str = Field(..., max_length=25000)
    region: str = Field("US", max_length=10)


class GuardianIndicator(BaseModel):
    category: str
    severity: str
    description: str


class ExtractedUrlReport(BaseModel):
    url: str
    host: str
    verdict: str  # SAFE_OFFICIAL | SUSPICIOUS | MALICIOUS
    reasons: List[str] = Field(default_factory=list)


class GuardianTriageResponse(BaseModel):
    scan_id: str
    channel: str
    threat_score: int
    category: str
    verdict: str
    action: str
    confidence: float
    urgency_detected: bool
    impersonation_target: Optional[str] = None
    senior_safe: bool
    senior_headline: str
    senior_reassurance: str
    safe_next_step: str
    why_we_flagged_this: List[str]
    speech_text: str
    indicators: List[GuardianIndicator] = Field(default_factory=list)
    extracted_urls: List[ExtractedUrlReport] = Field(default_factory=list)
    latency_ms: float


class GuardianOrderRequest(BaseModel):
    plan_tier: str = Field("family", max_length=40)  # individual, family, concierge_audit
    billing_cycle: str = Field("monthly", max_length=20)
    region: str = Field("US", max_length=10)  # US, UK, IN
    customer_name: str = Field(..., min_length=1, max_length=120)
    customer_email: str = Field(..., min_length=3, max_length=180)
    caregiver_phone: str = Field("", max_length=40)
    senior_name: str = Field("Protected Parent", max_length=120)
    payment_method: str = Field("auto", max_length=30)  # auto, card, upi, concierge_invoice
    success_url: str = Field("https://algorise-ai.com/?order=success", max_length=500)
    cancel_url: str = Field("https://algorise-ai.com/?order=cancelled", max_length=500)


class GuardianFamilyAlertRequest(BaseModel):
    protected_name: str = Field("Protected Parent", max_length=120)
    channel: str = Field("TEXT", max_length=20)
    scam_type: str = Field(..., max_length=160)
    threat_score: int = Field(85, ge=0, le=100)
    threat_snippet: str = Field(..., max_length=1000)
    region: str = Field("US", max_length=10)


class GuardianTelemetryEvent(BaseModel):
    event_name: str = Field(..., max_length=60)
    surface: str = Field("index", max_length=40)
    meta: Dict[str, Any] = Field(default_factory=dict)


# ==============================================================================
# 2. DETERMINISTIC SECURITY RULES & URL REPUTATION PARSER
# ==============================================================================

OFFICIAL_TRUSTED_DOMAINS = (
    "irs.gov",
    "ssa.gov",
    "medicare.gov",
    "usps.com",
    "gov.uk",
    "nhs.uk",
    "royalmail.com",
    "apple.com",
    "google.com",
    "microsoft.com",
    "amazon.com",
    "amazon.co.uk",
    "paypal.com",
    "chase.com",
    "bankofamerica.com",
    "barclays.co.uk",
    "hsbc.co.uk",
    "lloydsbank.com",
)

RISKY_TLDS = {
    "top",
    "xyz",
    "work",
    "buzz",
    "icu",
    "live",
    "click",
    "cyou",
    "shop",
    "sbs",
    "tk",
    "ml",
    "ga",
    "cf",
    "gq",
    "rest",
}

SHORTENER_DOMAINS = {
    "bit.ly",
    "tinyurl.com",
    "t.co",
    "rb.gy",
    "ow.ly",
    "is.gd",
    "cutt.ly",
    "shorturl.at",
}

SPOOF_HOST_TOKENS = (
    "track-usps",
    "usps-",
    "royalmail-",
    "evri-",
    "secure-chase",
    "login-hmrc",
    "claim-rebate",
    "toll-pay",
    "claim-dwp",
    "tvlicence-",
    "verify-paypal",
    "login-microsoft",
    "update-banking",
    "ssa-verify",
    "medicare-card",
)

URL_EXTRACT_RE = re.compile(
    r"(?:https?://[^\s<>'\"()]+|(?:[a-zA-Z0-9-]+\.)+(?:com|org|net|gov|edu|uk|top|xyz|work|buzz|icu|live|click|cyou|shop|sbs|io|co)(?:/[^\s<>'\"()]*)?)",
    re.IGNORECASE,
)

IPV4_HOST_RE = re.compile(r"^\d{1,3}(?:\.\d{1,3}){3}$")

HEALTHCARE_PATS = (
    re.compile(r"\b(NHS|GP surgery|hospital appointment|clinic appointment|dental appointment|optician)\b", re.IGNORECASE),
    re.compile(r"\bappointment\s+(reminder|scheduled|confirmed)\s+with\s+(dr|doctor)\.?\s+[a-z]+\b", re.IGNORECASE),
    re.compile(r"\b(st\.?\s*mary'?s\s*hospital|mayo clinic|cleveland clinic|kaiser|quest diagnostics|labcorp)\b", re.IGNORECASE),
)

PHARMACY_PATS = (
    re.compile(r"\bprescription\s+is\s+ready\s+for\s+(collection|pickup)\b", re.IGNORECASE),
    re.compile(r"\b(boots pharmacy|cvs pharmacy|walgreens|rite aid|lloyds pharmacy)\b", re.IGNORECASE),
    re.compile(r"\brx\s*#?\s*\d{4,}\b", re.IGNORECASE),
)

FAMILY_PAT = re.compile(
    r"\b(thank you so much for|thanks\s+(grandma|grandpa|nana|mom|dad)|love you so much|see you on sunday|happy birthday\s+(grandma|grandpa|mom|dad))\b",
    re.IGNORECASE,
)

OTP_PAT = re.compile(r"\b(one-time (passcode|password)|verification code is|security code is|never share this code)\b", re.IGNORECASE)

COERCION_RULES = (
    (
        "IRS / Tax Arrest Impersonation",
        re.compile(r"\b((?:IRS|Internal Revenue Service|HMRC)\s+(?:warrant|arrest|lawsuit|legal action|agent|officer|tax fraud|unpaid)|tax warrant|arrest warrant|sheriff department|federal warrant|police are on the way)\b", re.IGNORECASE),
        50,
    ),
    (
        "Social Security / Medicare Impersonation",
        re.compile(r"\b(social security (number|administration)|SSN (is|has been) suspended|medicare chip|plastic medicare card)\b", re.IGNORECASE),
        50,
    ),
    (
        "Tech Support & Remote Access Trap",
        re.compile(r"\b(geek squad|norton lifelock|mcafee|microsoft refund|anydesk|teamviewer|quickassist|ultraviewer|auto-?renewal.*\$[1-9]\d{2})\b", re.IGNORECASE),
        55,
    ),
    (
        "Gift Card / Crypto / Safe Account Extortion",
        re.compile(r"\b(target gift card|apple gift card|google play card|steam card|bitcoin atm|crypto kiosk|safe holding account|western union now)\b", re.IGNORECASE),
        55,
    ),
    (
        "Grandparent Emergency Bail Scam",
        re.compile(r"\b(i'm in jail|arrested|need bail money|don't tell mom|wire.*bail)\b", re.IGNORECASE),
        50,
    ),
    (
        "Delivery / Toll / Gov Rebate Smishing",
        re.compile(r"\b(DWP|winter fuel (payment|allowance)|tv licensing|court summons|unpaid customs fee|incomplete (street )?address|sunpass|fastrak|ezpass|dartford crossing)\b", re.IGNORECASE),
        45,
    ),
    (
        "Crypto Guaranteed Return Fraud",
        re.compile(r"\b(guaranteed \d+% daily|deposit USDT|VIP crypto mining|financial analyst uncle)\b", re.IGNORECASE),
        55,
    ),
)

URGENCY_PAT = re.compile(
    r"\b(within 24\s?h(?:ours)?|within 30 minutes|do not hang up|immediate action|account suspended|final (notice|warning)|avoid court|legal action)\b",
    re.IGNORECASE,
)


def _host_matches_official(host: str) -> bool:
    return any(host == dom or host.endswith(f".{dom}") for dom in OFFICIAL_TRUSTED_DOMAINS)


def analyze_urls(text: str) -> List[ExtractedUrlReport]:
    """Extracts and inspects URLs/domains using structural suffix and homograph checks."""
    reports: List[ExtractedUrlReport] = []
    seen: set[str] = set()
    for raw in URL_EXTRACT_RE.findall(text):
        cleaned = raw.rstrip(".,;:!?)")
        if cleaned.lower() in seen:
            continue
        seen.add(cleaned.lower())

        normalized = cleaned if "://" in cleaned else f"https://{cleaned}"
        try:
            parsed = urllib.parse.urlparse(normalized)
            host = (parsed.hostname or "").lower()
        except Exception:
            host = ""
        if not host:
            continue

        reasons: List[str] = []
        verdict = "SAFE_OFFICIAL"

        if _host_matches_official(host):
            reasons.append(f"Exact official domain suffix verified ({host}).")
        else:
            if "xn--" in host:
                verdict = "MALICIOUS"
                reasons.append("Punycode/IDN homograph domain encoding detected.")
            if IPV4_HOST_RE.match(host):
                verdict = "MALICIOUS"
                reasons.append("Raw IPv4 link instead of verifiable business domain.")
            tld = host.rsplit(".", 1)[-1] if "." in host else ""
            if tld in RISKY_TLDS:
                verdict = "MALICIOUS"
                reasons.append(f"High-abuse disposable top-level domain (.{tld}).")
            if any(tok in host for tok in SPOOF_HOST_TOKENS):
                verdict = "MALICIOUS"
                reasons.append("Brand/government lookalike domain pattern.")
            if host in SHORTENER_DOMAINS:
                if verdict == "SAFE_OFFICIAL":
                    verdict = "SUSPICIOUS"
                reasons.append("Masking URL shortener hides real destination.")
            if any(brand in host for brand in ("irs", "hmrc", "usps", "royalmail", "paypal", "chase", "microsoft", "apple")) and not _host_matches_official(host):
                verdict = "MALICIOUS"
                reasons.append("Brand name embedded inside unofficial third-party domain.")
            if verdict == "SAFE_OFFICIAL":
                verdict = "SUSPICIOUS"
                reasons.append("External third-party domain; verify independently before entering credentials.")

        reports.append(ExtractedUrlReport(url=cleaned, host=host, verdict=verdict, reasons=reasons))
    return reports


TRIAGE_CACHE: Dict[str, GuardianTriageResponse] = {}
MAX_CACHE = 2048


def run_guardian_triage(req: GuardianTriageRequest) -> GuardianTriageResponse:
    """Executes deterministic sub-millisecond triage on call transcripts, emails, SMS, OCR text, or URLs."""
    t0 = time.perf_counter()
    channel = req.channel.upper().strip() or "TEXT"
    scan_id = f"GA-{int(time.time() * 1000) % 10000000:07d}-{uuid.uuid4().hex[:4].upper()}"
    cache_key = hashlib.sha256(
        f"{channel}|{req.sender.strip().lower()}|{req.subject.strip().lower()}|{req.content.strip().lower()}|{req.region.upper()}".encode("utf-8")
    ).hexdigest()

    if cache_key in TRIAGE_CACHE:
        cached = TRIAGE_CACHE[cache_key].model_copy()
        cached.scan_id = scan_id
        cached.latency_ms = round((time.perf_counter() - t0) * 1000.0, 3)
        return cached

    full_text = f"{req.sender} {req.subject} {req.content}".strip()
    url_reports = analyze_urls(full_text)
    malicious_urls = [u for u in url_reports if u.verdict == "MALICIOUS"]
    suspicious_urls = [u for u in url_reports if u.verdict == "SUSPICIOUS"]

    indicators: List[GuardianIndicator] = []
    score = 0
    impersonation: Optional[str] = None
    urgency_detected = bool(URGENCY_PAT.search(full_text))

    # Lifeline check first ONLY when zero malicious URLs and zero extortion signatures exist
    has_coercion = any(pat.search(full_text) for _, pat, _ in COERCION_RULES)
    is_health = any(p.search(full_text) for p in HEALTHCARE_PATS) or any(p.search(full_text) for p in PHARMACY_PATS)
    is_family = bool(FAMILY_PAT.search(full_text))
    is_clean_otp = bool(OTP_PAT.search(full_text)) and not url_reports

    if not malicious_urls and not has_coercion and (is_health or is_family or is_clean_otp):
        if is_health:
            cat = "SAFE_HEALTHCARE"
            headline = "SAFE TO OPEN: Verified Medical / Pharmacy Notice"
            reassurance = "Matches legitimate healthcare/pharmacy notification syntax with no dangerous links or payment demands."
            next_step = "Verify against your normal clinic schedule or pharmacy location."
        elif is_clean_otp:
            cat = "TRANSACTIONAL"
            headline = "BANK SECURITY CODE — Keep Strictly Private"
            reassurance = "Normal one-time sign-in code with zero phishing links."
            next_step = "Only enter this code on a sign-in you started yourself. Never read OTPs to anyone calling on the phone."
        else:
            cat = "SAFE_FAMILY"
            headline = "SAFE TO OPEN: Personal / Family Message"
            reassurance = "Personal message with no payment coercion or phishing links."
            next_step = "Safe to read and respond directly."

        res = GuardianTriageResponse(
            scan_id=scan_id,
            channel=channel,
            threat_score=0,
            category=cat,
            verdict="VERIFIED SAFE",
            action="INBOX_SAFE",
            confidence=0.99,
            urgency_detected=False,
            impersonation_target=None,
            senior_safe=True,
            senior_headline=headline,
            senior_reassurance=reassurance,
            safe_next_step=next_step,
            why_we_flagged_this=[reassurance],
            speech_text=f"Guardian Angel scan complete. {headline}. {next_step}",
            indicators=[],
            extracted_urls=url_reports,
            latency_ms=round((time.perf_counter() - t0) * 1000.0, 3),
        )
        _record_scan_telemetry(res)
        return res

    # Run threat scorers
    for label, pat, weight in COERCION_RULES:
        if pat.search(full_text):
            score += weight
            if not impersonation:
                impersonation = label
            indicators.append(
                GuardianIndicator(
                    category="Fraud / Coercion Pattern",
                    severity="CRITICAL",
                    description=f"Matched high-risk fraud pattern: {label}",
                )
            )

    if malicious_urls:
        score += 75
        impersonation = impersonation or f"Malicious Lookalike Domain ({malicious_urls[0].host})"
        for u in malicious_urls[:3]:
            indicators.append(
                GuardianIndicator(
                    category="Malicious URL",
                    severity="CRITICAL",
                    description=f"{u.host}: {'; '.join(u.reasons)}",
                )
            )
    elif suspicious_urls:
        score += 35 if urgency_detected else 20
        for u in suspicious_urls[:2]:
            indicators.append(
                GuardianIndicator(
                    category="Unverified External Link",
                    severity="HIGH" if urgency_detected else "MEDIUM",
                    description=f"{u.host}: {'; '.join(u.reasons)}",
                )
            )

    if urgency_detected:
        score += 20
        indicators.append(
            GuardianIndicator(
                category="Artificial Urgency / Duress",
                severity="HIGH",
                description="Pressures recipient to act immediately without verifying.",
            )
        )

    score = min(max(score, 0), 100)
    why_list = [ind.description for ind in indicators] or ["No fraud or phishing signatures detected."]

    if score >= 70:
        cat = "CRITICAL_FRAUD"
        verdict = "CONFIRMED SCAM / HIGH THREAT"
        action = "BLOCK_AND_ALERT"
        conf = 0.99
        safe = False
        headline = f"STOP! Likely {impersonation or 'Fraud Attempt'}"
        reassurance = "You are safe as long as you do not click links, call back numbers in the notice, or pay."
        next_step = "Hang up or delete immediately. Call your bank or official agency only using the phone number on the back of your card."
    elif score >= 35:
        cat = "SUSPICIOUS_SPAM"
        verdict = "CAUTION: UNVERIFIED / SUSPICIOUS"
        action = "QUARANTINE_SPAM"
        conf = 0.91
        safe = False
        headline = "VERIFY BEFORE ACTING: Unverified Link or Urgency"
        reassurance = "This contains unverified links or urgent language common in phishing."
        next_step = "Do not tap any link or share passwords. Confirm via an official app or trusted family member."
    else:
        cat = "SAFE_PERSONAL"
        verdict = "LOW RISK / NO THREATS DETECTED"
        action = "INBOX_SAFE"
        conf = 0.96
        safe = True
        headline = "No Known Scam Signatures Detected"
        reassurance = "No phishing links, remote-access lures, or payment coercion found in this sample."
        next_step = "Safe to review, while keeping normal caution around personal passwords."

    res = GuardianTriageResponse(
        scan_id=scan_id,
        channel=channel,
        threat_score=score,
        category=cat,
        verdict=verdict,
        action=action,
        confidence=conf,
        urgency_detected=urgency_detected,
        impersonation_target=impersonation,
        senior_safe=safe,
        senior_headline=headline,
        senior_reassurance=reassurance,
        safe_next_step=next_step,
        why_we_flagged_this=why_list,
        speech_text=f"Guardian Angel scan complete. {headline}. {next_step}",
        indicators=indicators,
        extracted_urls=url_reports,
        latency_ms=round((time.perf_counter() - t0) * 1000.0, 3),
    )

    if len(TRIAGE_CACHE) < MAX_CACHE:
        TRIAGE_CACHE[cache_key] = res
    _record_scan_telemetry(res)
    return res


def _record_scan_telemetry(res: GuardianTriageResponse) -> None:
    try:
        with sqlite3.connect(TELEMETRY_DB_PATH) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO guardian_scans VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    res.scan_id,
                    time.time(),
                    res.channel,
                    "GLOBAL",
                    res.threat_score,
                    res.category,
                    res.impersonation_target or "",
                    len(res.extracted_urls),
                ),
            )
            conn.commit()
    except Exception as exc:
        logger.warning("guardian_scan_log_failed", error=str(exc))


# ==============================================================================
# 3. API ENDPOINTS
# ==============================================================================


@router.get("/health")
async def guardian_health() -> Dict[str, Any]:
    return {
        "status": "HEALTHY",
        "service": "Guardian Angel Sentinel Cloud API",
        "version": "3.2.0",
        "stripe_configured": bool(os.getenv("STRIPE_SECRET_KEY", "").strip()),
        "upi_configured": bool(os.getenv("FOUNDER_UPI_VPA", "").strip()),
        "telegram_configured": TELEGRAM_BOT.configured,
    }


@router.post("/triage", response_model=GuardianTriageResponse)
async def guardian_triage(payload: GuardianTriageRequest) -> GuardianTriageResponse:
    return run_guardian_triage(payload)


@router.post("/alert-family")
async def guardian_alert_family(
    req: GuardianFamilyAlertRequest, bg: BackgroundTasks
) -> Dict[str, Any]:
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    alert_msg = (
        f"🚨 <b>GUARDIAN ANGEL™ — FAMILY PROTECTION ALERT</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"<b>Protected Person:</b> {html.escape(req.protected_name)}\n"
        f"<b>Channel:</b> {html.escape(req.channel.upper())} ({html.escape(req.region)})\n"
        f"<b>Threat Score:</b> {req.threat_score}%\n"
        f"<b>Detected Threat:</b> {html.escape(req.scam_type)}\n"
        f"<b>Snippet:</b> <i>\"{html.escape(req.threat_snippet[:240])}\"</i>"
    )
    if TELEGRAM_BOT.configured and chat_id:
        bg.add_task(TELEGRAM_BOT.send_message, chat_id, alert_msg)
        dispatched = True
    else:
        dispatched = False
    return {
        "status": "ALERT_DISPATCHED" if dispatched else "LOGGED_NO_TELEGRAM_ENV",
        "dispatched": dispatched,
        "protected_name": req.protected_name,
    }


PLAN_CATALOG: Dict[str, Dict[str, Any]] = {
    "individual": {
        "label": "Guardian Individual Shield",
        "US": {"amount": 9.99, "currency": "USD"},
        "UK": {"amount": 7.99, "currency": "GBP"},
        "IN": {"amount": 799.0, "currency": "INR"},
    },
    "family": {
        "label": "Guardian Family Shield (Up to 5 Devices)",
        "US": {"amount": 19.99, "currency": "USD"},
        "UK": {"amount": 15.99, "currency": "GBP"},
        "IN": {"amount": 1499.0, "currency": "INR"},
    },
    "concierge_audit": {
        "label": "1-on-1 Device Lockdown & Family Setup",
        "US": {"amount": 49.00, "currency": "USD"},
        "UK": {"amount": 39.00, "currency": "GBP"},
        "IN": {"amount": 2499.0, "currency": "INR"},
    },
}


@router.post("/orders")
async def create_guardian_order(
    req: GuardianOrderRequest, bg: BackgroundTasks
) -> Dict[str, Any]:
    """Creates a persisted order record, notifies Telegram concierge, and prepares real payment rail."""
    tier_key = req.plan_tier.lower().strip()
    if tier_key not in PLAN_CATALOG:
        raise HTTPException(status_code=400, detail="Invalid plan_tier")

    region_key = req.region.upper().strip()
    if region_key not in ("US", "UK", "IN"):
        region_key = "US"

    plan_meta = PLAN_CATALOG[tier_key]
    pricing = plan_meta[region_key]
    amount = pricing["amount"]
    currency = pricing["currency"]
    order_id = f"GA-ORD-{uuid.uuid4().hex[:8].upper()}"

    # 1. Determine real configured payment rail (never return fake checkout.stripe.com homepage)
    stripe_key = os.getenv("STRIPE_SECRET_KEY", "").strip()
    upi_vpa = os.getenv("FOUNDER_UPI_VPA", "").strip()
    payment_mode = "concierge_invoice"
    checkout_url: Optional[str] = None
    upi_uri: Optional[str] = None

    if stripe_key and req.payment_method in ("auto", "card"):
        try:
            async with httpx.AsyncClient(timeout=12.0) as client:
                stripe_resp = await client.post(
                    "https://api.stripe.com/v1/checkout/sessions",
                    auth=(stripe_key, ""),
                    data={
                        "mode": "payment" if tier_key == "concierge_audit" else "subscription",
                        "customer_email": req.customer_email,
                        "success_url": req.success_url,
                        "cancel_url": req.cancel_url,
                        "client_reference_id": order_id,
                        "line_items[0][quantity]": 1,
                        "line_items[0][price_data][currency]": currency.lower(),
                        "line_items[0][price_data][unit_amount]": int(round(amount * 100)),
                        "line_items[0][price_data][product_data][name]": plan_meta["label"],
                        **(
                            {
                                "line_items[0][price_data][recurring][interval]": (
                                    "year" if req.billing_cycle == "yearly" else "month"
                                )
                            }
                            if tier_key != "concierge_audit"
                            else {}
                        ),
                    },
                )
            if stripe_resp.status_code == 200:
                checkout_url = stripe_resp.json().get("url")
                if checkout_url:
                    payment_mode = "stripe_live"
        except Exception as exc:
            logger.warning("stripe_session_error", error=str(exc))

    if payment_mode != "stripe_live" and upi_vpa and (req.payment_method == "upi" or region_key == "IN"):
        inr_amount = PLAN_CATALOG[tier_key]["IN"]["amount"]
        params = urllib.parse.urlencode(
            {
                "pa": upi_vpa,
                "pn": "Algorise AI Guardian",
                "am": f"{inr_amount:.2f}",
                "cu": "INR",
                "tn": f"Order {order_id}",
            }
        )
        upi_uri = f"upi://pay?{params}"
        payment_mode = "upi_direct"

    # 2. Persist order
    try:
        with sqlite3.connect(TELEMETRY_DB_PATH) as conn:
            conn.execute(
                "INSERT INTO guardian_orders VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    order_id,
                    time.time(),
                    tier_key,
                    req.billing_cycle,
                    region_key,
                    amount,
                    currency,
                    req.customer_name,
                    req.customer_email,
                    req.caregiver_phone,
                    req.senior_name,
                    req.payment_method,
                    payment_mode,
                    "pending_payment" if payment_mode != "concierge_invoice" else "pending_concierge",
                ),
            )
            conn.commit()
    except Exception as exc:
        logger.warning("guardian_order_save_failed", error=str(exc))

    # 3. Notify owner desk on Telegram
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    if TELEGRAM_BOT.configured and chat_id:
        msg = (
            f"🛡️ <b>NEW GUARDIAN ANGEL ORDER</b>\n"
            f"<b>Order ID:</b> <code>{order_id}</code>\n"
            f"<b>Plan:</b> {html.escape(plan_meta['label'])} ({currency} {amount})\n"
            f"<b>Customer:</b> {html.escape(req.customer_name)} &lt;{html.escape(req.customer_email)}&gt;\n"
            f"<b>Phone / Caregiver:</b> <code>{html.escape(req.caregiver_phone or 'N/A')}</code>\n"
            f"<b>Protected Parent:</b> {html.escape(req.senior_name)}\n"
            f"<b>Payment Rail:</b> <code>{payment_mode}</code>"
        )
        bg.add_task(TELEGRAM_BOT.send_message, chat_id, msg)

    telegram_activation_url = (
        f"https://t.me/Aassqqee_bot?start={urllib.parse.quote(f'guardian_{order_id}')}"
    )

    return {
        "order_id": order_id,
        "status": "CREATED",
        "plan_name": plan_meta["label"],
        "amount": amount,
        "currency": currency,
        "payment_mode": payment_mode,
        "checkout_url": checkout_url,
        "upi_uri": upi_uri,
        "upi_vpa": upi_vpa if payment_mode == "upi_direct" else None,
        "telegram_activation_url": telegram_activation_url,
    }


@router.get("/clips")
async def get_guardian_clips() -> Dict[str, Any]:
    return {
        "total_clips": 3,
        "clips": [
            {
                "id": "reel_irs_tea",
                "title": "IRS Arrest Scam Call vs. Earl Grey Tea",
                "duration_sec": 24,
                "video_url": "/assets/reels/reel_irs_tea.mp4",
                "caption": "Scammer threatens IRS arrest warrant; Margaret keeps him busy over Earl Grey tea.",
            },
            {
                "id": "reel_geeksquad_desk",
                "title": "Geek Squad $499 AnyDesk Trap vs. 1964 Oak Desk",
                "duration_sec": 25,
                "video_url": "/assets/reels/reel_geeksquad_desk.mp4",
                "caption": "Scammer begs for AnyDesk; Margaret thinks he means her oak writing desk.",
            },
            {
                "id": "reel_bail_kevin",
                "title": "Grandson Bail Extortion vs. Cousin Kevin's Parakeet",
                "duration_sec": 24,
                "video_url": "/assets/reels/reel_bail_kevin.mp4",
                "caption": "Bail scammer demands $3,000; Margaret asks about Cousin Kevin's parakeet.",
            },
        ],
    }


@router.post("/telemetry")
async def record_guardian_telemetry(ev: GuardianTelemetryEvent) -> Dict[str, Any]:
    try:
        with sqlite3.connect(TELEMETRY_DB_PATH) as conn:
            conn.execute(
                "INSERT INTO guardian_events (created_at, event_name, surface, meta_json) VALUES (?, ?, ?, ?)",
                (time.time(), ev.event_name[:60], ev.surface[:40], json.dumps(ev.meta)[:500]),
            )
            conn.commit()
    except Exception as exc:
        logger.warning("guardian_telemetry_error", error=str(exc))
    return {"recorded": True}


@router.get("/stats")
async def get_guardian_stats() -> Dict[str, Any]:
    """Returns real non-fabricated aggregate database counts."""
    scans_total = 0
    critical_blocked = 0
    orders_total = 0
    events_total = 0
    try:
        with sqlite3.connect(TELEMETRY_DB_PATH) as conn:
            scans_total = conn.execute("SELECT COUNT(*) FROM guardian_scans").fetchone()[0]
            critical_blocked = conn.execute(
                "SELECT COUNT(*) FROM guardian_scans WHERE category = 'CRITICAL_FRAUD'"
            ).fetchone()[0]
            orders_total = conn.execute("SELECT COUNT(*) FROM guardian_orders").fetchone()[0]
            events_total = conn.execute("SELECT COUNT(*) FROM guardian_events").fetchone()[0]
    except Exception as exc:
        logger.warning("guardian_stats_read_failed", error=str(exc))

    return {
        "scans_processed": scans_total,
        "scams_blocked": critical_blocked,
        "orders_created": orders_total,
        "events_recorded": events_total,
    }
