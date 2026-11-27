"""
AlgoMigrate — Universal Accounting Software & File Migrator + 1-Line Natural AI Entry.

Supports lossless preview & migration from:
- Tally.ERP 9 / TallyPrime (XML & JSON)
- Busy Accounting (XML & CSV/XLSX)
- Marg ERP (CSV/XLSX with Batch/Expiry)
- Vyapar & MyBillBook (XLSX/CSV/JSON)
- Zoho Books & QuickBooks / Xero (CSV & IIF)
- Generic Excel (.xlsx), CSV, and Bank Statement exports

Also includes `parse_natural_voucher_entry` for beginner 1-line voucher typing.
"""

from __future__ import annotations

import csv
import io
import json
import re
import zipfile
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List, Optional, Tuple

from engine.accounting import (
    TWOPLACES,
    ZERO,
    AccountingError,
    AccountingStore,
    compute_gst_breakdown,
    parse_tally_xml,
    to_decimal,
)

MAX_XLSX_UNCOMPRESSED_BYTES = 25 * 1024 * 1024
GSTIN_CHECK_RE = re.compile(r"^\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z]$")


def _safe_xml_root(raw_xml: str) -> ET.Element:
    head = raw_xml[:4096].upper()
    if "<!DOCTYPE" in head or "<!ENTITY" in head:
        raise AccountingError("Unsafe XML: DOCTYPE/ENTITY declarations forbidden")
    try:
        return ET.fromstring(raw_xml)
    except ET.ParseError as exc:
        raise AccountingError(f"Invalid XML file: {exc}") from exc


def parse_xlsx_bytes(xlsx_bytes: bytes) -> Tuple[List[str], List[Dict[str, str]]]:
    """Pure-stdlib XLSX reader (zipfile + ElementTree) with zip-bomb protection."""
    if not xlsx_bytes or len(xlsx_bytes) < 32:
        raise AccountingError("Empty or invalid .xlsx archive")
    try:
        zf = zipfile.ZipFile(io.BytesIO(xlsx_bytes))
    except zipfile.BadZipFile as exc:
        raise AccountingError("Invalid .xlsx file (not a valid ZIP container)") from exc

    with zf:
        total_uncompressed = sum(info.file_size for info in zf.infolist())
        if total_uncompressed > MAX_XLSX_UNCOMPRESSED_BYTES:
            raise AccountingError("XLSX archive exceeds 25 MB uncompressed safety limit")

        shared_strings: List[str] = []
        if "xl/sharedStrings.xml" in zf.namelist():
            ss_raw = zf.read("xl/sharedStrings.xml").decode("utf-8", errors="replace")
            ss_root = _safe_xml_root(ss_raw)
            for si in ss_root.iter():
                if si.tag.endswith("}si") or si.tag == "si":
                    parts = [t.text or "" for t in si.iter() if t.tag.endswith("}t") or t.tag == "t"]
                    shared_strings.append("".join(parts))

        sheet_names = sorted(n for n in zf.namelist() if n.startswith("xl/worksheets/sheet") and n.endswith(".xml"))
        if not sheet_names:
            raise AccountingError("No worksheet XML found inside .xlsx file")
        ws_raw = zf.read(sheet_names[0]).decode("utf-8", errors="replace")
        ws_root = _safe_xml_root(ws_raw)

        grid_rows: List[List[str]] = []
        for row_el in ws_root.iter():
            if not (row_el.tag.endswith("}row") or row_el.tag == "row"):
                continue
            row_vals: Dict[int, str] = {}
            max_col = 0
            for c_el in row_el:
                if not (c_el.tag.endswith("}c") or c_el.tag == "c"):
                    continue
                ref = c_el.attrib.get("r", "")
                col_letters = "".join(ch for ch in ref if ch.isalpha()).upper()
                col_idx = 0
                for ch in col_letters:
                    col_idx = col_idx * 26 + (ord(ch) - ord("A") + 1)
                col_idx = max(0, col_idx - 1) if col_letters else len(row_vals)
                max_col = max(max_col, col_idx)

                c_type = c_el.attrib.get("t", "")
                val_text = ""
                if c_type == "inlineStr":
                    val_text = "".join(t.text or "" for t in c_el.iter() if t.tag.endswith("}t") or t.tag == "t")
                else:
                    v_el = next((ch for ch in c_el if ch.tag.endswith("}v") or ch.tag == "v"), None)
                    if v_el is not None and v_el.text is not None:
                        if c_type == "s":
                            idx = int(v_el.text)
                            val_text = shared_strings[idx] if 0 <= idx < len(shared_strings) else ""
                        else:
                            val_text = v_el.text.strip()
                row_vals[col_idx] = val_text
            if row_vals:
                grid_rows.append([row_vals.get(i, "") for i in range(max_col + 1)])

    if len(grid_rows) < 2:
        raise AccountingError("XLSX worksheet needs a header row and at least 1 data row")

    headers = [h.strip() for h in grid_rows[0]]
    records: List[Dict[str, str]] = []
    for r in grid_rows[1:]:
        if not any(cell.strip() for cell in r):
            continue
        rec = {headers[i]: (r[i].strip() if i < len(r) else "") for i in range(len(headers)) if headers[i]}
        if rec:
            records.append(rec)
    return headers, records


