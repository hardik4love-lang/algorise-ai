"""
Phase 2 Tests for Algorise BooksOS:
- GSP / NIC IRP e-Invoice (IRN + Signed QR + Auto E-Way Bill + 24h Cancel + Merkle)
- Schedule III Balance Sheet & P&L + GSTR-9 Annual Return Aggregation
- AlgoBridge Port 9000 XML Connector + HMAC-SHA256 Anti-Replay Guard
- CA Super-Console Multi-Client Portfolio, 25% Rev-Share & Batch Merkle Verification
"""

import hashlib
import importlib.util
import json
import os
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from engine.accounting import AccountingError, AccountingStore
from engine.accounting_phase2 import (
    cancel_einvoice_irn,
    generate_einvoice_irn,
    generate_schedule_iii_and_gstr9,
    get_ca_portfolio,
    verify_all_ca_merkle_chains,
)

# Load standalone AlgoBridge agent cleanly without package assumptions
_BRIDGE_PATH = ROOT / "algorise-accounting" / "algobridge" / "algobridge_agent.py"
_SPEC = importlib.util.spec_from_file_location("algobridge_agent", str(_BRIDGE_PATH))
algobridge_agent = importlib.util.module_from_spec(_SPEC)
assert _SPEC and _SPEC.loader
_SPEC.loader.exec_module(algobridge_agent)


def test_gsp_einvoice_irn_qr_ewb_and_cancel_lifecycle(tmp_path):
    store = AccountingStore(db_path=tmp_path / "einv.db")

    # Reject bad GSTIN or short HSN
    with pytest.raises(AccountingError, match="GSTIN"):
        generate_einvoice_irn(
            store,
            company_id="demo_einv_01",
            seller_gstin="BADGSTIN",
            buyer_gstin="24AABCM7721Q1Z9",
            doc_no="INV-1",
            doc_date="2026-11-27",
            items=[{"hsn_code": "5407", "taxable_value": 10000, "gst_rate_pct": 5}],
        )

    with pytest.raises(AccountingError, match="HSN"):
        generate_einvoice_irn(
            store,
            company_id="demo_einv_01",
            seller_gstin="24AABCA1234F1Z5",
            buyer_gstin="24AABCM7721Q1Z9",
            doc_no="INV-1",
            doc_date="2026-11-27",
            items=[{"hsn_code": "54", "taxable_value": 10000, "gst_rate_pct": 5}],
        )

    # Invoice > 50,000 generates IRN + Signed QR + E-Way Bill
    res = generate_einvoice_irn(
        store,
        company_id="demo_einv_01",
        seller_gstin="24AABCA1234F1Z5",
        buyer_gstin="24AABCM7721Q1Z9",
        doc_no="INV/26-27/101",
        doc_date="2026-11-27",
        items=[{"hsn_code": "5407", "taxable_value": 100000, "gst_rate_pct": 5}],
    )
    expected_irn = hashlib.sha256(b"24AABCA1234F1Z5INV/26-27/101INV2026-27").hexdigest()
    assert res["irn"] == expected_irn
    assert len(res["ack_no"]) == 15
    assert res["signed_qr_payload"].startswith("ALG1.")
    assert res["ewb_no"].startswith("34") and len(res["ewb_no"]) == 12
    assert res["total_invoice_value"] == "105000.00"

    # Invoice <= 50,000 generates IRN without E-Way Bill
    small = generate_einvoice_irn(
        store,
        company_id="demo_einv_01",
        seller_gstin="24AABCA1234F1Z5",
        buyer_gstin="24AABCM7721Q1Z9",
        doc_no="INV/26-27/102",
        doc_date="2026-11-27",
        items=[{"hsn_code": "5407", "taxable_value": 10000, "gst_rate_pct": 5}],
    )
    assert small["ewb_no"] == ""

    # Cancel within 24 hours & verify Merkle audit chain
    cancelled = cancel_einvoice_irn(store, "demo_einv_01", res["irn"], reason="Wrong buyer")
    assert cancelled["status"] == "CANCELLED"
    assert store.verify_audit_chain("demo_einv_01")["valid"] is True

    # Cancelled IRN cannot be regenerated
    with pytest.raises(AccountingError, match="previously cancelled"):
        generate_einvoice_irn(
            store,
            company_id="demo_einv_01",
            seller_gstin="24AABCA1234F1Z5",
            buyer_gstin="24AABCM7721Q1Z9",
            doc_no="INV/26-27/101",
            doc_date="2026-11-27",
            items=[{"hsn_code": "5407", "taxable_value": 100000, "gst_rate_pct": 5}],
        )


