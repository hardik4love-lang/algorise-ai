"""
Comprehensive Test Suite for Algorise BooksOS (`engine.accounting` & `engine.accounting_routes`).
Validates double-entry Decimal invariants, Tally XML Port 9000 bridge + XXE defense,
GST CGST/SGST vs IGST calculation, Fuzzy GSTR-2B reconciliation, Section 43B(h) MSME
disallowance radar, SHA-256 Merkle Edit Log tamper detection, and production FastAPI routes.
"""

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from engine.accounting import (
    AccountingError,
    AccountingStore,
    ImbalancedVoucherError,
    build_whatsapp_ledger_reminder,
    compute_gst_breakdown,
    evaluate_msme_43bh,
    parse_tally_xml,
    reconcile_gstr2b,
)


def test_double_entry_rejects_imbalance_and_posts_balanced(tmp_path):
    store = AccountingStore(db_path=tmp_path / "books.sqlite")
    with pytest.raises(ImbalancedVoucherError):
        store.post_voucher(
            company_id="demo_test_01",
            voucher_type="SALES",
            voucher_date="2026-11-27",
            entries=[
                {"ledger_name": "Buyer A", "dr_cr": "DR", "amount": "10500.00"},
                {"ledger_name": "Sales GST", "dr_cr": "CR", "amount": "10000.00"},
            ],
        )

    posted = store.post_voucher(
        company_id="demo_test_01",
        voucher_type="SALES",
        voucher_date="2026-11-27",
        voucher_no="INV-101",
        entries=[
            {"ledger_name": "Buyer A", "dr_cr": "DR", "amount": "10500.00", "bill_ref": "INV-101"},
            {"ledger_name": "Sales GST", "dr_cr": "CR", "amount": "10000.00"},
            {"ledger_name": "CGST Output", "dr_cr": "CR", "amount": "250.00"},
            {"ledger_name": "SGST Output", "dr_cr": "CR", "amount": "250.00"},
        ],
    )
    assert posted["status"] == "POSTED"
    assert posted["total_amount"] == "10500.00"
    tb = store.get_trial_balance("demo_test_01")
    assert tb["is_balanced"] is True
    assert tb["variance"] == "0.00"


def test_gst_breakdown_intra_vs_interstate():
    intra = compute_gst_breakdown("10000.00", "5", company_state_code="24", party_gstin="24AABCM7721Q1Z9")
    assert intra["supply_type"] == "INTRA_STATE"
    assert intra["cgst"] == "250.00"
    assert intra["sgst"] == "250.00"
    assert intra["igst"] == "0.00"
    assert intra["gross_total"] == "10500.00"

    inter = compute_gst_breakdown("10000.00", "18", company_state_code="24", party_gstin="27AABCD8812M1Z1")
    assert inter["supply_type"] == "INTER_STATE"
    assert inter["igst"] == "1800.00"
    assert inter["cgst"] == "0.00"
    assert inter["gross_total"] == "11800.00"


