"""
Tests for Incremental Blast Radius Analyzer (T3.1)
Validates SQLite-backed incremental symbol-level graph for monorepo-scale.
"""

import os
import tempfile
import pytest
import subprocess
import sys

sys.path.insert(0, "D:\\algorise-ai")

from context_pr.incremental_blast_radius import IncrementalBlastRadiusAnalyzer, SQLiteASTIndex
from context_pr.models import BlastRadiusNode, BlastRadiusReport, ChangedSymbol, RiskLevel


class TestSQLiteASTIndex:
    """Tests for SQLite-backed AST index."""
    
    def setup_method(self):
        """Setup fresh database for each test."""
        # Use temp directory on same drive as working dir to avoid cross-drive issues
        self.temp_dir = tempfile.TemporaryDirectory(dir=os.getcwd())
        self.db_path = os.path.join(self.temp_dir.name, "test_index.db")
        self.index = SQLiteASTIndex(self.db_path)
        
    def teardown_method(self):
        self.temp_dir.cleanup()
        
    def test_upsert_and_query_file(self):
        """Test upserting file with symbols and querying."""
        with tempfile.TemporaryDirectory(dir=os.getcwd()) as tmpdir:
            test_file = os.path.join(tmpdir, "test.py")
            with open(test_file, "w") as f:
                f.write("""
def hello():
    return "world"

class MyClass:
    def method(self):
        pass
""")
            
            self.index.upsert_file(
                file_path="test.py",
                file_hash="abc123",
                module_name="test",
                symbols=[
                    {"name": "hello", "file_path": "test.py", "lineno": 2, "type": "defined", "module": ""},
                    {"name": "MyClass", "file_path": "test.py", "lineno": 5, "type": "defined", "module": ""},
                    {"name": "method", "file_path": "test.py", "lineno": 7, "type": "defined", "module": ""},
                ],
                imports=[
                    {"name": "os", "file_path": "test.py", "lineno": 1, "type": "import", "import_type": "import", "module": "os", "resolved_path": None},
                ]
            )
            
            # Query file symbols
            symbols = self.index.get_file_symbols("test.py")
            assert len(symbols) >= 3
            symbol_names = {s["symbol_name"] for s in symbols if s["symbol_type"] == "defined"}
            assert "hello" in symbol_names
            assert "MyClass" in symbol_names
            
    def test_incremental_update(self):
        """Test incremental update detects changes."""
        with tempfile.TemporaryDirectory(dir=os.getcwd()) as tmpdir:
            # Create initial file
            test_file = os.path.join(tmpdir, "service.py")
            with open(test_file, "w") as f:
                f.write("def get_user(id):\n    return users[id]\n")
                
            # First update
            stats1 = self.index.incremental_update([test_file], tmpdir)
            assert stats1["updated"] == 1
            
            # Second update without changes
            stats2 = self.index.incremental_update([test_file], tmpdir)
            assert stats2["updated"] == 0  # No change
            
            # Modify file
            with open(test_file, "w") as f:
                f.write("def get_user(id):\n    return users.get(id)\n")
                
            # Third update - should detect change
            stats3 = self.index.incremental_update([test_file], tmpdir)
            assert stats3["updated"] == 1
            
    def test_dependency_edges(self):
        """Test dependency edge creation between files."""
        with tempfile.TemporaryDirectory(dir=os.getcwd()) as tmpdir:
            # Create module with function
            service_file = os.path.join(tmpdir, "service.py")
            with open(service_file, "w") as f:
                f.write("def get_user(id):\n    return users[id]\n")
                
            # Create consumer
            consumer_file = os.path.join(tmpdir, "consumer.py")
            with open(consumer_file, "w") as f:
                f.write("from service import get_user\n")
                
            # Update both
            self.index.incremental_update([service_file, consumer_file], tmpdir)
            
            # Check dependency edge
            deps = self.index.get_dependencies("consumer.py")
            assert len(deps) > 0
            
            dependents = self.index.get_dependents("service.py")
            assert "consumer.py" in dependents
            
    def test_incremental_update_removed_file(self):
        """Test removal of deleted files."""
        with tempfile.TemporaryDirectory(dir=os.getcwd()) as tmpdir:
            test_file = os.path.join(tmpdir, "temp.py")
            with open(test_file, "w") as f:
                f.write("def temp(): pass\n")
                
            self.index.incremental_update([test_file], tmpdir)
            
            # Delete file
            os.remove(test_file)
            
            # Update with deleted file path
            stats = self.index.incremental_update([os.path.join(tmpdir, "temp.py")], tmpdir)
            assert stats["removed"] == 1


