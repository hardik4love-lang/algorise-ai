"""
FastAPI Router for Algorise BooksOS (Accounting, Tally XML Bridge, GST/IMS, 43B(h),
GSP e-Invoice Sandbox & Multi-Tenant CA Super-Console).

Security Policy:
- Demo sandbox companies (`demo_*`), demo CA firms (`demo_ca_*`), and the stateless
  Tally Shadow Audit tool allow interactive evaluation on algorise-ai.com.
- All production tenant company IDs and CA firm IDs require a valid `X-Algorise-Key`.
- AlgoBridge signed sync enforces HMAC-SHA256 + ±300s timestamp + single-use nonce.
"""

from __future__ import annotations

import base64
import hashlib
import json
import re
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel, Field

from engine.accounting import (
    AccountingError,
    accounting_store,
    build_whatsapp_ledger_reminder,
    compute_gst_breakdown,
    evaluate_msme_43bh,
    parse_tally_xml,
    reconcile_gstr2b,
)
from engine.accounting_phase2 import (
    cancel_einvoice_irn,
    generate_einvoice_irn,
    generate_schedule_iii_and_gstr9,
    get_ca_portfolio,
    list_einvoices,
    record_bridge_sync,
    register_ca_firm_and_link_client,
    verify_algobridge_hmac,
    verify_all_ca_merkle_chains,
)
from engine.accounting_migrator import (
    commit_universal_migration,
    parse_natural_voucher_entry,
    preview_universal_migration,
)
from engine.accounting_vault import (
    GmailVaultDispatcher,
    GoogleFreeVaultClient,
    export_company_snapshot,
    list_backup_history,
    pull_encrypted_vault_blob,
    push_encrypted_vault_blob,
    record_backup_event,
    restore_company_snapshot,
    seal_algobk_envelope,
    unseal_algobk_envelope,
)
from engine.security import verify_api_key

router = APIRouter(prefix="/api/v1/accounting", tags=["Algorise BooksOS Accounting"])

COMPANY_ID_RE = re.compile(r"^[A-Za-z0-9_-]{3,64}$")


def _validate_company_id(company_id: str) -> str:
    if not COMPANY_ID_RE.match(company_id or ""):
        raise HTTPException(
            status_code=400,
            detail="Invalid company_id: must be 3-64 alphanumeric, underscore, or hyphen characters",
        )
    return company_id


async def _authorize_company(company_id: str, x_algorise_key: Optional[str]) -> str:
    cid = _validate_company_id(company_id)
    if cid.startswith("demo_"):
        return cid
    if not x_algorise_key:
        raise HTTPException(
            status_code=401,
            detail="Missing X-Algorise-Key header for non-demo accounting tenant",
        )
    valid, _info = await verify_api_key(x_algorise_key)
    if not valid:
        raise HTTPException(status_code=401, detail="Invalid or inactive X-Algorise-Key")
    return cid


class GSTCalculateRequest(BaseModel):
    taxable_amount: float = Field(..., gt=0)
    gst_rate_pct: float = Field(18.0, ge=0, le=28)
    company_state_code: str = Field("24", min_length=2, max_length=2)
    party_gstin: Optional[str] = None
    party_state_code: Optional[str] = None


class LedgerCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    parent_group: str = Field("Sundry Debtors", max_length=64)
    gstin: str = Field("", max_length=20)
    msme_category: str = Field("NONE", max_length=16)
    udyam_no: str = Field("", max_length=32)
    opening_balance: float = Field(0.0, ge=0)
    opening_dr_cr: str = Field("DR")
    phone: str = Field("", max_length=24)
    actor: str = Field("accountant", max_length=64)


class VoucherLineRequest(BaseModel):
    ledger_name: str = Field(..., min_length=1, max_length=128)
    dr_cr: str = Field(...)
    amount: float = Field(..., gt=0)
    bill_ref: str = Field("", max_length=64)
    bill_type: str = Field("New Ref", max_length=32)


class VoucherCreateRequest(BaseModel):
    voucher_type: str = Field("JOURNAL", max_length=32)
    voucher_date: Optional[str] = None
    voucher_no: Optional[str] = None
    narration: str = Field("", max_length=512)
    is_pdc: bool = False
    pdc_date: str = ""
    party_gstin: str = ""
    has_written_agreement: bool = False
    agreed_credit_days: int = Field(15, ge=1, le=365)
    actor: str = Field("accountant", max_length=64)
    entries: List[VoucherLineRequest]