def test_tally_xml_xxe_rejected_and_valid_import_balanced(tmp_path):
    xxe_xml = '<?xml version="1.0"?><!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]><ENVELOPE>&xxe;</ENVELOPE>'
    with pytest.raises(AccountingError, match="Unsafe XML"):
        parse_tally_xml(xxe_xml)

    tally_xml = """<ENVELOPE>
      <BODY><IMPORTDATA><REQUESTDATA>
        <TALLYMESSAGE>
          <LEDGER NAME="Surat Looms" Action="Create">
            <PARENT>Sundry Debtors</PARENT>
            <PARTYGSTIN>24AABCS1111F1Z1</PARTYGSTIN>
            <OPENINGBALANCE>-5000.00</OPENINGBALANCE>
            <BILLALLOCATIONS.LIST>
              <NAME>OB-01</NAME>
              <BILLTYPE>New Ref</BILLTYPE>
              <AMOUNT>-4500.00</AMOUNT>
            </BILLALLOCATIONS.LIST>
          </LEDGER>
        </TALLYMESSAGE>
        <TALLYMESSAGE>
          <LEDGER NAME="Capital Reserve" Action="Create">
            <PARENT>Capital Account</PARENT>
            <OPENINGBALANCE>5000.00</OPENINGBALANCE>
          </LEDGER>
        </TALLYMESSAGE>
        <TALLYMESSAGE>
          <STOCKITEM NAME="Dola Grey 60G" Action="Create">
            <PARENT>Fabrics</PARENT>
            <BASEUNITS>Mtrs</BASEUNITS>
            <BATCHALLOCATIONS.LIST>
              <GODOWNNAME>Pandesara Godown</GODOWNNAME>
              <BATCHNAME>Lot-88</BATCHNAME>
              <OPENINGBALANCE>1000 Mtrs</OPENINGBALANCE>
              <OPENINGVALUE>85000.00</OPENINGVALUE>
            </BATCHALLOCATIONS.LIST>
          </STOCKITEM>
        </TALLYMESSAGE>
        <TALLYMESSAGE>
          <VOUCHER VCHTYPE="Sales" Action="Create">
            <DATE>20261120</DATE>
            <VOUCHERNUMBER>SL-01</VOUCHERNUMBER>
            <ALLLEDGERENTRIES.LIST>
              <LEDGERNAME>Surat Looms</LEDGERNAME>
              <ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE>
              <AMOUNT>-1050.00</AMOUNT>
            </ALLLEDGERENTRIES.LIST>
            <ALLLEDGERENTRIES.LIST>
              <LEDGERNAME>Sales GST</LEDGERNAME>
              <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>
              <AMOUNT>1000.00</AMOUNT>
            </ALLLEDGERENTRIES.LIST>
            <ALLLEDGERENTRIES.LIST>
              <LEDGERNAME>CGST Output</LEDGERNAME>
              <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>
              <AMOUNT>25.00</AMOUNT>
            </ALLLEDGERENTRIES.LIST>
            <ALLLEDGERENTRIES.LIST>
              <LEDGERNAME>SGST Output</LEDGERNAME>
              <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>
              <AMOUNT>25.00</AMOUNT>
            </ALLLEDGERENTRIES.LIST>
          </VOUCHER>
        </TALLYMESSAGE>
      </REQUESTDATA></IMPORTDATA></BODY>
    </ENVELOPE>"""

    parsed = parse_tally_xml(tally_xml)
    assert len(parsed["ledgers"]) == 2
    # Bill allocation residual (-5000 - (-4500) = -500) auto-reconciled into On Account
    assert len(parsed["ledgers"][0]["bills"]) == 2
    assert parsed["ledgers"][0]["bills"][1]["bill_type"] == "On Account"
    assert len(parsed["stock_items"]) == 1

    store = AccountingStore(db_path=tmp_path / "import.sqlite")
    res = store.import_tally_xml("demo_import_01", tally_xml)
    assert res["imported_ledgers"] == 2
    assert res["imported_stock_items"] == 1
    assert res["imported_vouchers"] == 1
    assert res["trial_balance_parity"]["is_balanced"] is True
    assert res["trial_balance_parity"]["variance"] == "0.00"


def test_fuzzy_gstr2b_reconciliation():
    books = [
        {"supplier_gstin": "24AABCN4411K1Z3", "invoice_no": "INV/26-27/0045", "invoice_date": "2026-11-10", "taxable_value": 10000, "total_tax": 500},
        {"supplier_gstin": "24AABCD5555B1Z7", "invoice_no": "CHEM-882", "invoice_date": "2026-11-12", "taxable_value": 20000, "total_tax": 3600},
    ]
    portal_2b = [
        {"supplier_gstin": "24AABCN4411K1Z3", "invoice_no": "45", "invoice_date": "2026-11-11", "taxable_value": 10000, "total_tax": 501},
        {"supplier_gstin": "24AABCZ1122M1Z2", "invoice_no": "TRANS-91", "invoice_date": "2026-11-14", "taxable_value": 5000, "total_tax": 900},
    ]
    res = reconcile_gstr2b(books, portal_2b, rounding_tolerance="2.00")
    assert res["summary"]["matched_count"] == 1
    assert res["matched"][0]["status"] == "FUZZY_MATCH_TOLERATED"
    assert res["summary"]["missing_in_2b_itc_risk_count"] == 1
    assert res["summary"]["missing_in_books_count"] == 1
    assert res["summary"]["itc_at_risk_amount"] == "3600.00"