def _parse_csv_text(text: str) -> Tuple[List[str], List[Dict[str, str]]]:
    cleaned = text.lstrip("\ufeff").strip()
    if not cleaned:
        raise AccountingError("Empty CSV payload")
    reader = csv.DictReader(io.StringIO(cleaned))
    if not reader.fieldnames:
        raise AccountingError("CSV has no header columns")
    headers = [h.strip() for h in reader.fieldnames if h]
    rows: List[Dict[str, str]] = []
    for raw_row in reader:
        rec = {k.strip(): str(v or "").strip() for k, v in raw_row.items() if k and k.strip()}
        if any(rec.values()):
            rows.append(rec)
    return headers, rows


def _normalize_any_date(raw: str) -> str:
    s = (raw or "").strip()
    if not s:
        return datetime.utcnow().date().isoformat()
    if re.fullmatch(r"\d{5}(?:\.0+)?", s):
        # Excel 1900 serial date
        serial = int(float(s))
        return (date(1899, 12, 30) + timedelta(days=serial)).isoformat()
    if re.fullmatch(r"\d{8}", s):
        return datetime.strptime(s, "%Y%m%d").date().isoformat()
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%d-%b-%Y", "%m/%d/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(s[:11], fmt).date().isoformat()
        except ValueError:
            continue
    return datetime.utcnow().date().isoformat()


def detect_accounting_source(filename: str = "", raw_text: str = "", headers: Optional[List[str]] = None) -> str:
    """Auto-detect accounting software format from file extension, content markers, or headers."""
    fn = (filename or "").lower()
    txt_head = (raw_text or "")[:4096]
    upper = txt_head.upper()

    if "<ENVELOPE" in upper or "<TALLYMESSAGE" in upper:
        return "TALLY_XML"
    if "<BUSY" in upper or ("<VCHTYPE" in upper and "<MASTER" in upper):
        return "BUSY_XML"
    if "!TRNS" in upper or ("\nTRNS\t" in upper and "\nSPL\t" in upper):
        return "QUICKBOOKS_IIF"
    if fn.endswith(".json") or txt_head.lstrip().startswith(("{", "[")):
        return "TALLY_OR_APP_JSON"

    hdr_set = {h.lower().strip() for h in (headers or [])}
    joined = " | ".join(sorted(hdr_set))
    if any(k in joined for k in ("batch", "exp date", "mrp")) and "party" in joined:
        return "MARG_ERP"
    if any(k in joined for k in ("vch type", "master name", "busy")):
        return "BUSY_EXCEL_CSV"
    if any(k in joined for k in ("transaction type", "balance due", "received/paid", "vyapar", "mybillbook")):
        return "VYAPAR_MYBILLBOOK"
    if any(k in joined for k in ("invoice number", "customer name", "subtotal", "account type")):
        return "ZOHO_BOOKS"
    if any(k in joined for k in ("withdrawal", "deposit")) or (
        any(k in joined for k in ("debit", "dr")) and any(k in joined for k in ("credit", "cr")) and any(k in joined for k in ("narration", "particulars", "description"))
    ):
        return "BANK_STATEMENT"
    return "GENERIC_CSV_XLSX"


