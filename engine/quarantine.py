"""
Algorise Dead-Letter Queue (DLQ) & Quarantine System
Phase 2 Hardening: Captures failed tasks, unhandled exceptions, and circuit breaker
rejections for forensic diagnosis, automated quarantine, and manual/automated replay.
"""

from __future__ import annotations

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

_DLQ_DB_PATH = os.getenv(
    "QUARANTINE_DB_PATH",
    os.path.join(os.path.dirname(__file__), "..", "data", "quarantine_dlq.db"),
)
_DLQ_DB_PATH = os.path.abspath(_DLQ_DB_PATH)


@dataclass
class DeadLetterTask:
    """Immutable record of an unexecutable or failed agent task."""
    task_id: str
    flow_id: str
    step_id: str
    bot_name: str
    client_id: str
    payload: Dict[str, Any]
    error_message: str
    error_type: str
    stack_trace: Optional[str] = None
    retry_count: int = 0
    resolved: bool = False
    resolution_notes: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DeadLetterTask":
        return cls(**data)


class DeadLetterQueue:
    """
    Durable quarantine repository for crashed or rejected multi-agent operations.
    Guarantees zero silent drops of mission-critical tasks.
    """

    def __init__(self, db_path: str = _DLQ_DB_PATH):
        self._db_path = db_path
        self._lock = Lock()
        os.makedirs(os.path.dirname(self._db_path), exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with self._lock, sqlite3.connect(self._db_path) as conn:
            conn.execute("""
            CREATE TABLE IF NOT EXISTS dead_letter_tasks (
                task_id          TEXT PRIMARY KEY,
                flow_id          TEXT NOT NULL,
                step_id          TEXT NOT NULL,
                bot_name         TEXT NOT NULL,
                client_id        TEXT NOT NULL,
                payload          TEXT NOT NULL,
                error_message    TEXT NOT NULL,
                error_type       TEXT NOT NULL,
                stack_trace      TEXT,
                retry_count      INTEGER DEFAULT 0,
                resolved         INTEGER DEFAULT 0,
                resolution_notes TEXT,
                created_at       TEXT NOT NULL
            );
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_dlq_flow ON dead_letter_tasks(flow_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_dlq_resolved ON dead_letter_tasks(resolved);")
            conn.commit()

    def quarantine(
        self,
        task_id: str,
        flow_id: str,
        step_id: str,
        bot_name: str,
        client_id: str,
        payload: Dict[str, Any],
        error: Exception | str,
        stack_trace: Optional[str] = None,
        retry_count: int = 0,
    ) -> bool:
        """Route failed task to quarantine repository."""
        error_type = type(error).__name__ if isinstance(error, Exception) else "GeneralError"
        error_msg = str(error)

        task = DeadLetterTask(
            task_id=task_id,
            flow_id=flow_id,
            step_id=step_id,
            bot_name=bot_name,
            client_id=client_id,
            payload=payload,
            error_message=error_msg,
            error_type=error_type,
            stack_trace=stack_trace,
            retry_count=retry_count,
        )

        try:
            with self._lock, sqlite3.connect(self._db_path, timeout=5) as conn:
                conn.execute("""
                INSERT OR REPLACE INTO dead_letter_tasks (
                    task_id, flow_id, step_id, bot_name, client_id, payload,
                    error_message, error_type, stack_trace, retry_count, resolved,
                    resolution_notes, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    task.task_id, task.flow_id, task.step_id, task.bot_name, task.client_id,
                    json.dumps(task.payload, default=str), task.error_message, task.error_type,
                    task.stack_trace, task.retry_count, 1 if task.resolved else 0,
                    task.resolution_notes, task.created_at
                ))
                conn.commit()

            log.warning(
                "task_quarantined_to_dlq",
                task_id=task_id,
                flow_id=flow_id,
                step_id=step_id,
                bot_name=bot_name,
                error=error_msg,
            )
            return True
        except Exception as exc:
            log.error("quarantine_write_failed", error=str(exc), task_id=task_id)
            return False

    def list_quarantined(self, unresolved_only: bool = True, limit: int = 100) -> List[Dict[str, Any]]:
        """Retrieve list of quarantined dead-letter tasks."""
        query = "SELECT * FROM dead_letter_tasks"
        if unresolved_only:
            query += " WHERE resolved = 0"
        query += " ORDER BY created_at DESC LIMIT ?"

        try:
            with self._lock, sqlite3.connect(self._db_path, timeout=5) as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute(query, (limit,)).fetchall()
                results = []
                for row in rows:
                    item = dict(row)
                    item["payload"] = json.loads(item["payload"])
                    item["resolved"] = bool(item["resolved"])
                    results.append(item)
                return results
        except Exception as exc:
            log.error("dlq_query_failed", error=str(exc))
            return []

    def resolve(self, task_id: str, notes: str = "Resolved by operator") -> bool:
        """Mark quarantined task as resolved."""
        try:
            with self._lock, sqlite3.connect(self._db_path, timeout=5) as conn:
                conn.execute(
                    "UPDATE dead_letter_tasks SET resolved = 1, resolution_notes = ? WHERE task_id = ?",
                    (notes, task_id)
                )
                conn.commit()
            log.info("task_dlq_resolved", task_id=task_id, notes=notes)
            return True
        except Exception as exc:
            log.error("dlq_resolve_failed", task_id=task_id, error=str(exc))
            return False


# Global DLQ instance
dlq = DeadLetterQueue()
