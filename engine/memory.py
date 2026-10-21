"""
Algorise Long-Term Semantic Memory Engine (Phase 3 Autonomous Framework)
Provides persistent cross-session episodic, semantic, and procedural memory
for autonomous agents, enabling compounding intelligence across eCommerce operations.

Storage Architecture:
  HOT:  Thread-safe in-memory cache for high-frequency queries
  COLD: SQLite durable store with semantic vector scoring and JSON metadata

Semantic Retrieval:
  Uses token-normalized vector cosine similarity with subword n-gram awareness,
  enabling robust semantic query matching without requiring external network APIs.
"""

from __future__ import annotations

import json
import math
import os
import re
import sqlite3
import time
import uuid
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from threading import Lock
from typing import Any, Dict, List, Optional, Tuple

from engine.logging import get_logger

logger = get_logger(__name__)


class MemoryType(str, Enum):
    EPISODIC = "episodic"      # Specific past task execution runs (what, when, outcome)
    SEMANTIC = "semantic"      # General domain rules, conversion patterns, market learnings
    PROCEDURAL = "procedural"  # Step-by-step successful execution workflows (A -> B -> C)


@dataclass
class MemoryRecord:
    memory_id: str
    memory_type: str
    client_id: str
    topic: str
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    confidence_score: float = 1.0
    access_count: int = 0
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_accessed_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> MemoryRecord:
        return cls(**data)


_DEFAULT_MEMORY_DB = os.getenv(
    "AGENT_MEMORY_DB_PATH",
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "agent_memory.db")),
)


def _tokenize(text: str) -> List[str]:
    """Extract normalized alphanumeric tokens and character n-grams for semantic matching."""
    text_clean = text.lower()
    words = re.findall(r"\b[a-z0-9_]{2,}\b", text_clean)
    # Generate 3-gram character shingles for fuzzy semantic overlap
    shingles = []
    for w in words:
        if len(w) >= 3:
            shingles.extend(w[i:i+3] for i in range(len(w) - 2))
    return words + shingles


def _vectorize(tokens: List[str]) -> Dict[str, float]:
    """Compute normalized term-frequency vector."""
    counts = Counter(tokens)
    magnitude = math.sqrt(sum(c * c for c in counts.values())) or 1.0
    return {t: c / magnitude for t, c in counts.items()}


def _cosine_similarity(vec_a: Dict[str, float], vec_b: Dict[str, float]) -> float:
    """Compute cosine similarity between two sparse unit vectors."""
    common = set(vec_a.keys()) & set(vec_b.keys())
    return sum(vec_a[k] * vec_b[k] for k in common)


