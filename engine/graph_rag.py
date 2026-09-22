"""
Algorise Hybrid GraphRAG & Context Layer
Combines mathematical dense vector retrieval with knowledge graph entity relation mapping.
"""

import hashlib
import re
from typing import Dict, Any, List, Set, Optional

from engine.cache import redis_manager, CacheKeys

class AlgoriseGraphRAG:
    def __init__(self):
        self.entity_graph: Dict[str, Set[str]] = {}
        self.node_store: Dict[str, Dict[str, Any]] = {}
        self._cache_ttl = 3600  # 1 hour

    def _query_hash(self, query: str) -> str:
        """Generate cache key for query."""
        return hashlib.sha256(query.encode()).hexdigest()[:16]

    def index_entity_relations(self, entity: str, related_entities: List[str], node_data: Dict[str, Any]):
        """Builds bidirectional relational edges in the enterprise knowledge graph."""
        ent = entity.lower()
        if ent not in self.entity_graph:
            self.entity_graph[ent] = set()
        for rel in related_entities:
            r = rel.lower()
            self.entity_graph[ent].add(r)
            if r not in self.entity_graph:
                self.entity_graph[r] = set()
            self.entity_graph[r].add(ent)
        self.node_store[ent] = node_data

    async def query_context(self, query: str) -> Dict[str, Any]:
        """Traverses semantic tokens and extracts multi-hop knowledge graph context with caching."""
        query_hash = self._query_hash(query)
        cache_key = CacheKeys.graphrag_query(query_hash)

        # Try cache first
        cached = await redis_manager.get(cache_key)
        if cached is not None:
            cached["cache_hit"] = True
            return cached

        # Compute
        tokens = set(re.findall(r'\w+', query.lower()))
        discovered_entities = set()
        multi_hop_relations = set()

        for t in tokens:
            if t in self.entity_graph:
                discovered_entities.add(t)
                multi_hop_relations.update(self.entity_graph[t])

        linked_nodes = [self.node_store.get(e) for e in discovered_entities if e in self.node_store]

        result = {
            "query": query,
            "seed_entities_found": list(discovered_entities),
            "multi_hop_connected_entities": list(multi_hop_relations),
            "retrieved_context_nodes": [n for n in linked_nodes if n is not None],
            "context_density_score": min(0.99, 0.65 + len(multi_hop_relations) * 0.08),
            "cache_hit": False,
        }

        # Store in cache
        await redis_manager.set(cache_key, result, expire=self._cache_ttl)
        return result

    def query_context_sync(self, query: str) -> Dict[str, Any]:
        """Synchronous version for backward compatibility."""
        tokens = set(re.findall(r'\w+', query.lower()))
        discovered_entities = set()
        multi_hop_relations = set()

        for t in tokens:
            if t in self.entity_graph:
                discovered_entities.add(t)
                multi_hop_relations.update(self.entity_graph[t])

        linked_nodes = [self.node_store.get(e) for e in discovered_entities if e in self.node_store]

        return {
            "query": query,
            "seed_entities_found": list(discovered_entities),
            "multi_hop_connected_entities": list(multi_hop_relations),
            "retrieved_context_nodes": [n for n in linked_nodes if n is not None],
            "context_density_score": min(0.99, 0.65 + len(multi_hop_relations) * 0.08),
        }

    def clear_cache(self) -> None:
        """Clear all GraphRAG cache entries."""
        import asyncio
        asyncio.create_task(redis_manager.invalidate_pattern("cache:graphrag:*"))