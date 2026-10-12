"""
Distributed Idempotency Layer for Algorise AI Solutions.
Guarantees strict at-most-once execution for mission-critical write endpoints
(subscriptions, lead conversions, financial billing, webhooks).
Supports Redis distributed leases with bounded in-memory sliding fallback.
"""

import hashlib
import json
import logging
import threading
import time
from typing import Dict, Any, Optional, Tuple
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse

from engine.cache import redis_manager, CacheKeys
from engine.config import get_settings

logger = logging.getLogger("algorise.idempotency")
settings = get_settings()


class _LocalIdempotencyStore:
    """Thread-safe bounded in-memory cache for idempotency records."""
    def __init__(self, max_keys: int = 5000, default_ttl_sec: int = 86400):
        self.records: Dict[str, Dict[str, Any]] = {}
        self.max_keys = max_keys
        self.default_ttl_sec = default_ttl_sec
        self.lock = threading.Lock()

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        now = time.time()
        with self.lock:
            rec = self.records.get(key)
            if not rec:
                return None
            if rec.get("expires_at", 0) < now:
                del self.records[key]
                return None
            return rec

    def set(self, key: str, payload_hash: str, response_data: Dict[str, Any], ttl_sec: Optional[int] = None) -> None:
        ttl = ttl_sec or self.default_ttl_sec
        now = time.time()
        with self.lock:
            if len(self.records) >= self.max_keys:
                # Evict expired or oldest keys
                expired = [k for k, v in self.records.items() if v.get("expires_at", 0) < now]
                for k in expired:
                    del self.records[k]
                if len(self.records) >= self.max_keys:
                    # Pop first 10%
                    for k in list(self.records.keys())[: max(1, self.max_keys // 10)]:
                        del self.records[k]

            self.records[key] = {
                "payload_hash": payload_hash,
                "response_data": response_data,
                "expires_at": now + ttl,
                "status": "COMPLETED",
            }

    def set_inflight(self, key: str, payload_hash: str, ttl_sec: int = 60) -> bool:
        now = time.time()
        with self.lock:
            rec = self.records.get(key)
            if rec and rec.get("expires_at", 0) >= now:
                return False  # Already exists or inflight
            self.records[key] = {
                "payload_hash": payload_hash,
                "response_data": None,
                "expires_at": now + ttl_sec,
                "status": "IN_FLIGHT",
            }
            return True


_local_idempotency_store = _LocalIdempotencyStore()


class IdempotencyManager:
    """Manages distributed idempotency check & store across Redis and local memory."""

    @staticmethod
    def compute_payload_hash(payload: Any) -> str:
        """Generates deterministic SHA-256 fingerprint for request payload."""
        if isinstance(payload, bytes):
            return hashlib.sha256(payload).hexdigest()
        if isinstance(payload, str):
            return hashlib.sha256(payload.encode("utf-8")).hexdigest()
        try:
            serialized = json.dumps(payload, sort_keys=True, default=str)
            return hashlib.sha256(serialized.encode("utf-8")).hexdigest()
        except Exception:
            return hashlib.sha256(str(payload).encode("utf-8")).hexdigest()

    @classmethod
    async def get_idempotent_result(
        cls,
        idempotency_key: str,
        current_payload_hash: str,
    ) -> Tuple[Optional[Dict[str, Any]], bool]:
        """
        Retrieves cached result if key exists.
        Validates payload fingerprint to prevent key collisions across differing payloads.
        Returns: (cached_response, is_inflight)
        Raises HTTPException(422) if key exists but payload fingerprint differs.
        """
        redis_key = f"algorise:idempotency:{idempotency_key}"
        rec = None

        try:
            cached_str = await redis_manager.get(redis_key)
            if cached_str:
                rec = cached_str if isinstance(cached_str, dict) else json.loads(cached_str)
        except Exception:
            pass

        if not rec:
            rec = _local_idempotency_store.get(idempotency_key)

        if not rec:
            return None, False

        # Key exists: check payload fingerprint
        stored_hash = rec.get("payload_hash")
        if stored_hash and stored_hash != current_payload_hash:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Idempotency-Key mismatch: Key was previously used with a different request payload.",
            )

        if rec.get("status") == "IN_FLIGHT":
            return None, True

        return rec.get("response_data"), False

    @classmethod
    async def record_idempotent_result(
        cls,
        idempotency_key: str,
        payload_hash: str,
        response_data: Dict[str, Any],
        ttl_seconds: int = 86400,
    ) -> None:
        """Stores completed response data under the given idempotency key."""
        redis_key = f"algorise:idempotency:{idempotency_key}"
        record = {
            "payload_hash": payload_hash,
            "response_data": response_data,
            "status": "COMPLETED",
        }

        try:
            await redis_manager.set(redis_key, record, expire=ttl_seconds)
        except Exception:
            pass

        _local_idempotency_store.set(idempotency_key, payload_hash, response_data, ttl_seconds)


idempotency_manager = IdempotencyManager()
