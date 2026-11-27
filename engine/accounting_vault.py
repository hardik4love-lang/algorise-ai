"""
Algorise BooksOS — Zero-Knowledge Envelope Cryptography (ALGBK01),
Encrypted Anywhere Cloud Relay, and User-Owned Gmail / Google Drive / Sheets Backups.

Cryptographic Envelope Layout (Binary `ALGBK01`):
  [0..7]   Magic:   b"ALGBK01" (7 bytes)
  [7..8]   Flags:   0x01 = GZip compressed JSON, 0x00 = Raw UTF-8 JSON
  [8..24]  Salt:    16 random bytes (per-vault CSPRNG)
  [24..28] Iter:    4-byte uint32 big-endian PBKDF2 iterations (default: 600,000)
  [28..40] Nonce:   12 random bytes (96-bit AES-GCM IV)
  [40..]   Payload: AES-256-GCM ciphertext + 16-byte authentication tag,
                    bound via AAD = header[0:40].

100% compatible with browser Web Crypto SubtleCrypto (`PBKDF2` SHA-256 + `AES-GCM`).
Neither Algorise Cloud nor Gmail/Google Drive ever sees plaintext or the passphrase.
"""

from __future__ import annotations

import base64
import gzip
import hashlib
import json
import os
import smtplib
import struct
import urllib.parse
from datetime import datetime, timezone
from email.message import EmailMessage
from typing import Any, Dict, List, Optional

import httpx
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from engine.accounting import AccountingError, AccountingStore

ALGBK_MAGIC = b"ALGBK01"
FLAG_RAW = 0x00
FLAG_GZIP = 0x01
HEADER_LEN = 40
DEFAULT_PBKDF2_ITERATIONS = 600_000
MIN_ALLOWED_ITERATIONS = 10_000


def _derive_kek(passphrase: str, salt: bytes, iterations: int) -> bytes:
    if not passphrase or len(passphrase) < 6:
        raise AccountingError("Vault passphrase must be at least 6 characters")
    if iterations < MIN_ALLOWED_ITERATIONS:
        raise AccountingError(f"PBKDF2 iterations too low: {iterations}")
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=iterations,
    )
    return kdf.derive(passphrase.encode("utf-8"))


def seal_algobk_envelope(
    payload_bytes: bytes,
    passphrase: str,
    compress: bool = True,
    iterations: int = DEFAULT_PBKDF2_ITERATIONS,
) -> bytes:
    """Compress (optional) and seal raw payload into ALGBK01 AES-256-GCM binary format."""
    salt = os.urandom(16)
    nonce = os.urandom(12)
    flag = FLAG_GZIP if compress else FLAG_RAW
    body = gzip.compress(payload_bytes, compresslevel=9) if compress else payload_bytes
    header = ALGBK_MAGIC + bytes([flag]) + salt + struct.pack(">I", int(iterations)) + nonce
    assert len(header) == HEADER_LEN

    key = _derive_kek(passphrase, salt, int(iterations))
    ciphertext = AESGCM(key).encrypt(nonce, body, header)
    return header + ciphertext


def unseal_algobk_envelope(envelope_bytes: bytes, passphrase: str) -> bytes:
    """Verify AAD + GCM tag and decrypt ALGBK01 binary package back to plaintext bytes."""
    if not envelope_bytes or len(envelope_bytes) < HEADER_LEN + 16:
        raise AccountingError("Corrupted ALGBK01 vault file: payload too short")

    header = envelope_bytes[:HEADER_LEN]
    magic = header[:7]
    if magic != ALGBK_MAGIC:
        raise AccountingError("Invalid vault header magic (expected ALGBK01)")

    flag = header[7]
    salt = header[8:24]
    (iterations,) = struct.unpack(">I", header[24:28])
    nonce = header[28:40]
    ciphertext = envelope_bytes[HEADER_LEN:]

    key = _derive_kek(passphrase, salt, iterations)
    try:
        decrypted = AESGCM(key).decrypt(nonce, ciphertext, header)
    except Exception as exc:
        raise AccountingError("Decryption failed: wrong passphrase or tampered vault") from exc

    if flag == FLAG_GZIP:
        try:
            return gzip.decompress(decrypted)
        except Exception as exc:
            raise AccountingError("Corrupted GZip stream inside ALGBK01 vault") from exc
    if flag == FLAG_RAW:
        return decrypted
    raise AccountingError(f"Unsupported ALGBK01 compression flag: {flag}")