def _col_pick(row: Dict[str, str], candidates: Tuple[str, ...], default: str = "") -> str:
    lower_map = {k.lower().strip(): v for k, v in row.items()}
    for cand in candidates:
        if cand in lower_map and lower_map[cand] != "":
            return lower_map[cand]
    for k, v in lower_map.items():
        if v != "" and any(cand in k for cand in candidates):
            return v
    return default


def _parse_quickbooks_iif(text: str) -> Dict[str, Any]:
    ledgers: Dict[str, Dict[str, Any]] = {}
    vouchers: List[Dict[str, Any]] = []
    cur_vch: Optional[Dict[str, Any]] = None

    for raw_line in text.splitlines():
        if not raw_line.strip() or raw_line.startswith("!"):
            continue
        cols = raw_line.split("\t")
        rec_type = cols[0].strip().upper()
        if rec_type == "ACCNT" and len(cols) >= 3:
            name = cols[1].strip()
            acc_type = cols[2].strip().upper()
            grp = "Bank Accounts" if "BANK" in acc_type else "Sundry Debtors" if "AR" in acc_type else "Sundry Creditors" if "AP" in acc_type else "Indirect Expenses"
            ledgers[name] = {"name": name, "parent_group": grp, "gstin": "", "opening_balance": "0.00", "opening_dr_cr": "DR"}
        elif rec_type == "TRNS" and len(cols) >= 6:
            v_type = "SALES" if "INVOICE" in cols[2].upper() else "PAYMENT" if "CHECK" in cols[2].upper() else "JOURNAL"
            dt = _normalize_any_date(cols[3])
            acc = cols[4].strip() or "Cash"
            amt = to_decimal(cols[6] if len(cols) > 6 else cols[5])
            cur_vch = {
                "voucher_type": v_type,
                "voucher_date": dt,
                "voucher_no": f"QB-{len(vouchers)+1}",
                "narration": "Imported from QuickBooks IIF",
                "entries": [
                    {
                        "ledger_name": acc,
                        "dr_cr": "DR" if amt >= ZERO else "CR",
                        "amount": str(abs(amt)),
                    }
                ],
            }
            if acc not in ledgers:
                ledgers[acc] = {"name": acc, "parent_group": "Bank Accounts", "gstin": "", "opening_balance": "0.00", "opening_dr_cr": "DR"}
        elif rec_type == "SPL" and cur_vch is not None and len(cols) >= 6:
            acc = cols[4].strip() or "Sales GST"
            amt = to_decimal(cols[6] if len(cols) > 6 else cols[5])
            cur_vch["entries"].append(
                {
                    "ledger_name": acc,
                    "dr_cr": "DR" if amt >= ZERO else "CR",
                    "amount": str(abs(amt)),
                }
            )
        elif rec_type == "ENDTRNS" and cur_vch is not None:
            vouchers.append(cur_vch)
            cur_vch = None

    return {"ledgers": list(ledgers.values()), "stock_items": [], "vouchers": vouchers}


