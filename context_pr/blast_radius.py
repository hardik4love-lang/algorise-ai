"""
ContextPR: Semantic Blast-Radius Analyzer
Builds reverse AST dependency graphs across a repository to compute downstream
impact and risk scores for pull request diffs.
"""

from __future__ import annotations

import ast
import os
from collections import defaultdict, deque
from typing import Dict, List, Optional, Set, Tuple

from .models import BlastRadiusNode, BlastRadiusReport, ChangedSymbol, RiskLevel


class ImportVisitor(ast.NodeVisitor):
    """Extracts all imported modules and symbols from a Python file."""

    def __init__(self):
        self.imported_modules: Set[str] = set()
        self.imported_symbols: Dict[str, List[str]] = defaultdict(list)

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            self.imported_modules.add(alias.name)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        module = node.module or ""
        self.imported_modules.add(module)
        for alias in node.names:
            self.imported_symbols[module].append(alias.name)


class BlastRadiusAnalyzer:
    """
    Constructs project-wide dependency matrices and calculates downstream impact.
    """

    CORE_COMPONENTS = {"engine", "database", "security", "auth", "api_gateway", "gateway"}

    DEFAULT_CACHE_PATH = os.path.join(".context_pr", "ast_cache.json")

    def __init__(self, root_dir: str = ".", cache_path: Optional[str] = None):
        self.root_dir = os.path.abspath(root_dir)
        self.cache_path = cache_path or os.path.join(self.root_dir, self.DEFAULT_CACHE_PATH)
        # graph[imported_file] -> list of files that import it
        self.reverse_deps: Dict[str, Set[str]] = defaultdict(set)
        # import_symbols[(consumer_file, imported_file)] -> list of symbols
        self.symbol_links: Dict[Tuple[str, str], List[str]] = defaultdict(list)
        self.cache_hits: int = 0
        self.cache_misses: int = 0
        self._build_dependency_graph()

    def _load_cache(self) -> Dict[str, dict]:
        if os.path.exists(self.cache_path):
            try:
                import json
                with open(self.cache_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _save_cache(self, cache: Dict[str, dict]) -> None:
        try:
            import json
            cache_dir = os.path.dirname(self.cache_path)
            if cache_dir and not os.path.exists(cache_dir):
                os.makedirs(cache_dir, exist_ok=True)
            with open(self.cache_path, "w", encoding="utf-8") as f:
                json.dump(cache, f, indent=2)
        except Exception:
            pass

    def _normalize_path(self, path: str) -> str:
        if not os.path.isabs(path):
            path = os.path.join(self.root_dir, path)
        rel = os.path.relpath(path, self.root_dir)
        return rel.replace("\\", "/")

    def _file_to_module(self, rel_path: str) -> str:
        mod = rel_path.replace("\\", "/")
        if mod.endswith(".py"):
            mod = mod[:-3]
        if mod.endswith("/__init__"):
            mod = mod[:-9]
        return mod.replace("/", ".")

    def _build_dependency_graph(self):
        """Scans Python files to construct the import dependency graph using incremental AST cache."""
        import hashlib
        py_files: Dict[str, str] = {}  # module_name -> relative_path
        cache = self._load_cache()
        updated_cache = {}

        for root, _, files in os.walk(self.root_dir):
            if any(part in root for part in [".git", ".pytest_cache", "node_modules", "dist", "build", "venv"]):
                continue
            for file in files:
                if file.endswith(".py"):
                    full_path = os.path.join(root, file)
                    rel_path = self._normalize_path(full_path)
                    mod_name = self._file_to_module(rel_path)
                    py_files[mod_name] = rel_path

        for mod_name, rel_path in py_files.items():
            full_path = os.path.join(self.root_dir, rel_path)
            try:
                with open(full_path, "rb") as f:
                    raw_bytes = f.read()
                file_hash = hashlib.sha256(raw_bytes).hexdigest()

                cached_entry = cache.get(rel_path)
                if cached_entry and cached_entry.get("hash") == file_hash:
                    self.cache_hits += 1
                    imported_modules = cached_entry.get("imported_modules", [])
                    imported_symbols = cached_entry.get("imported_symbols", {})
                    updated_cache[rel_path] = cached_entry
                else:
                    self.cache_misses += 1
                    content = raw_bytes.decode("utf-8", errors="ignore")
                    tree = ast.parse(content, filename=rel_path)
                    visitor = ImportVisitor()
                    visitor.visit(tree)
                    imported_modules = list(visitor.imported_modules)
                    imported_symbols = dict(visitor.imported_symbols)
                    entry = {
                        "hash": file_hash,
                        "imported_modules": imported_modules,
                        "imported_symbols": imported_symbols
                    }
                    updated_cache[rel_path] = entry

                # Link dependencies
                for imp_mod in imported_modules:
                    target_rel = py_files.get(imp_mod)
                    if not target_rel:
                        # Check package prefix
                        prefix = imp_mod.split(".")[0]
                        target_rel = py_files.get(prefix)

                    if target_rel and target_rel != rel_path:
                        self.reverse_deps[target_rel].add(rel_path)
                        symbols = imported_symbols.get(imp_mod, [])
                        if symbols:
                            self.symbol_links[(rel_path, target_rel)].extend(symbols)
            except Exception:
                continue

        self._save_cache(updated_cache)

    def compute_blast_radius(
        self,
        changed_files: List[str],
        changed_symbols: Optional[List[ChangedSymbol]] = None,
        base_ref: str = "master",
        head_ref: str = "HEAD",
    ) -> BlastRadiusReport:
        """
        Calculates transitive downstream blast radius starting from changed files.
        """
        changed_symbols = changed_symbols or []
        normalized_changed = {self._normalize_path(f) for f in changed_files}

        visited: Set[str] = set()
        impacted_nodes: List[BlastRadiusNode] = []
        queue: deque = deque([(f, 1) for f in normalized_changed])
        visited.update(normalized_changed)

        while queue:
            current_file, depth = queue.popleft()
            dependents = self.reverse_deps.get(current_file, set())

            for dep in dependents:
                if dep not in visited:
                    visited.add(dep)
                    symbols = self.symbol_links.get((dep, current_file), [])
                    impacted_nodes.append(
                        BlastRadiusNode(
                            file_path=dep,
                            direct_dependency=(depth == 1),
                            imported_symbols=symbols,
                            depth=depth,
                        )
                    )
                    queue.append((dep, depth + 1))

        # Risk Score Calculation
        breaking_count = sum(1 for s in changed_symbols if s.is_breaking)
        core_hit = any(
            any(core in f for core in self.CORE_COMPONENTS)
            for f in normalized_changed
        )

        risk_score = 0.0
        risk_reasons = []

        # 1. Base files score
        risk_score += min(3.0, len(normalized_changed) * 0.6)
        if len(normalized_changed) > 5:
            risk_reasons.append(f"Broad change surface: {len(normalized_changed)} files directly modified.")

        # 2. Downstream impact score
        risk_score += min(3.5, len(impacted_nodes) * 0.5)
        if len(impacted_nodes) > 3:
            risk_reasons.append(f"High downstream blast radius: {len(impacted_nodes)} dependent files impacted.")

        # 3. Breaking changes score
        if breaking_count > 0:
            risk_score += min(2.5, breaking_count * 1.5)
            risk_reasons.append(f"Breaking signature changes detected ({breaking_count}).")

        # 4. Core component touch
        if core_hit:
            risk_score += 1.5
            risk_reasons.append("Critical core platform/engine components touched.")

        risk_score = round(min(10.0, max(0.5, risk_score)), 2)

        if risk_score >= 8.0:
            risk_level = RiskLevel.CRITICAL
        elif risk_score >= 5.5:
            risk_level = RiskLevel.HIGH
        elif risk_score >= 2.5:
            risk_level = RiskLevel.MEDIUM
        else:
            risk_level = RiskLevel.LOW

        return BlastRadiusReport(
            base_ref=base_ref,
            head_ref=head_ref,
            risk_level=risk_level,
            risk_score=risk_score,
            total_files_changed=len(normalized_changed),
            impacted_downstream_files=impacted_nodes,
            changed_symbols=changed_symbols,
            breaking_changes_detected=breaking_count,
            high_risk_reasons=risk_reasons,
        )
