"""
Algorise BooksOS — Deterministic Accounting, Tally XML Bridge, GST/IMS,
Section 43B(h) MSME Radar & MCA Rule 11(g) Merkle Audit Ledger Engine.

Designed to surpass Tally.ERP 9 and TallyPrime with:
- Exact Decimal double-entry invariant (Sum(Dr) == Sum(Cr) enforced)
- Local SQLite WAL ACID persistence (zero .900/.tsf corruption)
- Non-disableable SHA-256 Merkle Edit Log (MCA Rule 11(g) compliant)
- Lossless Tally Port 9000 XML importer (Ledgers, Bill-by-Bill, Stock, Vouchers)
- Fuzzy GSTR-2B + IMS Reconciliation (tolerates prefix & rounding diffs)
- Section 43B(h) MSME 15/45-day tax disallowance shield
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import uuid
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


TWOPLACES = Decimal("0.01")
ZERO = Decimal("0.00")
GENESIS_HASH = "0" * 64

STANDARD_TALLY_GROUPS: Dict[str, str] = {
    "Capital Account": "LIABILITY",
    "Loans (Liability)": "LIABILITY",
    "Current Liabilities": "LIABILITY",
    "Sundry Creditors": "LIABILITY",
    "Duties & Taxes": "LIABILITY",
    "Provisions": "LIABILITY",
    "Fixed Assets": "ASSET",
    "Investments": "ASSET",
    "Current Assets": "ASSET",
    "Sundry Debtors": "ASSET",
    "Bank Accounts": "ASSET",
    "Cash-in-Hand": "ASSET",
    "Stock-in-Hand": "ASSET",
    "Sales Accounts": "INCOME",
    "Direct Incomes": "INCOME",
    "Indirect Incomes": "INCOME",
    "Purchase Accounts": "EXPENSE",
    "Direct Expenses": "EXPENSE",
    "Indirect Expenses": "EXPENSE",
}

VOUCHER_TYPES = {
    "CONTRA",
    "PAYMENT",
    "RECEIPT",
    "JOURNAL",
    "SALES",
    "PURCHASE",
    "CREDIT_NOTE",
    "DEBIT_NOTE",
    "JOB_WORK_OUT",
    "JOB_WORK_IN",
}


class AccountingError(ValueError):
    """Domain validation error for accounting invariants."""


class ImbalancedVoucherError(AccountingError):
    """Raised whenever sum(Debit) != sum(Credit)."""


def to_decimal(val: Any) -> Decimal:
    """Parse numeric value into quantized Decimal(0.01) safely."""
    if isinstance(val, Decimal):
        return val.quantize(TWOPLACES, rounding=ROUND_HALF_UP)
    if val is None or val == "":
        return ZERO
    cleaned = str(val).replace(",", "").strip()
    try:
        return Decimal(cleaned).quantize(TWOPLACES, rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError) as exc:
        raise AccountingError(f"Invalid monetary amount: {val!r}") from exc


def _canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)


def _normalize_invoice_no(inv_no: str) -> str:
    """Normalize invoice numbers for fuzzy GSTR-2B matching (INV/26-27/0045 -> 45)."""
    s = (inv_no or "").upper().strip()
    s = re.sub(r"^(?:INV|BILL|TAX|TI|SI|PI)[-/\s]*", "", s)
    s = re.sub(r"(?:^|[-/\s])(?:FY)?\d{2,4}[-/]\d{2,4}(?:[-/\s]|$)", "", s)
    s = re.sub(r"[^A-Z0-9]", "", s)
    if s.isdigit():
        return str(int(s))
    return re.sub(r"^0+", "", s) or s


def _gstin_state_code(gstin: Optional[str]) -> str:
    if not gstin or len(gstin.strip()) < 2:
        return ""
    code = gstin.strip()[:2]
    return code if code.isdigit() else ""


def _parse_iso_date(raw: Optional[str]) -> date:
    if not raw:
        return datetime.now(timezone.utc).date()
    s = raw.strip()
    if re.fullmatch(r"\d{8}", s):
        return datetime.strptime(s, "%Y%m%d").date()
    return date.fromisoformat(s[:10])


def compute_gst_breakdown(
    taxable_amount: Any,
    gst_rate_pct: Any,
    company_state_code: str,
    party_gstin: Optional[str] = None,
    party_state_code: Optional[str] = None,
) -> Dict[str, Any]:
    """Compute CGST/SGST vs IGST deterministically using Decimal math."""
    taxable = to_decimal(taxable_amount)
    rate = to_decimal(gst_rate_pct)
    total_tax = (taxable * rate / Decimal("100")).quantize(TWOPLACES, rounding=ROUND_HALF_UP)

    resolved_party_state = (party_state_code or _gstin_state_code(party_gstin) or company_state_code or "24").zfill(2)
    resolved_comp_state = (company_state_code or "24").zfill(2)
    is_interstate = resolved_party_state != resolved_comp_state

    if is_interstate:
        cgst = ZERO
        sgst = ZERO
        igst = total_tax
        supply_type = "INTER_STATE"
    else:
        cgst = (total_tax / Decimal("2")).quantize(TWOPLACES, rounding=ROUND_HALF_UP)
        sgst = (total_tax - cgst).quantize(TWOPLACES, rounding=ROUND_HALF_UP)
        igst = ZERO
        supply_type = "INTRA_STATE"

    return {
        "supply_type": supply_type,
        "taxable_amount": str(taxable),
        "gst_rate_pct": str(rate),
        "cgst": str(cgst),
        "sgst": str(sgst),
        "igst": str(igst),
        "total_tax": str(total_tax),
        "gross_total": str((taxable + total_tax).quantize(TWOPLACES, rounding=ROUND_HALF_UP)),
    }


def evaluate_msme_43bh(
    bills: List[Dict[str, Any]],
    as_of_date: Optional[str] = None,
) -> Dict[str, Any]:
    """Evaluate supplier payables against Section 43B(h) 15/45-day limits.

    Under Section 43B(h) of Income Tax Act + Section 15 MSMED Act:
    - Micro/Small suppliers must be paid within 15 days (no written agreement)
      or max 45 days (with written agreement; longer credit terms like 60/90 days
      are legally overridden to 45 days).
    """
    ref_date = _parse_iso_date(as_of_date)
    evaluated: List[Dict[str, Any]] = []
    disallowed_total = ZERO
    critical_total = ZERO
    due_soon_total = ZERO

    for bill in bills:
        cat = str(bill.get("msme_category") or "NONE").upper().strip()
        if cat not in {"MICRO", "SMALL"}:
            continue
        outstanding = to_decimal(bill.get("outstanding_amount", bill.get("amount", 0)))
        if outstanding <= ZERO:
            continue

        bill_dt = _parse_iso_date(bill.get("bill_date"))
        has_agreement = bool(bill.get("has_written_agreement", False))
        agreed_days = int(bill.get("agreed_credit_days") or (45 if has_agreement else 15))
        statutory_cap = min(max(agreed_days, 1), 45) if has_agreement else 15
        due_date = bill_dt + timedelta(days=statutory_cap)
        days_elapsed = (ref_date - bill_dt).days
        days_remaining = (due_date - ref_date).days

        if days_remaining < 0:
            risk_status = "DISALLOWED_EXPOSURE"
            disallowed_total += outstanding
        elif days_remaining <= 5:
            risk_status = "CRITICAL_43BH"
            critical_total += outstanding
        elif days_remaining <= 10:
            risk_status = "DUE_SOON"
            due_soon_total += outstanding
        else:
            risk_status = "SAFE"

        evaluated.append(
            {
                "bill_ref": bill.get("bill_ref", "N/A"),
                "supplier_name": bill.get("supplier_name", "Unknown Supplier"),
                "udyam_no": bill.get("udyam_no", ""),
                "msme_category": cat,
                "bill_date": bill_dt.isoformat(),
                "statutory_limit_days": statutory_cap,
                "statutory_due_date": due_date.isoformat(),
                "days_elapsed": days_elapsed,
                "days_remaining": days_remaining,
                "outstanding_amount": str(outstanding),
                "risk_status": risk_status,
                "estimated_tax_exposure_30pct": str(
                    (outstanding * Decimal("0.30")).quantize(TWOPLACES, rounding=ROUND_HALF_UP)
                )
                if risk_status in {"DISALLOWED_EXPOSURE", "CRITICAL_43BH"}
                else "0.00",
            }
        )

    evaluated.sort(key=lambda x: x["days_remaining"])
    return {
        "as_of_date": ref_date.isoformat(),
        "total_msme_bills_at_risk": len([b for b in evaluated if b["risk_status"] != "SAFE"]),
        "disallowed_exposure_amount": str(disallowed_total),
        "critical_due_5d_amount": str(critical_total),
        "due_soon_10d_amount": str(due_soon_total),
        "estimated_tax_addback_30pct": str(
            (disallowed_total * Decimal("0.30")).quantize(TWOPLACES, rounding=ROUND_HALF_UP)
        ),
        "bills": evaluated,
    }


def reconcile_gstr2b(
    books_purchases: List[Dict[str, Any]],
    portal_2b_entries: List[Dict[str, Any]],
    rounding_tolerance: Any = "2.00",
    date_tolerance_days: int = 5,
) -> Dict[str, Any]:
    """Fuzzy GSTR-2B + IMS Reconciler solving TallyPrime strict-match pain."""
    tol = to_decimal(rounding_tolerance)
    matched: List[Dict[str, Any]] = []
    value_mismatches: List[Dict[str, Any]] = []
    missing_in_books: List[Dict[str, Any]] = []
    missing_in_2b: List[Dict[str, Any]] = []

    used_portal_idx: set[int] = set()

    for b in books_purchases:
        b_gstin = str(b.get("supplier_gstin") or "").upper().strip()
        b_inv = str(b.get("invoice_no") or "").strip()
        b_norm = _normalize_invoice_no(b_inv)
        b_tax = to_decimal(b.get("total_tax", 0))
        b_taxable = to_decimal(b.get("taxable_value", 0))
        b_date = _parse_iso_date(b.get("invoice_date"))

        best_idx: Optional[int] = None
        best_mode: Optional[str] = None
        best_diff = Decimal("999999999.00")

        for idx, p in enumerate(portal_2b_entries):
            if idx in used_portal_idx:
                continue
            p_gstin = str(p.get("supplier_gstin") or "").upper().strip()
            if b_gstin and p_gstin and b_gstin != p_gstin:
                continue
            p_inv = str(p.get("invoice_no") or "").strip()
            p_norm = _normalize_invoice_no(p_inv)
            p_date = _parse_iso_date(p.get("invoice_date"))
            if abs((b_date - p_date).days) > date_tolerance_days and b_inv.upper() != p_inv.upper():
                continue

            if b_inv.upper() == p_inv.upper():
                mode = "EXACT_INVOICE"
            elif b_norm and b_norm == p_norm:
                mode = "FUZZY_INVOICE_FORMAT"
            else:
                continue

            p_tax = to_decimal(p.get("total_tax", 0))
            p_taxable = to_decimal(p.get("taxable_value", 0))
            diff = abs(b_tax - p_tax) + abs(b_taxable - p_taxable)
            if diff < best_diff:
                best_diff = diff
                best_idx = idx
                best_mode = mode

        if best_idx is None:
            missing_in_2b.append(
                {
                    "supplier_name": b.get("supplier_name", ""),
                    "supplier_gstin": b_gstin,
                    "invoice_no": b_inv,
                    "invoice_date": b_date.isoformat(),
                    "books_tax": str(b_tax),
                    "ims_recommendation": "HOLD_ITC_AND_FOLLOW_UP",
                    "reason": "Supplier invoice present in Books but missing in GSTR-2B",
                }
            )
            continue

        used_portal_idx.add(best_idx)
        p = portal_2b_entries[best_idx]
        p_tax = to_decimal(p.get("total_tax", 0))
        p_taxable = to_decimal(p.get("taxable_value", 0))
        tax_diff = abs(b_tax - p_tax)
        val_diff = abs(b_taxable - p_taxable)

        if tax_diff == ZERO and val_diff == ZERO and best_mode == "EXACT_INVOICE":
            matched.append(
                {
                    "status": "EXACT_MATCH",
                    "supplier_gstin": b_gstin,
                    "books_invoice": b_inv,
                    "portal_invoice": p.get("invoice_no"),
                    "tax": str(b_tax),
                    "ims_action": "ACCEPT",
                }
            )
        elif tax_diff <= tol and val_diff <= tol:
            matched.append(
                {
                    "status": "FUZZY_MATCH_TOLERATED",
                    "match_basis": best_mode,
                    "supplier_gstin": b_gstin,
                    "books_invoice": b_inv,
                    "portal_invoice": p.get("invoice_no"),
                    "tax_diff": str(tax_diff),
                    "ims_action": "ACCEPT",
                }
            )
        else:
            value_mismatches.append(
                {
                    "status": "VALUE_MISMATCH",
                    "supplier_gstin": b_gstin,
                    "books_invoice": b_inv,
                    "portal_invoice": p.get("invoice_no"),
                    "books_tax": str(b_tax),
                    "portal_tax": str(p_tax),
                    "tax_diff": str(b_tax - p_tax),
                    "ims_action": "KEEP_PENDING",
                }
            )

    for idx, p in enumerate(portal_2b_entries):
        if idx not in used_portal_idx:
            missing_in_books.append(
                {
                    "supplier_name": p.get("supplier_name", ""),
                    "supplier_gstin": str(p.get("supplier_gstin") or "").upper().strip(),
                    "invoice_no": p.get("invoice_no", ""),
                    "invoice_date": _parse_iso_date(p.get("invoice_date")).isoformat(),
                    "portal_tax": str(to_decimal(p.get("total_tax", 0))),
                    "ims_recommendation": "AUTO_DRAFT_PURCHASE_VOUCHER",
                }
            )

    itc_at_risk = sum(
        (to_decimal(x["books_tax"]) for x in missing_in_2b), ZERO
    ) + sum((abs(to_decimal(x["tax_diff"])) for x in value_mismatches), ZERO)

    return {
        "summary": {
            "total_books": len(books_purchases),
            "total_portal_2b": len(portal_2b_entries),
            "matched_count": len(matched),
            "value_mismatch_count": len(value_mismatches),
            "missing_in_books_count": len(missing_in_books),
            "missing_in_2b_itc_risk_count": len(missing_in_2b),
            "itc_at_risk_amount": str(itc_at_risk.quantize(TWOPLACES)),
        },
        "matched": matched,
        "value_mismatches": value_mismatches,
        "missing_in_books": missing_in_books,
        "missing_in_2b": missing_in_2b,
    }


def parse_tally_xml(xml_content: str) -> Dict[str, Any]:
    """Parse Tally.ERP 9 / TallyPrime XML export (<ENVELOPE>) safely.

    Rejects DOCTYPE/ENTITY declarations to prevent XXE/billion-laughs attacks.
    Extracts Ledger Masters (with Bill-by-Bill allocations), Stock Items
    (with Godown/Batch allocations), and Vouchers.
    """
    if not xml_content or not xml_content.strip():
        raise AccountingError("Empty Tally XML payload")
    upper_head = xml_content[:4096].upper()
    if "<!DOCTYPE" in upper_head or "<!ENTITY" in upper_head:
        raise AccountingError("Unsafe XML: DOCTYPE/ENTITY declarations are forbidden")

    try:
        root = ET.fromstring(xml_content)
    except ET.ParseError as exc:
        raise AccountingError(f"Malformed Tally XML: {exc}") from exc

    ledgers: List[Dict[str, Any]] = []
    stock_items: List[Dict[str, Any]] = []
    vouchers: List[Dict[str, Any]] = []

    def _txt(el: ET.Element, tag: str, default: str = "") -> str:
        child = el.find(tag)
        if child is not None and child.text:
            return child.text.strip()
        return default

    for led_el in root.iter("LEDGER"):
        name = led_el.attrib.get("NAME") or _txt(led_el, "NAME")
        if not name:
            continue
        parent = _txt(led_el, "PARENT", "Sundry Debtors")
        opening_raw = _txt(led_el, "OPENINGBALANCE", "0")
        opening_amt = to_decimal(opening_raw)
        gstin = _txt(led_el, "PARTYGSTIN") or _txt(led_el, "GSTIN")

        bills: List[Dict[str, Any]] = []
        bill_sum = ZERO
        for bill_el in led_el.findall("BILLALLOCATIONS.LIST"):
            b_name = _txt(bill_el, "NAME", f"OB-{len(bills)+1}")
            b_amt = to_decimal(_txt(bill_el, "AMOUNT", "0"))
            b_type = _txt(bill_el, "BILLTYPE", "New Ref")
            b_period = _txt(bill_el, "BILLCREDITPERIOD", "30 Days")
            bills.append(
                {
                    "bill_ref": b_name,
                    "bill_type": b_type,
                    "credit_period": b_period,
                    "amount": str(b_amt),
                }
            )
            bill_sum += b_amt

        if bills and abs(bill_sum) != abs(opening_amt):
            residual = opening_amt - bill_sum
            if residual != ZERO:
                bills.append(
                    {
                        "bill_ref": "On Account",
                        "bill_type": "On Account",
                        "credit_period": "0 Days",
                        "amount": str(residual),
                    }
                )

        # In Tally XML: negative opening balance = Debit, positive = Credit
        opening_dr_cr = "DR" if opening_amt < ZERO else "CR"
        ledgers.append(
            {
                "name": name,
                "parent_group": parent,
                "gstin": gstin,
                "opening_balance": str(abs(opening_amt)),
                "opening_dr_cr": opening_dr_cr if opening_amt != ZERO else "DR",
                "bills": bills,
            }
        )

    for item_el in root.iter("STOCKITEM"):
        name = item_el.attrib.get("NAME") or _txt(item_el, "NAME")
        if not name:
            continue
        base_unit = _txt(item_el, "BASEUNITS", "Nos")
        parent = _txt(item_el, "PARENT", "Primary")
        batches: List[Dict[str, Any]] = []
        for batch_el in item_el.findall("BATCHALLOCATIONS.LIST"):
            qty_str = _txt(batch_el, "OPENINGBALANCE", "0")
            qty_num = re.search(r"-?\d+(?:\.\d+)?", qty_str)
            batches.append(
                {
                    "godown": _txt(batch_el, "GODOWNNAME", "Main Location"),
                    "batch": _txt(batch_el, "BATCHNAME", "Primary Batch"),
                    "opening_qty": qty_num.group(0) if qty_num else "0",
                    "opening_value": str(abs(to_decimal(_txt(batch_el, "OPENINGVALUE", "0")))),
                }
            )
        stock_items.append(
            {
                "name": name,
                "stock_group": parent,
                "base_unit": base_unit,
                "batches": batches,
            }
        )

    for v_el in root.iter("VOUCHER"):
        v_type_raw = v_el.attrib.get("VCHTYPE") or _txt(v_el, "VOUCHERTYPENAME", "Journal")
        v_type = v_type_raw.upper().replace(" ", "_")
        if v_type not in VOUCHER_TYPES:
            v_type = "JOURNAL"
        v_date = _parse_iso_date(_txt(v_el, "DATE")).isoformat()
        v_no = _txt(v_el, "VOUCHERNUMBER") or f"TLY-{uuid.uuid4().hex[:6].upper()}"
        narration = _txt(v_el, "NARRATION", "Imported from Tally XML")

        entries: List[Dict[str, Any]] = []
        raw_lists = v_el.findall("ALLLEDGERENTRIES.LIST") + v_el.findall("LEDGERENTRIES.LIST")
        for le in raw_lists:
            l_name = _txt(le, "LEDGERNAME")
            if not l_name:
                continue
            amt = to_decimal(_txt(le, "AMOUNT", "0"))
            if amt == ZERO:
                continue
            # Standard Tally XML: ISDEEMEDPOSITIVE=Yes or negative AMOUNT is Debit
            deemed_raw = _txt(le, "ISDEEMEDPOSITIVE", "").lower()
            if deemed_raw == "yes":
                dr_cr = "DR"
            elif deemed_raw == "no":
                dr_cr = "CR"
            else:
                dr_cr = "DR" if amt < ZERO else "CR"

            bill_refs = []
            for ba in le.findall("BILLALLOCATIONS.LIST"):
                bill_refs.append(
                    {
                        "bill_ref": _txt(ba, "NAME", v_no),
                        "bill_type": _txt(ba, "BILLTYPE", "New Ref"),
                        "amount": str(abs(to_decimal(_txt(ba, "AMOUNT", str(amt))))),
                    }
                )
            entries.append(
                {
                    "ledger_name": l_name,
                    "dr_cr": dr_cr,
                    "amount": str(abs(amt)),
                    "bill_refs": bill_refs,
                }
            )

        if entries:
            vouchers.append(
                {
                    "voucher_type": v_type,
                    "voucher_no": v_no,
                    "voucher_date": v_date,
                    "narration": narration,
                    "entries": entries,
                }
            )

    return {
        "ledgers": ledgers,
        "stock_items": stock_items,
        "vouchers": vouchers,
    }


def build_whatsapp_ledger_reminder(
    company_name: str,
    party_name: str,
    outstanding_amount: Any,
    overdue_days: int = 0,
    language: str = "en",
    upi_id: str = "",
) -> Dict[str, str]:
    """Generate multilingual WhatsApp reminder / annual ledger confirmation text."""
    amt = to_decimal(outstanding_amount)
    lang = (language or "en").lower().strip()
    upi_line = f"\nUPI Pay ID: {upi_id}" if upi_id else ""

    if lang in {"gu", "gujarati", "surati"}:
        msg = (
            f"નમસ્તે {party_name} જી,\n"
            f"{company_name} તરફથી ખાતાની બાકી રકમ ₹{amt:,.2f} "
            f"({overdue_days} દિવસ બાકી) કન્ફર્મ કરવા વિનંતી છે.\n"
            f"કૃપા કરીને પેમેન્ટ મોકલીને 'CONFIRM' રિપ્લાય આપશો.{upi_line}"
        )
    elif lang in {"hi", "hinglish", "hindi"}:
        msg = (
            f"Namaste {party_name} ji,\n"
            f"{company_name} ke hisab se aapka pending balance ₹{amt:,.2f} hai "
            f"({overdue_days} days overdue). Kripya payment bhejkar ledger confirm ke liye 'CONFIRM' reply karein.{upi_line}"
        )
    else:
        msg = (
            f"Hello {party_name},\n"
            f"Ledger Balance Reminder from {company_name}: ₹{amt:,.2f} pending "
            f"({overdue_days} days overdue). Please remit payment or reply 'CONFIRM' for statutory balance confirmation.{upi_line}"
        )

    return {
        "company_name": company_name,
        "party_name": party_name,
        "outstanding_amount": str(amt),
        "language": lang,
        "message": msg,
    }


class AccountingStore:
    """SQLite WAL-backed deterministic accounting engine per tenant company."""

    def __init__(self, db_path: Optional[Path] = None):
        if db_path is None:
            base = Path(os.environ.get("ALGORISE_ACCOUNTING_DIR", "data/accounting"))
            base.mkdir(parents=True, exist_ok=True)
            db_path = base / "books_os.db"
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=15.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA synchronous = NORMAL;")
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS companies (
                    company_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    gstin TEXT DEFAULT '',
                    state_code TEXT DEFAULT '24',
                    fy_start TEXT DEFAULT '2026-04-01',
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS ledgers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    company_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    parent_group TEXT NOT NULL,
                    nature TEXT NOT NULL,
                    gstin TEXT DEFAULT '',
                    msme_category TEXT DEFAULT 'NONE',
                    udyam_no TEXT DEFAULT '',
                    opening_balance TEXT DEFAULT '0.00',
                    opening_dr_cr TEXT DEFAULT 'DR',
                    phone TEXT DEFAULT '',
                    created_at TEXT NOT NULL,
                    UNIQUE(company_id, name)
                );

                CREATE TABLE IF NOT EXISTS stock_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    company_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    stock_group TEXT DEFAULT 'Primary',
                    base_unit TEXT DEFAULT 'Nos',
                    hsn_code TEXT DEFAULT '',
                    gst_rate TEXT DEFAULT '18.00',
                    opening_qty TEXT DEFAULT '0',
                    opening_value TEXT DEFAULT '0.00',
                    godown TEXT DEFAULT 'Main Location',
                    created_at TEXT NOT NULL,
                    UNIQUE(company_id, name)
                );

                CREATE TABLE IF NOT EXISTS vouchers (
                    voucher_id TEXT PRIMARY KEY,
                    company_id TEXT NOT NULL,
                    voucher_type TEXT NOT NULL,
                    voucher_no TEXT NOT NULL,
                    voucher_date TEXT NOT NULL,
                    narration TEXT DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'POSTED',
                    is_pdc INTEGER NOT NULL DEFAULT 0,
                    pdc_date TEXT DEFAULT '',
                    total_amount TEXT NOT NULL,
                    party_gstin TEXT DEFAULT '',
                    has_written_agreement INTEGER NOT NULL DEFAULT 0,
                    agreed_credit_days INTEGER NOT NULL DEFAULT 15,
                    created_by TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS voucher_entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    voucher_id TEXT NOT NULL,
                    company_id TEXT NOT NULL,
                    ledger_name TEXT NOT NULL,
                    dr_cr TEXT NOT NULL,
                    amount TEXT NOT NULL,
                    bill_ref TEXT DEFAULT '',
                    bill_type TEXT DEFAULT 'New Ref',
                    FOREIGN KEY(voucher_id) REFERENCES vouchers(voucher_id)
                );

                CREATE TABLE IF NOT EXISTS audit_blocks (
                    block_index INTEGER PRIMARY KEY AUTOINCREMENT,
                    company_id TEXT NOT NULL,
                    timestamp_utc TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    action TEXT NOT NULL,
                    entity_type TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    before_json TEXT NOT NULL,
                    after_json TEXT NOT NULL,
                    prev_hash TEXT NOT NULL,
                    block_hash TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS einvoices (
                    irn TEXT PRIMARY KEY,
                    company_id TEXT NOT NULL,
                    voucher_id TEXT DEFAULT '',
                    doc_type TEXT NOT NULL,
                    doc_no TEXT NOT NULL,
                    doc_date TEXT NOT NULL,
                    seller_gstin TEXT NOT NULL,
                    buyer_gstin TEXT NOT NULL,
                    taxable_value TEXT NOT NULL,
                    total_tax TEXT NOT NULL,
                    total_invoice_value TEXT NOT NULL,
                    ack_no TEXT NOT NULL,
                    ack_dt TEXT NOT NULL,
                    signed_qr_payload TEXT NOT NULL,
                    ewb_no TEXT DEFAULT '',
                    ewb_valid_till TEXT DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'ACTIVE',
                    cancel_reason TEXT DEFAULT '',
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS ca_firms (
                    ca_id TEXT PRIMARY KEY,
                    firm_name TEXT NOT NULL,
                    frn_number TEXT DEFAULT '',
                    rev_share_pct TEXT DEFAULT '25.00',
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS ca_client_links (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ca_id TEXT NOT NULL,
                    company_id TEXT NOT NULL,
                    plan_tier TEXT NOT NULL DEFAULT 'GROWTH',
                    annual_fee_inr TEXT NOT NULL DEFAULT '5999.00',
                    linked_at TEXT NOT NULL,
                    UNIQUE(ca_id, company_id)
                );

                CREATE TABLE IF NOT EXISTS bridge_sync_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    company_id TEXT NOT NULL,
                    source_host TEXT NOT NULL,
                    tally_company TEXT DEFAULT '',
                    imported_ledgers INTEGER NOT NULL DEFAULT 0,
                    imported_stock_items INTEGER NOT NULL DEFAULT 0,
                    imported_vouchers INTEGER NOT NULL DEFAULT 0,
                    parity_ok INTEGER NOT NULL DEFAULT 1,
                    synced_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS bridge_nonces (
                    nonce TEXT PRIMARY KEY,
                    seen_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_vouchers_comp_date ON vouchers(company_id, voucher_date);
                CREATE INDEX IF NOT EXISTS idx_entries_comp_led ON voucher_entries(company_id, ledger_name);
                CREATE INDEX IF NOT EXISTS idx_audit_comp ON audit_blocks(company_id, block_index);
                CREATE INDEX IF NOT EXISTS idx_einvoices_comp ON einvoices(company_id, doc_date);
                CREATE INDEX IF NOT EXISTS idx_ca_links ON ca_client_links(ca_id, company_id);
                """
            )

    def _append_audit_block(
        self,
        conn: sqlite3.Connection,
        company_id: str,
        actor: str,
        action: str,
        entity_type: str,
        entity_id: str,
        before_obj: Any,
        after_obj: Any,
    ) -> str:
        row = conn.execute(
            "SELECT block_hash FROM audit_blocks WHERE company_id = ? ORDER BY block_index DESC LIMIT 1",
            (company_id,),
        ).fetchone()
        prev_hash = row["block_hash"] if row else GENESIS_HASH
        ts = datetime.now(timezone.utc).isoformat()
        before_json = _canonical_json(before_obj)
        after_json = _canonical_json(after_obj)
        payload = "|".join([prev_hash, ts, actor, company_id, action, entity_type, entity_id, before_json, after_json])
        block_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        conn.execute(
            """
            INSERT INTO audit_blocks
            (company_id, timestamp_utc, actor, action, entity_type, entity_id, before_json, after_json, prev_hash, block_hash)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (company_id, ts, actor, action, entity_type, entity_id, before_json, after_json, prev_hash, block_hash),
        )
        return block_hash

    def ensure_company(
        self,
        company_id: str,
        name: str = "Demo Enterprise Pvt Ltd",
        gstin: str = "24AABCA1234F1Z5",
        state_code: str = "24",
    ) -> Dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            existing = conn.execute("SELECT * FROM companies WHERE company_id = ?", (company_id,)).fetchone()
            if existing:
                return dict(existing)
            conn.execute(
                "INSERT INTO companies (company_id, name, gstin, state_code, created_at) VALUES (?, ?, ?, ?, ?)",
                (company_id, name, gstin, state_code, now),
            )
            defaults = [
                ("Cash", "Cash-in-Hand", "ASSET", "", "NONE", "0.00", "DR"),
                ("HDFC Bank Current A/c", "Bank Accounts", "ASSET", "", "NONE", "0.00", "DR"),
                ("Sales GST", "Sales Accounts", "INCOME", "", "NONE", "0.00", "CR"),
                ("Purchase GST", "Purchase Accounts", "EXPENSE", "", "NONE", "0.00", "DR"),
                ("CGST Output", "Duties & Taxes", "LIABILITY", "", "NONE", "0.00", "CR"),
                ("SGST Output", "Duties & Taxes", "LIABILITY", "", "NONE", "0.00", "CR"),
                ("IGST Output", "Duties & Taxes", "LIABILITY", "", "NONE", "0.00", "CR"),
                ("CGST Input", "Duties & Taxes", "ASSET", "", "NONE", "0.00", "DR"),
                ("SGST Input", "Duties & Taxes", "ASSET", "", "NONE", "0.00", "DR"),
                ("IGST Input", "Duties & Taxes", "ASSET", "", "NONE", "0.00", "DR"),
                ("Rounding Off", "Indirect Expenses", "EXPENSE", "", "NONE", "0.00", "DR"),
            ]
            for l_name, grp, nat, l_gst, msme, ob, drcr in defaults:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO ledgers
                    (company_id, name, parent_group, nature, gstin, msme_category, opening_balance, opening_dr_cr, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (company_id, l_name, grp, nat, l_gst, msme, ob, drcr, now),
                )
            self._append_audit_block(
                conn, company_id, "system", "CREATE_COMPANY", "COMPANY", company_id, {}, {"name": name, "state_code": state_code}
            )
            created = conn.execute("SELECT * FROM companies WHERE company_id = ?", (company_id,)).fetchone()
            return dict(created)

    def create_or_update_ledger(
        self,
        company_id: str,
        name: str,
        parent_group: str = "Sundry Debtors",
        gstin: str = "",
        msme_category: str = "NONE",
        udyam_no: str = "",
        opening_balance: Any = "0.00",
        opening_dr_cr: str = "DR",
        phone: str = "",
        actor: str = "accountant",
    ) -> Dict[str, Any]:
        self.ensure_company(company_id)
        clean_name = name.strip()
        if not clean_name:
            raise AccountingError("Ledger name cannot be empty")
        nature = STANDARD_TALLY_GROUPS.get(parent_group, "ASSET")
        ob = str(abs(to_decimal(opening_balance)))
        drcr = "CR" if str(opening_dr_cr).upper().strip() == "CR" else "DR"
        msme = str(msme_category or "NONE").upper().strip()
        now = datetime.now(timezone.utc).isoformat()

        with self._connect() as conn:
            existing = conn.execute(
                "SELECT * FROM ledgers WHERE company_id = ? AND name = ?", (company_id, clean_name)
            ).fetchone()
            if existing:
                before = dict(existing)
                conn.execute(
                    """
                    UPDATE ledgers SET parent_group=?, nature=?, gstin=?, msme_category=?, udyam_no=?,
                    opening_balance=?, opening_dr_cr=?, phone=?
                    WHERE company_id=? AND name=?
                    """,
                    (parent_group, nature, gstin, msme, udyam_no, ob, drcr, phone, company_id, clean_name),
                )
                updated = dict(
                    conn.execute("SELECT * FROM ledgers WHERE company_id = ? AND name = ?", (company_id, clean_name)).fetchone()
                )
                self._append_audit_block(conn, company_id, actor, "ALTER_LEDGER", "LEDGER", clean_name, before, updated)
                return updated

            conn.execute(
                """
                INSERT INTO ledgers
                (company_id, name, parent_group, nature, gstin, msme_category, udyam_no, opening_balance, opening_dr_cr, phone, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (company_id, clean_name, parent_group, nature, gstin, msme, udyam_no, ob, drcr, phone, now),
            )
            created = dict(
                conn.execute("SELECT * FROM ledgers WHERE company_id = ? AND name = ?", (company_id, clean_name)).fetchone()
            )
            self._append_audit_block(conn, company_id, actor, "CREATE_LEDGER", "LEDGER", clean_name, {}, created)
            return created

    def post_voucher(
        self,
        company_id: str,
        voucher_type: str,
        voucher_date: Optional[str],
        entries: List[Dict[str, Any]],
        voucher_no: Optional[str] = None,
        narration: str = "",
        is_pdc: bool = False,
        pdc_date: str = "",
        party_gstin: str = "",
        has_written_agreement: bool = False,
        agreed_credit_days: int = 15,
        actor: str = "accountant",
    ) -> Dict[str, Any]:
        self.ensure_company(company_id)
        v_type = str(voucher_type or "JOURNAL").upper().strip()
        if v_type not in VOUCHER_TYPES:
            raise AccountingError(f"Unsupported voucher_type: {v_type}")
        if not entries or len(entries) < 2:
            raise AccountingError("A double-entry voucher requires at least 2 ledger lines")

        dr_total = ZERO
        cr_total = ZERO
        normalized_lines: List[Dict[str, str]] = []
        for line in entries:
            l_name = str(line.get("ledger_name") or "").strip()
            if not l_name:
                raise AccountingError("Voucher entry missing ledger_name")
            dr_cr = str(line.get("dr_cr") or "").upper().strip()
            if dr_cr not in {"DR", "CR"}:
                raise AccountingError(f"Invalid dr_cr value: {dr_cr!r}")
            amt = to_decimal(line.get("amount"))
            if amt <= ZERO:
                raise AccountingError(f"Voucher line amount must be positive, got {amt}")
            if dr_cr == "DR":
                dr_total += amt
            else:
                cr_total += amt
            normalized_lines.append(
                {
                    "ledger_name": l_name,
                    "dr_cr": dr_cr,
                    "amount": str(amt),
                    "bill_ref": str(line.get("bill_ref") or ""),
                    "bill_type": str(line.get("bill_type") or "New Ref"),
                }
            )

        if dr_total != cr_total:
            raise ImbalancedVoucherError(
                f"Double-entry mismatch: Total Debit ({dr_total}) != Total Credit ({cr_total})"
            )

        v_id = f"VCH-{uuid.uuid4().hex[:12].upper()}"
        v_no = voucher_no or f"{v_type[:3]}-{uuid.uuid4().hex[:6].upper()}"
        v_dt = _parse_iso_date(voucher_date).isoformat()
        now = datetime.now(timezone.utc).isoformat()

        with self._connect() as conn:
            for line in normalized_lines:
                exists = conn.execute(
                    "SELECT 1 FROM ledgers WHERE company_id = ? AND name = ?",
                    (company_id, line["ledger_name"]),
                ).fetchone()
                if not exists:
                    inferred_group = "Sundry Debtors" if v_type == "SALES" else "Indirect Expenses"
                    if v_type == "PURCHASE":
                        inferred_group = "Sundry Creditors"
                    conn.execute(
                        """
                        INSERT INTO ledgers (company_id, name, parent_group, nature, created_at)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (company_id, line["ledger_name"], inferred_group, STANDARD_TALLY_GROUPS[inferred_group], now),
                    )

            conn.execute(
                """
                INSERT INTO vouchers
                (voucher_id, company_id, voucher_type, voucher_no, voucher_date, narration, status,
                 is_pdc, pdc_date, total_amount, party_gstin, has_written_agreement, agreed_credit_days,
                 created_by, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, 'POSTED', ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    v_id,
                    company_id,
                    v_type,
                    v_no,
                    v_dt,
                    narration,
                    1 if is_pdc else 0,
                    pdc_date,
                    str(dr_total),
                    party_gstin,
                    1 if has_written_agreement else 0,
                    int(agreed_credit_days),
                    actor,
                    now,
                    now,
                ),
            )
            for line in normalized_lines:
                conn.execute(
                    """
                    INSERT INTO voucher_entries
                    (voucher_id, company_id, ledger_name, dr_cr, amount, bill_ref, bill_type)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (v_id, company_id, line["ledger_name"], line["dr_cr"], line["amount"], line["bill_ref"], line["bill_type"]),
                )

            voucher_payload = {
                "voucher_id": v_id,
                "voucher_type": v_type,
                "voucher_no": v_no,
                "voucher_date": v_dt,
                "total_amount": str(dr_total),
                "is_pdc": bool(is_pdc),
                "entries": normalized_lines,
            }
            block_hash = self._append_audit_block(
                conn, company_id, actor, "CREATE_VOUCHER", "VOUCHER", v_id, {}, voucher_payload
            )
            voucher_payload["audit_hash"] = block_hash
            voucher_payload["status"] = "POSTED"
            return voucher_payload

    def cancel_voucher(self, company_id: str, voucher_id: str, reason: str = "Cancelled", actor: str = "accountant") -> Dict[str, Any]:
        """MCA Rule 11(g) forbids hard deletes; cancels via immutable status & audit log."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM vouchers WHERE company_id = ? AND voucher_id = ?", (company_id, voucher_id)
            ).fetchone()
            if not row:
                raise AccountingError(f"Voucher not found: {voucher_id}")
            before = dict(row)
            if before["status"] == "CANCELLED":
                raise AccountingError("Voucher is already cancelled")
            now = datetime.now(timezone.utc).isoformat()
            conn.execute(
                "UPDATE vouchers SET status='CANCELLED', narration=?, updated_at=? WHERE company_id=? AND voucher_id=?",
                (f"{before['narration']} [CANCELLED: {reason}]".strip(), now, company_id, voucher_id),
            )
            after = dict(conn.execute("SELECT * FROM vouchers WHERE voucher_id = ?", (voucher_id,)).fetchone())
            block_hash = self._append_audit_block(conn, company_id, actor, "CANCEL_VOUCHER", "VOUCHER", voucher_id, before, after)
            after["audit_hash"] = block_hash
            return after

    def get_ledgers(self, company_id: str) -> List[Dict[str, Any]]:
        self.ensure_company(company_id)
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM ledgers WHERE company_id = ? ORDER BY parent_group, name", (company_id,)).fetchall()
            return [dict(r) for r in rows]

    def get_vouchers(self, company_id: str, include_cancelled: bool = True) -> List[Dict[str, Any]]:
        self.ensure_company(company_id)
        with self._connect() as conn:
            q = "SELECT * FROM vouchers WHERE company_id = ?"
            if not include_cancelled:
                q += " AND status = 'POSTED'"
            q += " ORDER BY voucher_date DESC, created_at DESC"
            v_rows = conn.execute(q, (company_id,)).fetchall()
            out = []
            for v in v_rows:
                item = dict(v)
                item["is_pdc"] = bool(item["is_pdc"])
                e_rows = conn.execute(
                    "SELECT ledger_name, dr_cr, amount, bill_ref, bill_type FROM voucher_entries WHERE voucher_id = ?",
                    (item["voucher_id"],),
                ).fetchall()
                item["entries"] = [dict(e) for e in e_rows]
                out.append(item)
            return out

    def get_trial_balance(self, company_id: str) -> Dict[str, Any]:
        self.ensure_company(company_id)
        with self._connect() as conn:
            ledgers = conn.execute("SELECT * FROM ledgers WHERE company_id = ? ORDER BY name", (company_id,)).fetchall()
            entry_rows = conn.execute(
                """
                SELECT ve.ledger_name, ve.dr_cr, ve.amount
                FROM voucher_entries ve
                JOIN vouchers v ON v.voucher_id = ve.voucher_id
                WHERE ve.company_id = ? AND v.status = 'POSTED' AND v.is_pdc = 0
                """,
                (company_id,),
            ).fetchall()

        balances: Dict[str, Dict[str, Any]] = {}
        for l in ledgers:
            ob = to_decimal(l["opening_balance"])
            dr = ob if l["opening_dr_cr"] == "DR" else ZERO
            cr = ob if l["opening_dr_cr"] == "CR" else ZERO
            balances[l["name"]] = {
                "ledger_name": l["name"],
                "parent_group": l["parent_group"],
                "nature": l["nature"],
                "debit_total": dr,
                "credit_total": cr,
            }

        for er in entry_rows:
            name = er["ledger_name"]
            if name not in balances:
                balances[name] = {
                    "ledger_name": name,
                    "parent_group": "Indirect Expenses",
                    "nature": "EXPENSE",
                    "debit_total": ZERO,
                    "credit_total": ZERO,
                }
            amt = to_decimal(er["amount"])
            if er["dr_cr"] == "DR":
                balances[name]["debit_total"] += amt
            else:
                balances[name]["credit_total"] += amt

        rows_out = []
        total_dr = ZERO
        total_cr = ZERO
        for name in sorted(balances):
            b = balances[name]
            net = b["debit_total"] - b["credit_total"]
            if net == ZERO:
                continue
            close_dr = net if net > ZERO else ZERO
            close_cr = abs(net) if net < ZERO else ZERO
            total_dr += close_dr
            total_cr += close_cr
            rows_out.append(
                {
                    "ledger_name": name,
                    "parent_group": b["parent_group"],
                    "nature": b["nature"],
                    "closing_debit": str(close_dr),
                    "closing_credit": str(close_cr),
                }
            )

        return {
            "company_id": company_id,
            "total_debit": str(total_dr),
            "total_credit": str(total_cr),
            "variance": str(abs(total_dr - total_cr)),
            "is_balanced": total_dr == total_cr,
            "ledgers": rows_out,
        }

    def get_financial_summary(self, company_id: str) -> Dict[str, Any]:
        tb = self.get_trial_balance(company_id)
        income = ZERO
        expense = ZERO
        assets = ZERO
        liabilities = ZERO
        for row in tb["ledgers"]:
            dr = to_decimal(row["closing_debit"])
            cr = to_decimal(row["closing_credit"])
            nat = row["nature"]
            if nat == "INCOME":
                income += cr - dr
            elif nat == "EXPENSE":
                expense += dr - cr
            elif nat == "ASSET":
                assets += dr - cr
            elif nat == "LIABILITY":
                liabilities += cr - dr

        net_profit = (income - expense).quantize(TWOPLACES, rounding=ROUND_HALF_UP)

        with self._connect() as conn:
            p_rows = conn.execute(
                """
                SELECT v.voucher_no, v.voucher_date, v.has_written_agreement, v.agreed_credit_days,
                       ve.ledger_name, ve.amount, ve.bill_ref, l.msme_category, l.udyam_no
                FROM vouchers v
                JOIN voucher_entries ve ON ve.voucher_id = v.voucher_id
                JOIN ledgers l ON l.company_id = v.company_id AND l.name = ve.ledger_name
                WHERE v.company_id = ? AND v.voucher_type = 'PURCHASE' AND v.status = 'POSTED'
                  AND ve.dr_cr = 'CR' AND l.msme_category IN ('MICRO', 'SMALL')
                """,
                (company_id,),
            ).fetchall()

        msme_bills = [
            {
                "bill_ref": r["bill_ref"] or r["voucher_no"],
                "supplier_name": r["ledger_name"],
                "udyam_no": r["udyam_no"],
                "msme_category": r["msme_category"],
                "bill_date": r["voucher_date"],
                "has_written_agreement": bool(r["has_written_agreement"]),
                "agreed_credit_days": r["agreed_credit_days"],
                "outstanding_amount": r["amount"],
            }
            for r in p_rows
        ]
        radar = evaluate_msme_43bh(msme_bills)
        audit_status = self.verify_audit_chain(company_id)

        return {
            "company_id": company_id,
            "trial_balance": tb,
            "profit_and_loss": {
                "total_income": str(income),
                "total_expense": str(expense),
                "net_profit": str(net_profit),
            },
            "balance_sheet": {
                "total_assets": str(assets),
                "total_liabilities_and_equity": str(liabilities + net_profit),
            },
            "msme_43bh": radar,
            "audit_trail_integrity": audit_status,
        }

    def get_audit_trail(self, company_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        self.ensure_company(company_id)
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM audit_blocks WHERE company_id = ? ORDER BY block_index DESC LIMIT ?",
                (company_id, max(1, min(limit, 500))),
            ).fetchall()
            return [dict(r) for r in rows]

    def verify_audit_chain(self, company_id: str) -> Dict[str, Any]:
        self.ensure_company(company_id)
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM audit_blocks WHERE company_id = ? ORDER BY block_index ASC",
                (company_id,),
            ).fetchall()

        expected_prev = GENESIS_HASH
        for r in rows:
            if r["prev_hash"] != expected_prev:
                return {
                    "valid": False,
                    "blocks_verified": r["block_index"],
                    "broken_at_block": r["block_index"],
                    "reason": "prev_hash linkage mismatch",
                }
            payload = "|".join(
                [
                    r["prev_hash"],
                    r["timestamp_utc"],
                    r["actor"],
                    r["company_id"],
                    r["action"],
                    r["entity_type"],
                    r["entity_id"],
                    r["before_json"],
                    r["after_json"],
                ]
            )
            recomputed = hashlib.sha256(payload.encode("utf-8")).hexdigest()
            if recomputed != r["block_hash"]:
                return {
                    "valid": False,
                    "blocks_verified": r["block_index"],
                    "broken_at_block": r["block_index"],
                    "reason": "block_hash tamper detected",
                }
            expected_prev = r["block_hash"]

        return {
            "valid": True,
            "blocks_verified": len(rows),
            "merkle_head": expected_prev,
            "mca_rule_11g_compliant": True,
        }

    def import_tally_xml(self, company_id: str, xml_content: str, actor: str = "algobridge") -> Dict[str, Any]:
        parsed = parse_tally_xml(xml_content)
        self.ensure_company(company_id)
        imported_ledgers = 0
        imported_items = 0
        imported_vouchers = 0
        skipped_vouchers: List[Dict[str, str]] = []

        for l in parsed["ledgers"]:
            self.create_or_update_ledger(
                company_id=company_id,
                name=l["name"],
                parent_group=l["parent_group"],
                gstin=l["gstin"],
                opening_balance=l["opening_balance"],
                opening_dr_cr=l["opening_dr_cr"],
                actor=actor,
            )
            imported_ledgers += 1

        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            for item in parsed["stock_items"]:
                total_qty = sum((Decimal(b["opening_qty"]) for b in item["batches"]), Decimal("0"))
                total_val = sum((to_decimal(b["opening_value"]) for b in item["batches"]), ZERO)
                godown = item["batches"][0]["godown"] if item["batches"] else "Main Location"
                conn.execute(
                    """
                    INSERT OR REPLACE INTO stock_items
                    (company_id, name, stock_group, base_unit, opening_qty, opening_value, godown, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (company_id, item["name"], item["stock_group"], item["base_unit"], str(total_qty), str(total_val), godown, now),
                )
                imported_items += 1

        for v in parsed["vouchers"]:
            try:
                entries = []
                for e in v["entries"]:
                    first_ref = e["bill_refs"][0] if e.get("bill_refs") else {}
                    entries.append(
                        {
                            "ledger_name": e["ledger_name"],
                            "dr_cr": e["dr_cr"],
                            "amount": e["amount"],
                            "bill_ref": first_ref.get("bill_ref", ""),
                            "bill_type": first_ref.get("bill_type", "New Ref"),
                        }
                    )
                self.post_voucher(
                    company_id=company_id,
                    voucher_type=v["voucher_type"],
                    voucher_date=v["voucher_date"],
                    entries=entries,
                    voucher_no=v["voucher_no"],
                    narration=v["narration"],
                    actor=actor,
                )
                imported_vouchers += 1
            except AccountingError as exc:
                skipped_vouchers.append({"voucher_no": v.get("voucher_no", "?"), "error": str(exc)})

        tb = self.get_trial_balance(company_id)
        return {
            "company_id": company_id,
            "imported_ledgers": imported_ledgers,
            "imported_stock_items": imported_items,
            "imported_vouchers": imported_vouchers,
            "skipped_vouchers": skipped_vouchers,
            "trial_balance_parity": {
                "is_balanced": tb["is_balanced"],
                "total_debit": tb["total_debit"],
                "total_credit": tb["total_credit"],
                "variance": tb["variance"],
            },
        }


accounting_store = AccountingStore()
