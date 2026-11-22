"""
================================================================================
ALGORISE AI — ARIA 24/7 PRODUCTION ASGI SERVICE & AUTOHEAL SUPERVISOR (HARDENED)
ALTERNATE B: WEB & TELEGRAM-FIRST ARCHITECTURE (ZERO WHATSAPP BOT FOOTPRINT)
Personal Phone: +91 92270 95624 (100% Air-Gapped) | Merchant UPI: 9227095624@upi
Telegram Alerts Dispatcher: @Aassqqee_bot -> Chat ID: 8737013099
================================================================================
"""
from fastapi import FastAPI, Request, BackgroundTasks, HTTPException, Header, Depends
from fastapi.responses import JSONResponse, PlainTextResponse, FileResponse
import sqlite3
import hmac
import hashlib
import os
import re
import json
import time
import asyncio
import uvicorn
from datetime import datetime, timezone
from typing import Optional, Dict, Any
import urllib.parse
import urllib.request

from autoheal.invariants import ZeroCrashProcessMiddleware
from autoheal.probes import DiagnosticProbeMatrix, get_local_anydesk_id
from autoheal.rca_engine import RootCauseAnalysisEngine, ResolutionDomain
from autoheal.remediators import AutonomousRemediationExecutor, sanitize_phone_e164
from autoheal.handoff import HumanHandoffProtocol

app = FastAPI(title="Algorise AI — Aria Production Inbound & AutoHeal Service", version="2.8.0")
app.add_middleware(ZeroCrashProcessMiddleware)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "aria_production.db")
CONFIG_PATH = os.path.join(BASE_DIR, "config", "aria_assistant_config.json")

# Load Telegram Credentials safely
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8585331609:AAFa_foTU82ToL7EFBiZ3EIrSbCDCfW0cPA")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "8737013099")

if os.path.exists(CONFIG_PATH):
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = json.load(f)
            TELEGRAM_BOT_TOKEN = cfg.get("telegram_bot_token") or TELEGRAM_BOT_TOKEN
            TELEGRAM_CHAT_ID = cfg.get("telegram_chat_id") or TELEGRAM_CHAT_ID
    except Exception:
        pass

# Human Contact and Pricing (Read-only Air-Gapped)
FOUNDER_PHONE = "9227095624"
FOUNDER_PHONE_DISPLAY = "+91 92270 95624"
FOUNDER_UPI_VPA = f"{FOUNDER_PHONE}@upi"

REMOTE_SUPPORT_FEE = 250
BASE_VISIT_FEE = 500

