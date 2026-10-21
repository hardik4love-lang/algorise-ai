"""
T3.1: Incremental Symbol-Level Graph with SQLite Index
Enhanced BlastRadiusAnalyzer with SQLite-backed persistent index for monorepo-scale support.
"""

import ast
import os
import sqlite3
import hashlib
import json
import threading
from collections import defaultdict, deque
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass
from contextlib import contextmanager

from .models import BlastRadiusNode, BlastRadiusReport, ChangedSymbol, RiskLevel


class SymbolVisitor(ast.NodeVisitor):
    """Extracts all imported modules, symbols, and defined symbols from a Python file."""
    
    def __init__(self):
        self.imported_modules: Set[str] = set()
        self.imported_symbols: Dict[str, List[str]] = defaultdict(list)
        self.defined_symbols: Dict[str, List[str]] = defaultdict(list)  # symbol -> [lines]
        self.function_defs: List[Dict] = []
        self.class_defs: List[Dict] = []
        
    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            self.imported_modules.add(alias.name)
            
    def visit_ImportFrom(self, node: ast.ImportFrom):
        module = node.module or ""
        self.imported_modules.add(module)
        for alias in node.names:
            self.imported_symbols[module].append(alias.name)
            
    def visit_FunctionDef(self, node: ast.FunctionDef):
        self.defined_symbols[node.name].append(node.lineno)
        self.function_defs.append({
            "name": node.name,
            "lineno": node.lineno,
            "args": [arg.arg for arg in node.args.args],
            "returns": ast.unparse(node.returns) if node.returns else None,
        })
        self.generic_visit(node)
        
    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self.visit_FunctionDef(node)
        
    def visit_ClassDef(self, node: ast.ClassDef):
        self.defined_symbols[node.name].append(node.lineno)
        self.class_defs.append({
            "name": node.name,
            "lineno": node.lineno,
            "bases": [ast.unparse(b) for b in node.bases],
        })
        self.generic_visit(node)


@dataclass
class SymbolInfo:
    """Symbol-level dependency information."""
    symbol_name: str
    source_file: str
    target_file: str
    import_type: str  # "import", "from_import"
    line_number: int


