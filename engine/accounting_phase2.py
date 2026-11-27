"""
Algorise BooksOS Phase 2 Engine:
- Live GSP / NIC IRP e-Invoice (IRN + Signed QR) & e-Way Bill Sandbox
- Schedule III Statutory Balance Sheet & P&L + GSTR-9 Annual Summary
- Multi-Tenant CA Super-Console Aggregation & 25% Lifetime Rev-Share Ledger
- HMAC-SHA256 Anti-Replay Guard & Sync Telemetry for AlgoBridge Port 9000 Agent
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import re
import time
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List, Optional

from engine.accounting import (
    TWOPLACES,
    ZERO,
    AccountingError,
    AccountingStore,
    _parse_iso_date,
    accounting_store,
    to_decimal,
)

GSTIN_REGEX = re.compile(r"^\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z]$")
HSN_REGEX = re.compile(r"^\d{4}(\d{2})?(\d{2})?$")

PLAN_FEES_INR: Dict[str, Decimal] = {
    "STARTER": Decimal("2499.00"),
    "GROWTH": Decimal("5999.00"),
    "ENTERPRISE": Decimal("14999.00"),
}


def _fy_string(doc_dt_iso: str) -> str:
    d = _parse_iso_date(doc_dt_iso)
    start_year = d.year if d.month >= 4 else d.year - 1
    end_short = str((start_year + 1) % 100).zfill(2)
    return f"{start_year}-{end_short}"


def verify_algobridge_hmac(
    store: AccountingStore,
    raw_body: bytes,
    timestamp_hdr: Optional[str],
    nonce_hdr: Optional[str],
    signature_hdr: Optional[str],
    secret: Optional[str] = None,
    max_drift_seconds: int = 300,
) -> None:
    """Validate HMAC-SHA256 signature and timestamp/nonce anti-replay window."""
    if not timestamp_hdr or not nonce_hdr or not signature_hdr:
        raise AccountingError("Missing AlgoBridge HMAC headers (Timestamp, Nonce, Signature)")
    try:
        ts_val = int(str(timestamp_hdr).strip())
    except ValueError as exc:
        raise AccountingError("Invalid X-AlgoBridge-Timestamp") from exc

    now_sec = int(time.time())
    if abs(now_sec - ts_val) > max_drift_seconds:
        raise AccountingError("AlgoBridge request timestamp outside ±300s drift window")

    clean_nonce = str(nonce_hdr).strip()
    if len(clean_nonce) < 8:
        raise AccountingError("Invalid X-AlgoBridge-Nonce")

    signing_secret = (secret or os.environ.get("ALGOBRIDGE_HMAC_SECRET") or "algorise-bridge-dev-secret").encode("utf-8")
    body_hash = hashlib.sha256(raw_body).hexdigest()
    msg = f"{ts_val}.{clean_nonce}.{body_hash}".encode("utf-8")
    expected_sig = hmac.new(signing_secret, msg, hashlib.sha256).hexdigest()

    if not hmac.compare_digest(expected_sig.lower(), str(signature_hdr).strip().lower()):
        raise AccountingError("Invalid AlgoBridge HMAC signature")

    with store._connect() as conn:
        existing = conn.execute("SELECT 1 FROM bridge_nonces WHERE nonce = ?", (clean_nonce,)).fetchone()
        if existing:
            raise AccountingError("Replay detected: AlgoBridge nonce already used")
        conn.execute(
            "INSERT INTO bridge_nonces (nonce, seen_at) VALUES (?, ?)",
            (clean_nonce, datetime.now(timezone.utc).isoformat()),
        )


def generate_einvoice_irn(
    store: AccountingStore,
    company_id: str,
    seller_gstin: str,
    buyer_gstin: str,
    doc_no: str,
    doc_date: str,
    items: List[Dict[str, Any]],
    doc_type: str = "INV",
    voucher_id: str = "",
    generate_eway_bill: bool = True,
    distance_km: int = 45,
    vehicle_no: str = "",
    actor: str = "gsp_sandbox",
) -> Dict[str, Any]:
    """Generate NIC-compliant deterministic 64-char IRN, Signed QR payload, and E-Way Bill."""
    store.ensure_company(company_id)
    s_gst = (seller_gstin or "").upper().strip()
    b_gst = (buyer_gstin or "").upper().strip()
    if not GSTIN_REGEX.match(s_gst):
        raise AccountingError(f"Invalid Seller GSTIN format: {s_gst!r}")
    if not GSTIN_REGEX.match(b_gst):
        raise AccountingError(f"Invalid Buyer GSTIN format for B2B e-Invoice: {b_gst!r}")
    if not doc_no or not doc_no.strip():
        raise AccountingError("doc_no cannot be empty")
    if not items:
        raise AccountingError("At least one ItemList entry is required for e-Invoice")

    clean_doc_type = (doc_type or "INV").upper().strip()
    if clean_doc_type not in {"INV", "CRN", "DBN"}:
        raise AccountingError(f"Unsupported IRP DocTyp: {clean_doc_type}")

    iso_dt = _parse_iso_date(doc_date).isoformat()
    fy = _fy_string(iso_dt)
    is_interstate = s_gst[:2] != b_gst[:2]

    ass_total = ZERO
    cgst_total = ZERO
    sgst_total = ZERO
    igst_total = ZERO

    for idx, item in enumerate(items, start=1):
        hsn = str(item.get("hsn_code") or "").strip()
        if not HSN_REGEX.match(hsn):
            raise AccountingError(f"Item #{idx} has invalid HSN code (must be 4, 6, or 8 digits): {hsn!r}")
        taxable = to_decimal(item.get("taxable_value"))
        if taxable <= ZERO:
            raise AccountingError(f"Item #{idx} taxable_value must be positive")
        rate = to_decimal(item.get("gst_rate_pct", 5))
        line_tax = (taxable * rate / Decimal("100")).quantize(TWOPLACES, rounding=ROUND_HALF_UP)
        ass_total += taxable
        if is_interstate:
            igst_total += line_tax
        else:
            half = (line_tax / Decimal("2")).quantize(TWOPLACES, rounding=ROUND_HALF_UP)
            cgst_total += half
            sgst_total += line_tax - half

    total_tax = (cgst_total + sgst_total + igst_total).quantize(TWOPLACES, rounding=ROUND_HALF_UP)
    tot_inv_val = (ass_total + total_tax).quantize(TWOPLACES, rounding=ROUND_HALF_UP)

    # NIC IRP Official IRN Derivation: SHA-256(SellerGstin + DocNo + DocTyp + FY)
    irn_seed = f"{s_gst}{doc_no.strip().upper()}{clean_doc_type}{fy}"
    irn = hashlib.sha256(irn_seed.encode("utf-8")).hexdigest()

    now_utc = datetime.now(timezone.utc)
    ack_dt = now_utc.isoformat()
    ack_no = str(int(irn[:13], 16))[:15].rjust(15, "1")

    qr_claims = {
        "SellerGstin": s_gst,
        "BuyerGstin": b_gst,
        "DocNo": doc_no.strip().upper(),
        "DocTyp": clean_doc_type,
        "DocDt": iso_dt,
        "TotInvVal": str(tot_inv_val),
        "ItemCnt": len(items),
        "MainHsnCode": str(items[0]["hsn_code"]),
        "Irn": irn,
        "IrnDt": ack_dt,
    }
    claims_b64 = base64.urlsafe_b64encode(json.dumps(qr_claims, sort_keys=True).encode("utf-8")).decode("ascii").rstrip("=")
    qr_sig = hmac.new(b"algorise-irp-sandbox-key", claims_b64.encode("utf-8"), hashlib.sha256).hexdigest()[:32]
    signed_qr_payload = f"ALG1.{claims_b64}.{qr_sig}"

    ewb_no = ""
    ewb_valid_till = ""
    if generate_eway_bill and tot_inv_val > Decimal("50000.00"):
        ewb_no = "34" + str(int(irn[13:23], 16))[:10].rjust(10, "0")
        days_valid = max(1, (max(distance_km, 1) + 199) // 200)
        ewb_valid_till = (now_utc + timedelta(days=days_valid)).isoformat()

    with store._connect() as conn:
        existing = conn.execute("SELECT * FROM einvoices WHERE irn = ?", (irn,)).fetchone()
        if existing:
            row = dict(existing)
            if row["status"] == "ACTIVE":
                return row
            raise AccountingError(f"IRN {irn[:16]}... was previously cancelled and cannot be regenerated")

        conn.execute(
            """
            INSERT INTO einvoices
            (irn, company_id, voucher_id, doc_type, doc_no, doc_date, seller_gstin, buyer_gstin,
             taxable_value, total_tax, total_invoice_value, ack_no, ack_dt, signed_qr_payload,
             ewb_no, ewb_valid_till, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'ACTIVE', ?)
            """,
            (
                irn,
                company_id,
                voucher_id,
                clean_doc_type,
                doc_no.strip().upper(),
                iso_dt,
                s_gst,
                b_gst,
                str(ass_total),
                str(total_tax),
                str(tot_inv_val),
                ack_no,
                ack_dt,
                signed_qr_payload,
                ewb_no,
                ewb_valid_till,
                ack_dt,
            ),
        )
        created = dict(conn.execute("SELECT * FROM einvoices WHERE irn = ?", (irn,)).fetchone())
        store._append_audit_block(conn, company_id, actor, "GENERATE_IRN", "EINVOICE", irn, {}, created)
        return created


def cancel_einvoice_irn(
    store: AccountingStore,
    company_id: str,
    irn: str,
    reason: str = "Data entry mistake",
    actor: str = "gsp_sandbox",
) -> Dict[str, Any]:
    """Cancel an active IRN within NIC's 24-hour window and seal via Merkle audit log."""
    with store._connect() as conn:
        row = conn.execute("SELECT * FROM einvoices WHERE company_id = ? AND irn = ?", (company_id, irn)).fetchone()
        if not row:
            raise AccountingError(f"IRN not found: {irn}")
        before = dict(row)
        if before["status"] == "CANCELLED":
            raise AccountingError("IRN is already cancelled")
        ack_dt = datetime.fromisoformat(before["ack_dt"])
        if datetime.now(timezone.utc) - ack_dt > timedelta(hours=24):
            raise AccountingError("NIC 24-hour cancellation window expired; issue a Credit Note (CRN) instead")
        conn.execute(
            "UPDATE einvoices SET status='CANCELLED', cancel_reason=? WHERE company_id=? AND irn=?",
            (reason, company_id, irn),
        )
        after = dict(conn.execute("SELECT * FROM einvoices WHERE irn = ?", (irn,)).fetchone())
        store._append_audit_block(conn, company_id, actor, "CANCEL_IRN", "EINVOICE", irn, before, after)
        return after


