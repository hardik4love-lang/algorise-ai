"""
Tests for T3.3: Policy-as-Code & Custom Rules Engine
Validates policy registry, rule engines, YAML/JSON loading, tenant scoping,
dry-run, approval gates, and provenance tracking.
"""

import os
import tempfile
import pytest
import yaml
import json
from pathlib import Path

from policy.policy_engine import (
    PolicyRule,
    RuleScope,
    RuleProvenance,
    PolicyRegistry,
    ModernizeAIRuleEngine,
    TraceRootRuleEngine,
    policy_context,
)


class TestPolicyRule:
    """Tests for PolicyRule data model."""
    
    def test_rule_creation(self):
        """Test basic rule creation."""
        rule = PolicyRule(
            rule_id="test-rule-001",
            name="Test Rule",
            description="A test rule",
            scope=RuleScope.TENANT,
            provenance=RuleProvenance.TENANT_PACK,
            config={"package": "pydantic", "target_version": "2.0"},
        )
        
        assert rule.rule_id == "test-rule-001"
        assert rule.scope == RuleScope.TENANT
        assert rule.provenance == RuleProvenance.TENANT_PACK
        assert rule.enabled is True
        assert rule.dry_run_only is False
        assert rule.requires_approval is False
        
    def test_rule_serialization(self):
        """Test rule to_dict and from_dict roundtrip."""
        rule = PolicyRule(
            rule_id="test-002",
            name="Serialization Test",
            description="Test roundtrip",
            scope=RuleScope.PROJECT,
            provenance=RuleProvenance.CUSTOM_HOOK,
            config={"hook": "./hooks/test.py"},
            dry_run_only=True,
            requires_approval=True,
            tenant_id="test_tenant",
        )
        
        data = rule.to_dict()
        restored = PolicyRule.from_dict(data)
        
        assert restored.rule_id == rule.rule_id
        assert restored.name == rule.name
        assert restored.scope == rule.scope
        assert restored.provenance == rule.provenance
        assert restored.config == rule.config
        assert restored.dry_run_only == rule.dry_run_only
        assert restored.requires_approval == rule.requires_approval
        assert restored.tenant_id == rule.tenant_id