class SQLiteASTIndex:
    """SQLite-backed persistent AST index for symbol-level dependency tracking."""
    
    SCHEMA = """
    CREATE TABLE IF NOT EXISTS file_index (
        file_path TEXT PRIMARY KEY,
        file_hash TEXT NOT NULL,
        module_name TEXT,
        last_modified REAL,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    
    CREATE TABLE IF NOT EXISTS symbol_index (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol_name TEXT NOT NULL,
        file_path TEXT NOT NULL,
        line_number INTEGER,
        symbol_type TEXT,  -- 'function', 'class', 'import', 'defined'
        import_type TEXT,  -- 'import', 'from_import'
        source_module TEXT,
        FOREIGN KEY (file_path) REFERENCES file_index(file_path)
    );
    
    CREATE TABLE IF NOT EXISTS dependency_edges (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        consumer_file TEXT NOT NULL,
        provider_file TEXT NOT NULL,
        symbol_name TEXT,
        import_type TEXT,
        FOREIGN KEY (consumer_file) REFERENCES file_index(file_path),
        FOREIGN KEY (provider_file) REFERENCES file_index(file_path)
    );
    
    CREATE INDEX IF NOT EXISTS idx_symbol_name ON symbol_index(symbol_name);
    CREATE INDEX IF NOT EXISTS idx_symbol_file ON symbol_index(file_path);
    CREATE INDEX IF NOT EXISTS idx_dep_consumer ON dependency_edges(consumer_file);
    CREATE INDEX IF NOT EXISTS idx_dep_provider ON dependency_edges(provider_file);
    """
    
    def __init__(self, db_path: str, root_dir: str = None):
        self.db_path = db_path
        self.root_dir = root_dir or os.getcwd()
        self._init_db()
        
    def _init_db(self):
        """Initialize database schema."""
        with self._get_conn() as conn:
            conn.executescript(self.SCHEMA)
            
    @contextmanager
    def _get_conn(self):
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
            
    def get_file_hash(self, file_path: str) -> Optional[str]:
        """Get stored hash for a file."""
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT file_hash FROM file_index WHERE file_path = ?", 
                (file_path,)
            ).fetchone()
            return row[0] if row else None
            
    def get_file_symbols(self, file_path: str) -> List[Dict]:
        """Get all symbols defined in a file."""
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM symbol_index WHERE file_path = ? AND symbol_type = 'defined'",
                (file_path,)
            ).fetchall()
            return [dict(r) for r in rows]
            
    def get_file_imports(self, file_path: str) -> List[Dict]:
        """Get all imports in a file."""
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM symbol_index WHERE file_path = ? AND symbol_type IN ('import', 'from_import')",
                (file_path,)
            ).fetchall()
            return [dict(r) for r in rows]
            
    def get_dependents(self, file_path: str) -> List[str]:
        """Get files that depend on this file (reverse dependencies)."""
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT DISTINCT consumer_file FROM dependency_edges WHERE provider_file = ?",
                (file_path,)
            ).fetchall()
            return [r[0] for r in rows]
            
    def get_dependencies(self, file_path: str) -> List[Dict]:
        """Get files this file depends on."""
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT provider_file, symbol_name, import_type FROM dependency_edges WHERE consumer_file = ?",
                (file_path,)
            ).fetchall()
            return [dict(r) for r in rows]
            
    def upsert_file(self, file_path: str, file_hash: str, module_name: str, 
                    symbols: List[Dict], imports: List[Dict]):
        """Upsert file with its symbols and imports in a transaction."""
        with self._get_conn() as conn:
            # Update file index
            conn.execute(
                """INSERT OR REPLACE INTO file_index 
                   (file_path, file_hash, module_name, last_modified) 
                   VALUES (?, ?, ?, ?)""",
                (file_path, file_hash, module_name, os.path.getmtime(file_path) if os.path.exists(file_path) else 0)
            )
            
            # Clear old symbols and imports for this file
            conn.execute("DELETE FROM symbol_index WHERE file_path = ?", (file_path,))
            conn.execute("DELETE FROM dependency_edges WHERE consumer_file = ? OR provider_file = ?", 
                        (file_path, file_path))
            
            # Insert defined symbols
            for sym in symbols:
                if sym.get("type") == "defined":
                    conn.execute(
                        """INSERT INTO symbol_index 
                           (symbol_name, file_path, line_number, symbol_type, import_type, source_module)
                           VALUES (?, ?, ?, 'defined', ?, ?)""",
                        (sym["name"], sym["file_path"], sym.get("lineno", 0), 
                         sym.get("import_type", ""), sym.get("module", ""))
                    )
                    
            # Insert imports and create dependency edges
            for imp in imports:
                conn.execute(
                    """INSERT INTO symbol_index 
                       (symbol_name, file_path, line_number, symbol_type, import_type, source_module)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (imp.get("name", ""), imp["file_path"], imp.get("lineno", 0),
                     imp.get("type", "import"), imp.get("import_type", "import"), imp.get("module", ""))
                )
                
                # Create dependency edge
                provider = imp.get("resolved_path")
                if provider and provider != imp.get("file_path", ""):
                    conn.execute(
                        """INSERT OR IGNORE INTO dependency_edges 
                           (consumer_file, provider_file, symbol_name, import_type)
                           VALUES (?, ?, ?, ?)""",
                        (imp["file_path"], provider, imp.get("name", ""), imp.get("import_type", "import"))
                    )
                        
    def remove_file(self, file_path: str):
        """Remove file and all its symbols/edges from index."""
        with self._get_conn() as conn:
            conn.execute("DELETE FROM symbol_index WHERE file_path = ?", (file_path,))
            conn.execute("DELETE FROM dependency_edges WHERE consumer_file = ? OR provider_file = ?", 
                        (file_path, file_path))
            conn.execute("DELETE FROM file_index WHERE file_path = ?", (file_path,))
            
    def get_changed_files(self, file_paths: List[str]) -> List[str]:
        """Return subset of files that have changed since last index."""
        changed = []
        with self._get_conn() as conn:
            for fp in file_paths:
                row = conn.execute(
                    "SELECT file_hash FROM file_index WHERE file_path = ?",
                    (fp,)
                ).fetchone()
                if row is None:
                    changed.append(fp)
                else:
                    try:
                        with open(fp, "rb") as f:
                            current_hash = hashlib.sha256(f.read()).hexdigest()
                        if row[0] != current_hash:
                            changed.append(fp)
                    except Exception:
                        changed.append(fp)
        return changed
        
    def incremental_update(self, changed_files: List[str], root_dir: str) -> Dict[str, Any]:
        """Incrementally update index for changed files only."""
        stats = {"updated": 0, "removed": 0, "errors": 0}
        
        for fp in changed_files:
            try:
                rel_path = os.path.relpath(fp, root_dir).replace("\\", "/")
                if not os.path.exists(fp):
                    self.remove_file(rel_path)
                    stats["removed"] += 1
                    continue
                    
                with open(fp, "rb") as f:
                    content = f.read()
                file_hash = hashlib.sha256(content).hexdigest()
                
                # Check if already up to date
                old_hash = self.get_file_hash(rel_path)
                if old_hash == file_hash:
                    continue
                    
                # Parse and extract symbols
                content = content.decode("utf-8", errors="ignore")
                tree = ast.parse(content, filename=rel_path)
                visitor = SymbolVisitor()
                visitor.visit(tree)
                
                module_name = rel_path.replace("/", ".").replace(".py", "")
                if module_name.endswith(".__init__"):
                    module_name = module_name[:-9]
                    
                symbols = []
                for fn in visitor.function_defs:
                    symbols.append({"name": fn["name"], "file_path": rel_path, 
                                  "lineno": fn["lineno"], "type": "defined", "module": ""})
                for cls in visitor.class_defs:
                    symbols.append({"name": cls["name"], "file_path": rel_path,
                                  "lineno": cls["lineno"], "type": "defined", "module": ""})
                
                imports = []
                for mod in visitor.imported_modules:
                    imports.append({"name": mod, "file_path": rel_path, "lineno": 0,
                                  "type": "import", "import_type": "import", "module": mod,
                                  "resolved_path": self._resolve_module(mod, rel_path)})
                for mod, syms in visitor.imported_symbols.items():
                    for sym in syms:
                        imports.append({"name": sym, "file_path": rel_path, "lineno": 0,
                                      "type": "from_import", "import_type": "from_import", "module": mod,
                                      "resolved_path": self._resolve_module(mod, rel_path, sym)})
                
                self.upsert_file(rel_path, file_hash, module_name, symbols, imports)
                stats["updated"] += 1
            except Exception as e:
                stats["errors"] += 1
                
        return stats
        
    def _resolve_module(self, module: str, consumer_path: str, symbol: str = None) -> Optional[str]:
        """Resolve module name to file path in index."""
        with self._get_conn() as conn:
            # Try exact module match
            row = conn.execute(
                "SELECT file_path FROM file_index WHERE module_name = ?",
                (module,)
            ).fetchone()
            if row:
                return row[0]
                
            # Try prefix match
            prefix = module.split(".")[0]
            row = conn.execute(
                "SELECT file_path FROM file_index WHERE module_name LIKE ?",
                (prefix + "%",)
            ).fetchone()
            if row:
                return row[0]
                
            # Debug: print what's in the index
            all_rows = conn.execute("SELECT file_path, module_name FROM file_index").fetchall()
            print(f"DEBUG _resolve_module: looking for '{module}', index has: {[(r[0], r[1]) for r in all_rows]}")
                
            return None
            
    def compute_blast_radius_sqlite(self, changed_files: List[str], 
                                    max_depth: int = 10) -> Dict[str, Any]:
        """Compute blast radius using SQLite index (fast, no full graph build)."""
        # Normalize paths to match what's stored in the database (relative to root_dir)
        def normalize_path(f):
            try:
                # Try to get path relative to the analyzer's root_dir
                return os.path.relpath(f, self.root_dir).replace("\\", "/")
            except ValueError:
                # Cross-drive paths on Windows - use basename
                return os.path.basename(f).replace("\\", "/")
        
        normalized = {normalize_path(f) for f in changed_files}
        
        visited = set(normalized)
        impacted = []
        queue = deque([(f, 1) for f in normalized])
        
        while queue:
            current, depth = queue.popleft()
            if depth > max_depth:
                continue
                
            with self._get_conn() as conn:
                rows = conn.execute(
                    "SELECT DISTINCT consumer_file FROM dependency_edges WHERE provider_file = ?",
                    (current,)
                ).fetchall()
                
            for row in rows:
                dep = row[0]
                if dep not in visited:
                    visited.add(dep)
                    # Get symbols for this dependency
                    with self._get_conn() as conn:
                        sym_rows = conn.execute(
                            "SELECT symbol_name FROM dependency_edges WHERE provider_file = ? AND consumer_file = ?",
                            (current, dep)
                        ).fetchall()
                    symbols = [r[0] for r in sym_rows]
                    
                    impacted.append({
                        "file_path": dep,
                        "direct_dependency": depth == 1,
                        "imported_symbols": symbols,
                        "depth": depth
                    })
                    queue.append((dep, depth + 1))
                    
        return {
            "impacted_downstream_files": impacted,
            "total_impacted": len(impacted)
        }


class IncrementalBlastRadiusAnalyzer:
    """
    Enhanced BlastRadiusAnalyzer with SQLite-backed incremental symbol-level graph.
    Supports monorepo-scale with incremental updates.
    """
    
    CORE_COMPONENTS = {"engine", "database", "security", "auth", "api_gateway", "gateway"}
    
    def __init__(self, root_dir: str = ".", cache_path: Optional[str] = None, 
                 sqlite_path: Optional[str] = None):
        self.root_dir = os.path.abspath(root_dir)
        self.sqlite_path = sqlite_path or os.path.join(self.root_dir, ".context_pr", "ast_index.db")
        self.cache_path = cache_path or os.path.join(self.root_dir, ".context_pr", "ast_cache.json")
        
        # Ensure cache directory exists
        os.makedirs(os.path.dirname(self.sqlite_path), exist_ok=True)
        os.makedirs(os.path.dirname(self.cache_path), exist_ok=True)
        
        self.index = SQLiteASTIndex(self.sqlite_path, root_dir=self.root_dir)
        self._graph_built: bool = False
        self._build_lock = None
        
        # Legacy compatibility
        self.reverse_deps: Dict[str, Set[str]] = defaultdict(set)
        self.symbol_links: Dict[Tuple[str, str], List[str]] = defaultdict(list)
        self.cache_hits: int = 0
        self.cache_misses: int = 0
        
    def _ensure_graph_built(self):
        """Ensure legacy graph is built from SQLite index (for backward compat)."""
        if self._graph_built:
            return
        import threading
        if self._build_lock is None:
            self._build_lock = threading.Lock()
        with self._build_lock:
            if self._graph_built:
                return
            self._build_legacy_graph()
            self._graph_built = True
            
    def _build_legacy_graph(self):
        """Build legacy in-memory graph from SQLite index for backward compatibility."""
        with self.index._get_conn() as conn:
            rows = conn.execute("SELECT consumer_file, provider_file, symbol_name FROM dependency_edges").fetchall()
            for row in rows:
                self.reverse_deps[row[1]].add(row[0])
                self.symbol_links[(row[0], row[1])].append(row[2])
                
    def incremental_update(self, changed_files: List[str]) -> Dict[str, Any]:
        """Incrementally update index for changed files only (monorepo-scale)."""
        return self.index.incremental_update(changed_files, self.root_dir)
        
    def compute_blast_radius(
        self,
        changed_files: List[str],
        changed_symbols: Optional[List[ChangedSymbol]] = None,
        base_ref: str = "master",
        head_ref: str = "HEAD",
        use_sqlite: bool = True,
    ) -> BlastRadiusReport:
        """
        Calculates transitive downstream blast radius starting from changed files.
        Uses SQLite index for fast incremental computation when use_sqlite=True.
        """
        print(f"DEBUG compute_blast_radius: use_sqlite={use_sqlite}, changed_files={changed_files}")
        if use_sqlite:
            # Fast path: use SQLite index directly
            result = self.index.compute_blast_radius_sqlite(changed_files)
            print(f"DEBUG compute_blast_radius: result={result}")
            impacted_nodes = result["impacted_downstream_files"]
        else:
            # Legacy path
            self._ensure_graph_built()
            return self._compute_blast_radius_legacy(changed_files, changed_symbols, base_ref, head_ref)
            
        # Risk Score Calculation (same as legacy)
        changed_symbols = changed_symbols or []
        normalized_changed = {os.path.relpath(f, self.root_dir).replace("\\", "/") for f in changed_files}
        
        breaking_count = sum(1 for s in changed_symbols if s.is_breaking)
        core_hit = any(
            any(core in f for core in self.CORE_COMPONENTS)
            for f in normalized_changed
        )
        
        risk_score = 0.0
        risk_reasons = []
        
        risk_score += min(3.0, len(normalized_changed) * 0.6)
        if len(normalized_changed) > 5:
            risk_reasons.append(f"Broad change surface: {len(normalized_changed)} files directly modified.")
            
        risk_score += min(3.5, len(result["impacted_downstream_files"]) * 0.5)
        if len(result["impacted_downstream_files"]) > 3:
            risk_reasons.append(f"High downstream blast radius: {len(result['impacted_downstream_files'])} dependent files impacted.")
            
        if breaking_count > 0:
            risk_score += min(2.5, breaking_count * 1.5)
            risk_reasons.append(f"Breaking signature changes detected ({breaking_count}).")
            
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
            
        # Convert dict to BlastRadiusNode objects
        impacted_nodes = [
            BlastRadiusNode(
                file_path=n["file_path"],
                direct_dependency=n["direct_dependency"],
                imported_symbols=n["imported_symbols"],
                depth=n["depth"],
            )
            for n in result["impacted_downstream_files"]
        ]
        
        return BlastRadiusReport(
            base_ref=base_ref,
            head_ref=head_ref,
            risk_level=risk_level,
            risk_score=risk_score,
            total_files_changed=len(normalized_changed),
            impacted_downstream_files=impacted_nodes,
            changed_symbols=changed_symbols,
            breaking_changes_detected=sum(1 for s in changed_symbols if s.is_breaking),
            high_risk_reasons=risk_reasons,
        )
        
    def _compute_blast_radius_legacy(self, changed_files, changed_symbols, base_ref, head_ref):
        """Legacy implementation for backward compatibility."""
        # ... existing legacy implementation
        pass
        
    def warmup_graph_async(self):
        """Start background warmup of dependency graph (fire-and-forget)."""
        import threading
        if self._graph_built:
            return
        def _warmup():
            try:
                self._ensure_graph_built()
            except Exception:
                pass
        thread = threading.Thread(target=_warmup, daemon=True)
        thread.start()
        return thread