def ensure_vault_schema(store: AccountingStore) -> None:
    """Create encrypted cloud relay & backup attestation tables in SQLite WAL."""
    with store._connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS vault_sync_blobs (
                company_id TEXT PRIMARY KEY,
                device_id TEXT NOT NULL,
                version_seq INTEGER NOT NULL DEFAULT 1,
                envelope_b64 TEXT NOT NULL,
                envelope_sha256 TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS vault_backup_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id TEXT NOT NULL,
                target TEXT NOT NULL,
                recipient_or_path TEXT NOT NULL,
                envelope_sha256 TEXT NOT NULL,
                size_bytes INTEGER NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            """
        )


def export_company_snapshot(store: AccountingStore, company_id: str) -> Dict[str, Any]:
    """Export full deterministic company state + Merkle audit blocks for backup."""
    company = store.ensure_company(company_id)
    ledgers = store.get_ledgers(company_id)
    vouchers = store.get_vouchers(company_id, include_cancelled=True)
    audit_blocks = store.get_audit_trail(company_id, limit=500)
    with store._connect() as conn:
        stock_rows = [dict(r) for r in conn.execute("SELECT * FROM stock_items WHERE company_id = ?", (company_id,)).fetchall()]
        einv_rows = [dict(r) for r in conn.execute("SELECT * FROM einvoices WHERE company_id = ?", (company_id,)).fetchall()]
    return {
        "schema": "algorise_booksos_snapshot_v1",
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "company": company,
        "ledgers": ledgers,
        "stock_items": stock_rows,
        "vouchers": vouchers,
        "einvoices": einv_rows,
        "audit_blocks": audit_blocks,
    }


def restore_company_snapshot(
    store: AccountingStore,
    company_id: str,
    snapshot: Dict[str, Any],
    actor: str = "vault_restore",
) -> Dict[str, Any]:
    """Restore an unsealed ALGBK01 snapshot into a target company and verify parity."""
    if not isinstance(snapshot, dict) or snapshot.get("schema") != "algorise_booksos_snapshot_v1":
        raise AccountingError("Unsupported or invalid BooksOS snapshot schema")

    comp_meta = snapshot.get("company") or {}
    store.ensure_company(
        company_id,
        name=str(comp_meta.get("name") or "Restored Enterprise"),
        gstin=str(comp_meta.get("gstin") or "24AABCA1234F1Z5"),
        state_code=str(comp_meta.get("state_code") or "24"),
    )

    restored_ledgers = 0
    for l in snapshot.get("ledgers") or []:
        store.create_or_update_ledger(
            company_id=company_id,
            name=l["name"],
            parent_group=l.get("parent_group", "Sundry Debtors"),
            gstin=l.get("gstin", ""),
            msme_category=l.get("msme_category", "NONE"),
            udyam_no=l.get("udyam_no", ""),
            opening_balance=l.get("opening_balance", "0.00"),
            opening_dr_cr=l.get("opening_dr_cr", "DR"),
            phone=l.get("phone", ""),
            actor=actor,
        )
        restored_ledgers += 1

    restored_vouchers = 0
    for v in snapshot.get("vouchers") or []:
        if v.get("status") == "CANCELLED":
            continue
        entries = v.get("entries") or []
        if len(entries) < 2:
            continue
        store.post_voucher(
            company_id=company_id,
            voucher_type=v.get("voucher_type", "JOURNAL"),
            voucher_date=v.get("voucher_date"),
            voucher_no=v.get("voucher_no"),
            narration=v.get("narration", "Restored from ALGBK01 Vault"),
            is_pdc=bool(v.get("is_pdc", False)),
            pdc_date=str(v.get("pdc_date") or ""),
            party_gstin=str(v.get("party_gstin") or ""),
            has_written_agreement=bool(v.get("has_written_agreement", False)),
            agreed_credit_days=int(v.get("agreed_credit_days") or 15),
            entries=entries,
            actor=actor,
        )
        restored_vouchers += 1

    tb = store.get_trial_balance(company_id)
    audit = store.verify_audit_chain(company_id)
    return {
        "status": "RESTORED",
        "company_id": company_id,
        "restored_ledgers": restored_ledgers,
        "restored_vouchers": restored_vouchers,
        "trial_balance_balanced": tb["is_balanced"],
        "merkle_audit_valid": audit["valid"],
    }


def push_encrypted_vault_blob(
    store: AccountingStore,
    company_id: str,
    envelope_b64: str,
    device_id: str = "web_client",
    expected_min_version: Optional[int] = None,
) -> Dict[str, Any]:
    """Store opaque client-encrypted ALGBK01 blob for multi-device anywhere sync."""
    ensure_vault_schema(store)
    store.ensure_company(company_id)
    try:
        raw = base64.b64decode(envelope_b64.encode("ascii"), validate=True)
    except Exception as exc:
        raise AccountingError("Invalid base64 encrypted vault blob") from exc
    if len(raw) < HEADER_LEN + 16 or raw[:7] != ALGBK_MAGIC:
        raise AccountingError("Rejected non-ALGBK01 ciphertext blob")

    digest = hashlib.sha256(raw).hexdigest()
    now = datetime.now(timezone.utc).isoformat()
    with store._connect() as conn:
        existing = conn.execute(
            "SELECT version_seq FROM vault_sync_blobs WHERE company_id = ?",
            (company_id,),
        ).fetchone()
        next_ver = 1
        if existing:
            cur_ver = int(existing["version_seq"])
            if expected_min_version is not None and expected_min_version < cur_ver:
                raise AccountingError(f"Sync conflict: server version {cur_ver} > client base {expected_min_version}")
            next_ver = cur_ver + 1

        conn.execute(
            """
            INSERT OR REPLACE INTO vault_sync_blobs
            (company_id, device_id, version_seq, envelope_b64, envelope_sha256, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (company_id, device_id, next_ver, envelope_b64, digest, now),
        )
    return {
        "status": "SYNCED_OPAQUE_E2EE",
        "company_id": company_id,
        "version_seq": next_ver,
        "envelope_sha256": digest,
        "size_bytes": len(raw),
        "updated_at": now,
    }


def pull_encrypted_vault_blob(store: AccountingStore, company_id: str) -> Dict[str, Any]:
    ensure_vault_schema(store)
    with store._connect() as conn:
        row = conn.execute("SELECT * FROM vault_sync_blobs WHERE company_id = ?", (company_id,)).fetchone()
        if not row:
            return {"exists": False, "company_id": company_id}
        data = dict(row)
        data["exists"] = True
        return data


def record_backup_event(
    store: AccountingStore,
    company_id: str,
    target: str,
    recipient_or_path: str,
    envelope_bytes: bytes,
    status: str = "DISPATCHED",
) -> Dict[str, Any]:
    ensure_vault_schema(store)
    digest = hashlib.sha256(envelope_bytes).hexdigest()
    now = datetime.now(timezone.utc).isoformat()
    with store._connect() as conn:
        conn.execute(
            """
            INSERT INTO vault_backup_history
            (company_id, target, recipient_or_path, envelope_sha256, size_bytes, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (company_id, target, recipient_or_path, digest, len(envelope_bytes), status, now),
        )
    return {
        "target": target,
        "recipient_or_path": recipient_or_path,
        "sha256": digest,
        "size_bytes": len(envelope_bytes),
        "status": status,
        "timestamp": now,
    }


def list_backup_history(store: AccountingStore, company_id: str) -> List[Dict[str, Any]]:
    ensure_vault_schema(store)
    with store._connect() as conn:
        rows = conn.execute(
            "SELECT * FROM vault_backup_history WHERE company_id = ? ORDER BY id DESC LIMIT 50",
            (company_id,),
        ).fetchall()
        return [dict(r) for r in rows]


class GmailVaultDispatcher:
    """Dispatches zero-knowledge ALGBK01 encrypted backups to the user's own Gmail."""

    @staticmethod
    def build_backup_email_message(
        envelope_bytes: bytes,
        file_name: str,
        recipient_email: str,
        sender_email: str,
        company_name: str,
    ) -> EmailMessage:
        checksum = hashlib.sha256(envelope_bytes).hexdigest()
        size_kb = len(envelope_bytes) / 1024.0
        msg = EmailMessage()
        msg["Subject"] = f"[Algorise BooksOS Vault] Encrypted Backup ({company_name}) - {datetime.now(timezone.utc).strftime('%Y-%m-%d')}"
        msg["From"] = sender_email
        msg["To"] = recipient_email
        msg.set_content(
            f"Zero-Knowledge Encrypted Accounting Backup (ALGBK01)\n"
            f"Company: {company_name}\n"
            f"Encryption: PBKDF2-HMAC-SHA256 (600,000 iter) + AES-256-GCM (AAD Authenticated)\n"
            f"File: {file_name} ({size_kb:.2f} KB)\n"
            f"SHA-256 Integrity Checksum: {checksum}\n\n"
            f"Neither Gmail nor Algorise Cloud can decrypt this file without your Master Vault Passphrase.\n"
            f"To restore anywhere: open Algorise BooksOS -> Vault -> Restore From .algobook & enter your passphrase.\n"
        )
        msg.add_attachment(
            envelope_bytes,
            maintype="application",
            subtype="octet-stream",
            filename=file_name,
        )
        return msg

    @classmethod
    def dispatch_via_smtp(
        cls,
        envelope_bytes: bytes,
        file_name: str,
        recipient_email: str,
        sender_email: str,
        gmail_app_password: str,
        company_name: str = "BooksOS Company",
    ) -> Dict[str, Any]:
        if not recipient_email or "@" not in recipient_email:
            raise AccountingError("Valid Gmail recipient address required")
        if not gmail_app_password:
            raise AccountingError("Gmail App Password is required for SMTP dispatch")

        msg = cls.build_backup_email_message(
            envelope_bytes=envelope_bytes,
            file_name=file_name,
            recipient_email=recipient_email,
            sender_email=sender_email or recipient_email,
            company_name=company_name,
        )
        with smtplib.SMTP("smtp.gmail.com", 587, timeout=20) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(sender_email or recipient_email, gmail_app_password)
            server.send_message(msg)

        return {
            "status": "DISPATCHED_GMAIL_SMTP",
            "recipient": recipient_email,
            "file_name": file_name,
            "sha256": hashlib.sha256(envelope_bytes).hexdigest(),
            "size_bytes": len(envelope_bytes),
        }

    @classmethod
    async def insert_via_gmail_api(
        cls,
        access_token: str,
        envelope_bytes: bytes,
        file_name: str,
        user_email: str,
        company_name: str = "BooksOS Company",
    ) -> Dict[str, Any]:
        """Insert encrypted backup directly into user's own Gmail via OAuth2 gmail.insert scope."""
        if not access_token:
            raise AccountingError("Google OAuth2 access_token is required")
        msg = cls.build_backup_email_message(
            envelope_bytes=envelope_bytes,
            file_name=file_name,
            recipient_email=user_email,
            sender_email=user_email,
            company_name=company_name,
        )
        raw_b64 = base64.urlsafe_b64encode(msg.as_bytes()).decode("ascii")
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                "https://gmail.googleapis.com/gmail/v1/users/me/messages",
                headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
                json={"raw": raw_b64, "labelIds": ["INBOX"]},
            )
            if resp.status_code >= 400:
                raise AccountingError(f"Gmail API insert error ({resp.status_code}): {resp.text[:200]}")
            data = resp.json()
            return {
                "status": "INSERTED_GMAIL_OAUTH",
                "gmail_message_id": data.get("id", ""),
                "sha256": hashlib.sha256(envelope_bytes).hexdigest(),
                "size_bytes": len(envelope_bytes),
            }


class GoogleFreeVaultClient:
    """Least-privilege OAuth2 URL builder + Google Drive (drive.file) & Opt-In Sheets adapter."""

    BASE_SCOPES = [
        "https://www.googleapis.com/auth/gmail.insert",
        "https://www.googleapis.com/auth/drive.file",
    ]
    SHEETS_SCOPE = "https://www.googleapis.com/auth/spreadsheets"

    @classmethod
    def build_oauth_authorize_url(
        cls,
        client_id: str,
        redirect_uri: str,
        include_sheets_opt_in: bool = False,
        state: str = "algorise_booksos_vault",
    ) -> Dict[str, Any]:
        if not client_id:
            raise AccountingError("Google OAuth Client ID is required")
        scopes = list(cls.BASE_SCOPES)
        if include_sheets_opt_in:
            scopes.append(cls.SHEETS_SCOPE)
        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": " ".join(scopes),
            "access_type": "offline",
            "prompt": "consent",
            "state": state,
        }
        return {
            "authorize_url": "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode(params),
            "scopes": scopes,
            "least_privilege_note": "drive.file only sees files created by Algorise BooksOS; Sheets is strictly opt-in.",
        }

    @staticmethod
    async def upload_to_google_drive(
        access_token: str,
        envelope_bytes: bytes,
        file_name: str,
        folder_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Upload encrypted ALGBK01 package to user's own Google Drive (drive.file scope)."""
        if not access_token:
            raise AccountingError("Google OAuth2 access_token is required")
        metadata: Dict[str, Any] = {"name": file_name, "mimeType": "application/octet-stream"}
        if folder_id:
            metadata["parents"] = [folder_id]

        boundary = "algorise_vault_boundary_2026"
        meta_part = (
            f"--{boundary}\r\n"
            "Content-Type: application/json; charset=UTF-8\r\n\r\n"
            + json.dumps(metadata)
            + "\r\n"
        ).encode("utf-8")
        file_part_hdr = (
            f"--{boundary}\r\n"
            "Content-Type: application/octet-stream\r\n\r\n"
        ).encode("utf-8")
        closing = f"\r\n--{boundary}--".encode("utf-8")
        multipart_body = meta_part + file_part_hdr + envelope_bytes + closing

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": f"multipart/related; boundary={boundary}",
                },
                content=multipart_body,
            )
            if resp.status_code >= 400:
                raise AccountingError(f"Google Drive upload failed ({resp.status_code}): {resp.text[:200]}")
            data = resp.json()
            return {
                "status": "UPLOADED_GOOGLE_DRIVE",
                "drive_file_id": data.get("id", ""),
                "file_name": file_name,
                "sha256": hashlib.sha256(envelope_bytes).hexdigest(),
                "size_bytes": len(envelope_bytes),
            }

    @staticmethod
    async def sync_optin_google_sheet(
        access_token: str,
        spreadsheet_id: str,
        summary_rows: List[List[Any]],
        opt_in_confirmed: bool = False,
    ) -> Dict[str, Any]:
        """Push summarized KPIs to user's Google Sheet ONLY when opt_in_confirmed=True."""
        if not opt_in_confirmed:
            raise AccountingError(
                "Google Sheets KPI Mirror is opt-in only because Sheets stores readable summaries. Set opt_in_confirmed=True to proceed."
            )
        if not access_token or not spreadsheet_id:
            raise AccountingError("access_token and spreadsheet_id are required")

        url = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/A1:append?valueInputOption=USER_ENTERED"
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(
                url,
                headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
                json={"values": summary_rows},
            )
            if resp.status_code >= 400:
                raise AccountingError(f"Google Sheets sync failed ({resp.status_code}): {resp.text[:200]}")
            return {"status": "SYNCED_OPTIN_SHEETS", "spreadsheet_id": spreadsheet_id, "rows_written": len(summary_rows)}