class VoucherCancelRequest(BaseModel):
    reason: str = Field("Cancelled via BooksOS", max_length=256)
    actor: str = Field("accountant", max_length=64)


class TallyXMLImportRequest(BaseModel):
    xml_content: str = Field(..., min_length=10)
    actor: str = Field("algobridge", max_length=64)


class GSTR2BReconcileRequest(BaseModel):
    books_purchases: List[Dict[str, Any]] = Field(default_factory=list)
    portal_2b_entries: List[Dict[str, Any]] = Field(default_factory=list)
    rounding_tolerance: float = Field(2.0, ge=0, le=50)
    date_tolerance_days: int = Field(5, ge=0, le=30)


class MSME43BHRequest(BaseModel):
    bills: List[Dict[str, Any]] = Field(default_factory=list)
    as_of_date: Optional[str] = None


class WhatsAppReminderRequest(BaseModel):
    company_name: str = Field("Algorise Client Enterprise", max_length=128)
    party_name: str = Field(..., min_length=1, max_length=128)
    outstanding_amount: float = Field(..., gt=0)
    overdue_days: int = Field(0, ge=0)
    language: str = Field("en", max_length=16)
    upi_id: str = Field("", max_length=64)


class EInvoiceItemRequest(BaseModel):
    item_name: str = Field("Goods / Service", max_length=128)
    hsn_code: str = Field(..., min_length=4, max_length=8)
    taxable_value: float = Field(..., gt=0)
    gst_rate_pct: float = Field(5.0, ge=0, le=28)


class EInvoiceGenerateRequest(BaseModel):
    seller_gstin: str = Field(..., min_length=15, max_length=15)
    buyer_gstin: str = Field(..., min_length=15, max_length=15)
    doc_no: str = Field(..., min_length=1, max_length=32)
    doc_date: str
    doc_type: str = Field("INV", max_length=3)
    voucher_id: str = Field("", max_length=64)
    generate_eway_bill: bool = True
    distance_km: int = Field(45, ge=1, le=5000)
    vehicle_no: str = Field("", max_length=24)
    actor: str = Field("gsp_sandbox", max_length=64)
    items: List[EInvoiceItemRequest]


class EInvoiceCancelRequest(BaseModel):
    reason: str = Field("Data entry mistake", max_length=256)
    actor: str = Field("gsp_sandbox", max_length=64)


class BridgeSyncRequest(BaseModel):
    company_id: str = Field(..., min_length=3, max_length=64)
    source_host: str = Field("localhost:9000", max_length=128)
    tally_company: str = Field("", max_length=128)
    xml_content: str = Field(..., min_length=10)


class CAClientLinkRequest(BaseModel):
    firm_name: str = Field(..., min_length=2, max_length=128)
    frn_number: str = Field("", max_length=32)
    company_id: str = Field(..., min_length=3, max_length=64)
    company_name: str = Field(..., min_length=2, max_length=128)
    company_gstin: str = Field("24AABCA1234F1Z5", min_length=15, max_length=15)
    plan_tier: str = Field("GROWTH", max_length=16)


@router.get("/health")
async def accounting_health():
    return {
        "status": "HEALTHY",
        "product": "Algorise BooksOS",
        "capabilities": [
            "double_entry_decimal_ledger",
            "mca_rule_11g_merkle_audit",
            "tally_port_9000_xml_bridge",
            "fuzzy_gstr2b_ims_reconciler",
            "msme_43bh_disallowance_radar",
            "gsp_irp_einvoice_sandbox",
            "ca_super_console_schedule_iii_gstr9",
        ],
    }


@router.post("/gst/calculate")
async def calculate_gst(req: GSTCalculateRequest):
    try:
        return compute_gst_breakdown(
            taxable_amount=req.taxable_amount,
            gst_rate_pct=req.gst_rate_pct,
            company_state_code=req.company_state_code,
            party_gstin=req.party_gstin,
            party_state_code=req.party_state_code,
        )
    except AccountingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/shadow-audit")
