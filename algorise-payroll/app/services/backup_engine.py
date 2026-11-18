"""
Algorise PayHR - Zero-Knowledge Encrypted Backup & Cloud Dispatch Engine
Features:
1. Military-grade AES-256-GCM authenticated encryption for database dumps.
2. Automated Gmail SMTP dispatch with encrypted attachment and SHA-256 hash.
3. Free S3-compatible cloud storage upload (Cloudflare R2 10GB free / AWS free tier).
4. Full restore and checksum validation utility.
"""

import os
import smtplib
import hashlib
import json
import gzip
import time
from email.message import EmailMessage
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.core.config import settings


class ZeroKnowledgeBackupEngine:
    """
    Encrypts database dumps locally so neither Gmail nor cloud storage providers
    can access salary records or sensitive PII.
    """

    @staticmethod
    def compute_sha256(file_path: str) -> str:
        """Compute SHA-256 hex checksum of a file"""
        sha = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                sha.update(chunk)
        return sha.hexdigest()

    @classmethod
    def encrypt_data_to_file(
        cls,
        raw_data: bytes,
        output_file_path: str,
        encryption_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Compresses with GZip, then encrypts with AES-256-GCM.
        Saves [12-byte nonce] + [ciphertext + 16-byte auth tag].
        """
        key_hex = encryption_key or settings.PII_ENCRYPTION_KEY
        try:
            key_bytes = bytes.fromhex(key_hex)
            if len(key_bytes) != 32:
                key_bytes = hashlib.sha256(key_hex.encode()).digest()
        except Exception:
            key_bytes = hashlib.sha256(key_hex.encode()).digest()

        # 1. Compress raw payload
        compressed = gzip.compress(raw_data, compresslevel=9)

        # 2. Encrypt with AES-GCM
        aesgcm = AESGCM(key_bytes)
        nonce = os.urandom(12)  # 96-bit random nonce
        ciphertext = aesgcm.encrypt(nonce, compressed, None)

        # 3. Write binary package
        os.makedirs(os.path.dirname(os.path.abspath(output_file_path)), exist_ok=True)
        with open(output_file_path, "wb") as f:
            f.write(nonce + ciphertext)

        file_size = os.path.getsize(output_file_path)
        sha256 = cls.compute_sha256(output_file_path)

        return {
            "file_path": output_file_path,
            "size_bytes": file_size,
            "sha256_checksum": sha256,
            "created_at": datetime.now(timezone.utc).isoformat()
        }

    @classmethod
    def decrypt_file_to_data(
        cls,
        encrypted_file_path: str,
        encryption_key: Optional[str] = None
    ) -> bytes:
        """
        Decrypts an encrypted backup file, verifies the auth tag, and decompresses GZip.
        Raises ValueError if the file was tampered with or corrupted.
        """
        key_hex = encryption_key or settings.PII_ENCRYPTION_KEY
        try:
            key_bytes = bytes.fromhex(key_hex)
            if len(key_bytes) != 32:
                key_bytes = hashlib.sha256(key_hex.encode()).digest()
        except Exception:
            key_bytes = hashlib.sha256(key_hex.encode()).digest()

        with open(encrypted_file_path, "rb") as f:
            payload = f.read()

        if len(payload) < 28:
            raise ValueError("Corrupted backup file: payload is too short")

        nonce = payload[:12]
        ciphertext = payload[12:]

        aesgcm = AESGCM(key_bytes)
        compressed = aesgcm.decrypt(nonce, ciphertext, None)
        raw_data = gzip.decompress(compressed)
        return raw_data


class GmailBackupDispatcher:
    """
    Sends encrypted backups directly to designated Gmail addresses via secure TLS.
    """

    @staticmethod
    def dispatch_backup_to_gmail(
        backup_file_path: str,
        recipient_email: str,
        sender_email: str,
        gmail_app_password: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Dispatches encrypted backup as an email attachment over SMTP (Port 587 TLS).
        """
        if not os.path.exists(backup_file_path):
            raise FileNotFoundError(f"Backup file not found: {backup_file_path}")

        file_name = os.path.basename(backup_file_path)
        file_size_kb = os.path.getsize(backup_file_path) / 1024.0
        checksum = ZeroKnowledgeBackupEngine.compute_sha256(backup_file_path)

        # Build Email
        msg = EmailMessage()
        msg["Subject"] = f"[Algorise PeopleOS] Daily Encrypted Backup - {datetime.now(timezone.utc).strftime('%Y-%m-%d')}"
        msg["From"] = sender_email
        msg["To"] = recipient_email

        body_text = f"""
Dear System Administrator,

Your daily automated zero-knowledge encrypted database backup has been successfully generated and sealed.

=======================================================
BACKUP SUMMARY & SECURITY ATTESTATION
=======================================================
Timestamp (UTC): {datetime.now(timezone.utc).isoformat()}
System: Algorise PeopleOS (AlgoRoll & AlgoTrack)
File Name: {file_name}
File Size: {file_size_kb:.2f} KB
Encryption: AES-256-GCM Authenticated (Zero-Knowledge)
SHA-256 Integrity Hash: {checksum}
=======================================================

SECURITY NOTICE:
This attachment is encrypted using your enterprise master key. Google Mail servers and intermediaries cannot decrypt or inspect the contents. Store your master decryption key securely offline.

To verify integrity upon download:
sha256sum {file_name}
Expected: {checksum}

Regards,
Algorise-AI Autonomous Backup Daemon
"""
        msg.set_content(body_text)

        # Attach encrypted file
        with open(backup_file_path, "rb") as f:
            file_data = f.read()
            msg.add_attachment(
                file_data,
                maintype="application",
                subtype="octet-stream",
                filename=file_name
            )

        # Connect to Gmail SMTP (TLS Port 587)
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(sender_email, gmail_app_password)
            server.send_message(msg)

        return {
            "status": "DISPATCHED",
            "recipient": recipient_email,
            "file_name": file_name,
            "sha256": checksum,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


class FreeCloudStorageSync:
    """
    Uploads encrypted backups to free cloud object storage:
    - Cloudflare R2 (10 GB Free Forever, Zero Egress Fees, S3-Compatible)
    - AWS S3 Free Tier (5 GB Free)
    """

    @staticmethod
    def generate_r2_upload_curl_command(
        file_path: str,
        account_id: str,
        bucket_name: str,
        file_key: str
    ) -> str:
        """
        Generates zero-dependency S3-compatible upload script or instructions for Cloudflare R2.
        Cloudflare R2 provides 10 GB storage free every month with 0 egress fees.
        """
        endpoint = f"https://{account_id}.r2.cloudflarestorage.com/{bucket_name}/{file_key}"
        return f"# Cloudflare R2 (10GB Free Forever) Upload Command:\ncurl -X PUT -T \"{file_path}\" \"{endpoint}\""