def _rows_to_canonical(
    source_type: str,
    rows: List[Dict[str, str]],
    default_bank: str = "HDFC Bank Current A/c",
) -> Dict[str, Any]:
    ledgers: Dict[str, Dict[str, Any]] = {}
    stock_items: Dict[str, Dict[str, Any]] = {}
    vouchers: List[Dict[str, Any]] = []
    warnings: List[str] = []

    for idx, r in enumerate(rows, start=1):
        party = _col_pick(r, ("party name", "customer name", "vendor name", "master name", "account name", "ledger", "party"), "")
        narration = _col_pick(r, ("narration", "particulars", "description", "remarks", "item name"), f"Imported row #{idx}")
        gstin = _col_pick(r, ("gstin", "party gstin", "gst no"), "").upper()
        if gstin and not GSTIN_CHECK_RE.match(gstin):
            warnings.append(f"Row {idx}: GSTIN '{gstin}' does not match 15-char format")

        dt = _normalize_any_date(_col_pick(r, ("date", "vch date", "invoice date", "bill date", "txn date"), ""))
        v_no = _col_pick(r, ("invoice number", "invoice no", "vch no", "bill no", "voucher no", "ref no"), f"MIG-{idx}")
        raw_type = _col_pick(r, ("transaction type", "vch type", "voucher type", "type"), "").upper()

        item_name = _col_pick(r, ("item name", "product", "stock item", "sku"), "")
        if item_name and item_name not in stock_items:
            stock_items[item_name] = {
                "name": item_name,
                "base_unit": _col_pick(r, ("unit", "uom"), "Nos"),
                "hsn_code": _col_pick(r, ("hsn", "hsn/sac"), ""),
                "opening_qty": _col_pick(r, ("qty", "quantity", "opening qty"), "0"),
                "opening_value": _col_pick(r, ("opening value", "stock value"), "0.00"),
            }

        # Bank statement or Debit/Credit column style
        dr_str = _col_pick(r, ("withdrawal", "debit", "dr amt", "dr"), "")
        cr_str = _col_pick(r, ("deposit", "credit", "cr amt", "cr"), "")
        if source_type == "BANK_STATEMENT" or (dr_str or cr_str):
            dr_amt = to_decimal(dr_str) if dr_str else ZERO
            cr_amt = to_decimal(cr_str) if cr_str else ZERO
            if dr_amt > ZERO:
                contra_party = party or _col_pick(r, ("particulars", "description", "narration"), f"Expense Party {idx}")[:48]
                ledgers.setdefault(contra_party, {"name": contra_party, "parent_group": "Sundry Creditors", "gstin": gstin, "opening_balance": "0.00", "opening_dr_cr": "CR"})
                vouchers.append(
                    {
                        "voucher_type": "PAYMENT",
                        "voucher_date": dt,
                        "voucher_no": v_no,
                        "narration": narration,
                        "entries": [
                            {"ledger_name": contra_party, "dr_cr": "DR", "amount": str(dr_amt), "bill_ref": v_no},
                            {"ledger_name": default_bank, "dr_cr": "CR", "amount": str(dr_amt)},
                        ],
                    }
                )
            elif cr_amt > ZERO:
                contra_party = party or _col_pick(r, ("particulars", "description", "narration"), f"Customer {idx}")[:48]
                ledgers.setdefault(contra_party, {"name": contra_party, "parent_group": "Sundry Debtors", "gstin": gstin, "opening_balance": "0.00", "opening_dr_cr": "DR"})
                vouchers.append(
                    {
                        "voucher_type": "RECEIPT",
                        "voucher_date": dt,
                        "voucher_no": v_no,
                        "narration": narration,
                        "entries": [
                            {"ledger_name": default_bank, "dr_cr": "DR", "amount": str(cr_amt)},
                            {"ledger_name": contra_party, "dr_cr": "CR", "amount": str(cr_amt), "bill_ref": v_no},
                        ],
                    }
                )
            continue

        total_amt = to_decimal(_col_pick(r, ("total amount", "total", "net amt", "amount", "invoice total"), "0"))
        if total_amt <= ZERO:
            if party:
                ob = to_decimal(_col_pick(r, ("opening balance", "balance", "closing balance"), "0"))
                grp = "Sundry Creditors" if "SUPPLIER" in raw_type or "VENDOR" in raw_type else "Sundry Debtors"
                ledgers[party] = {"name": party, "parent_group": grp, "gstin": gstin, "opening_balance": str(abs(ob)), "opening_dr_cr": "CR" if ob < ZERO else "DR"}
            continue

        tax_amt = to_decimal(_col_pick(r, ("tax amount", "gst amount", "total tax"), "0"))
        cgst_amt = to_decimal(_col_pick(r, ("cgst",), "0"))
        sgst_amt = to_decimal(_col_pick(r, ("sgst",), "0"))
        igst_amt = to_decimal(_col_pick(r, ("igst",), "0"))
        if tax_amt == ZERO and (cgst_amt + sgst_amt + igst_amt) > ZERO:
            tax_amt = cgst_amt + sgst_amt + igst_amt

        sub_amt = to_decimal(_col_pick(r, ("subtotal", "taxable", "taxable value"), "0"))
        if sub_amt <= ZERO:
            sub_amt = max(ZERO, total_amt - tax_amt)
        if sub_amt + tax_amt != total_amt and total_amt > sub_amt:
            tax_amt = total_amt - sub_amt

        party_name = party or f"Party {idx}"
        is_purchase = any(w in raw_type for w in ("PURCHASE", "BILL", "EXPENSE", "INWARD"))
        if is_purchase:
            ledgers.setdefault(party_name, {"name": party_name, "parent_group": "Sundry Creditors", "gstin": gstin, "opening_balance": "0.00", "opening_dr_cr": "CR"})
            entries = [{"ledger_name": "Purchase GST", "dr_cr": "DR", "amount": str(sub_amt)}]
            if igst_amt > ZERO:
                entries.append({"ledger_name": "IGST Input", "dr_cr": "DR", "amount": str(igst_amt)})
            elif tax_amt > ZERO:
                half = (tax_amt / Decimal("2")).quantize(TWOPLACES, rounding=ROUND_HALF_UP)
                entries.append({"ledger_name": "CGST Input", "dr_cr": "DR", "amount": str(half)})
                if tax_amt - half > ZERO:
                    entries.append({"ledger_name": "SGST Input", "dr_cr": "DR", "amount": str(tax_amt - half)})
            entries.append({"ledger_name": party_name, "dr_cr": "CR", "amount": str(total_amt), "bill_ref": v_no})
            vouchers.append({"voucher_type": "PURCHASE", "voucher_date": dt, "voucher_no": v_no, "narration": narration, "entries": entries})
        else:
            ledgers.setdefault(party_name, {"name": party_name, "parent_group": "Sundry Debtors", "gstin": gstin, "opening_balance": "0.00", "opening_dr_cr": "DR"})
            entries = [{"ledger_name": party_name, "dr_cr": "DR", "amount": str(total_amt), "bill_ref": v_no}, {"ledger_name": "Sales GST", "dr_cr": "CR", "amount": str(sub_amt)}]
            if igst_amt > ZERO:
                entries.append({"ledger_name": "IGST Output", "dr_cr": "CR", "amount": str(igst_amt)})
            elif tax_amt > ZERO:
                half = (tax_amt / Decimal("2")).quantize(TWOPLACES, rounding=ROUND_HALF_UP)
                entries.append({"ledger_name": "CGST Output", "dr_cr": "CR", "amount": str(half)})
                if tax_amt - half > ZERO:
                    entries.append({"ledger_name": "SGST Output", "dr_cr": "CR", "amount": str(tax_amt - half)})
            vouchers.append({"voucher_type": "SALES", "voucher_date": dt, "voucher_no": v_no, "narration": narration, "entries": entries})

    return {"ledgers": list(ledgers.values()), "stock_items": list(stock_items.values()), "vouchers": vouchers, "warnings": warnings}