class TestPolicyRegistry:
    """Tests for PolicyRegistry."""
    
    def setup_method(self):
        """Setup fresh registry with temp directory."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.registry_path = os.path.join(self.temp_dir.name, ".algorise", "policies")
        os.makedirs(self.registry_path, exist_ok=True)
        self.registry = PolicyRegistry(self.registry_path)
        
    def teardown_method(self):
        self.temp_dir.cleanup()
        
    def test_registry_initialization(self):
        """Test registry initializes with empty rules."""
        assert len(self.registry.rules) == 0
        assert "modernize_ai" not in self.registry.engines
        assert "trace_root_ai" not in self.registry.engines
        
    def test_register_engines(self):
        """Test registering rule engines."""
        modernize_engine = ModernizeAIRuleEngine()
        trace_engine = TraceRootRuleEngine()
        
        self.registry.register_engine("modernize_ai", modernize_engine)
        self.registry.register_engine("trace_root_ai", trace_engine)
        
        assert "modernize_ai" in self.registry.engines
        assert "trace_root_ai" in self.registry.engines
        
    def test_add_and_get_rule(self):
        """Test adding and retrieving rules."""
        rule = PolicyRule(
            rule_id="test-001",
            name="Test Rule",
            description="Test",
            scope=RuleScope.GLOBAL,
            provenance=RuleProvenance.BUILTIN,
        )
        
        result = self.registry.add_rule(rule, persist=False)
        assert result is True
        
        retrieved = self.registry.get_rule("test-001")
        assert retrieved is not None
        assert retrieved.rule_id == "test-001"
        assert retrieved.name == "Test Rule"
        
    def test_add_duplicate_rule_fails(self):
        """Test adding duplicate rule fails."""
        rule = PolicyRule(
            rule_id="duplicate",
            name="Duplicate",
            description="Test",
            scope=RuleScope.GLOBAL,
            provenance=RuleProvenance.BUILTIN,
        )
        
        self.registry.add_rule(rule, persist=False)
        result = self.registry.add_rule(rule, persist=False)
        assert result is False
        
    def test_get_rules_by_scope(self):
        """Test filtering rules by scope."""
        rule1 = PolicyRule(rule_id="g1", name="Global 1", description="Global rule 1", scope=RuleScope.GLOBAL, provenance=RuleProvenance.BUILTIN)
        rule2 = PolicyRule(rule_id="t1", name="Tenant 1", description="Tenant rule 1", scope=RuleScope.TENANT, provenance=RuleProvenance.TENANT_PACK, tenant_id="tenant_a")
        rule3 = PolicyRule(rule_id="t2", name="Tenant 2", description="Tenant rule 2", scope=RuleScope.TENANT, provenance=RuleProvenance.TENANT_PACK, tenant_id="tenant_b")
        rule4 = PolicyRule(rule_id="p1", name="Project 1", description="Project rule 1", scope=RuleScope.PROJECT, provenance=RuleProvenance.PROJECT_CONFIG)
        
        for r in [rule1, rule2, rule3, rule4]:
            self.registry.add_rule(r, persist=False)
            
        global_rules = self.registry.get_rules_by_scope(RuleScope.GLOBAL)
        assert len(global_rules) == 1
        assert global_rules[0].rule_id == "g1"
        
        tenant_a_rules = self.registry.get_rules_by_scope(RuleScope.TENANT, tenant_id="tenant_a")
        assert len(tenant_a_rules) == 1
        assert tenant_a_rules[0].rule_id == "t1"
        
        tenant_b_rules = self.registry.get_rules_by_scope(RuleScope.TENANT, tenant_id="tenant_b")
        assert len(tenant_b_rules) == 1
        assert tenant_b_rules[0].rule_id == "t2"
        
        project_rules = self.registry.get_rules_by_scope(RuleScope.PROJECT)
        assert len(project_rules) == 1
        assert project_rules[0].rule_id == "p1"
        
    def test_get_applicable_rules(self):
        """Test getting applicable rules for a context."""
        self.registry.add_rule(PolicyRule(rule_id="g1", name="Global", description="Global rule", scope=RuleScope.GLOBAL, provenance=RuleProvenance.BUILTIN), persist=False)
        self.registry.add_rule(PolicyRule(rule_id="t1", name="Tenant A", description="Tenant A rule", scope=RuleScope.TENANT, provenance=RuleProvenance.TENANT_PACK, tenant_id="tenant_a"), persist=False)
        self.registry.add_rule(PolicyRule(rule_id="t2", name="Tenant B", description="Tenant B rule", scope=RuleScope.TENANT, provenance=RuleProvenance.TENANT_PACK, tenant_id="tenant_b"), persist=False)
        self.registry.add_rule(PolicyRule(rule_id="p1", name="Project", description="Project rule", scope=RuleScope.PROJECT, provenance=RuleProvenance.PROJECT_CONFIG), persist=False)
        self.registry.add_rule(PolicyRule(rule_id="c1", name="Custom", description="Custom rule", scope=RuleScope.CUSTOM, provenance=RuleProvenance.CUSTOM_HOOK), persist=False)
        
        # Context with tenant_a
        ctx = {"tenant_id": "tenant_a", "scope": RuleScope.TENANT, "engine": "modernize_ai"}
        applicable = self.registry.get_applicable_rules(ctx)
        
        # Should have: global (1) + tenant_a (1) + project (0) + custom (1) = 3
        # But project rules need project_path in context
        rule_ids = {r.rule_id for r in applicable}
        assert "g1" in rule_ids
        assert "t1" in rule_ids
        assert "c1" in rule_ids
        assert "t2" not in rule_ids
        assert "p1" not in rule_ids
        
    def test_update_rule(self):
        """Test updating an existing rule."""
        rule = PolicyRule(rule_id="update-test", name="Original", description="Original rule", scope=RuleScope.GLOBAL, provenance=RuleProvenance.BUILTIN)
        self.registry.add_rule(rule, persist=False)
        
        result = self.registry.update_rule("update-test", {"name": "Updated", "priority": 10}, persist=False)
        assert result is True
        
        updated = self.registry.get_rule("update-test")
        assert updated.name == "Updated"
        assert updated.priority == 10
        
    def test_update_nonexistent_fails(self):
        """Test updating nonexistent rule fails."""
        result = self.registry.update_rule("nonexistent", {"name": "New"}, persist=False)
        assert result is False
        
    def test_approve_rule(self):
        """Test approving a rule requiring approval."""
        rule = PolicyRule(
            rule_id="approval-test",
            name="Approval Test",
            description="Approval test rule",
            scope=RuleScope.TENANT,
            provenance=RuleProvenance.TENANT_PACK,
            requires_approval=True,
            tenant_id="tenant_a",
        )
        self.registry.add_rule(rule, persist=False)
        
        result = self.registry.approve_rule("approval-test", "admin@example.com")
        assert result is True
        
        approved = self.registry.get_rule("approval-test")
        assert approved.approved_by == "admin@example.com"
        assert approved.approved_at is not None
        
    def test_load_yaml_policy_pack(self):
        """Test loading policy pack from YAML file."""
        # Create a policy pack file
        packs_dir = os.path.join(self.registry_path, "policy_packs")
        os.makedirs(packs_dir, exist_ok=True)
        
        pack_data = {
            "pack_name": "test_pack",
            "version": "1.0",
            "tenant_id": "test_tenant",
            "rules": [
                {
                    "rule_id": "yaml-rule-1",
                    "name": "YAML Rule 1",
                    "description": "Loaded from YAML",
                    "scope": "tenant",
                    "provenance": "tenant_pack",
                    "enabled": True,
                    "priority": 50,
                    "config": {"package": "test"},
                    "dry_run_only": False,
                    "requires_approval": False,
                    "tenant_id": "test_tenant",
                }
            ]
        }
        
        pack_file = os.path.join(self.registry_path, "policy_packs", "test_pack.yaml")
        os.makedirs(os.path.dirname(pack_file), exist_ok=True)
        with open(pack_file, "w") as f:
            yaml.dump(pack_data, f)
            
        # Create new registry to trigger loading
        new_registry = PolicyRegistry(self.registry_path)
        
        rule = new_registry.get_rule("yaml-rule-1")
        assert rule is not None
        assert rule.name == "YAML Rule 1"
        assert rule.tenant_id == "test_tenant"
        assert rule.provenance == RuleProvenance.TENANT_PACK
        
    def test_load_json_policy_pack(self):
        """Test loading policy pack from JSON file."""
        packs_dir = os.path.join(self.registry_path, "policy_packs")
        os.makedirs(packs_dir, exist_ok=True)
        
        pack_data = {
            "pack_name": "json_pack",
            "version": "1.0",
            "rules": [
                {
                    "rule_id": "json-rule-1",
                    "name": "JSON Rule 1",
                    "description": "Loaded from JSON",
                    "scope": "global",
                    "provenance": "builtin",
                    "enabled": True,
                    "priority": 100,
                    "config": {"test": True},
                    "dry_run_only": False,
                    "requires_approval": False,
                }
            ]
        }
        
        pack_file = os.path.join(packs_dir, "json_pack.json")
        with open(pack_file, "w") as f:
            json.dump(pack_data, f)
            
        new_registry = PolicyRegistry(self.registry_path)
        rule = new_registry.get_rule("json-rule-1")
        assert rule is not None
        assert rule.name == "JSON Rule 1"
        assert rule.provenance == RuleProvenance.BUILTIN


class TestModernizeAIRuleEngine:
    """Tests for ModernizeAI rule engine."""
    
    def setup_method(self):
        self.engine = ModernizeAIRuleEngine()
        
    def test_evaluate_migration_rule(self):
        """Test evaluating a migration rule."""
        rule = PolicyRule(
            rule_id="migrate-test",
            name="Migration Test",
            description="Migration test rule",
            scope=RuleScope.GLOBAL,
            provenance=RuleProvenance.TENANT_PACK,
            config={"package": "pydantic", "target_version": "2.0", "engine": "modernize_ai"},
        )
        
        context = {"package": "pydantic", "target_version": "2.0", "root_dir": "/tmp"}
        results = self.engine.evaluate(rule, context)
        
        assert len(results) == 1
        assert results[0]["action"] == "migrate"
        assert results[0]["rule_id"] == "migrate-test"
        
    def test_evaluate_custom_hook(self):
        """Test evaluating a custom hook rule."""
        # Create a temporary hook file
        with tempfile.TemporaryDirectory() as tmpdir:
            hook_file = os.path.join(tmpdir, "custom_hook.py")
            with open(hook_file, "w") as f:
                f.write("""