async def tally_shadow_audit(req: TallyXMLImportRequest):
    """Lead-magnet diagnostic: audits a Tally XML export for Rule 11(g), 43B(h), and parity gaps."""
    try:
        parsed = parse_tally_xml(req.xml_content)
    except AccountingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    debtors = [l for l in parsed["ledgers"] if "debtor" in l["parent_group"].lower() and l["opening_dr_cr"] == "DR"]
    creditors = [l for l in parsed["ledgers"] if "creditor" in l["parent_group"].lower()]
    total_receivables = sum(float(l["opening_balance"]) for l in debtors)

    return {
        "status": "AUDIT_COMPLETE",
        "source_detected": "Tally.ERP 9 / TallyPrime XML",
        "masters_scanned": {
            "ledgers": len(parsed["ledgers"]),
            "stock_items": len(parsed["stock_items"]),
            "vouchers": len(parsed["vouchers"]),
            "sundry_debtors": len(debtors),
            "sundry_creditors": len(creditors),
        },
        "risk_findings": [
            {
                "code": "MCA_RULE_11G_GAP",
                "severity": "HIGH",
                "message": "Legacy Tally XML carries zero cryptographic edit-log proof. Algorise BooksOS adds automatic SHA-256 Merkle audit chaining.",
            },
            {
                "code": "RECEIVABLES_RECOVERY_OPPORTUNITY",
                "severity": "MEDIUM",
                "amount_inr": round(total_receivables, 2),
                "message": "Automatable via zero-markup WhatsApp ledger confirmations & UPI pay links.",
            },
            {
                "code": "SINGLE_THREADED_CORRUPTION_RISK",
                "severity": "HIGH",
                "message": "Eliminated upon migrating from local .900/.tsf files to Algorise ACID WAL + cloud sync.",
            },
        ],
    }


@router.get("/companies/{company_id}/summary")
async def get_company_summary(company_id: str, x_algorise_key: Optional[str] = Header(default=None)):
    cid = await _authorize_company(company_id, x_algorise_key)
    return accounting_store.get_financial_summary(cid)


@router.get("/companies/{company_id}/ledgers")
async def list_ledgers(company_id: str, x_algorise_key: Optional[str] = Header(default=None)):
    cid = await _authorize_company(company_id, x_algorise_key)
    return {"company_id": cid, "ledgers": accounting_store.get_ledgers(cid)}


@router.post("/companies/{company_id}/ledgers")
async def create_ledger(
    company_id: str, req: LedgerCreateRequest, x_algorise_key: Optional[str] = Header(default=None)
):
    cid = await _authorize_company(company_id, x_algorise_key)
    try:
        return accounting_store.create_or_update_ledger(
            company_id=cid,
            name=req.name,
            parent_group=req.parent_group,
            gstin=req.gstin,
            msme_category=req.msme_category,
            udyam_no=req.udyam_no,
            opening_balance=req.opening_balance,
            opening_dr_cr=req.opening_dr_cr,
            phone=req.phone,
            actor=req.actor,
        )
    except AccountingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/companies/{company_id}/vouchers")
async def list_vouchers(company_id: str, x_algorise_key: Optional[str] = Header(default=None)):
    cid = await _authorize_company(company_id, x_algorise_key)
    return {"company_id": cid, "vouchers": accounting_store.get_vouchers(cid)}


@router.post("/companies/{company_id}/vouchers")
async def create_voucher(
    company_id: str, req: VoucherCreateRequest, x_algorise_key: Optional[str] = Header(default=None)
):
    cid = await _authorize_company(company_id, x_algorise_key)
    try:
        return accounting_store.post_voucher(
            company_id=cid,
            voucher_type=req.voucher_type,
            voucher_date=req.voucher_date,
            entries=[e.model_dump() for e in req.entries],
            voucher_no=req.voucher_no,
            narration=req.narration,
            is_pdc=req.is_pdc,
            pdc_date=req.pdc_date,
            party_gstin=req.party_gstin,
            has_written_agreement=req.has_written_agreement,
            agreed_credit_days=req.agreed_credit_days,
            actor=req.actor,
        )
    except AccountingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/companies/{company_id}/vouchers/{voucher_id}/cancel")