def test_msme_43bh_overrides_60_day_contract_to_45_days():
    bills = [
        {
            "bill_ref": "NDM/045",
            "supplier_name": "Navkar Dyeing Mills",
            "msme_category": "MICRO",
            "bill_date": "2026-10-01",
            "has_written_agreement": True,
            "agreed_credit_days": 90,
            "outstanding_amount": "100000.00",
        },
        {
            "bill_ref": "SYP/019",
            "supplier_name": "Shree Yarn Processors",
            "msme_category": "SMALL",
            "bill_date": "2026-11-10",
            "has_written_agreement": False,
            "outstanding_amount": "50000.00",
        },
    ]
    res = evaluate_msme_43bh(bills, as_of_date="2026-11-27")
    assert res["bills"][0]["statutory_limit_days"] == 45
    assert res["bills"][0]["risk_status"] == "DISALLOWED_EXPOSURE"
    assert res["bills"][1]["statutory_limit_days"] == 15
    assert res["bills"][1]["risk_status"] == "DISALLOWED_EXPOSURE"
    assert res["disallowed_exposure_amount"] == "150000.00"
    assert res["estimated_tax_addback_30pct"] == "45000.00"


def test_merkle_audit_chain_detects_tampering(tmp_path):
    db_file = tmp_path / "merkle.sqlite"
    store = AccountingStore(db_path=db_file)
    v = store.post_voucher(
        company_id="demo_merkle_01",
        voucher_type="PAYMENT",
        voucher_date="2026-11-27",
        entries=[
            {"ledger_name": "Rent Expense", "dr_cr": "DR", "amount": "25000.00"},
            {"ledger_name": "Cash", "dr_cr": "CR", "amount": "25000.00"},
        ],
    )
    store.cancel_voucher("demo_merkle_01", v["voucher_id"], reason="Wrong cash ledger")
    assert store.verify_audit_chain("demo_merkle_01")["valid"] is True

    # Simulate illicit direct SQL tampering on audit trail payload
    import sqlite3
    with sqlite3.connect(str(db_file)) as conn:
        conn.execute("UPDATE audit_blocks SET actor = 'tamperer' WHERE action = 'CREATE_VOUCHER'")
    tampered = store.verify_audit_chain("demo_merkle_01")
    assert tampered["valid"] is False
    assert tampered["reason"] == "block_hash tamper detected"


def test_whatsapp_multilingual_reminder():
    wa = build_whatsapp_ledger_reminder(
        company_name="Apex Fabrics",
        party_name="Mahalaxmi Sarees",
        outstanding_amount="262500",
        overdue_days=18,
        language="gu",
        upi_id="apex@upi",
    )
    assert "CONFIRM" in wa["message"]
    assert "apex@upi" in wa["message"]


def test_accounting_api_routes_in_production_mode(tmp_path, monkeypatch):
    import engine.accounting_routes as accounting_routes

    monkeypatch.setattr(
        accounting_routes,
        "accounting_store",
        AccountingStore(db_path=tmp_path / "api_test.db"),
    )
    previous = dict(os.environ)
    os.environ["ENVIRONMENT"] = "production"
    os.environ["MIGRATE_ON_START"] = "false"
    os.environ["REDIS_REQUIRED"] = "false"
    os.environ["ENABLE_EMBEDDED_SCHEDULER"] = "false"
    os.environ.setdefault("SECRET_KEY", "test-not-a-real-secret")
    os.environ.setdefault("ADMIN_SECRET", "test-not-a-real-secret")
    os.environ.setdefault("FB_APP_SECRET", "test-not-a-real-secret")

    try:
        from fastapi.testclient import TestClient
        from engine.main import app

        with TestClient(app) as client:
            health = client.get("/api/v1/accounting/health")
            assert health.status_code == 200
            assert health.json()["product"] == "Algorise BooksOS"

            # Production non-demo company must enforce X-Algorise-Key
            denied = client.get("/api/v1/accounting/companies/prod_tenant_01/summary")
            assert denied.status_code == 401

            # Demo sandbox company works openly for website visitors
            demo_summary = client.get("/api/v1/accounting/companies/demo_web_01/summary")
            assert demo_summary.status_code == 200
            assert demo_summary.json()["trial_balance"]["is_balanced"] is True
            assert demo_summary.json()["audit_trail_integrity"]["valid"] is True
    finally:
        os.environ.clear()
        os.environ.update(previous)