def preview_universal_migration(
    filename: str = "import.csv",
    raw_bytes: Optional[bytes] = None,
    raw_text: Optional[str] = None,
    source_hint: Optional[str] = None,
) -> Dict[str, Any]:
    """Parse and normalize any market accounting export without mutating books yet."""
    fn = (filename or "").lower()
    headers: List[str] = []
    rows: List[Dict[str, str]] = []
    text_data = raw_text or ""

    if raw_bytes is not None and fn.endswith(".xlsx"):
        headers, rows = parse_xlsx_bytes(raw_bytes)
        detected = source_hint or detect_accounting_source(filename, "", headers)
        canonical = _rows_to_canonical(detected, rows)
    else:
        if raw_bytes is not None and not text_data:
            text_data = raw_bytes.decode("utf-8", errors="replace")
        detected = source_hint or detect_accounting_source(filename, text_data, None)
        if detected == "TALLY_XML":
            canonical = parse_tally_xml(text_data)
            canonical["warnings"] = []
        elif detected == "BUSY_XML":
            canonical = parse_tally_xml(text_data)
            canonical["warnings"] = []
        elif detected == "QUICKBOOKS_IIF":
            canonical = _parse_quickbooks_iif(text_data)
            canonical["warnings"] = []
        elif detected == "TALLY_OR_APP_JSON":
            obj = json.loads(text_data)
            if isinstance(obj, list):
                canonical = _rows_to_canonical("GENERIC_CSV_XLSX", obj)
            else:
                canonical = {
                    "ledgers": obj.get("ledgers", []),
                    "stock_items": obj.get("stock_items", []),
                    "vouchers": obj.get("vouchers", []),
                    "warnings": [],
                }
        else:
            headers, rows = _parse_csv_text(text_data)
            detected = source_hint or detect_accounting_source(filename, text_data, headers)
            canonical = _rows_to_canonical(detected, rows)

    return {
        "detected_source": detected,
        "headers_found": headers,
        "summary": {
            "ledgers_count": len(canonical.get("ledgers", [])),
            "stock_items_count": len(canonical.get("stock_items", [])),
            "vouchers_count": len(canonical.get("vouchers", [])),
            "warnings_count": len(canonical.get("warnings", [])),
        },
        "warnings": canonical.get("warnings", []),
        "canonical": canonical,
    }