async def cancel_voucher(
    company_id: str,
    voucher_id: str,
    req: VoucherCancelRequest,
    x_algorise_key: Optional[str] = Header(default=None),
):
    cid = await _authorize_company(company_id, x_algorise_key)
    try:
        return accounting_store.cancel_voucher(cid, voucher_id, reason=req.reason, actor=req.actor)
    except AccountingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/companies/{company_id}/import-tally-xml")
async def import_tally_xml(
    company_id: str, req: TallyXMLImportRequest, x_algorise_key: Optional[str] = Header(default=None)
):
    cid = await _authorize_company(company_id, x_algorise_key)
    try:
        return accounting_store.import_tally_xml(cid, req.xml_content, actor=req.actor)
    except AccountingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/companies/{company_id}/reconcile-gstr2b")
async def run_gstr2b_reconciliation(
    company_id: str, req: GSTR2BReconcileRequest, x_algorise_key: Optional[str] = Header(default=None)
):
    await _authorize_company(company_id, x_algorise_key)
    try:
        return reconcile_gstr2b(
            books_purchases=req.books_purchases,
            portal_2b_entries=req.portal_2b_entries,
            rounding_tolerance=req.rounding_tolerance,
            date_tolerance_days=req.date_tolerance_days,
        )
    except AccountingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/companies/{company_id}/msme-43bh-radar")
async def run_msme_43bh_radar(
    company_id: str, req: MSME43BHRequest, x_algorise_key: Optional[str] = Header(default=None)
):
    await _authorize_company(company_id, x_algorise_key)
    try:
        return evaluate_msme_43bh(bills=req.bills, as_of_date=req.as_of_date)
    except AccountingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/companies/{company_id}/audit-trail")
async def get_audit_trail(company_id: str, limit: int = 100, x_algorise_key: Optional[str] = Header(default=None)):
    cid = await _authorize_company(company_id, x_algorise_key)
    return {"company_id": cid, "blocks": accounting_store.get_audit_trail(cid, limit=limit)}


@router.get("/companies/{company_id}/audit-trail/verify")
async def verify_audit_trail(company_id: str, x_algorise_key: Optional[str] = Header(default=None)):
    cid = await _authorize_company(company_id, x_algorise_key)
    return accounting_store.verify_audit_chain(cid)


@router.post("/companies/{company_id}/whatsapp-reminder")
async def generate_whatsapp_reminder(
    company_id: str, req: WhatsAppReminderRequest, x_algorise_key: Optional[str] = Header(default=None)
):
    await _authorize_company(company_id, x_algorise_key)
    try:
        return build_whatsapp_ledger_reminder(
            company_name=req.company_name,
            party_name=req.party_name,
            outstanding_amount=req.outstanding_amount,
            overdue_days=req.overdue_days,
            language=req.language,
            upi_id=req.upi_id,
        )
    except AccountingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/companies/{company_id}/einvoices")
async def get_company_einvoices(company_id: str, x_algorise_key: Optional[str] = Header(default=None)):
    cid = await _authorize_company(company_id, x_algorise_key)
    return {"company_id": cid, "einvoices": list_einvoices(accounting_store, cid)}


@router.post("/companies/{company_id}/einvoice/generate")
async def create_einvoice_irn(
    company_id: str, req: EInvoiceGenerateRequest, x_algorise_key: Optional[str] = Header(default=None)
):
    cid = await _authorize_company(company_id, x_algorise_key)
    try:
        return generate_einvoice_irn(
            store=accounting_store,
            company_id=cid,
            seller_gstin=req.seller_gstin,
            buyer_gstin=req.buyer_gstin,
            doc_no=req.doc_no,
            doc_date=req.doc_date,
            items=[i.model_dump() for i in req.items],
            doc_type=req.doc_type,
            voucher_id=req.voucher_id,
            generate_eway_bill=req.generate_eway_bill,
            distance_km=req.distance_km,
            vehicle_no=req.vehicle_no,
            actor=req.actor,
        )
    except AccountingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/companies/{company_id}/einvoice/{irn}/cancel")
async def cancel_company_einvoice(
    company_id: str,
    irn: str,
    req: EInvoiceCancelRequest,
    x_algorise_key: Optional[str] = Header(default=None),
):
    cid = await _authorize_company(company_id, x_algorise_key)
    try:
        return cancel_einvoice_irn(accounting_store, cid, irn, reason=req.reason, actor=req.actor)
    except AccountingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/companies/{company_id}/schedule-iii-gstr9")