def evaluate(context, config):
    return [{"custom": True, "config_value": config.get("test_key")}]
""")
            
            rule = PolicyRule(
                rule_id="hook-test",
                name="Hook Test",
                description="Hook test rule",
                scope=RuleScope.CUSTOM,
                provenance=RuleProvenance.CUSTOM_HOOK,
                config={"hook": hook_file, "test_key": "test_value", "engine": "modernize_ai"},
            )
            
            engine = ModernizeAIRuleEngine()
            context = {"test": "context"}
            results = engine.evaluate(rule, context)
            
            assert len(results) == 1
            assert results[0]["custom"] is True
            assert results[0]["config_value"] == "test_value"
            
    def test_apply_requires_approval(self):
        """Test apply fails when approval required but not given."""
        rule = PolicyRule(
            rule_id="approval-required",
            name="Approval Required",
            description="Approval required test",
            scope=RuleScope.TENANT,
            provenance=RuleProvenance.TENANT_PACK,
            requires_approval=True,
            tenant_id="tenant_a",
        )
        
        engine = ModernizeAIRuleEngine()
        context = {"package": "test", "target_version": "1.0", "root_dir": "/tmp"}
        result = engine.apply(rule, context, dry_run=False)
        
        assert result["status"] == "pending_approval"
        
    def test_apply_dry_run_only(self):
        """Test apply respects dry_run_only flag."""
        rule = PolicyRule(
            rule_id="dry-run-only",
            name="Dry Run Only",
            description="Dry run only test",
            scope=RuleScope.GLOBAL,
            provenance=RuleProvenance.BUILTIN,
            dry_run_only=True,
        )
        
        engine = ModernizeAIRuleEngine()
        context = {"package": "test", "root_dir": "/tmp"}
        result = engine.apply(rule, context, dry_run=False)  # Try to apply for real
        
        assert result["status"] == "dry_run_only"


class TestTraceRootRuleEngine:
    """Tests for TraceRoot rule engine."""
    
    def setup_method(self):
        self.engine = TraceRootRuleEngine()
        
    def test_evaluate_healing_rule(self):
        """Test evaluating a healing rule."""
        from trace_root_ai.models import IncidentPayload
        
        rule = PolicyRule(
            rule_id="heal-test",
            name="Heal Test",
            description="Heal test rule",
            scope=RuleScope.TENANT,
            provenance=RuleProvenance.TENANT_PACK,
            config={"error_type": "KeyError", "engine": "trace_root_ai"},
        )
        
        incident = IncidentPayload(
            incident_id="INC-001",
            service_name="test-service",
            error_type="KeyError",
            error_message="'user_id'",
            raw_stack_trace="KeyError: 'user_id'",
        )
        
        context = {"incident": incident, "engine": "trace_root_ai"}
        results = self.engine.evaluate(rule, context)
        
        assert len(results) == 1
        assert results[0]["action"] == "heal"
        assert results[0]["rule_id"] == "heal-test"
        
    def test_evaluate_wrong_error_type(self):
        """Test rule doesn't match wrong error type."""
        from trace_root_ai.models import IncidentPayload
        
        rule = PolicyRule(
            rule_id="heal-test",
            name="Heal Test",
            description="Heal test rule",
            scope=RuleScope.TENANT,
            provenance=RuleProvenance.TENANT_PACK,
            config={"error_type": "ZeroDivisionError", "engine": "trace_root_ai"},
        )
        
        incident = IncidentPayload(
            incident_id="INC-001",
            service_name="test-service",
            error_type="KeyError",
            error_message="'user_id'",
            raw_stack_trace="KeyError: 'user_id'",
        )
        
        context = {"incident": incident, "engine": "trace_root_ai"}
        results = self.engine.evaluate(rule, context)
        
        assert len(results) == 0