def test_schedule_iii_and_gstr9_aggregation(tmp_path):
    store = AccountingStore(db_path=tmp_path / "sched.db")
    store.ensure_company("demo_s3_01")
    store.create_or_update_ledger("demo_s3_01", "Capital", "Capital Account", opening_balance="500000.00", opening_dr_cr="CR")
    store.create_or_update_ledger("demo_s3_01", "HDFC Bank Current A/c", "Bank Accounts", opening_balance="500000.00", opening_dr_cr="DR")
    store.create_or_update_ledger("demo_s3_01", "Micro Yarn Co", "Sundry Creditors", msme_category="MICRO")
    store.create_or_update_ledger("demo_s3_01", "Big Trader Ltd", "Sundry Creditors", msme_category="NONE")
    store.create_or_update_ledger("demo_s3_01", "Surat Buyer", "Sundry Debtors", gstin="24AABCB1234F1Z1")

    store.post_voucher(
        "demo_s3_01",
        "PURCHASE",
        "2026-11-10",
        entries=[
            {"ledger_name": "Purchase GST", "dr_cr": "DR", "amount": "100000.00"},
            {"ledger_name": "CGST Input", "dr_cr": "DR", "amount": "2500.00"},
            {"ledger_name": "SGST Input", "dr_cr": "DR", "amount": "2500.00"},
            {"ledger_name": "Micro Yarn Co", "dr_cr": "CR", "amount": "105000.00", "bill_ref": "MY-1"},
        ],
    )
    store.post_voucher(
        "demo_s3_01",
        "SALES",
        "2026-11-15",
        entries=[
            {"ledger_name": "Surat Buyer", "dr_cr": "DR", "amount": "210000.00", "bill_ref": "SB-1"},
            {"ledger_name": "Sales GST", "dr_cr": "CR", "amount": "200000.00"},
            {"ledger_name": "CGST Output", "dr_cr": "CR", "amount": "5000.00"},
            {"ledger_name": "SGST Output", "dr_cr": "CR", "amount": "5000.00"},
        ],
    )

    report = generate_schedule_iii_and_gstr9(store, "demo_s3_01")
    s3 = report["schedule_iii"]
    assert s3["balance_sheet_parity"] is True
    assert s3["equity_and_liabilities"]["trade_payables_msme_micro_small"] == "105000.00"
    assert s3["profit_and_loss"]["profit_before_tax"] == "100000.00"

    g9 = report["gstr_9_annual"]
    assert g9["table_4_outward_supplies"]["total_output_tax"] == "10000.00"
    assert g9["table_6_itc_availed"]["total_itc"] == "5000.00"
    assert g9["net_cash_tax_payable"] == "5000.00"


