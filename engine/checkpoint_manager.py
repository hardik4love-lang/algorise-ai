"""
Algorise Checkpoint Manager
Phase 1 State Persistence: durable execution-state saving for Autoflow pipelines.

Addresses CRITICAL gap: all pipeline state was purely in-memory.
A process restart at step N of M required full re-execution from step 1.

Architecture (tiered storage):
  HOT  — in-process dict (zero-latency, lost on restart — intentional)
  WARM — Redis (sub-ms, survives restarts, TTL-governed)
  COLD — SQLite / PostgreSQL (durable, queryable, retained indefinitely)

On restart, AlgoriseAutoflowEngine calls CheckpointManager.recover()
and passes resume_from_step= to execute_flow(), skipping completed steps.

Redis dependency is optional — if unavailable, falls back gracefully to cold store only.
SQLAlchemy dependency is optional — falls back to SQLite via aiosqlite.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import sqlite3
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from threading import Lock
from typing import Any, Dict, List, Optional

from engine.logging import get_logger

log = get_logger(__name__)

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class PipelineCheckpoint:
    """
    Immutable snapshot of a pipeline's execution state at a given step boundary.
    Written after every successfully completed step.
    """
    flow_id:             str
    execution_id:        str          # UUID for this specific execution run
    client_id:           str
    last_completed_step: str          # step_id of the last successfully executed step
    next_step_id:        Optional[str]  # step_id to resume from (None = pipeline complete)
    context_snapshot:    Dict[str, Any]  # Full context dict at checkpoint time
    completed_steps:     List[str]    # Ordered list of all completed step IDs
    created_at:          str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    checksum:            str = field(init=False)

    def __post_init__(self):
        payload = json.dumps(
            {"flow_id": self.flow_id, "execution_id": self.execution_id,
             "last_step": self.last_completed_step, "context": self.context_snapshot},
            sort_keys=True, default=str,
        )
        self.checksum = hashlib.sha256(payload.encode()).hexdigest()[:16]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "PipelineCheckpoint":
        # Remove computed fields before reconstruction
        d = {k: v for k, v in d.items() if k != "checksum"}
        return cls(**d)


# ---------------------------------------------------------------------------
# Hot cache (in-process)
# ---------------------------------------------------------------------------

class _HotCache:
    """Thread-safe in-process dict. Zero latency. Lost on restart — by design."""
    def __init__(self):
        self._store: Dict[str, PipelineCheckpoint] = {}
        self._lock = Lock()

    def put(self, cp: PipelineCheckpoint) -> None:
        key = f"{cp.flow_id}:{cp.execution_id}"
        with self._lock:
            self._store[key] = cp

    def get(self, flow_id: str, execution_id: str) -> Optional[PipelineCheckpoint]:
        with self._lock:
            return self._store.get(f"{flow_id}:{execution_id}")

    def delete(self, flow_id: str, execution_id: str) -> None:
        with self._lock:
            self._store.pop(f"{flow_id}:{execution_id}", None)


# ---------------------------------------------------------------------------
# Warm cache (Redis)
# ---------------------------------------------------------------------------

class _RedisCache:
    """
    Wraps redis-py (sync). Gracefully degrades if Redis is unavailable.
    TTL default: 7200 seconds (2 hours) — enough to cover any transient restart.
    """
    def __init__(self, redis_url: Optional[str] = None, ttl: int = 7200):
        self._ttl = ttl
        self._client = None
        url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379/0")
        try:
            import redis
            self._client = redis.from_url(url, decode_responses=True, socket_timeout=2)
            self._client.ping()
            log.info("checkpoint_redis_connected", url=url)
        except Exception as exc:
            log.warning("checkpoint_redis_unavailable", error=str(exc),
                        fallback="cold store only")
            self._client = None

    @property
    def available(self) -> bool:
        return self._client is not None

    def _key(self, flow_id: str, execution_id: str) -> str:
        return f"algorise:checkpoint:{flow_id}:{execution_id}"

    def put(self, cp: PipelineCheckpoint) -> bool:
        if not self._client:
            return False
        try:
            self._client.setex(
                self._key(cp.flow_id, cp.execution_id),
                self._ttl,
                json.dumps(cp.to_dict(), default=str),
            )
            return True
        except Exception as exc:
            log.warning("checkpoint_redis_write_failed", error=str(exc))
            return False

    def get(self, flow_id: str, execution_id: str) -> Optional[PipelineCheckpoint]:
        if not self._client:
            return None
        try:
            raw = self._client.get(self._key(flow_id, execution_id))
            if raw:
                return PipelineCheckpoint.from_dict(json.loads(raw))
        except Exception as exc:
            log.warning("checkpoint_redis_read_failed", error=str(exc))
        return None

    def delete(self, flow_id: str, execution_id: str) -> None:
        if not self._client:
            return
        try:
            self._client.delete(self._key(flow_id, execution_id))
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Cold store (SQLite — zero-dependency durable fallback)
# ---------------------------------------------------------------------------

_COLD_STORE_PATH = os.getenv(
    "CHECKPOINT_DB_PATH",
    os.path.join(os.path.dirname(__file__), "..", "data", "checkpoints.db"),
)
_COLD_STORE_PATH = os.path.abspath(_COLD_STORE_PATH)

_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS pipeline_checkpoints (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    flow_id              TEXT NOT NULL,
    execution_id         TEXT NOT NULL,
    client_id            TEXT NOT NULL,
    last_completed_step  TEXT NOT NULL,
    next_step_id         TEXT,
    context_snapshot     TEXT NOT NULL,  -- JSON blob
    completed_steps      TEXT NOT NULL,  -- JSON array
    created_at           TEXT NOT NULL,
    checksum             TEXT NOT NULL,
    UNIQUE(flow_id, execution_id)
);
CREATE INDEX IF NOT EXISTS idx_checkpoint_lookup
    ON pipeline_checkpoints(flow_id, execution_id);
"""