class TestPolicyContext:
    """Tests for policy_context context manager."""
    
    def test_context_manager(self):
        """Test policy_context context manager."""
        with policy_context(
            tenant_id="test_tenant",
            project_path="/tmp/project",
            scope=RuleScope.TENANT,
            engine="modernize_ai",
            dry_run=True,
        ) as ctx:
            assert ctx["tenant_id"] == "test_tenant"
            assert ctx["project_path"] == "/tmp/project"
            assert ctx["scope"] == RuleScope.TENANT
            assert ctx["engine"] == "modernize_ai"
            assert ctx["dry_run"] is True
            
    def test_context_manager_defaults(self):
        """Test context manager with defaults."""
        with policy_context() as ctx:
            assert ctx["tenant_id"] is None
            assert ctx["project_path"] is None
            assert ctx["scope"] == RuleScope.GLOBAL
            assert ctx["engine"] == "modernize_ai"
            assert ctx["dry_run"] is True


class TestAuditTrail:
    """Tests for audit trail export."""
    
    def setup_method(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.registry_path = os.path.join(self.temp_dir.name, ".algorise", "policies")
        os.makedirs(self.registry_path, exist_ok=True)
        self.registry = PolicyRegistry(self.registry_path)
        
    def teardown_method(self):
        self.temp_dir.cleanup()
        
    def test_export_audit_trail(self):
        """Test exporting audit trail."""
        rule1 = PolicyRule(rule_id="r1", name="Rule 1", description="Audit rule 1", scope=RuleScope.GLOBAL, provenance=RuleProvenance.BUILTIN)
        rule2 = PolicyRule(rule_id="r2", name="Rule 2", description="Audit rule 2", scope=RuleScope.TENANT, provenance=RuleProvenance.TENANT_PACK, tenant_id="tenant_a")
        
        self.registry.add_rule(rule1, persist=False)
        self.registry.add_rule(rule2, persist=False)
        
        # Export all
        audit = self.registry.export_audit_trail()
        assert len(audit) == 2
        assert audit[0]["rule_id"] == "r1"
        assert audit[1]["rule_id"] == "r2"
        
        # Export specific
        audit = self.registry.export_audit_trail(["r1"])
        assert len(audit) == 1
        assert audit[0]["rule_id"] == "r1"


class TestExamplePolicyPack:
    """Test loading the example acme_corp policy pack."""
    
    def setup_method(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.registry_path = os.path.join(self.temp_dir.name, ".algorise", "policies")
        os.makedirs(self.registry_path, exist_ok=True)
        
        # Copy the example pack
        packs_dir = os.path.join(self.registry_path, "policy_packs")
        os.makedirs(packs_dir, exist_ok=True)
        
        with open(os.path.join(packs_dir, "acme_corp_pack.yaml"), "w") as f:
            f.write("""
pack_name: "tenant_acme_corp"
version: "1.0"
tenant_id: "acme_corp"
rules:
  - rule_id: "modernize-pydantic-v2"
    name: "Pydantic v1 to v2 Migration"
    description: "Automatically migrate Pydantic v1 patterns to v2"
    scope: "tenant"
    provenance: "tenant_pack"
    enabled: true
    priority: 50
    config:
      package: "pydantic"
      target_version: "2.0"
      engine: "modernize_ai"
    dry_run_only: false
    requires_approval: true
    tenant_id: "acme_corp"
""")
        
    def teardown_method(self):
        self.temp_dir.cleanup()
        
    def test_load_acme_pack(self):
        """Test loading the example ACME corp pack."""
        registry = PolicyRegistry(self.registry_path)
        
        rule1 = registry.get_rule("modernize-pydantic-v2")
        assert rule1 is not None
        assert rule1.name == "Pydantic v1 to v2 Migration"
        assert rule1.tenant_id == "acme_corp"
        assert rule1.requires_approval is True
        assert rule1.config["package"] == "pydantic"
        
    def test_applicable_rules_for_acme(self):
        """Test getting applicable rules for acme_corp tenant."""
        registry = PolicyRegistry(self.registry_path)
        registry.register_engine("modernize_ai", ModernizeAIRuleEngine())
        registry.register_engine("trace_root_ai", TraceRootRuleEngine())
        
        ctx = {"tenant_id": "acme_corp", "scope": RuleScope.TENANT, "engine": "modernize_ai"}
        applicable = registry.get_applicable_rules(ctx)
        
        rule_ids = {r.rule_id for r in applicable}
        assert "modernize-pydantic-v2" in rule_ids
        
        # Test evaluation
        eval_ctx = {**ctx, "package": "pydantic", "target_version": "2.0", "root_dir": "/tmp"}
        results = registry.evaluate_rules(eval_ctx)
        
        assert "modernize-pydantic-v2" in results
        assert len(results["modernize-pydantic-v2"]) == 1
        assert results["modernize-pydantic-v2"][0]["action"] == "migrate"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])