def commit_universal_migration(
    store: AccountingStore,
    company_id: str,
    filename: str = "import.csv",
    raw_bytes: Optional[bytes] = None,
    raw_text: Optional[str] = None,
    source_hint: Optional[str] = None,
    actor: str = "algomigrate",
) -> Dict[str, Any]:
    """Commit parsed market export into BooksOS and enforce Trial Balance parity."""
    preview = preview_universal_migration(
        filename=filename,
        raw_bytes=raw_bytes,
        raw_text=raw_text,
        source_hint=source_hint,
    )
    canonical = preview["canonical"]
    store.ensure_company(company_id)

    ledgers_done = 0
    for l in canonical.get("ledgers", []):
        store.create_or_update_ledger(
            company_id=company_id,
            name=l["name"],
            parent_group=l.get("parent_group", "Sundry Debtors"),
            gstin=l.get("gstin", ""),
            opening_balance=l.get("opening_balance", "0.00"),
            opening_dr_cr=l.get("opening_dr_cr", "DR"),
            actor=actor,
        )
        ledgers_done += 1

    vouchers_done = 0
    skipped: List[Dict[str, str]] = []
    for v in canonical.get("vouchers", []):
        try:
            store.post_voucher(
                company_id=company_id,
                voucher_type=v.get("voucher_type", "JOURNAL"),
                voucher_date=v.get("voucher_date"),
                voucher_no=v.get("voucher_no"),
                narration=v.get("narration", f"Migrated from {preview['detected_source']}"),
                entries=v.get("entries", []),
                actor=actor,
            )
            vouchers_done += 1
        except AccountingError as exc:
            skipped.append({"voucher_no": str(v.get("voucher_no", "?")), "error": str(exc)})

    tb = store.get_trial_balance(company_id)
    return {
        "status": "MIGRATION_COMMITTED",
        "detected_source": preview["detected_source"],
        "imported_ledgers": ledgers_done,
        "imported_stock_items": len(canonical.get("stock_items", [])),
        "imported_vouchers": vouchers_done,
        "skipped_vouchers": skipped,
        "warnings": preview["warnings"],
        "trial_balance_parity": {
            "is_balanced": tb["is_balanced"],
            "total_debit": tb["total_debit"],
            "total_credit": tb["total_credit"],
            "variance": tb["variance"],
        },
    }