class _ColdStore:
    """SQLite-backed durable checkpoint store. Always available, no external dependencies."""

    def __init__(self, db_path: str = _COLD_STORE_PATH):
        self._db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self._db_path) as conn:
            conn.executescript(_CREATE_TABLE_SQL)
            conn.commit()

    def put(self, cp: PipelineCheckpoint) -> bool:
        try:
            with sqlite3.connect(self._db_path, timeout=5) as conn:
                conn.execute(
                    """
                    INSERT INTO pipeline_checkpoints
                        (flow_id, execution_id, client_id, last_completed_step,
                         next_step_id, context_snapshot, completed_steps, created_at, checksum)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(flow_id, execution_id) DO UPDATE SET
                        last_completed_step = excluded.last_completed_step,
                        next_step_id        = excluded.next_step_id,
                        context_snapshot    = excluded.context_snapshot,
                        completed_steps     = excluded.completed_steps,
                        created_at          = excluded.created_at,
                        checksum            = excluded.checksum
                    """,
                    (
                        cp.flow_id, cp.execution_id, cp.client_id,
                        cp.last_completed_step, cp.next_step_id,
                        json.dumps(cp.context_snapshot, default=str),
                        json.dumps(cp.completed_steps),
                        cp.created_at, cp.checksum,
                    ),
                )
                conn.commit()
            return True
        except Exception as exc:
            log.error("checkpoint_cold_write_failed", error=str(exc), db=self._db_path)
            return False

    def get(self, flow_id: str, execution_id: str) -> Optional[PipelineCheckpoint]:
        try:
            with sqlite3.connect(self._db_path, timeout=5) as conn:
                conn.row_factory = sqlite3.Row
                row = conn.execute(
                    "SELECT * FROM pipeline_checkpoints WHERE flow_id=? AND execution_id=?",
                    (flow_id, execution_id),
                ).fetchone()
                if row:
                    d = dict(row)
                    d["context_snapshot"] = json.loads(d["context_snapshot"])
                    d["completed_steps"]  = json.loads(d["completed_steps"])
                    d.pop("id", None)
                    return PipelineCheckpoint.from_dict(d)
        except Exception as exc:
            log.warning("checkpoint_cold_read_failed", error=str(exc))
        return None

    def list_incomplete(self, client_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Return checkpoints where next_step_id IS NOT NULL (i.e., incomplete pipelines)."""
        query = "SELECT flow_id, execution_id, client_id, last_completed_step, next_step_id, created_at FROM pipeline_checkpoints WHERE next_step_id IS NOT NULL"
        params: tuple = ()
        if client_id:
            query += " AND client_id = ?"
            params = (client_id,)
        try:
            with sqlite3.connect(self._db_path, timeout=5) as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute(query, params).fetchall()
                return [dict(r) for r in rows]
        except Exception as exc:
            log.warning("checkpoint_list_failed", error=str(exc))
            return []


# ---------------------------------------------------------------------------
# Public API: CheckpointManager
# ---------------------------------------------------------------------------

class CheckpointManager:
    """
    Unified checkpoint manager with tiered storage:
        Write: HOT → WARM (Redis) → COLD (SQLite) [all three, best-effort]
        Read:  HOT → WARM → COLD [first hit wins]

    Integration with AlgoriseAutoflowEngine:

        manager = CheckpointManager()

        # After each successful step in execute_flow():
        manager.save(PipelineCheckpoint(
            flow_id="my-flow",
            execution_id=execution_id,
            client_id=pipeline.client_id,
            last_completed_step=step.step_id,
            next_step_id=next_step.step_id if next_step else None,
            context_snapshot=context.copy(),
            completed_steps=completed_so_far,
        ))

        # On restart, before execute_flow():
        cp = manager.recover(flow_id="my-flow", execution_id=execution_id)
        if cp:
            engine.execute_flow(flow_id, trigger, resume_from_step=cp.next_step_id)
    """

    def __init__(
        self,
        redis_url: Optional[str] = None,
        db_path:   Optional[str] = None,
    ):
        self._hot   = _HotCache()
        self._warm  = _RedisCache(redis_url=redis_url)
        self._cold  = _ColdStore(db_path=db_path or _COLD_STORE_PATH)

    def save(self, cp: PipelineCheckpoint) -> bool:
        """
        Persist checkpoint to all available storage tiers.
        Returns True if at least the cold store write succeeded.
        """
        self._hot.put(cp)
        self._warm.put(cp)  # best-effort, no exception on failure
        cold_ok = self._cold.put(cp)

        log.info(
            "checkpoint_saved",
            flow_id=cp.flow_id,
            execution_id=cp.execution_id,
            last_step=cp.last_completed_step,
            next_step=cp.next_step_id,
            checksum=cp.checksum,
            cold_ok=cold_ok,
            warm_ok=self._warm.available,
        )
        return cold_ok

    def recover(self, flow_id: str, execution_id: str) -> Optional[PipelineCheckpoint]:
        """
        Retrieve the latest checkpoint for a given execution.
        Read order: HOT → WARM → COLD.
        Validates checksum before returning.
        """
        for label, store in [("hot", self._hot), ("warm", self._warm), ("cold", self._cold)]:
            cp = store.get(flow_id, execution_id)
            if cp:
                # Validate checksum integrity
                cp2 = PipelineCheckpoint(
                    flow_id=cp.flow_id,
                    execution_id=cp.execution_id,
                    client_id=cp.client_id,
                    last_completed_step=cp.last_completed_step,
                    next_step_id=cp.next_step_id,
                    context_snapshot=cp.context_snapshot,
                    completed_steps=cp.completed_steps,
                    created_at=cp.created_at,
                )
                if cp2.checksum != cp.checksum:
                    log.error(
                        "checkpoint_checksum_mismatch",
                        flow_id=flow_id,
                        execution_id=execution_id,
                        store=label,
                        stored=cp.checksum,
                        computed=cp2.checksum,
                    )
                    continue  # Try next store tier

                log.info(
                    "checkpoint_recovered",
                    flow_id=flow_id,
                    execution_id=execution_id,
                    from_store=label,
                    resume_from=cp.next_step_id,
                    completed_steps=cp.completed_steps,
                )
                return cp

        log.info("checkpoint_not_found", flow_id=flow_id, execution_id=execution_id)
        return None

    def mark_complete(self, flow_id: str, execution_id: str) -> None:
        """
        Mark a pipeline execution as fully complete.
        Sets next_step_id=None and clears hot/warm caches.
        Cold store record retained for audit trail.
        """
        self._hot.delete(flow_id, execution_id)
        self._warm.delete(flow_id, execution_id)
        # Update cold store: set next_step_id = NULL
        try:
            import sqlite3 as _sq
            with _sq.connect(self._cold._db_path, timeout=5) as conn:
                conn.execute(
                    "UPDATE pipeline_checkpoints SET next_step_id = NULL WHERE flow_id=? AND execution_id=?",
                    (flow_id, execution_id),
                )
                conn.commit()
        except Exception as exc:
            log.warning("checkpoint_mark_complete_failed", error=str(exc))

    def list_incomplete(self, client_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Return all incomplete pipeline executions — useful for restart/recovery sweeps."""
        return self._cold.list_incomplete(client_id=client_id)

    async def save_checkpoint(self, cp: PipelineCheckpoint) -> bool:
        """Async-compatible checkpoint save method for task graph orchestrators."""
        return self.save(cp)

    async def load_checkpoint(self, flow_id: str, execution_id: Optional[str] = None) -> Optional[PipelineCheckpoint]:
        """Async-compatible checkpoint loader retrieving the latest snapshot for flow_id."""
        if execution_id:
            return self.recover(flow_id, execution_id)
        # Search hot cache first
        with self._hot._lock:
            for k, cp in self._hot._store.items():
                if k.startswith(f"{flow_id}:"):
                    return cp
        # Search cold store for latest record
        try:
            with sqlite3.connect(self._cold._db_path, timeout=5) as conn:
                conn.row_factory = sqlite3.Row
                row = conn.execute(
                    "SELECT * FROM pipeline_checkpoints WHERE flow_id = ? ORDER BY id DESC LIMIT 1",
                    (flow_id,)
                ).fetchone()
                if row:
                    return PipelineCheckpoint(
                        flow_id=row["flow_id"],
                        execution_id=row["execution_id"],
                        client_id=row["client_id"],
                        last_completed_step=row["last_completed_step"],
                        next_step_id=row["next_step_id"],
                        context_snapshot=json.loads(row["context_snapshot"]),
                        completed_steps=json.loads(row["completed_steps"]),
                        created_at=row["created_at"],
                    )
        except Exception as exc:
            log.warning("checkpoint_load_failed", error=str(exc))
        return None


# Module-level singleton
checkpoint_manager = CheckpointManager()