async def get_schedule_iii_gstr9(company_id: str, x_algorise_key: Optional[str] = Header(default=None)):
    cid = await _authorize_company(company_id, x_algorise_key)
    return generate_schedule_iii_and_gstr9(accounting_store, cid)


@router.post("/bridge/sync")
async def algobridge_signed_sync(
    request: Request,
    req: BridgeSyncRequest,
    x_algorise_key: Optional[str] = Header(default=None),
    x_algobridge_timestamp: Optional[str] = Header(default=None),
    x_algobridge_nonce: Optional[str] = Header(default=None),
    x_algobridge_signature: Optional[str] = Header(default=None),
):
    """Receive HMAC-SHA256 authenticated Tally Port 9000 XML sync from AlgoBridge."""
    cid = await _authorize_company(req.company_id, x_algorise_key)
    raw_body = await request.body()
    try:
        verify_algobridge_hmac(
            accounting_store,
            raw_body=raw_body,
            timestamp_hdr=x_algobridge_timestamp,
            nonce_hdr=x_algobridge_nonce,
            signature_hdr=x_algobridge_signature,
        )
        res = accounting_store.import_tally_xml(cid, req.xml_content, actor="algobridge")
        record_bridge_sync(accounting_store, cid, req.source_host, req.tally_company, res)
        res["hmac_verified"] = True
        return res
    except AccountingError as exc:
        msg = str(exc)
        status = 403 if ("HMAC" in msg or "Replay" in msg or "drift" in msg or "Signature" in msg) else 400
        raise HTTPException(status_code=status, detail=msg) from exc


@router.get("/ca/{ca_id}/portfolio")
async def get_ca_firm_portfolio(ca_id: str, x_algorise_key: Optional[str] = Header(default=None)):
    cid = await _authorize_company(ca_id, x_algorise_key)
    return get_ca_portfolio(accounting_store, cid)


@router.post("/ca/{ca_id}/clients")
async def link_ca_client(
    ca_id: str, req: CAClientLinkRequest, x_algorise_key: Optional[str] = Header(default=None)
):
    firm_id = await _authorize_company(ca_id, x_algorise_key)
    client_cid = _validate_company_id(req.company_id)
    try:
        return register_ca_firm_and_link_client(
            store=accounting_store,
            ca_id=firm_id,
            firm_name=req.firm_name,
            company_id=client_cid,
            company_name=req.company_name,
            company_gstin=req.company_gstin,
            plan_tier=req.plan_tier,
            frn_number=req.frn_number,
        )
    except AccountingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/ca/{ca_id}/verify-all-merkle")
async def verify_ca_merkle_batch(ca_id: str, x_algorise_key: Optional[str] = Header(default=None)):
    cid = await _authorize_company(ca_id, x_algorise_key)
    return verify_all_ca_merkle_chains(accounting_store, cid)


# ============================================================================
# PHASE 3: ALGOMIGRATE, 1-LINE NATURAL AI ENTRY & ZERO-KNOWLEDGE GOOGLE VAULT
# ============================================================================

class NaturalEntryRequest(BaseModel):
    sentence: str = Field(..., min_length=3, max_length=400)
    company_state_code: str = Field("24", min_length=2, max_length=2)
    party_gstin: Optional[str] = None


class UniversalMigrateRequest(BaseModel):
    filename: str = Field("import.csv", max_length=128)
    raw_text: Optional[str] = None
    raw_base64: Optional[str] = None
    source_hint: Optional[str] = None
    actor: str = Field("algomigrate", max_length=64)


class VaultSealRequest(BaseModel):
    passphrase: str = Field(..., min_length=6, max_length=128)
    compress: bool = True


class VaultUnsealRequest(BaseModel):
    passphrase: str = Field(..., min_length=6, max_length=128)
    envelope_b64: str = Field(..., min_length=32)
    actor: str = Field("vault_restore", max_length=64)


class VaultSyncPushRequest(BaseModel):
    device_id: str = Field("web_client", max_length=64)
    envelope_b64: str = Field(..., min_length=32)
    expected_min_version: Optional[int] = None


class GmailSMTPBackupRequest(BaseModel):
    passphrase: str = Field(..., min_length=6, max_length=128)
    recipient_email: str
    sender_email: Optional[str] = None
    gmail_app_password: str = Field(..., min_length=4)