class TestIncrementalBlastRadiusAnalyzer:
    """Tests for IncrementalBlastRadiusAnalyzer."""
    
    def setup_method(self):
        # Use temp directory on same drive as working dir
        self.temp_dir = tempfile.TemporaryDirectory(dir=os.getcwd())
        self.analyzer = IncrementalBlastRadiusAnalyzer(root_dir=self.temp_dir.name)
        
    def teardown_method(self):
        self.temp_dir.cleanup()
        
    def test_incremental_update_workflow(self):
        """Test full incremental update workflow."""
        # Create dependency chain
        os.makedirs(os.path.join(self.temp_dir.name, "src"), exist_ok=True)
        
        # Core module
        with open(os.path.join(self.temp_dir.name, "src", "core.py"), "w") as f:
            f.write("""
def get_config():
    return {"debug": True}

def validate(data):
    if not isinstance(data, dict):
        raise ValueError("Expected dict")
    return True
""")
        
        # Service depending on core
        with open(os.path.join(self.temp_dir.name, "src", "service.py"), "w") as f:
            f.write("""
from src.core import get_config, validate

def process(data):
    config = get_config()
    validate(data)
    return {"status": "ok"}
""")
        
        # API depending on service
        with open(os.path.join(self.temp_dir.name, "src", "api.py"), "w") as f:
            f.write("""
from src.service import process

def handle_request(data):
    return process(data)
""")
        
        # Initialize git repo
        subprocess.run(["git", "init"], cwd=self.temp_dir.name, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=self.temp_dir.name)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=self.temp_dir.name)
        subprocess.run(["git", "add", "."], cwd=self.temp_dir.name)
        subprocess.run(["git", "commit", "-m", "Initial"], cwd=self.temp_dir.name)
        
        # Initial incremental update
        all_files = [
            os.path.join(self.temp_dir.name, "src", "core.py"),
            os.path.join(self.temp_dir.name, "src", "service.py"),
            os.path.join(self.temp_dir.name, "src", "api.py"),
        ]
        stats = self.analyzer.incremental_update(all_files)
        assert stats["updated"] == 3
        assert stats["errors"] == 0
        
        # Test blast radius with SQLite (fast path)
        report = self.analyzer.compute_blast_radius(
            changed_files=[os.path.join(self.temp_dir.name, "src", "core.py")],
            use_sqlite=True
        )
        
        assert report.risk_level in [RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL]
        assert len(report.impacted_downstream_files) >= 2  # service.py and api.py
        impacted_paths = {n.file_path for n in report.impacted_downstream_files}
        assert "src/service.py" in impacted_paths
        assert "src/api.py" in impacted_paths
        
    def test_incremental_update_after_change(self):
        """Test incremental update after modifying a file."""
        # Create simple module
        with open(os.path.join(self.temp_dir.name, "utils.py"), "w") as f:
            f.write("def helper():\n    return 42\n")
            
        subprocess.run(["git", "init"], cwd=self.temp_dir.name, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=self.temp_dir.name)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=self.temp_dir.name)
        subprocess.run(["git", "add", "."], cwd=self.temp_dir.name)
        subprocess.run(["git", "commit", "-m", "Initial"], cwd=self.temp_dir.name)
        
        # Initial update
        self.analyzer.incremental_update([os.path.join(self.temp_dir.name, "utils.py")])
        
        # Modify file
        with open(os.path.join(self.temp_dir.name, "utils.py"), "w") as f:
            f.write("def helper():\n    return 43\n")
            
        # Incremental update should detect change
        stats = self.analyzer.incremental_update([os.path.join(self.temp_dir.name, "utils.py")])
        assert stats["updated"] == 1
        
    def test_compute_blast_radius_sqlite_fast_path(self):
        """Test fast SQLite-based blast radius computation."""
        # Create dependency chain
        with open(os.path.join(self.temp_dir.name, "a.py"), "w") as f:
            f.write("def a(): pass\n")
        with open(os.path.join(self.temp_dir.name, "b.py"), "w") as f:
            f.write("from a import a\n")
        with open(os.path.join(self.temp_dir.name, "c.py"), "w") as f:
            f.write("from b import a\n")
            
        subprocess.run(["git", "init"], cwd=self.temp_dir.name, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=self.temp_dir.name)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=self.temp_dir.name)
        subprocess.run(["git", "add", "."], cwd=self.temp_dir.name)
        subprocess.run(["git", "commit", "-m", "Initial"], cwd=self.temp_dir.name)
        
        # Update all files
        all_files = [
            os.path.join(self.temp_dir.name, "a.py"),
            os.path.join(self.temp_dir.name, "b.py"),
            os.path.join(self.temp_dir.name, "c.py"),
        ]
        self.analyzer.incremental_update(all_files)
        
        # Test fast SQLite blast radius
        report = self.analyzer.compute_blast_radius(
            changed_files=[os.path.join(self.temp_dir.name, "a.py")],
            use_sqlite=True
        )
        
        assert len(report.impacted_downstream_files) >= 2
        paths = {n.file_path for n in report.impacted_downstream_files}
        assert "b.py" in paths
        assert "c.py" in paths


if __name__ == "__main__":
    pytest.main([__file__, "-v"])