"""
AlgoBridge — Lightweight Local Tally.ERP 9 / TallyPrime Port 9000 Connector.

Polls Tally's built-in HTTP XML Server (`http://localhost:9000`), merges Masters
(Ledgers, Bill-by-Bill, Stock Items) + Vouchers into a unified <ENVELOPE>, signs
with HMAC-SHA256 + timestamp + nonce, and syncs to Algorise BooksOS Cloud.

Zero external dependencies (Python 3.11+ stdlib only) — runs directly or compiles
to a standalone Windows tray/CLI `.exe` via PyInstaller (`build_exe.bat`).
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import http.server
import json
import os
import socketserver
import threading
import time
import urllib.error
import urllib.request
import uuid
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple


DEFAULT_TALLY_URL = "http://localhost:9000"
DEFAULT_CLOUD_URL = "https://algorise-ai-backend.onrender.com/api/v1/accounting/bridge/sync"


def build_tally_export_envelope(
    report_name: str,
    company_name: str = "",
    from_date: str = "20260401",
    to_date: str = "20270331",
) -> str:
    """Construct an official Tally.ERP 9 / TallyPrime Port 9000 XML Export envelope."""
    company_tag = f"<SVCURRENTCOMPANY>{company_name}</SVCURRENTCOMPANY>" if company_name else ""
    date_tags = ""
    if "voucher" in report_name.lower() or "daybook" in report_name.lower():
        date_tags = f"<SVFROMDATE>{from_date}</SVFROMDATE><SVTODATE>{to_date}</SVTODATE>"
    return (
        "<ENVELOPE>"
        "<HEADER><TALLYREQUEST>Export Data</TALLYREQUEST></HEADER>"
        "<BODY><EXPORTDATA><REQUESTDESC>"
        f"<REPORTNAME>{report_name}</REPORTNAME>"
        f"<STATICVARIABLES><SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>{company_tag}{date_tags}</STATICVARIABLES>"
        "</REQUESTDESC></EXPORTDATA></BODY>"
        "</ENVELOPE>"
    )


def fetch_tally_port9000(tally_url: str, xml_payload: str, timeout: float = 10.0) -> str:
    """POST an XML <ENVELOPE> query to Tally's local HTTP XML server."""
    req = urllib.request.Request(
        tally_url,
        data=xml_payload.encode("utf-8"),
        headers={"Content-Type": "application/xml; charset=utf-8"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def merge_tally_envelopes(xml_chunks: list[str]) -> str:
    """Merge Ledgers, Stock Items, and Vouchers exports into one clean <ENVELOPE>."""
    messages: list[str] = []
    for chunk in xml_chunks:
        if not chunk or not chunk.strip():
            continue
        upper = chunk[:4096].upper()
        if "<!DOCTYPE" in upper or "<!ENTITY" in upper:
            raise ValueError("Unsafe XML returned from Tally endpoint")
        root = ET.fromstring(chunk)
        for tag in ("LEDGER", "STOCKITEM", "VOUCHER"):
            for el in root.iter(tag):
                messages.append("<TALLYMESSAGE>" + ET.tostring(el, encoding="unicode") + "</TALLYMESSAGE>")
    joined = "\n".join(messages)
    return f"<ENVELOPE><BODY><IMPORTDATA><REQUESTDATA>{joined}</REQUESTDATA></IMPORTDATA></BODY></ENVELOPE>"


def sign_bridge_payload(
    raw_body: bytes,
    secret: str,
    timestamp: Optional[int] = None,
    nonce: Optional[str] = None,
) -> Tuple[int, str, str]:
    """Compute HMAC-SHA256 headers matching engine.accounting_phase2.verify_algobridge_hmac."""
    ts = int(timestamp if timestamp is not None else time.time())
    nc = nonce or uuid.uuid4().hex
    body_hash = hashlib.sha256(raw_body).hexdigest()
    msg = f"{ts}.{nc}.{body_hash}".encode("utf-8")
    sig = hmac.new(secret.encode("utf-8"), msg, hashlib.sha256).hexdigest()
    return ts, nc, sig


def push_to_algorise_cloud(
    cloud_sync_url: str,
    company_id: str,
    xml_content: str,
    hmac_secret: str,
    api_key: str = "",
    tally_company: str = "",
    source_host: str = DEFAULT_TALLY_URL,
    timeout: float = 20.0,
) -> Dict[str, Any]:
    """Sign and POST consolidated Tally XML to Algorise BooksOS Cloud."""
    body_dict = {
        "company_id": company_id,
        "source_host": source_host,
        "tally_company": tally_company,
        "xml_content": xml_content,
    }
    raw_body = json.dumps(body_dict, separators=(",", ":")).encode("utf-8")
    ts, nonce, sig = sign_bridge_payload(raw_body, hmac_secret)

    headers = {
        "Content-Type": "application/json",
        "X-AlgoBridge-Timestamp": str(ts),
        "X-AlgoBridge-Nonce": nonce,
        "X-AlgoBridge-Signature": sig,
    }
    if api_key:
        headers["X-Algorise-Key"] = api_key

    req = urllib.request.Request(cloud_sync_url, data=raw_body, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


class BridgeStatusState:
    def __init__(self) -> None:
        self.last_sync_utc: str = ""
        self.last_hash: str = ""
        self.last_status: str = "IDLE"
        self.tally_connected: bool = False
        self.last_result: Dict[str, Any] = {}


def sync_once(
    tally_url: str,
    cloud_url: str,
    company_id: str,
    hmac_secret: str,
    api_key: str = "",
    tally_company: str = "",
    state: Optional[BridgeStatusState] = None,
) -> Dict[str, Any]:
    """Pull Masters + Vouchers from Tally Port 9000 and sync if changed."""
    chunks = [
        fetch_tally_port9000(tally_url, build_tally_export_envelope("List of Ledgers", tally_company)),
        fetch_tally_port9000(tally_url, build_tally_export_envelope("List of Stock Items", tally_company)),
        fetch_tally_port9000(tally_url, build_tally_export_envelope("Voucher Register", tally_company)),
    ]
    merged_xml = merge_tally_envelopes(chunks)
    digest = hashlib.sha256(merged_xml.encode("utf-8")).hexdigest()

    if state and state.last_hash == digest:
        state.tally_connected = True
        state.last_status = "NO_CHANGES"
        return {"skipped": True, "reason": "No changes since last sync", "digest": digest}

    res = push_to_algorise_cloud(
        cloud_sync_url=cloud_url,
        company_id=company_id,
        xml_content=merged_xml,
        hmac_secret=hmac_secret,
        api_key=api_key,
        tally_company=tally_company,
        source_host=tally_url,
    )
    if state:
        state.tally_connected = True
        state.last_hash = digest
        state.last_sync_utc = datetime.now(timezone.utc).isoformat()
        state.last_status = "SYNCED"
        state.last_result = res
    return res


def start_local_status_server(state: BridgeStatusState, port: int = 9095) -> socketserver.TCPServer:
    """Expose local JSON status on 127.0.0.1:9095 so BooksOS web UI detects AlgoBridge live."""

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            if self.path != "/status":
                self.send_response(404)
                self.end_headers()
                return
            payload = json.dumps(
                {
                    "agent": "AlgoBridge",
                    "version": "1.0.0",
                    "tally_connected": state.tally_connected,
                    "last_status": state.last_status,
                    "last_sync_utc": state.last_sync_utc,
                    "last_result": state.last_result,
                }
            ).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, fmt: str, *args: Any) -> None:
            pass

    srv = socketserver.TCPServer(("127.0.0.1", port), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def start_mock_tally_server(port: int = 9000) -> socketserver.TCPServer:
    """Built-in Tally Port 9000 XML Server simulator for offline testing & demos."""
    sample_ledgers = """<ENVELOPE><BODY><IMPORTDATA><REQUESTDATA>
      <TALLYMESSAGE><LEDGER NAME="Surat Weaving Mills" Action="Create"><PARENT>Sundry Debtors</PARENT><PARTYGSTIN>24AABCS7721Q1Z2</PARTYGSTIN><OPENINGBALANCE>-25000.00</OPENINGBALANCE></LEDGER></TALLYMESSAGE>
      <TALLYMESSAGE><LEDGER NAME="Owner Capital" Action="Create"><PARENT>Capital Account</PARENT><OPENINGBALANCE>25000.00</OPENINGBALANCE></LEDGER></TALLYMESSAGE>
    </REQUESTDATA></IMPORTDATA></BODY></ENVELOPE>"""
    sample_items = """<ENVELOPE><BODY><IMPORTDATA><REQUESTDATA>
      <TALLYMESSAGE><STOCKITEM NAME="Jacquard Silk 60G" Action="Create"><PARENT>Fabrics</PARENT><BASEUNITS>Mtrs</BASEUNITS><BATCHALLOCATIONS.LIST><GODOWNNAME>Ring Road Godown</GODOWNNAME><OPENINGBALANCE>500 Mtrs</OPENINGBALANCE><OPENINGVALUE>42500.00</OPENINGVALUE></BATCHALLOCATIONS.LIST></STOCKITEM></TALLYMESSAGE>
    </REQUESTDATA></IMPORTDATA></BODY></ENVELOPE>"""
    sample_vouchers = """<ENVELOPE><BODY><IMPORTDATA><REQUESTDATA>
      <TALLYMESSAGE><VOUCHER VCHTYPE="Sales" Action="Create"><DATE>20261126</DATE><VOUCHERNUMBER>MOCK/9000/1</VOUCHERNUMBER>
      <ALLLEDGERENTRIES.LIST><LEDGERNAME>Surat Weaving Mills</LEDGERNAME><ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE><AMOUNT>-10500.00</AMOUNT></ALLLEDGERENTRIES.LIST>
      <ALLLEDGERENTRIES.LIST><LEDGERNAME>Sales GST</LEDGERNAME><ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE><AMOUNT>10000.00</AMOUNT></ALLLEDGERENTRIES.LIST>
      <ALLLEDGERENTRIES.LIST><LEDGERNAME>CGST Output</LEDGERNAME><ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE><AMOUNT>250.00</AMOUNT></ALLLEDGERENTRIES.LIST>
      <ALLLEDGERENTRIES.LIST><LEDGERNAME>SGST Output</LEDGERNAME><ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE><AMOUNT>250.00</AMOUNT></ALLLEDGERENTRIES.LIST>
      </VOUCHER></TALLYMESSAGE>
    </REQUESTDATA></IMPORTDATA></BODY></ENVELOPE>"""

    class TallyMockHandler(http.server.BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length).decode("utf-8", errors="replace")
            if "Stock Items" in raw:
                body = sample_items
            elif "Voucher" in raw:
                body = sample_vouchers
            else:
                body = sample_ledgers
            data = body.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/xml")
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, fmt: str, *args: Any) -> None:
            pass

    srv = socketserver.TCPServer(("127.0.0.1", port), TallyMockHandler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def main() -> int:
    parser = argparse.ArgumentParser(description="AlgoBridge Tally Port 9000 Sync Agent")
    parser.add_argument("--tally-url", default=os.environ.get("TALLY_URL", DEFAULT_TALLY_URL))
    parser.add_argument("--cloud-url", default=os.environ.get("ALGORISE_BRIDGE_URL", DEFAULT_CLOUD_URL))
    parser.add_argument("--company-id", default=os.environ.get("ALGORISE_COMPANY_ID", "demo_booksos_01"))
    parser.add_argument("--tally-company", default=os.environ.get("TALLY_COMPANY_NAME", ""))
    parser.add_argument("--secret", default=os.environ.get("ALGOBRIDGE_HMAC_SECRET", "algorise-bridge-dev-secret"))
    parser.add_argument("--api-key", default=os.environ.get("ALGORISE_API_KEY", ""))
    parser.add_argument("--interval", type=int, default=60, help="Sync interval in seconds")
    parser.add_argument("--once", action="store_true", help="Run a single sync and exit")
    parser.add_argument("--mock-tally", action="store_true", help="Spin up a local simulated Tally Port 9000 XML server")
    args = parser.parse_args()

    state = BridgeStatusState()
    if args.mock_tally:
        start_mock_tally_server(9000)
        print("[AlgoBridge] Mock Tally XML server listening on http://127.0.0.1:9000")

    if not args.once:
        start_local_status_server(state, 9095)
        print("[AlgoBridge] Local status endpoint listening on http://127.0.0.1:9095/status")

    while True:
        try:
            res = sync_once(
                tally_url=args.tally_url,
                cloud_url=args.cloud_url,
                company_id=args.company_id,
                hmac_secret=args.secret,
                api_key=args.api_key,
                tally_company=args.tally_company,
                state=state,
            )
            print("[AlgoBridge]", json.dumps(res))
        except Exception as exc:
            state.tally_connected = False
            state.last_status = f"ERROR: {exc}"
            print("[AlgoBridge] Sync error:", exc)
        if args.once:
            break
        time.sleep(max(5, args.interval))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
