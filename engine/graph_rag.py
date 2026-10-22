"""
Algorise Hybrid GraphRAG & Context Layer
Combines mathematical dense vector retrieval with knowledge graph entity relation mapping.
Provides multi-hop entity traversal, semantic vector similarity, and grounded factual context generation.
"""

from __future__ import annotations

import hashlib
import math
import re
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from engine.cache import redis_manager, CacheKeys


@dataclass
class GraphNode:
    id: str
    node_type: str  # PRODUCT, FABRIC, CATEGORY, SIZE, OCCASION, PRICE, POLICY, MERCHANT
    name: str
    attributes: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GraphEdge:
    source_id: str
    target_id: str
    relation: str  # BELONGS_TO, HAS_FABRIC, AVAILABLE_IN, SUITED_FOR, PRICED_AT, GOVERNED_BY
    weight: float = 1.0


class AlgoriseGraphRAG:
    """Enterprise Hybrid GraphRAG combining Knowledge Graph traversal and Semantic Vector retrieval."""

    def __init__(self):
        self.nodes: Dict[str, GraphNode] = {}
        self.adjacency: Dict[str, List[GraphEdge]] = defaultdict(list)
        self.reverse_adjacency: Dict[str, List[GraphEdge]] = defaultdict(list)
        self.entity_graph: Dict[str, Set[str]] = defaultdict(set)
        self.node_store: Dict[str, Dict[str, Any]] = {}
        self.doc_vectors: Dict[str, Dict[str, float]] = {}
        self._cache_ttl = 3600  # 1 hour
        self._seed_default_ontology()

    def _seed_default_ontology(self):
        """Populate the foundational commerce ontology and the merchant node.

        The merchant node is loaded from the client configuration rather
        than hardcoded, so the knowledge graph describes the client that
        is actually being served.
        """
        # 1. Merchant node, from the client configuration.
        merchant_node_id = "merchant_default"
        merchant_name = "Our Store"
        merchant_props = {
            "location": "India",
            "currency": "INR",
        }
        try:
            from engine.client_agent_ops import load_client_config

            config = load_client_config("client_srt_shruhi")
            settings = config.get("settings", {}) or {}
            rules = settings.get("agent_rules", {}) or {}
            merchant_node_id = f"merchant_{config.get('client_id', 'default')}"
            merchant_name = (config.get("name") or "Our Store").split("(")[0].strip()
            domain = (settings.get("domain") or "").replace("https://", "").rstrip("/")
            if domain:
                merchant_props["domain"] = domain
            if config.get("phone"):
                merchant_props["whatsapp"] = config["phone"]
            if rules.get("sector"):
                merchant_props["sector"] = rules["sector"]
        except Exception:
            # The ontology is still useful without a merchant node.
            pass

        self.add_node(merchant_node_id, "MERCHANT", merchant_name, merchant_props)
        self._merchant_node_id = merchant_node_id

        # 2. Categories
        categories = [
            ("cat_suit", "3-Piece Suit Set"),
            ("cat_coord", "Festive Co-ord Set"),
            ("cat_tunic", "Artisan Tunic & Midi Dress"),
            ("cat_plussize", "Curvy Couture Plus-Size"),
        ]
        for cid, cname in categories:
            self.add_node(cid, "CATEGORY", cname)
            self.add_edge(merchant_node_id, cid, "OFFERS_CATEGORY")


        # 3. Fabrics
        fabrics = [
            ("fab_silk", "Pure Roman Silk & Festive Silk Blend"),
            ("fab_organza", "Luxury Organza"),
            ("fab_bandhani", "Traditional Bandhani & Patola"),
            ("fab_chanderi", "Festive Chanderi & Zari"),
            ("fab_cotton", "Pure Breathable Cotton"),
        ]
        for fid, fname in fabrics:
            self.add_node(fid, "FABRIC", fname)

        # 4. Sizes
        sizes = ["S", "M", "L", "XL", "2XL", "3XL", "4XL", "5XL", "6XL"]
        for sz in sizes:
            self.add_node(f"sz_{sz.lower()}", "SIZE", f"Size {sz}")

        # 5. Core Catalog Products
        products = [
            {
                "id": "prod_tejal",
                "name": "TEJAL 3-Piece Heavy Designer Suit",
                "price": "₹2,850",
                "price_val": 2850,
                "cat": "cat_suit",
                "fab": "fab_silk",
                "sizes": ["M", "L", "XL", "2XL", "3XL", "4XL", "5XL", "6XL"],
                "occasion": "Wedding & Heavy Festive",
            },
            {
                "id": "prod_b2876",
                "name": "B-2876 Curvy Plus-Size Festive Edition",
                "price": "₹2,650",
                "price_val": 2650,
                "cat": "cat_plussize",
                "fab": "fab_silk",
                "sizes": ["3XL", "4XL", "5XL", "6XL"],
                "occasion": "Family Functions & Festive Curvy Couture",
            },
            {
                "id": "prod_kavya",
                "name": "KAVYA Royal Bandhani & Zari Couture",
                "price": "₹2,950 – ₹3,250",
                "price_val": 3100,
                "cat": "cat_suit",
                "fab": "fab_bandhani",
                "sizes": ["M", "L", "XL", "2XL", "3XL", "4XL", "5XL", "6XL"],
                "occasion": "Heritage Weddings & Traditional Celebrations",
            },
            {
                "id": "prod_galaxy",
                "name": "GALAXY Festive Silk Co-ord & Banarasi Set",
                "price": "₹2,450 – ₹2,850",
                "price_val": 2650,
                "cat": "cat_coord",
                "fab": "fab_silk",
                "sizes": ["S", "M", "L", "XL", "2XL", "3XL", "4XL", "5XL"],
                "occasion": "Sangeet, Cocktail & Contemporary Ethnic",
            },
            {
                "id": "prod_dno1042",
                "name": "D.NO 1042 Everyday Chic Cotton Tunic & Set",
                "price": "₹850 – ₹1,550",
                "price_val": 1200,
                "cat": "cat_tunic",
                "fab": "fab_cotton",
                "sizes": ["S", "M", "L", "XL", "2XL", "3XL", "4XL"],
                "occasion": "Daily Wear & Semi-Formal",
            },
            {
                "id": "prod_glory",
                "name": "GLORY Luxury Organza & Silk Ensemble",
                "price": "₹2,750",
                "price_val": 2750,
                "cat": "cat_suit",
                "fab": "fab_organza",
                "sizes": ["M", "L", "XL", "2XL", "3XL", "4XL", "5XL"],
                "occasion": "Reception & High-Tea Festive",
            },
        ]

        for p in products:
            pid = p["id"]
            self.add_node(pid, "PRODUCT", p["name"], {
                "price": p["price"],
                "price_numeric": p["price_val"],
                "occasion": p["occasion"],
            })
            self.add_edge(pid, p["cat"], "BELONGS_TO")
            self.add_edge(pid, p["fab"], "HAS_FABRIC")
            for sz in p["sizes"]:
                self.add_edge(pid, f"sz_{sz.lower()}", "AVAILABLE_IN")
            # Index document vector
            doc_text = f"{p['name']} {p['price']} {p['occasion']} {p['cat']} {p['fab']} {' '.join(p['sizes'])}"
            self.index_vector(pid, doc_text)

        # 6. Policies
        policies = [
            ("pol_delivery", "POLICY", "Pan-India Express & Worldwide Shipping", {"dispatch": "24-48 hours", "carrier": "BlueDart/Delhivery/DHL"}),
            ("pol_attribution", "POLICY", "Closed-Loop WhatsApp Attribution", {"tracking": "Deterministic #AG Hash Codes"}),
            ("pol_meta_tax", "POLICY", "Zero Markup Meta Conversation Billing", {"tax": "0% markup", "rate": "Meta India card"}),
        ]
        for pol_id, ptype, pname, pattrs in policies:
            self.add_node(pol_id, ptype, pname, pattrs)
            self.add_edge(self._merchant_node_id, pol_id, "GOVERNED_BY")
            self.index_vector(pol_id, f"{pname} {str(pattrs)}")

    def add_node(self, node_id: str, node_type: str, name: str, attributes: Optional[Dict[str, Any]] = None):
        """Adds a verified entity node to the knowledge graph."""
        nid = node_id.lower()
        self.nodes[nid] = GraphNode(id=nid, node_type=node_type, name=name, attributes=attributes or {})

    def add_edge(self, source_id: str, target_id: str, relation: str, weight: float = 1.0):
        """Adds a directed relational edge to the knowledge graph."""
        sid, tid = source_id.lower(), target_id.lower()
        edge = GraphEdge(source_id=sid, target_id=tid, relation=relation, weight=weight)
        self.adjacency[sid].append(edge)
        rev_edge = GraphEdge(source_id=tid, target_id=sid, relation=f"REV_{relation}", weight=weight)
        self.reverse_adjacency[tid].append(rev_edge)

    def index_entity_relations(self, entity: str, related_entities: List[str], node_data: Optional[Dict[str, Any]] = None):
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
            self.add_node(r, "ENTITY", rel)
            self.add_edge(ent, r, "RELATED_TO")
        self.node_store[ent] = node_data or {}
        self.add_node(ent, "ENTITY", entity, node_data or {})
        self.index_vector(ent, f"{entity} {' '.join(related_entities)} {str(node_data or {})}")

    def _tokenize(self, text: str) -> List[str]:
        return [w for w in re.findall(r"\w+", text.lower()) if len(w) > 1]

    def index_vector(self, doc_id: str, text: str):
        """Compute term frequency vector for dense semantic scoring."""
        tokens = self._tokenize(text)
        if not tokens:
            return
        tf = defaultdict(float)
        for t in tokens:
            tf[t] += 1.0
        # Normalize
        norm = math.sqrt(sum(v * v for v in tf.values())) or 1.0
        self.doc_vectors[doc_id.lower()] = {k: v / norm for k, v in tf.items()}

    def _cosine_similarity(self, query_vec: Dict[str, float], doc_vec: Dict[str, float]) -> float:
        dot_product = sum(query_vec[k] * doc_vec[k] for k in query_vec if k in doc_vec)
        return max(0.0, min(1.0, dot_product))

    def _query_hash(self, query: str) -> str:
        return hashlib.sha256(query.encode()).hexdigest()[:16]

    def multi_hop_traversal(
        self,
        seed_node_ids: List[str],
        max_hops: int = 2,
        decay: float = 0.7,
    ) -> Tuple[Dict[str, float], List[Dict[str, Any]]]:
        """
        Traverses semantic multi-hop relations using breadth-first search with attenuation.
        Returns: (node_scores, traversal_paths)
        """
        visited: Dict[str, float] = {}
        paths: List[Dict[str, Any]] = []
        queue = deque([(nid.lower(), 1.0, 0, [nid.lower()]) for nid in seed_node_ids if nid.lower() in self.nodes])

        for nid in seed_node_ids:
            if nid.lower() in self.nodes:
                visited[nid.lower()] = 1.0

        while queue:
            curr_id, curr_score, hops, path = queue.popleft()
            if hops >= max_hops:
                continue

            # Check outbound and inbound edges
            all_edges = self.adjacency.get(curr_id, []) + self.reverse_adjacency.get(curr_id, [])
            for edge in all_edges:
                neighbor = edge.target_id if edge.source_id == curr_id else edge.source_id
                next_score = curr_score * edge.weight * decay
                if neighbor not in visited or next_score > visited[neighbor]:
                    visited[neighbor] = next_score
                    new_path = path + [edge.relation, neighbor]
                    paths.append({
                        "from": curr_id,
                        "to": neighbor,
                        "relation": edge.relation,
                        "hop": hops + 1,
                        "path": new_path,
                    })
                    queue.append((neighbor, next_score, hops + 1, new_path))

        return visited, paths

    async def query_context(self, query: str, top_k: int = 5) -> Dict[str, Any]:
        """
        Hybrid GraphRAG retrieval:
        Combines multi-hop knowledge graph traversal with dense semantic vector scoring.
        """
        query_hash = self._query_hash(query)
        cache_key = CacheKeys.graphrag_query(query_hash)

        # Check Redis Cache if available
        try:
            cached = await redis_manager.get(cache_key)
            if cached is not None:
                cached["cache_hit"] = True
                return cached
        except Exception:
            pass

        res = self.query_context_sync(query, top_k=top_k)
        try:
            await redis_manager.set(cache_key, res, expire=self._cache_ttl)
        except Exception:
            pass
        return res

    def query_context_sync(self, query: str, top_k: int = 5) -> Dict[str, Any]:
        """Synchronous version for execution engines and offline benchmarking."""
        query_tokens = self._tokenize(query)
        if not query_tokens:
            return {
                "query": query,
                "matched_entities": [],
                "grounded_context": "No valid search terms provided.",
                "confidence_score": 0.0,
                "cache_hit": False,
            }

        # 1. Vectorize query
        q_tf = defaultdict(float)
        for t in query_tokens:
            q_tf[t] += 1.0
        q_norm = math.sqrt(sum(v * v for v in q_tf.values())) or 1.0
        q_vec = {k: v / q_norm for k, v in q_tf.items()}

        # 2. Find Seed Entities in Graph
        seed_nodes = set()
        for nid, node in self.nodes.items():
            name_tokens = set(self._tokenize(node.name))
            if any(t in name_tokens or t in nid for t in query_tokens):
                seed_nodes.add(nid)

        # Also check specific keywords
        query_lower = query.lower()
        for sz in ["s", "m", "l", "xl", "2xl", "3xl", "4xl", "5xl", "6xl"]:
            if f"size {sz}" in query_lower or f"{sz} size" in query_lower or f" {sz} " in f" {query_lower} ":
                seed_nodes.add(f"sz_{sz}")
        if "plus" in query_lower or "curvy" in query_lower or "b-2876" in query_lower or "2876" in query_lower:
            seed_nodes.add("cat_plussize")
            seed_nodes.add("prod_b2876")
        if "suit" in query_lower:
            seed_nodes.add("cat_suit")
        if "silk" in query_lower:
            seed_nodes.add("fab_silk")
        if "bandhani" in query_lower or "patola" in query_lower:
            seed_nodes.add("fab_bandhani")

        # 3. Multi-Hop Graph Traversal
        graph_scores, paths = self.multi_hop_traversal(list(seed_nodes), max_hops=2)

        # 4. Dense Vector Similarity Scoring
        vector_scores: Dict[str, float] = {}
        for doc_id, doc_vec in self.doc_vectors.items():
            vector_scores[doc_id] = self._cosine_similarity(q_vec, doc_vec)

        # 5. Hybrid Fusion Scoring: score = 0.5 * vector + 0.5 * graph
        all_candidate_ids = set(self.nodes.keys())
        scored_candidates: List[Tuple[str, float, float, float]] = []

        for cid in all_candidate_ids:
            g_score = graph_scores.get(cid, 0.0)
            v_score = vector_scores.get(cid, 0.0)
            # If it's a seed node or high vector score
            if g_score > 0.0 or v_score > 0.0:
                hybrid = (0.5 * v_score) + (0.5 * g_score)
                scored_candidates.append((cid, hybrid, v_score, g_score))

        scored_candidates.sort(key=lambda x: x[1], reverse=True)
        top_candidates = scored_candidates[:top_k]

        # 6. Build Grounded Context Representation
        retrieved_nodes = []
        context_lines = []
        for cid, h_score, v_score, g_score in top_candidates:
            node = self.nodes.get(cid)
            if not node:
                continue
            retrieved_nodes.append({
                "id": node.id,
                "type": node.node_type,
                "name": node.name,
                "attributes": node.attributes,
                "hybrid_score": round(h_score, 4),
                "semantic_vector_score": round(v_score, 4),
                "graph_traversal_score": round(g_score, 4),
            })
            attr_str = ", ".join(f"{k}: {v}" for k, v in node.attributes.items())
            context_lines.append(f"[{node.node_type}] {node.name}" + (f" ({attr_str})" if attr_str else ""))

        # 7. Multi-hop connected entities collection (Graph & Entity Store)
        multi_hop_entities = set()
        for p in paths:
            if p.get("to"):
                multi_hop_entities.add(p["to"])
        for sn in seed_nodes:
            if sn in self.entity_graph:
                multi_hop_entities.update(self.entity_graph[sn])
                for neighbor in self.entity_graph[sn]:
                    if neighbor in self.entity_graph:
                        multi_hop_entities.update(self.entity_graph[neighbor])

        confidence = round(min(0.99, max(0.55, sum(c[1] for c in top_candidates[:3]) / max(1, len(top_candidates[:3])))), 4) if top_candidates else 0.0
        density_score = round(max(confidence, min(0.99, 0.65 + len(multi_hop_entities) * 0.08)), 4) if (multi_hop_entities or top_candidates) else 0.0

        return {
            "query": query,
            "seed_entities_found": list(seed_nodes),
            "multi_hop_connected_entities": list(multi_hop_entities),
            "multi_hop_traversal_paths": paths[:10],
            "retrieved_context_nodes": retrieved_nodes,
            "grounded_context": "\n".join(context_lines) if context_lines else "No direct entity links found in knowledge graph.",
            "confidence_score": confidence,
            "context_density_score": density_score,
            "cache_hit": False,
        }

    def clear_cache(self) -> None:
        """Clear all GraphRAG cache entries."""
        import asyncio
        asyncio.create_task(redis_manager.invalidate_pattern("cache:graphrag:*"))


graph_rag = AlgoriseGraphRAG()