def send_telegram_alert(text: str) -> bool:
    """Dispatches real-time HTML notifications directly to Hardik's Telegram chat."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("[TELEGRAM ALERT NOTICE]\n" + text)
        return False
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = urllib.parse.urlencode({
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML"
    }).encode("utf-8")
    req = urllib.request.Request(url, data=data)
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            res = json.loads(resp.read().decode())
            return bool(res.get("ok"))
    except Exception as e:
        print(f"[WARN] Failed to send Telegram alert: {e}")
        return False

class IndianBankSMSParser:
    """Pan-Indian Bank SMS & UPI Credit Alert Parser supporting HDFC, SBI, ICICI, Axis, Kotak, BOB, Paytm, PhonePe, GPay."""
    AMOUNT_PATTERNS = [
        re.compile(r"(?:credited|received|deposited|added)\s+(?:with|by)?\s*(?:INR|Rs\.?|₹)\s*([\d,]+\.?\d*)", re.IGNORECASE),
        re.compile(r"(?:INR|Rs\.?|₹)\s*([\d,]+\.?\d*)\s+(?:credited|deposited|received)", re.IGNORECASE),
        re.compile(r"received\s+(?:INR|Rs\.?|₹)\s*([\d,]+\.?\d*)\s+from", re.IGNORECASE)
    ]
    REF_PATTERNS = [
        re.compile(r"(?:UPI\s*(?:Ref|txn|id|RRN)?[:\s\/-]+(\d{12}))", re.IGNORECASE),
        re.compile(r"(?:Ref\s*(?:no|num)?[:\s\/-]+(\d{12}))", re.IGNORECASE),
        re.compile(r"(?:IMPS\s*(?:ref|no)?[:\s\/-]+(\d{12}))", re.IGNORECASE)
    ]

    @classmethod
    def parse_sms(cls, text: str) -> Optional[Dict[str, Any]]:
        lower = text.lower()
        if "debited" in lower or "sent" in lower or "otp" in lower or "withdrawn" in lower:
            return None

        amount = None
        for pattern in cls.AMOUNT_PATTERNS:
            match = pattern.search(text)
            if match:
                clean_amt = match.group(1).replace(",", "")
                try:
                    amount = float(clean_amt)
                    break
                except ValueError:
                    continue

        if amount is None or amount <= 0:
            return None

        txn_ref = "UNKNOWN_RRN"
        for pattern in cls.REF_PATTERNS:
            match = pattern.search(text)
            if match:
                txn_ref = match.group(1)
                break

        bank = "UPI_APP"
        if "hdfc" in lower: bank = "HDFC"
        elif "sbi" in lower: bank = "SBI"
        elif "icici" in lower: bank = "ICICI"
        elif "axis" in lower: bank = "AXIS"
        elif "kotak" in lower: bank = "KOTAK"
        elif "baroda" in lower or "bob" in lower: bank = "BOB"
        elif "paytm" in lower: bank = "PAYTM"
        elif "phonepe" in lower: bank = "PHONEPE"
        elif "gpay" in lower or "google pay" in lower: bank = "GPAY"

        return {
            "amount": amount,
            "txn_ref": txn_ref,
            "bank": bank,
            "raw_text": text
        }

def get_hardened_sqlite_conn(timeout: float = 5.0) -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=timeout)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA busy_timeout = 5000;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    return conn

def init_production_db():
    os.makedirs(DATA_DIR, exist_ok=True)
    with get_hardened_sqlite_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS leads (
                phone TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                sector TEXT,
                market TEXT,
                zone TEXT,
                distance_km REAL DEFAULT 5.0,
                remote_fee REAL DEFAULT 250.0,
                visiting_fee REAL DEFAULT 500.0,
                status TEXT DEFAULT 'NEW',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id TEXT PRIMARY KEY,
                lead_phone TEXT,
                amount REAL NOT NULL,
                purpose TEXT NOT NULL,
                upi_txn_ref TEXT,
                status TEXT DEFAULT 'PENDING',
                verified_via TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                verified_at TIMESTAMP,
                FOREIGN KEY(lead_phone) REFERENCES leads(phone)
            );
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS triage_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                phone TEXT NOT NULL,
                message TEXT NOT NULL,
                on_site_score REAL NOT NULL,
                mode TEXT NOT NULL,
                reply_dispatched TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS support_tickets (
                id TEXT PRIMARY KEY,
                client_name TEXT NOT NULL,
                client_phone TEXT NOT NULL,
                mode TEXT NOT NULL,
                amount REAL NOT NULL,
                anydesk_id TEXT,
                market_location TEXT,
                issue_description TEXT,
                upi_intent TEXT,
                status TEXT DEFAULT 'PENDING_PAYMENT',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                verified_at TIMESTAMP
            );
        """)
        conn.commit()

init_production_db()

# --- AutoHeal Background Supervisor Loop ---
@app.on_event("startup")
async def start_autoheal_supervisor():
    async def _supervision_loop():
        matrix = DiagnosticProbeMatrix(
            db_path=DB_PATH,
            meta_token="",
            page_id=""
        )
        executor = AutonomousRemediationExecutor(db_path=DB_PATH, repo_root=BASE_DIR)
        rca = RootCauseAnalysisEngine()
        handoff = HumanHandoffProtocol(
            telegram_token=TELEGRAM_BOT_TOKEN,
            telegram_chat_id=TELEGRAM_CHAT_ID,
            founder_phone=FOUNDER_PHONE
        )

        while True:
            try:
                results = await matrix.run_full_matrix()
                for res in results:
                    if not res.healthy:
                        plan = rca.evaluate_incident(
                            incident_id=f"INC-{int(time.time())}",
                            error_text=res.message,
                            context={"component": res.probe_id, "meta": res.metadata}
                        )
                        if plan.domain == ResolutionDomain.AUTONOMOUS_SOFTWARE_HEAL:
                            if plan.action_type == "FORCE_WAL_CHECKPOINT_AND_RETRY":
                                await executor.execute_wal_lock_recovery()
                            elif plan.action_type == "RESTART_ANYDESK_SERVICE":
                                await executor.execute_anydesk_service_restart()
                        elif plan.domain == ResolutionDomain.PHYSICAL_ON_SITE_ESCALATION:
                            runbook_text = handoff.compile_tactical_runbook(
                                incident_id=plan.incident_id,
                                client_name="Surat Commercial Account",
                                market_location="Ring Road / Katargam",
                                visiting_deposit_status="VERIFIED_PAID",
                                hardware_symptoms=res.message,
                                step_by_step_runbook=[
                                    "Inspect client router Ethernet WAN LED",
                                    "Verify AnyDesk service autorun status",
                                    "Confirm local IP subnet (192.168.1.x)"
                                ]
                            )
                            handoff.dispatch_alert(runbook_text)
            except Exception:
                pass
            await asyncio.sleep(20)  # Continuous non-blocking 20-second probe cycle

    asyncio.create_task(_supervision_loop())