def list_einvoices(store: AccountingStore, company_id: str) -> List[Dict[str, Any]]:
    store.ensure_company(company_id)
    with store._connect() as conn:
        rows = conn.execute(
            "SELECT * FROM einvoices WHERE company_id = ? ORDER BY created_at DESC",
            (company_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def generate_schedule_iii_and_gstr9(store: AccountingStore, company_id: str) -> Dict[str, Any]:
    """Build Companies Act Schedule III Financial Statements & GSTR-9 Annual Summary."""
    summary = store.get_financial_summary(company_id)
    tb = summary["trial_balance"]
    ledgers = {l["name"]: l for l in store.get_ledgers(company_id)}

    shareholders_funds = ZERO
    long_term_borrowings = ZERO
    trade_payables_msme = ZERO
    trade_payables_other = ZERO
    other_current_liabilities = ZERO

    fixed_assets = ZERO
    inventories = ZERO
    trade_receivables = ZERO
    cash_and_bank = ZERO
    other_current_assets = ZERO

    revenue_ops = ZERO
    other_income = ZERO
    purchases = ZERO
    direct_expenses = ZERO
    indirect_expenses = ZERO

    for row in tb["ledgers"]:
        name = row["ledger_name"]
        grp = row["parent_group"]
        dr = to_decimal(row["closing_debit"])
        cr = to_decimal(row["closing_credit"])
        net_cr = cr - dr
        net_dr = dr - cr
        msme_cat = (ledgers.get(name, {}).get("msme_category") or "NONE").upper()

        if grp == "Capital Account":
            shareholders_funds += net_cr
        elif grp == "Loans (Liability)":
            long_term_borrowings += net_cr
        elif grp == "Sundry Creditors":
            if msme_cat in {"MICRO", "SMALL"}:
                trade_payables_msme += net_cr
            else:
                trade_payables_other += net_cr
        elif grp in {"Duties & Taxes", "Current Liabilities", "Provisions"} and row["nature"] == "LIABILITY":
            other_current_liabilities += net_cr
        elif grp in {"Fixed Assets", "Investments"}:
            fixed_assets += net_dr
        elif grp == "Stock-in-Hand":
            inventories += net_dr
        elif grp == "Sundry Debtors":
            trade_receivables += net_dr
        elif grp in {"Cash-in-Hand", "Bank Accounts"}:
            cash_and_bank += net_dr
        elif row["nature"] == "ASSET":
            other_current_assets += net_dr
        elif grp == "Sales Accounts":
            revenue_ops += net_cr
        elif row["nature"] == "INCOME":
            other_income += net_cr
        elif grp == "Purchase Accounts":
            purchases += net_dr
        elif grp == "Direct Expenses":
            direct_expenses += net_dr
        elif row["nature"] == "EXPENSE":
            indirect_expenses += net_dr

    net_profit = (revenue_ops + other_income - purchases - direct_expenses - indirect_expenses).quantize(TWOPLACES)
    total_equity_liab = (
        shareholders_funds + net_profit + long_term_borrowings + trade_payables_msme + trade_payables_other + other_current_liabilities
    ).quantize(TWOPLACES)
    total_assets = (fixed_assets + inventories + trade_receivables + cash_and_bank + other_current_assets).quantize(TWOPLACES)

    # GSTR-9 Aggregation from Posted Sales/Purchase/Credit Note Vouchers
    vouchers = store.get_vouchers(company_id, include_cancelled=False)
    outward_taxable = ZERO
    out_cgst = ZERO
    out_sgst = ZERO
    out_igst = ZERO
    inward_taxable = ZERO
    in_cgst = ZERO
    in_sgst = ZERO
    in_igst = ZERO

    for v in vouchers:
        vt = v["voucher_type"]
        if vt == "SALES":
            for e in v["entries"]:
                ln = e["ledger_name"].lower()
                amt = to_decimal(e["amount"])
                if e["dr_cr"] == "CR":
                    if "cgst" in ln:
                        out_cgst += amt
                    elif "sgst" in ln:
                        out_sgst += amt
                    elif "igst" in ln:
                        out_igst += amt
                    else:
                        outward_taxable += amt
        elif vt == "CREDIT_NOTE":
            for e in v["entries"]:
                ln = e["ledger_name"].lower()
                amt = to_decimal(e["amount"])
                if e["dr_cr"] == "DR":
                    if "cgst" in ln:
                        out_cgst -= amt
                    elif "sgst" in ln:
                        out_sgst -= amt
                    elif "igst" in ln:
                        out_igst -= amt
                    else:
                        outward_taxable -= amt
        elif vt == "PURCHASE":
            for e in v["entries"]:
                ln = e["ledger_name"].lower()
                amt = to_decimal(e["amount"])
                if e["dr_cr"] == "DR":
                    if "cgst" in ln:
                        in_cgst += amt
                    elif "sgst" in ln:
                        in_sgst += amt
                    elif "igst" in ln:
                        in_igst += amt
                    else:
                        inward_taxable += amt

    total_out_tax = (out_cgst + out_sgst + out_igst).quantize(TWOPLACES)
    total_in_itc = (in_cgst + in_sgst + in_igst).quantize(TWOPLACES)

    return {
        "company_id": company_id,
        "schedule_iii": {
            "equity_and_liabilities": {
                "shareholders_funds": str((shareholders_funds + net_profit).quantize(TWOPLACES)),
                "non_current_liabilities": str(long_term_borrowings),
                "trade_payables_msme_micro_small": str(trade_payables_msme),
                "trade_payables_other": str(trade_payables_other),
                "other_current_liabilities": str(other_current_liabilities),
                "total": str(total_equity_liab),
            },
            "assets": {
                "fixed_assets": str(fixed_assets),
                "inventories": str(inventories),
                "trade_receivables": str(trade_receivables),
                "cash_and_cash_equivalents": str(cash_and_bank),
                "other_current_assets": str(other_current_assets),
                "total": str(total_assets),
            },
            "profit_and_loss": {
                "revenue_from_operations": str(revenue_ops),
                "other_income": str(other_income),
                "purchases_of_stock": str(purchases),
                "direct_expenses": str(direct_expenses),
                "indirect_expenses": str(indirect_expenses),
                "profit_before_tax": str(net_profit),
            },
            "balance_sheet_parity": total_equity_liab == total_assets,
        },
        "gstr_9_annual": {
            "table_4_outward_supplies": {
                "taxable_value": str(outward_taxable),
                "cgst": str(out_cgst),
                "sgst": str(out_sgst),
                "igst": str(out_igst),
                "total_output_tax": str(total_out_tax),
            },
            "table_6_itc_availed": {
                "taxable_purchases": str(inward_taxable),
                "cgst": str(in_cgst),
                "sgst": str(in_sgst),
                "igst": str(in_igst),
                "total_itc": str(total_in_itc),
            },
            "net_cash_tax_payable": str(max(ZERO, total_out_tax - total_in_itc)),
            "excess_itc_carryforward": str(max(ZERO, total_in_itc - total_out_tax)),
        },
    }


def register_ca_firm_and_link_client(
    store: AccountingStore,
    ca_id: str,
    firm_name: str,
    company_id: str,
    company_name: str,
    company_gstin: str = "24AABCA1234F1Z5",
    plan_tier: str = "GROWTH",
    frn_number: str = "",
) -> Dict[str, Any]:
    """Register a CA Firm and link an SME client with rev-share tracking."""
    tier = (plan_tier or "GROWTH").upper().strip()
    if tier not in PLAN_FEES_INR:
        raise AccountingError(f"Unsupported plan_tier: {tier}")
    fee = PLAN_FEES_INR[tier]
    state_code = company_gstin[:2] if len(company_gstin) >= 2 and company_gstin[:2].isdigit() else "24"
    store.ensure_company(company_id, name=company_name, gstin=company_gstin, state_code=state_code)
    now = datetime.now(timezone.utc).isoformat()

    with store._connect() as conn:
        conn.execute(
            """
            INSERT OR IGNORE INTO ca_firms (ca_id, firm_name, frn_number, rev_share_pct, created_at)
            VALUES (?, ?, ?, '25.00', ?)
            """,
            (ca_id, firm_name, frn_number, now),
        )
        conn.execute(
            """
            INSERT OR REPLACE INTO ca_client_links (ca_id, company_id, plan_tier, annual_fee_inr, linked_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (ca_id, company_id, tier, str(fee), now),
        )
    return {"ca_id": ca_id, "company_id": company_id, "plan_tier": tier, "annual_fee_inr": str(fee)}


def seed_demo_ca_portfolio(store: AccountingStore, ca_id: str) -> None:
    """Seed realistic multi-client CA portfolio ONLY for demo_* CA firms."""
    if not ca_id.startswith("demo_"):
        return
    with store._connect() as conn:
        count = conn.execute("SELECT COUNT(*) AS c FROM ca_client_links WHERE ca_id = ?", (ca_id,)).fetchone()["c"]
        if count > 0:
            return

    demo_clients = [
        ("demo_booksos_01", "Apex Fabrics & Traders", "24AABCA1234F1Z5", "GROWTH", "Navkar Dyeing Mills", "MICRO", "120000.00", "2026-10-10"),
        ("demo_ca_cli_02", "Varachha CVD Diamonds LLP", "24AABCV5512D1Z8", "ENTERPRISE", "Surat Laser Polishers", "SMALL", "85000.00", "2026-11-18"),
        ("demo_ca_cli_03", "Pandesara Chem & Dyes", "24AABCP8821K1Z4", "STARTER", "Shree Drum Packaging", "MICRO", "45000.00", "2026-11-01"),
    ]
    for cid, cname, cgst, tier, sup_name, msme_cat, pur_amt, bill_dt in demo_clients:
        register_ca_firm_and_link_client(
            store,
            ca_id=ca_id,
            firm_name="Mehta & Shah Chartered Accountants",
            company_id=cid,
            company_name=cname,
            company_gstin=cgst,
            plan_tier=tier,
            frn_number="124891W",
        )
        if not store.get_vouchers(cid):
            store.create_or_update_ledger(cid, "Capital Reserve", "Capital Account", opening_balance="500000.00", opening_dr_cr="CR")
            store.create_or_update_ledger(cid, "HDFC Bank Current A/c", "Bank Accounts", opening_balance="500000.00", opening_dr_cr="DR")
            store.create_or_update_ledger(cid, sup_name, "Sundry Creditors", msme_category=msme_cat, udyam_no="UDYAM-GJ-22-0011223")
            store.create_or_update_ledger(cid, "Surat Buyer Mart", "Sundry Debtors", gstin="24AABCS2211A1Z1")
            amt = to_decimal(pur_amt)
            half_tax = (amt * Decimal("0.025")).quantize(TWOPLACES)
            gross = (amt + half_tax * 2).quantize(TWOPLACES)
            store.post_voucher(
                cid,
                "PURCHASE",
                bill_dt,
                voucher_no=f"PUR-{cid[-2:]}",
                entries=[
                    {"ledger_name": "Purchase GST", "dr_cr": "DR", "amount": str(amt)},
                    {"ledger_name": "CGST Input", "dr_cr": "DR", "amount": str(half_tax)},
                    {"ledger_name": "SGST Input", "dr_cr": "DR", "amount": str(half_tax)},
                    {"ledger_name": sup_name, "dr_cr": "CR", "amount": str(gross), "bill_ref": f"BILL-{cid[-2:]}"},
                ],
                has_written_agreement=False,
                agreed_credit_days=15,
            )
            store.post_voucher(
                cid,
                "SALES",
                "2026-11-20",
                voucher_no=f"INV-{cid[-2:]}",
                entries=[
                    {"ledger_name": "Surat Buyer Mart", "dr_cr": "DR", "amount": "210000.00", "bill_ref": f"INV-{cid[-2:]}"},
                    {"ledger_name": "Sales GST", "dr_cr": "CR", "amount": "200000.00"},
                    {"ledger_name": "CGST Output", "dr_cr": "CR", "amount": "5000.00"},
                    {"ledger_name": "SGST Output", "dr_cr": "CR", "amount": "5000.00"},
                ],
            )


def get_ca_portfolio(store: AccountingStore, ca_id: str) -> Dict[str, Any]:
    """Return multi-tenant CA Super-Console health, rev-share, and compliance matrix."""
    seed_demo_ca_portfolio(store, ca_id)
    with store._connect() as conn:
        firm_row = conn.execute("SELECT * FROM ca_firms WHERE ca_id = ?", (ca_id,)).fetchone()
        links = conn.execute(
            """
            SELECT l.company_id, l.plan_tier, l.annual_fee_inr, c.name, c.gstin
            FROM ca_client_links l
            JOIN companies c ON c.company_id = l.company_id
            WHERE l.ca_id = ?
            ORDER BY l.id ASC
            """,
            (ca_id,),
        ).fetchall()

    rev_pct = to_decimal(firm_row["rev_share_pct"]) if firm_row else Decimal("25.00")
    total_arr = ZERO
    total_msme_risk = ZERO
    clients_out: List[Dict[str, Any]] = []
    all_merkle_valid = True

    for link in links:
        cid = link["company_id"]
        summary = store.get_financial_summary(cid)
        fee = to_decimal(link["annual_fee_inr"])
        total_arr += fee
        msme_exp = to_decimal(summary["msme_43bh"]["disallowed_exposure_amount"]) + to_decimal(
            summary["msme_43bh"]["critical_due_5d_amount"]
        )
        total_msme_risk += msme_exp
        audit = summary["audit_trail_integrity"]
        if not audit.get("valid"):
            all_merkle_valid = False

        with store._connect() as conn:
            last_sync = conn.execute(
                "SELECT synced_at, source_host FROM bridge_sync_runs WHERE company_id = ? ORDER BY id DESC LIMIT 1",
                (cid,),
            ).fetchone()
            irn_count = conn.execute(
                "SELECT COUNT(*) AS c FROM einvoices WHERE company_id = ? AND status = 'ACTIVE'",
                (cid,),
            ).fetchone()["c"]

        clients_out.append(
            {
                "company_id": cid,
                "name": link["name"],
                "gstin": link["gstin"],
                "plan_tier": link["plan_tier"],
                "annual_fee_inr": str(fee),
                "ca_rev_share_inr": str((fee * rev_pct / Decimal("100")).quantize(TWOPLACES)),
                "trial_balance_balanced": summary["trial_balance"]["is_balanced"],
                "net_profit": summary["profit_and_loss"]["net_profit"],
                "msme_43bh_risk": str(msme_exp),
                "merkle_valid": audit.get("valid", False),
                "merkle_blocks": audit.get("blocks_verified", 0),
                "active_einvoices": irn_count,
                "last_bridge_sync": last_sync["synced_at"] if last_sync else "Never (Direct Cloud)",
            }
        )

    ca_earnings = (total_arr * rev_pct / Decimal("100")).quantize(TWOPLACES)
    return {
        "ca_id": ca_id,
        "firm_name": firm_row["firm_name"] if firm_row else "CA Partner Firm",
        "frn_number": firm_row["frn_number"] if firm_row else "",
        "rev_share_pct": str(rev_pct),
        "portfolio_summary": {
            "total_clients": len(clients_out),
            "total_arr_inr": str(total_arr),
            "ca_recurring_earnings_inr": str(ca_earnings),
            "total_msme_43bh_exposure_inr": str(total_msme_risk),
            "all_merkle_chains_valid": all_merkle_valid,
        },
        "clients": clients_out,
    }


def verify_all_ca_merkle_chains(store: AccountingStore, ca_id: str) -> Dict[str, Any]:
    """Run batch MCA Rule 11(g) SHA-256 verification across every client of a CA firm."""
    portfolio = get_ca_portfolio(store, ca_id)
    results = []
    passed = 0
    for c in portfolio["clients"]:
        res = store.verify_audit_chain(c["company_id"])
        if res.get("valid"):
            passed += 1
        results.append(
            {
                "company_id": c["company_id"],
                "name": c["name"],
                "valid": res.get("valid", False),
                "blocks_verified": res.get("blocks_verified", 0),
                "merkle_head": res.get("merkle_head", ""),
            }
        )
    return {
        "ca_id": ca_id,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "clients_checked": len(results),
        "clients_passed": passed,
        "all_compliant": passed == len(results),
        "results": results,
    }


def record_bridge_sync(
    store: AccountingStore,
    company_id: str,
    source_host: str,
    tally_company: str,
    import_result: Dict[str, Any],
) -> None:
    now = datetime.now(timezone.utc).isoformat()
    with store._connect() as conn:
        conn.execute(
            """
            INSERT INTO bridge_sync_runs
            (company_id, source_host, tally_company, imported_ledgers, imported_stock_items, imported_vouchers, parity_ok, synced_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                company_id,
                source_host,
                tally_company,
                int(import_result.get("imported_ledgers", 0)),
                int(import_result.get("imported_stock_items", 0)),
                int(import_result.get("imported_vouchers", 0)),
                1 if import_result.get("trial_balance_parity", {}).get("is_balanced", True) else 0,
                now,
            ),
        )