class GoogleOAuthUrlRequest(BaseModel):
    client_id: str = Field(..., min_length=8)
    redirect_uri: str = Field(..., min_length=8)
    include_sheets_opt_in: bool = False


class GoogleCloudBackupRequest(BaseModel):
    access_token: str = Field(..., min_length=10)
    passphrase: str = Field(..., min_length=6, max_length=128)
    user_email: Optional[str] = None
    upload_to_drive: bool = True
    insert_into_gmail: bool = False
    sync_optin_sheets: bool = False
    spreadsheet_id: Optional[str] = None


@router.post("/natural-entry/parse")
async def parse_natural_entry(req: NaturalEntryRequest):
    try:
        return parse_natural_voucher_entry(
            sentence=req.sentence,
            company_state_code=req.company_state_code,
            party_gstin=req.party_gstin,
        )
    except AccountingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/migrate/preview")
async def preview_market_migration(req: UniversalMigrateRequest):
    raw_bytes = None
    if req.raw_base64:
        try:
            raw_bytes = base64.b64decode(req.raw_base64.encode("ascii"), validate=True)
        except Exception as exc:
            raise HTTPException(status_code=400, detail="Invalid base64 migration payload") from exc
    try:
        return preview_universal_migration(
            filename=req.filename,
            raw_bytes=raw_bytes,
            raw_text=req.raw_text,
            source_hint=req.source_hint,
        )
    except AccountingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/companies/{company_id}/migrate/commit")
async def commit_market_migration(
    company_id: str,
    req: UniversalMigrateRequest,
    x_algorise_key: Optional[str] = Header(default=None),
):
    cid = await _authorize_company(company_id, x_algorise_key)
    raw_bytes = None
    if req.raw_base64:
        try:
            raw_bytes = base64.b64decode(req.raw_base64.encode("ascii"), validate=True)
        except Exception as exc:
            raise HTTPException(status_code=400, detail="Invalid base64 migration payload") from exc
    try:
        return commit_universal_migration(
            store=accounting_store,
            company_id=cid,
            filename=req.filename,
            raw_bytes=raw_bytes,
            raw_text=req.raw_text,
            source_hint=req.source_hint,
            actor=req.actor,
        )
    except AccountingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/companies/{company_id}/vault/seal")
async def seal_company_vault(
    company_id: str,
    req: VaultSealRequest,
    x_algorise_key: Optional[str] = Header(default=None),
):
    cid = await _authorize_company(company_id, x_algorise_key)
    try:
        snapshot = export_company_snapshot(accounting_store, cid)
        raw_json = json.dumps(snapshot, separators=(",", ":"), default=str).encode("utf-8")
        envelope = seal_algobk_envelope(raw_json, req.passphrase, compress=req.compress)
        digest = hashlib.sha256(envelope).hexdigest()
        return {
            "format": "ALGBK01",
            "company_id": cid,
            "file_name": f"{cid}-vault.algobook",
            "size_bytes": len(envelope),
            "sha256": digest,
            "envelope_b64": base64.b64encode(envelope).decode("ascii"),
        }
    except AccountingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/companies/{company_id}/vault/unseal-restore")
async def unseal_and_restore_vault(
    company_id: str,
    req: VaultUnsealRequest,
    x_algorise_key: Optional[str] = Header(default=None),
):
    cid = await _authorize_company(company_id, x_algorise_key)
    try:
        raw_env = base64.b64decode(req.envelope_b64.encode("ascii"), validate=True)
        plaintext = unseal_algobk_envelope(raw_env, req.passphrase)
        snapshot = json.loads(plaintext.decode("utf-8"))
        return restore_company_snapshot(accounting_store, cid, snapshot, actor=req.actor)
    except AccountingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid snapshot content: {exc}") from exc


@router.post("/companies/{company_id}/vault/sync-push")
async def push_vault_sync(
    company_id: str,
    req: VaultSyncPushRequest,
    x_algorise_key: Optional[str] = Header(default=None),
):
    cid = await _authorize_company(company_id, x_algorise_key)
    try:
        return push_encrypted_vault_blob(
            store=accounting_store,
            company_id=cid,
            envelope_b64=req.envelope_b64,
            device_id=req.device_id,
            expected_min_version=req.expected_min_version,
        )
    except AccountingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/companies/{company_id}/vault/sync-pull")