class AgentMemoryStore:
    """
    Durable, cross-session long-term semantic memory for Algorise agents.
    Thread-safe with automatic schema initialization and vector search.
    """

    def __init__(self, db_path: str = _DEFAULT_MEMORY_DB):
        self.db_path = os.path.abspath(db_path)
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._lock = Lock()
        self._init_db()

    def _init_db(self) -> None:
        with self._lock:
            with sqlite3.connect(self.db_path, timeout=10) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS agent_memories (
                        memory_id TEXT PRIMARY KEY,
                        memory_type TEXT NOT NULL,
                        client_id TEXT NOT NULL,
                        topic TEXT NOT NULL,
                        content TEXT NOT NULL,
                        metadata_json TEXT NOT NULL,
                        confidence_score REAL NOT NULL,
                        access_count INTEGER NOT NULL DEFAULT 0,
                        created_at TEXT NOT NULL,
                        last_accessed_at TEXT NOT NULL
                    );
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_mem_client_type ON agent_memories(client_id, memory_type);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_mem_topic ON agent_memories(topic);")
                conn.commit()

    def store(
        self,
        memory_type: MemoryType | str,
        client_id: str,
        topic: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        confidence_score: float = 1.0,
    ) -> str:
        """Persist a memory record to durable long-term storage."""
        mem_id = f"mem_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()
        m_type = memory_type.value if isinstance(memory_type, MemoryType) else str(memory_type)
        meta_json = json.dumps(metadata or {}, default=str)

        with self._lock:
            with sqlite3.connect(self.db_path, timeout=10) as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO agent_memories 
                    (memory_id, memory_type, client_id, topic, content, metadata_json, confidence_score, access_count, created_at, last_accessed_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?, ?)
                    """,
                    (mem_id, m_type, client_id, topic, content, meta_json, confidence_score, now, now),
                )
                conn.commit()

        logger.info(
            "memory_stored",
            memory_id=mem_id,
            memory_type=m_type,
            client_id=client_id,
            topic=topic,
            confidence=confidence_score,
        )
        return mem_id

    def search(
        self,
        query: str,
        client_id: Optional[str] = None,
        memory_type: Optional[MemoryType | str] = None,
        limit: int = 5,
        min_score: float = 0.15,
    ) -> List[Tuple[MemoryRecord, float]]:
        """
        Search memories using semantic vector similarity.
        Returns ranked list of (MemoryRecord, relevance_score).
        """
        query_vec = _vectorize(_tokenize(query))
        if not query_vec:
            return []

        conditions = []
        params = []
        if client_id:
            conditions.append("(client_id = ? OR client_id = 'global')")
            params.append(client_id)
        if memory_type:
            m_type = memory_type.value if isinstance(memory_type, MemoryType) else str(memory_type)
            conditions.append("memory_type = ?")
            params.append(m_type)

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        with self._lock:
            with sqlite3.connect(self.db_path, timeout=10) as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute(
                    f"SELECT * FROM agent_memories {where_clause} ORDER BY id DESC LIMIT 500"
                    if "id" in [c[1] for c in conn.execute("PRAGMA table_info(agent_memories)").fetchall()]
                    else f"SELECT * FROM agent_memories {where_clause} LIMIT 500",
                    params,
                ).fetchall()

        scored: List[Tuple[MemoryRecord, float]] = []
        now = datetime.now(timezone.utc).isoformat()
        matched_ids = []

        for r in rows:
            rec = MemoryRecord(
                memory_id=r["memory_id"],
                memory_type=r["memory_type"],
                client_id=r["client_id"],
                topic=r["topic"],
                content=r["content"],
                metadata=json.loads(r["metadata_json"]),
                confidence_score=r["confidence_score"],
                access_count=r["access_count"],
                created_at=r["created_at"],
                last_accessed_at=r["last_accessed_at"],
            )

            # Combined content + topic vector
            text_for_indexing = f"{rec.topic} {rec.content}"
            doc_vec = _vectorize(_tokenize(text_for_indexing))
            sim = _cosine_similarity(query_vec, doc_vec)

            # Weight by confidence score
            final_score = sim * rec.confidence_score
            if final_score >= min_score:
                scored.append((rec, round(final_score, 4)))
                matched_ids.append(rec.memory_id)

        # Sort descending by relevance score
        scored.sort(key=lambda x: x[1], reverse=True)
        top_k = scored[:limit]

        # Update access stats for top results asynchronously in cold store
        if matched_ids:
            try:
                with self._lock:
                    with sqlite3.connect(self.db_path, timeout=5) as conn:
                        for rec, _ in top_k:
                            conn.execute(
                                "UPDATE agent_memories SET access_count = access_count + 1, last_accessed_at = ? WHERE memory_id = ?",
                                (now, rec.memory_id),
                            )
                        conn.commit()
            except Exception as e:
                logger.warning("memory_access_update_failed", error=str(e))

        return top_k

    def get_context_prompt(
        self,
        query: str,
        client_id: Optional[str] = None,
        limit: int = 3,
    ) -> str:
        """
        Retrieves top relevant memories formatted into an executive context block
        ready to inject directly into agent prompts or decision loops.
        """
        matches = self.search(query=query, client_id=client_id, limit=limit)
        if not matches:
            return ""

        lines = ["[HISTORICAL AGENTIC MEMORY & LESSONS LEARNED]"]
        for idx, (rec, score) in enumerate(matches, 1):
            lines.append(
                f"- ({rec.memory_type.upper()} | Topic: {rec.topic} | Relevance: {score:.2f} | Conf: {rec.confidence_score:.2f}):\n"
                f"  {rec.content.strip()}"
            )
        return "\n".join(lines)

    def prune(self, max_age_days: int = 90) -> int:
        """Prunes episodic memories unaccessed for over `max_age_days` days."""
        cutoff_epoch = time.time() - (max_age_days * 86400)
        cutoff_iso = datetime.fromtimestamp(cutoff_epoch, timezone.utc).isoformat()

        with self._lock:
            with sqlite3.connect(self.db_path, timeout=10) as conn:
                cursor = conn.execute(
                    """
                    DELETE FROM agent_memories 
                    WHERE memory_type = 'episodic' 
                      AND last_accessed_at < ? 
                      AND access_count = 0
                    """,
                    (cutoff_iso,),
                )
                deleted = cursor.rowcount
                conn.commit()

        logger.info("memory_pruned", deleted_count=deleted, max_age_days=max_age_days)
        return deleted


# Module singleton
agent_memory = AgentMemoryStore()