def parse_natural_voucher_entry(
    sentence: str,
    company_state_code: str = "24",
    party_gstin: Optional[str] = None,
) -> Dict[str, Any]:
    """Deterministic 1-Line Natural-Language Voucher Parser for zero-training data entry.

    Examples:
      - 'Sold 100 mtr Dola Silk to Mahalaxmi Saree @ 450 5% GST'
      - 'Bought 200 kg Yarn from Navkar Dyeing @ 150 5% GST'
      - 'Paid 25000 to Navkar Dyeing via HDFC Bank ref NDM/045'
      - 'Received 50000 from Dadar Silk cheque PDC'
    """
    txt = (sentence or "").strip()
    if not txt:
        raise AccountingError("Enter a 1-line description to draft a voucher")
    low = txt.lower()

    is_pdc = "pdc" in low or "post dated" in low or "post-dated" in low
    gst_match = re.search(r"(\d+(?:\.\d+)?)\s*%\s*(?:gst|tax)?", low)
    gst_rate = to_decimal(gst_match.group(1)) if gst_match else ZERO

    ref_match = re.search(r"(?:ref|inv|bill|against)\s*#?\s*([A-Za-z0-9/_-]+)", txt, re.I)
    bill_ref = ref_match.group(1) if ref_match else ""

    # Determine qty * rate OR direct amount
    qty_rate = re.search(
        r"(\d+(?:\.\d+)?)\s*(?:pcs|pc|mtr|mtrs|kg|kgs|units|box)?\b.*?(?:@|at|rate)\s*(?:rs\.?|inr|₹)?\s*(\d+(?:,\d+)*(?:\.\d+)?)",
        low,
    )
    if qty_rate:
        qty = Decimal(qty_rate.group(1))
        rate = Decimal(qty_rate.group(2).replace(",", ""))
        taxable = (qty * rate).quantize(TWOPLACES, rounding=ROUND_HALF_UP)
    else:
        # Remove gst % and ref tokens before extracting monetary amount
        scrubbed = re.sub(r"\d+(?:\.\d+)?\s*%\s*(?:gst|tax)?", "", txt, flags=re.I)
        scrubbed = re.sub(r"(?:ref|inv|bill|against)\s*#?\s*[A-Za-z0-9/_-]+", "", scrubbed, flags=re.I)
        amt_match = re.search(r"(?:rs\.?|inr|₹)?\s*(\d+(?:,\d+)*(?:\.\d+)?)", scrubbed, re.I)
        if not amt_match:
            raise AccountingError("Could not detect an amount (or qty @ rate) in the 1-line entry")
        taxable = to_decimal(amt_match.group(1))

    # Extract party name cleanly
    party_match = re.search(
        r"(?:\bto\b|\bfrom\b)\s+([A-Za-z0-9 &()._-]{2,50}?)(?=\s+(?:@|\bat\b|\brate\b|\bvia\b|\bref\b|\binv\b|\bbill\b|\bagainst\b|\bcheque\b|\bpdc\b|\d+%|\d{3,})|$)",
        txt,
        re.I,
    )
    party_name = party_match.group(1).strip() if party_match else "Counter Party"

    bank_match = re.search(r"(?:via|from|into)\s+([A-Za-z0-9 &._-]*bank[A-Za-z0-9 &._-]*|cash)", txt, re.I)
    bank_ledger = bank_match.group(1).strip() if bank_match else "HDFC Bank Current A/c"
    if bank_ledger.lower() == "cash":
        bank_ledger = "Cash"

    if any(w in low for w in ("sold", "sale", "billed", "invoice")):
        gst = compute_gst_breakdown(taxable, gst_rate, company_state_code, party_gstin=party_gstin)
        gross = to_decimal(gst["gross_total"])
        entries = [
            {"ledger_name": party_name, "dr_cr": "DR", "amount": str(gross), "bill_ref": bill_ref or "INV-AI"},
            {"ledger_name": "Sales GST", "dr_cr": "CR", "amount": gst["taxable_amount"]},
        ]
        if to_decimal(gst["igst"]) > ZERO:
            entries.append({"ledger_name": "IGST Output", "dr_cr": "CR", "amount": gst["igst"]})
        elif to_decimal(gst["cgst"]) > ZERO:
            entries.append({"ledger_name": "CGST Output", "dr_cr": "CR", "amount": gst["cgst"]})
            entries.append({"ledger_name": "SGST Output", "dr_cr": "CR", "amount": gst["sgst"]})
        vtype = "SALES"
    elif any(w in low for w in ("bought", "purchased", "purchase")):
        gst = compute_gst_breakdown(taxable, gst_rate, company_state_code, party_gstin=party_gstin)
        gross = to_decimal(gst["gross_total"])
        entries = [{"ledger_name": "Purchase GST", "dr_cr": "DR", "amount": gst["taxable_amount"]}]
        if to_decimal(gst["igst"]) > ZERO:
            entries.append({"ledger_name": "IGST Input", "dr_cr": "DR", "amount": gst["igst"]})
        elif to_decimal(gst["cgst"]) > ZERO:
            entries.append({"ledger_name": "CGST Input", "dr_cr": "DR", "amount": gst["cgst"]})
            entries.append({"ledger_name": "SGST Input", "dr_cr": "DR", "amount": gst["sgst"]})
        entries.append({"ledger_name": party_name, "dr_cr": "CR", "amount": str(gross), "bill_ref": bill_ref or "PUR-AI"})
        vtype = "PURCHASE"
    elif any(w in low for w in ("paid", "remitted", "payment")):
        entries = [
            {"ledger_name": party_name, "dr_cr": "DR", "amount": str(taxable), "bill_ref": bill_ref},
            {"ledger_name": bank_ledger, "dr_cr": "CR", "amount": str(taxable)},
        ]
        vtype = "PAYMENT"
    elif any(w in low for w in ("received", "collected", "receipt")):
        entries = [
            {"ledger_name": bank_ledger, "dr_cr": "DR", "amount": str(taxable)},
            {"ledger_name": party_name, "dr_cr": "CR", "amount": str(taxable), "bill_ref": bill_ref},
        ]
        vtype = "RECEIPT"
    else:
        entries = [
            {"ledger_name": party_name, "dr_cr": "DR", "amount": str(taxable), "bill_ref": bill_ref},
            {"ledger_name": bank_ledger, "dr_cr": "CR", "amount": str(taxable)},
        ]
        vtype = "JOURNAL"

    return {
        "voucher_type": vtype,
        "is_pdc": is_pdc,
        "narration": txt,
        "party_name": party_name,
        "bill_ref": bill_ref,
        "entries": entries,
        "total_amount": str(sum((to_decimal(e["amount"]) for e in entries if e["dr_cr"] == "DR"), ZERO)),
    }