# --- Web Support Portal Static Serving ---
@app.get("/")
@app.get("/support")
async def serve_support_portal():
    portal_path = os.path.join(BASE_DIR, "techsupport.html")
    if os.path.exists(portal_path):
        return FileResponse(portal_path, media_type="text/html")
    return PlainTextResponse("AlgoRise Tech Support Portal active.")

# --- Health Check ---
@app.get("/health")
async def health():
    local_anydesk = get_local_anydesk_id()
    return {
        "status": "online",
        "service": "Algorise AI Aria AutoHeal Daemon (Alternate B: Web & Telegram-First)",
        "version": "2.8.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "founder_phone": FOUNDER_PHONE_DISPLAY,
        "upi_vpa": FOUNDER_UPI_VPA,
        "local_anydesk_id": local_anydesk or "NOT_CONFIGURED",
        "telegram_alerts": "ENABLED" if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID else "DISABLED",
        "pricing": {
            "remote_support": REMOTE_SUPPORT_FEE,
            "base_visit": BASE_VISIT_FEE
        }
    }

# --- Inbound Web Support Ticket Submission ---
@app.post("/v1/support/ticket")
async def create_support_ticket(request: Request, bg_tasks: BackgroundTasks):
    """
    Receives interactive ticket submissions from techsupport.html.
    Calculates calibrated price, generates UPI QR, and alerts Hardik on Telegram.
    """
    body = await request.json()
    client_name = body.get("name", "Unknown Surat Business").strip()
    client_phone = body.get("phone", "").strip()
    mode = body.get("mode", "REMOTE_ANYDESK")
    anydesk_id = body.get("anydesk_id", "").strip()
    market = body.get("market", "Surat Market").strip()
    issue = body.get("issue", "General Tech Support").strip()

    # Calibrate fee
    if mode == "REMOTE_ANYDESK":
        amount = float(REMOTE_SUPPORT_FEE)
        tx_note = f"Remote_{client_name.replace(' ', '_')[:10]}"
        mode_label = "⚡ AnyDesk Remote Support (Flat ₹250)"
    else:
        amount = 750.0 if any(z in market for z in ["Katargam", "Varachha", "Vesu", "Sachin"]) else 500.0
        tx_note = f"Visit_{client_name.replace(' ', '_')[:10]}"
        mode_label = f"🚗 Surat Onsite Doorstep Repair (₹{amount:.0f} Deposit)"

    ticket_id = f"TKT-{int(time.time())}"
    
    # Generate UPI intent URL & QR image
    params = {
        'pa': FOUNDER_UPI_VPA,
        'pn': 'AlgoRise AI Engineering',
        'am': f'{amount:.2f}',
        'cu': 'INR',
        'tn': tx_note
    }
    intent_url = f"upi://pay?{urllib.parse.urlencode(params)}"
    qr_image = f"https://api.qrserver.com/v1/create-qr-code/?size=300x300&data={urllib.parse.quote(intent_url)}"

    # Insert into SQLite
    with get_hardened_sqlite_conn() as conn:
        conn.execute("""
            INSERT OR REPLACE INTO support_tickets (id, client_name, client_phone, mode, amount, anydesk_id, market_location, issue_description, upi_intent, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'PENDING_PAYMENT');
        """, (ticket_id, client_name, client_phone, mode, amount, anydesk_id, market, issue, intent_url))
        
        # Also register a pending transaction so bank SMS can reconcile it
        conn.execute("""
            INSERT OR REPLACE INTO transactions (id, lead_phone, amount, purpose, status)
            VALUES (?, ?, ?, ?, 'PENDING');
        """, (ticket_id, client_phone, amount, f"{mode}_TICKET"))
        conn.commit()

    # Dispatch rich Telegram Alert
    telegram_msg = (
        f"⚡ <b>NEW INBOUND SUPPORT TICKET</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"<b>Ticket ID:</b> <code>{ticket_id}</code>\n"
        f"<b>Service:</b> {mode_label}\n"
        f"<b>Amount Due:</b> <b>₹{amount:.2f}</b>\n"
        f"<b>Client:</b> {client_name}\n"
        f"<b>Phone:</b> 📞 <code>{client_phone}</code>\n"
        f"<b>Market / Area:</b> 📍 {market}\n"
        + (f"<b>AnyDesk 9-Digit ID:</b> <code>{anydesk_id}</code>\n" if anydesk_id else "")
        + f"<b>Issue:</b> <i>{issue}</i>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"💳 <i>Awaiting client UPI transfer of ₹{amount:.2f} to <code>{FOUNDER_UPI_VPA}</code>.</i>"
    )
    bg_tasks.add_task(send_telegram_alert, telegram_msg)

    return {
        "status": "created",
        "ticket_id": ticket_id,
        "client_name": client_name,
        "amount": amount,
        "upi_vpa": FOUNDER_UPI_VPA,
        "upi_intent": intent_url,
        "qr_image": qr_image
    }