def test_algobridge_mock_tally_pull_hmac_sync_and_replay_defense(tmp_path, monkeypatch):
    import engine.accounting_routes as accounting_routes

    monkeypatch.setattr(accounting_routes, "accounting_store", AccountingStore(db_path=tmp_path / "bridge.db"))

    # Start built-in Mock Tally HTTP XML Server on a free localhost port
    srv = algobridge_agent.start_mock_tally_server(0)
    mock_port = srv.server_address[1]
    tally_url = f"http://127.0.0.1:{mock_port}"

    try:
        chunks = [
            algobridge_agent.fetch_tally_port9000(tally_url, algobridge_agent.build_tally_export_envelope("List of Ledgers")),
            algobridge_agent.fetch_tally_port9000(tally_url, algobridge_agent.build_tally_export_envelope("List of Stock Items")),
            algobridge_agent.fetch_tally_port9000(tally_url, algobridge_agent.build_tally_export_envelope("Voucher Register")),
        ]
        merged_xml = algobridge_agent.merge_tally_envelopes(chunks)
    finally:
        srv.shutdown()
        srv.server_close()

    from fastapi.testclient import TestClient
    from engine.main import app

    payload = {
        "company_id": "demo_bridge_01",
        "source_host": tally_url,
        "tally_company": "Surat Weaving Mills",
        "xml_content": merged_xml,
    }
    raw_body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    ts, nonce, sig = algobridge_agent.sign_bridge_payload(raw_body, "algorise-bridge-dev-secret")

    with TestClient(app) as client:
        # 1. Valid HMAC sync succeeds
        ok = client.post(
            "/api/v1/accounting/bridge/sync",
            content=raw_body,
            headers={
                "Content-Type": "application/json",
                "X-AlgoBridge-Timestamp": str(ts),
                "X-AlgoBridge-Nonce": nonce,
                "X-AlgoBridge-Signature": sig,
            },
        )
        assert ok.status_code == 200
        body = ok.json()
        assert body["hmac_verified"] is True
        assert body["imported_ledgers"] == 2
        assert body["imported_stock_items"] == 1
        assert body["imported_vouchers"] == 1
        assert body["trial_balance_parity"]["is_balanced"] is True

        # 2. Replay attack reusing exact same nonce is blocked
        replay = client.post(
            "/api/v1/accounting/bridge/sync",
            content=raw_body,
            headers={
                "Content-Type": "application/json",
                "X-AlgoBridge-Timestamp": str(ts),
                "X-AlgoBridge-Nonce": nonce,
                "X-AlgoBridge-Signature": sig,
            },
        )
        assert replay.status_code == 403

        # 3. Stale timestamp outside +-300s is blocked
        old_ts, new_nonce, old_sig = algobridge_agent.sign_bridge_payload(
            raw_body, "algorise-bridge-dev-secret", timestamp=int(time.time()) - 900
        )
        expired = client.post(
            "/api/v1/accounting/bridge/sync",
            content=raw_body,
            headers={
                "Content-Type": "application/json",
                "X-AlgoBridge-Timestamp": str(old_ts),
                "X-AlgoBridge-Nonce": new_nonce,
                "X-AlgoBridge-Signature": old_sig,
            },
        )
        assert expired.status_code == 403


def test_ca_super_console_portfolio_batch_merkle_and_prod_auth(tmp_path, monkeypatch):
    import engine.accounting_routes as accounting_routes

    monkeypatch.setattr(accounting_routes, "accounting_store", AccountingStore(db_path=tmp_path / "ca.db"))
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
            # Production CA firm without X-Algorise-Key rejected
            unauth = client.get("/api/v1/accounting/ca/prod_ca_firm_01/portfolio")
            assert unauth.status_code == 401

            # Demo CA portfolio auto-seeds 3 SMEs and computes 25% rev-share
            port = client.get("/api/v1/accounting/ca/demo_ca_firm_01/portfolio")
            assert port.status_code == 200
            pdata = port.json()
            assert pdata["portfolio_summary"]["total_clients"] == 3
            assert pdata["portfolio_summary"]["all_merkle_chains_valid"] is True

            # Link a 4th SME client under CA firm
            link = client.post(
                "/api/v1/accounting/ca/demo_ca_firm_01/clients",
                json={
                    "firm_name": "Mehta & Shah Chartered Accountants",
                    "frn_number": "124891W",
                    "company_id": "demo_ca_cli_04",
                    "company_name": "Kataragam Silk Mills",
                    "company_gstin": "24AABCK9911Q1Z4",
                    "plan_tier": "GROWTH",
                },
            )
            assert link.status_code == 200

            batch = client.get("/api/v1/accounting/ca/demo_ca_firm_01/verify-all-merkle")
            assert batch.status_code == 200
            bdata = batch.json()
            assert bdata["clients_checked"] == 4
            assert bdata["clients_passed"] == 4
            assert bdata["all_compliant"] is True
    finally:
        os.environ.clear()
        os.environ.update(previous)