async def pull_vault_sync(company_id: str, x_algorise_key: Optional[str] = Header(default=None)):
    cid = await _authorize_company(company_id, x_algorise_key)
    return pull_encrypted_vault_blob(accounting_store, cid)


@router.get("/companies/{company_id}/vault/history")
async def get_vault_backup_history(company_id: str, x_algorise_key: Optional[str] = Header(default=None)):
    cid = await _authorize_company(company_id, x_algorise_key)
    return {"company_id": cid, "history": list_backup_history(accounting_store, cid)}


@router.post("/companies/{company_id}/vault/gmail-smtp-backup")
async def send_encrypted_gmail_smtp_backup(
    company_id: str,
    req: GmailSMTPBackupRequest,
    x_algorise_key: Optional[str] = Header(default=None),
):
    cid = await _authorize_company(company_id, x_algorise_key)
    try:
        snapshot = export_company_snapshot(accounting_store, cid)
        raw_json = json.dumps(snapshot, separators=(",", ":"), default=str).encode("utf-8")
        envelope = seal_algobk_envelope(raw_json, req.passphrase, compress=True)
        fname = f"{cid}-booksos-vault.algobook"
        res = GmailVaultDispatcher.dispatch_via_smtp(
            envelope_bytes=envelope,
            file_name=fname,
            recipient_email=req.recipient_email,
            sender_email=req.sender_email or req.recipient_email,
            gmail_app_password=req.gmail_app_password,
            company_name=snapshot["company"]["name"],
        )
        record_backup_event(accounting_store, cid, "GMAIL_SMTP", req.recipient_email, envelope, res["status"])
        return res
    except AccountingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Gmail SMTP dispatch error: {exc}") from exc


@router.post("/vault/google-oauth-url")
async def create_google_vault_oauth_url(req: GoogleOAuthUrlRequest):
    try:
        return GoogleFreeVaultClient.build_oauth_authorize_url(
            client_id=req.client_id,
            redirect_uri=req.redirect_uri,
            include_sheets_opt_in=req.include_sheets_opt_in,
        )
    except AccountingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/companies/{company_id}/vault/google-cloud-backup")
async def dispatch_google_oauth_cloud_backup(
    company_id: str,
    req: GoogleCloudBackupRequest,
    x_algorise_key: Optional[str] = Header(default=None),
):
    cid = await _authorize_company(company_id, x_algorise_key)
    try:
        snapshot = export_company_snapshot(accounting_store, cid)
        raw_json = json.dumps(snapshot, separators=(",", ":"), default=str).encode("utf-8")
        envelope = seal_algobk_envelope(raw_json, req.passphrase, compress=True)
        fname = f"{cid}-booksos-vault.algobook"
        results: Dict[str, Any] = {"company_id": cid, "format": "ALGBK01", "targets": {}}

        if req.upload_to_drive:
            drv = await GoogleFreeVaultClient.upload_to_google_drive(req.access_token, envelope, fname)
            record_backup_event(accounting_store, cid, "GOOGLE_DRIVE", fname, envelope, drv["status"])
            results["targets"]["google_drive"] = drv

        if req.insert_into_gmail:
            if not req.user_email:
                raise AccountingError("user_email is required when insert_into_gmail=True")
            gml = await GmailVaultDispatcher.insert_via_gmail_api(
                req.access_token, envelope, fname, req.user_email, snapshot["company"]["name"]
            )
            record_backup_event(accounting_store, cid, "GMAIL_OAUTH", req.user_email, envelope, gml["status"])
            results["targets"]["gmail"] = gml

        if req.sync_optin_sheets:
            tb = accounting_store.get_trial_balance(cid)
            rows = [["Ledger", "Group", "Debit", "Credit"]] + [
                [r["ledger_name"], r["parent_group"], r["closing_debit"], r["closing_credit"]] for r in tb["ledgers"]
            ]
            sh = await GoogleFreeVaultClient.sync_optin_google_sheet(
                req.access_token,
                req.spreadsheet_id or "",
                rows,
                opt_in_confirmed=True,
            )
            results["targets"]["google_sheets"] = sh

        return results
    except AccountingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