# --- Automated Bank SMS Payment Ingestion ---
@app.post("/v1/payments/ingest-sms")
async def ingest_bank_sms(request: Request, bg_tasks: BackgroundTasks):
    body = await request.json()
    sms_text = body.get("message", "")
    parsed = IndianBankSMSParser.parse_sms(sms_text)
    
    if not parsed:
        return {"status": "ignored", "reason": "Not a recognized credit SMS alert"}
        
    amount = parsed["amount"]
    txn_ref = parsed["txn_ref"]
    bank = parsed["bank"]
    
    bg_tasks.add_task(reconcile_and_unlock_hardened, amount, txn_ref, bank, sms_text)
    return {"status": "processing", "amount": amount, "txn_ref": txn_ref, "bank": bank}

async def reconcile_and_unlock_hardened(amount: float, txn_ref: str, bank: str, raw_sms: str):
    """Windows-hardened reconciliation loop with 5s busy timeout and Telegram alert."""
    with get_hardened_sqlite_conn() as conn:
        cursor = conn.cursor()
        
        # Check pending transactions
        cursor.execute(
            "SELECT id, lead_phone FROM transactions WHERE amount = ? AND status = 'PENDING' ORDER BY created_at DESC LIMIT 1;",
            (amount,)
        )
        row = cursor.fetchone()
        now = datetime.now(timezone.utc).isoformat()
        
        if row:
            tx_id, lead_phone = row["id"], row["lead_phone"]
            cursor.execute(
                "UPDATE transactions SET status = 'CONFIRMED', upi_txn_ref = ?, verified_via = ?, verified_at = ? WHERE id = ?;",
                (txn_ref, f"BANK_SMS_{bank}", now, tx_id)
            )
            
            # Check if this tx is a support ticket
            cursor.execute("SELECT client_name, mode, anydesk_id, market_location FROM support_tickets WHERE id = ?;", (tx_id,))
            tkt = cursor.fetchone()
            client_name = tkt["client_name"] if tkt else lead_phone
            
            # Update ticket status
            cursor.execute("UPDATE support_tickets SET status = 'CONFIRMED_PAID', verified_at = ? WHERE id = ?;", (now, tx_id))
            
            digits = re.sub(r'\D', '', lead_phone)[-10:] if lead_phone else ""
            cursor.execute("""
                UPDATE leads SET status = 'DEPOSIT_PAID' 
                WHERE phone = ? OR REPLACE(REPLACE(REPLACE(phone, ' ', ''), '+', ''), '-', '') LIKE ?;
            """, (lead_phone, f"%{digits}%"))
            conn.commit()
            
            # Instant Celebratory Telegram Notification!
            telegram_msg = (
                f"💰 <b>PAYMENT CONFIRMED via {bank}!</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"<b>Amount:</b> <b>₹{amount:.2f}</b>\n"
                f"<b>Client:</b> {client_name}\n"
                f"<b>Phone:</b> 📞 <code>{lead_phone}</code>\n"
                f"<b>UPI Ref / RRN:</b> <code>{txn_ref}</code>\n"
                + (f"<b>AnyDesk ID:</b> <code>{tkt['anydesk_id']}</code>\n" if tkt and tkt['anydesk_id'] else "")
                + (f"<b>Location:</b> 📍 {tkt['market_location']}\n" if tkt and tkt['market_location'] else "")
                + f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"✅ <i>Session unlocked! Ready to connect or dispatch.</i>"
            )
            send_telegram_alert(telegram_msg)
            print(f"✅ [RECONCILED] TX {tx_id} confirmed for {lead_phone} (₹{amount}) via {bank} Ref: {txn_ref}!")
        else:
            cursor.execute(
                "INSERT INTO transactions (id, lead_phone, amount, purpose, upi_txn_ref, status, verified_via, verified_at) VALUES (?, 'UNKNOWN', ?, 'UNALLOCATED_CREDIT', ?, 'CONFIRMED', ?, ?);",
                (f"TX_{int(datetime.now().timestamp())}", amount, txn_ref, f"BANK_SMS_{bank}", now)
            )
            conn.commit()
            print(f"ℹ️ [UNALLOCATED RECONCILIATION] ₹{amount} received from {bank} Ref: {txn_ref}.")

# --- Client Remote AnyDesk Reverse Beacon ---
@app.post("/v1/session/beacon")
async def client_session_beacon(request: Request, bg_tasks: BackgroundTasks):
    """Receives connection handshake beacon from client AnyDesk QuickAssist helper."""
    body = await request.json()
    lead_phone = body.get("lead_phone", "UNKNOWN")
    anydesk_id = body.get("anydesk_id", "")
    status = body.get("status", "ONLINE")

    digits = re.sub(r'\D', '', lead_phone)[-10:] if lead_phone else ""
    with get_hardened_sqlite_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT name, market FROM leads 
            WHERE phone = ? OR REPLACE(REPLACE(REPLACE(phone, ' ', ''), '+', ''), '-', '') LIKE ? LIMIT 1;
        """, (lead_phone, f"%{digits}%"))
        lead = cursor.fetchone()
        lead_name = lead["name"] if lead else lead_phone

    print(f"🚀 [ANYDESK BEACON] {lead_name} AnyDesk Online! ID: {anydesk_id} (Status: {status})")
    
    # Telegram Alert
    beacon_msg = (
        f"🚀 <b>ANYDESK SESSION ONLINE</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"<b>Client:</b> {lead_name}\n"
        f"<b>AnyDesk 9-Digit ID:</b> <code>{anydesk_id}</code>\n"
        f"<b>Direct Connect URI:</b> <code>anydesk:{anydesk_id}</code>\n"
        f"<b>Status:</b> {status}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👉 <i>Open AnyDesk and connect to <code>{anydesk_id}</code>.</i>"
    )
    bg_tasks.add_task(send_telegram_alert, beacon_msg)

    return {
        "status": "acknowledged",
        "lead_name": lead_name,
        "anydesk_id": anydesk_id,
        "direct_connect_uri": f"anydesk:{anydesk_id}"
    }

if __name__ == "__main__":
    print("=" * 80)
    print("  ALGORISE AI — ARIA 24/7 PRODUCTION ASGI SERVICE & AUTOHEAL SUPERVISOR")
    print("  ALTERNATE B: WEB & TELEGRAM-FIRST ARCHITECTURE (ZERO WHATSAPP BOT)")
    print(f"  Engineering Desk: {FOUNDER_PHONE_DISPLAY} | Merchant UPI: {FOUNDER_UPI_VPA}")
    print(f"  Telegram Bot: @Aassqqee_bot | Alerts Chat ID: {TELEGRAM_CHAT_ID}")
    print(f"  Remote Flat Fee: ₹{REMOTE_SUPPORT_FEE} | Visiting Base Fee: ₹{BASE_VISIT_FEE}")
    print("=" * 80)
    uvicorn.run("aria_service:app", host="127.0.0.1", port=8000, reload=False)
