"""
T3.3: Policy-as-Code & Custom Rules Engine
Makes ModernizeAI and TraceRoot rule sets pluggable with YAML/JSON + Python hooks,
tenant-scoped rule packs, dry-run + approval gates, provenance tracking.
"""

import os
import yaml
import json
import importlib.util
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, field
from pathlib import Path
from abc import ABC, abstractmethod
from enum import Enum
import hashlib
import datetime
from contextlib import contextmanager

from modernize_ai.rule_engine import MigrationRule, RuleType, MigrationPlan
from modernize_ai.models import MigrationRule as ModernizeMigrationRule
from trace_root_ai.models import IncidentPayload, HotfixPlan


class RuleScope(Enum):
    """Scope of rule application."""
    GLOBAL = "global"          # Built-in rules
    TENANT = "tenant"          # Tenant-specific rules
    PROJECT = "project"        # Project-specific rules
    CUSTOM = "custom"          # Ad-hoc custom rules


class RuleProvenance(Enum):
    """Provenance tracking for audit trails."""
    BUILTIN = "builtin"
    TENANT_PACK = "tenant_pack"
    PROJECT_CONFIG = "project_config"
    CUSTOM_HOOK = "custom_hook"
    AUTO_GENERATED = "auto_generated"


@dataclass
class PolicyRule:
    """Universal policy rule that can apply to ModernizeAI or TraceRoot."""
    rule_id: str
    name: str
    description: str
    scope: RuleScope
    provenance: RuleProvenance
    enabled: bool = True
    priority: int = 100  # Lower = higher priority
    
    # Rule-specific configuration (flexible schema)
    config: Dict[str, Any] = field(default_factory=dict)
    
    # Metadata
    created_at: str = field(default_factory=lambda: datetime.datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.datetime.utcnow().isoformat())
    author: str = "system"
    version: str = "1.0"
    
    # Dry-run and approval
    dry_run_only: bool = False
    requires_approval: bool = False
    approved_by: Optional[str] = None
    approved_at: Optional[str] = None
    
    # Tenant scoping
    tenant_id: Optional[str] = None
    project_path: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "name": self.name,
            "description": self.description,
            "scope": self.scope.value,
            "provenance": self.provenance.value,
            "enabled": self.enabled,
            "priority": self.priority,
            "config": self.config,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "author": self.author,
            "version": self.version,
            "dry_run_only": self.dry_run_only,
            "requires_approval": self.requires_approval,
            "approved_by": self.approved_by,
            "approved_at": self.approved_at,
            "tenant_id": self.tenant_id,
            "project_path": self.project_path,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PolicyRule":
        return cls(
            rule_id=data["rule_id"],
            name=data["name"],
            description=data["description"],
            scope=RuleScope(data["scope"]),
            provenance=RuleProvenance(data["provenance"]),
            enabled=data.get("enabled", True),
            priority=data.get("priority", 100),
            config=data.get("config", {}),
            created_at=data.get("created_at", datetime.datetime.utcnow().isoformat()),
            updated_at=data.get("updated_at", datetime.datetime.utcnow().isoformat()),
            author=data.get("author", "system"),
            version=data.get("version", "1.0"),
            dry_run_only=data.get("dry_run_only", False),
            requires_approval=data.get("requires_approval", False),
            approved_by=data.get("approved_by"),
            approved_at=data.get("approved_at"),
            tenant_id=data.get("tenant_id"),
            project_path=data.get("project_path"),
        )


class RuleEngine(ABC):
    """Abstract base for rule engines (ModernizeAI, TraceRoot, etc.)."""
    
    @abstractmethod
    def evaluate(self, rule: PolicyRule, context: Dict[str, Any]) -> List[Any]:
        """Evaluate a rule against context, return actions/findings."""
        pass
    
    @abstractmethod
    def apply(self, rule: PolicyRule, context: Dict[str, Any], dry_run: bool = True) -> Dict[str, Any]:
        """Apply a rule, return result metadata."""
        pass


class ModernizeAIRuleEngine(RuleEngine):
    """Policy engine for ModernizeAI codemod rules."""
    
    def __init__(self, base_engine=None):
        self.base_engine = base_engine  # CodemodRuleEngine instance
        
    def evaluate(self, rule: PolicyRule, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Evaluate a ModernizeAI policy rule."""
        # Convert PolicyRule to MigrationRule if needed
        if rule.provenance == RuleProvenance.CUSTOM_HOOK and "hook" in rule.config:
            return self._evaluate_custom_hook(rule, context)
        elif rule.provenance in [RuleProvenance.TENANT_PACK, RuleProvenance.PROJECT_CONFIG]:
            return self._evaluate_migration_rule(rule, context)
        return []
    
    def _evaluate_custom_hook(self, rule: PolicyRule, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Execute custom Python hook."""
        hook_path = rule.config.get("hook")
        if not hook_path:
            return []
        
        try:
            spec = importlib.util.spec_from_file_location("custom_hook", hook_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            if hasattr(module, "evaluate"):
                return module.evaluate(context, rule.config)
        except Exception as e:
            return [{"error": f"Hook execution failed: {e}", "rule_id": rule.rule_id}]
        return []
    
    def _evaluate_migration_rule(self, rule: PolicyRule, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Evaluate as standard migration rule."""
        return [{
            "action": "migrate",
            "rule_id": rule.rule_id,
            "config": rule.config,
            "dry_run": rule.dry_run_only,
        }]
    
    def apply(self, rule: PolicyRule, context: Dict[str, Any], dry_run: bool = True) -> Dict[str, Any]:
        """Apply ModernizeAI rule."""
        if rule.requires_approval and not rule.approved_by:
            return {"status": "pending_approval", "rule_id": rule.rule_id}
        
        if rule.dry_run_only and not dry_run:
            return {"status": "dry_run_only", "rule_id": rule.rule_id}
        
        # Delegate to base engine if available
        if self.base_engine and hasattr(self.base_engine, "run_migration"):
            results = self.base_engine.run_migration(
                package=context.get("package"),
                target_version=context.get("target_version"),
                root_dir=context.get("root_dir"),
                write=not dry_run,
            )
            return {
                "status": "applied" if not dry_run else "dry_run",
                "rule_id": rule.rule_id,
                "results": [r.model_dump() for r in results] if results else [],
            }
        
        return {"status": "no_engine", "rule_id": rule.rule_id}


class TraceRootRuleEngine(RuleEngine):
    """Policy engine for TraceRoot AI incident healing rules."""
    
    def __init__(self, healer=None, blame_analyzer=None):
        self.healer = healer
        self.blame_analyzer = blame_analyzer
        
    def evaluate(self, rule: PolicyRule, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Evaluate a TraceRoot policy rule."""
        incident = context.get("incident")
        if not incident:
            return []
        
        if rule.provenance == RuleProvenance.CUSTOM_HOOK and "hook" in rule.config:
            return self._evaluate_custom_hook(rule, context)
        elif rule.config.get("error_type"):
            return self._evaluate_healing_rule(rule, context)
        return []
    
    def _evaluate_custom_hook(self, rule: PolicyRule, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Execute custom Python hook for incident analysis."""
        hook_path = rule.config.get("hook")
        if not hook_path:
            return []
        
        try:
            spec = importlib.util.spec_from_file_location("custom_hook", hook_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            if hasattr(module, "evaluate"):
                return module.evaluate(context, rule.config)
        except Exception as e:
            return [{"error": f"Hook execution failed: {e}", "rule_id": rule.rule_id}]
        return []
    
    def _evaluate_healing_rule(self, rule: PolicyRule, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Evaluate as standard healing rule."""
        incident = context.get("incident")
        if not incident:
            return []
        
        error_type = rule.config.get("error_type")
        if error_type and incident.error_type != error_type:
            return []
        
        return [{
            "action": "heal",
            "rule_id": rule.rule_id,
            "config": rule.config,
            "dry_run": rule.dry_run_only,
        }]
    
    def apply(self, rule: PolicyRule, context: Dict[str, Any], dry_run: bool = True) -> Dict[str, Any]:
        """Apply TraceRoot healing rule."""
        if rule.requires_approval and not rule.approved_by:
            return {"status": "pending_approval", "rule_id": rule.rule_id}
        
        incident = context.get("incident")
        if not incident:
            return {"status": "no_incident", "rule_id": rule.rule_id}
        
        if rule.requires_approval and not rule.approved_by:
            return {"status": "pending_approval", "rule_id": rule.rule_id}
        
        if rule.dry_run_only and not dry_run:
            return {"status": "dry_run_only", "rule_id": rule.rule_id}
        
        # Use healer if available
        if self.healer:
            from trace_root_ai.models import BlameContext
            blame = self.blame_analyzer.analyze_culprit_frame(incident) if self.blame_analyzer else None
            if blame:
                plan = self.healer.synthesize_hotfix(incident, blame)
                if plan and not dry_run:
                    self.healer.stage_hotfix_branch(plan, create_branch=False)
                return {
                    "status": "applied" if not dry_run else "dry_run",
                    "rule_id": rule.rule_id,
                    "plan": plan.model_dump() if plan else None,
                }
        
        return {"status": "no_healer", "rule_id": rule.rule_id}


class PolicyRegistry:
    """
    Central registry for all policy rules with YAML/JSON + Python hook support.
    Supports tenant-scoped rule packs, dry-run, approval gates, provenance tracking.
    """
    
    def __init__(self, registry_path: str = None):
        self.registry_path = registry_path or os.path.join(os.getcwd(), ".algorise", "policies")
        self.rules: Dict[str, PolicyRule] = {}
        self.engines: Dict[str, RuleEngine] = {}
        self._load_registry()
        
    def _load_registry(self):
        """Load rules from YAML/JSON files in registry directory."""
        os.makedirs(self.registry_path, exist_ok=True)
        
        # Load from policy_packs subdirectory
        packs_dir = os.path.join(self.registry_path, "policy_packs")
        os.makedirs(packs_dir, exist_ok=True)
        
        for file_path in Path(packs_dir).rglob("*.yaml"):
            self._load_policy_pack(file_path)
        for file_path in Path(packs_dir).rglob("*.yml"):
            self._load_policy_pack(file_path)
        for file_path in Path(packs_dir).rglob("*.json"):
            self._load_policy_pack(file_path)
            
    def _load_policy_pack(self, file_path: Path):
        """Load a policy pack from YAML/JSON file."""
        try:
            with open(file_path, "r") as f:
                if file_path.suffix in [".yaml", ".yml"]:
                    data = yaml.safe_load(f)
                else:
                    data = json.load(f)
            
            if not data or "rules" not in data:
                return
                
            pack_name = data.get("pack_name", file_path.stem)
            pack_version = data.get("version", "1.0")
            tenant_id = data.get("tenant_id")
            
            for rule_data in data["rules"]:
                rule_data["provenance"] = rule_data.get("provenance", "tenant_pack")
                rule_data["tenant_id"] = rule_data.get("tenant_id", tenant_id)
                
                rule = PolicyRule.from_dict(rule_data)
                self.rules[rule.rule_id] = rule
                
        except Exception as e:
            print(f"Warning: Failed to load policy pack {file_path}: {e}")
            
    def register_engine(self, name: str, engine: RuleEngine):
        """Register a rule engine."""
        self.engines[name] = engine
        
    def get_rule(self, rule_id: str) -> Optional[PolicyRule]:
        """Get rule by ID."""
        return self.rules.get(rule_id)
    
    def get_rules_by_scope(self, scope: RuleScope, tenant_id: str = None) -> List[PolicyRule]:
        """Get all rules matching scope and optional tenant."""
        result = []
        for rule in self.rules.values():
            if rule.scope != scope:
                continue
            if tenant_id and rule.tenant_id and rule.tenant_id != tenant_id:
                continue
            if rule.enabled:
                result.append(rule)
        return sorted(result, key=lambda r: r.priority)
    
    def get_applicable_rules(self, context: Dict[str, Any]) -> List[PolicyRule]:
        """Get all rules applicable to a given context."""
        tenant_id = context.get("tenant_id")
        scope = context.get("scope", RuleScope.GLOBAL)
        
        rules = []
        # Global rules
        rules.extend(self.get_rules_by_scope(RuleScope.GLOBAL))
        # Tenant rules
        if tenant_id:
            rules.extend(self.get_rules_by_scope(RuleScope.TENANT, tenant_id))
        # Project rules
        project_path = context.get("project_path")
        if project_path:
            rules.extend(self.get_rules_by_scope(RuleScope.PROJECT))
        # Custom rules
        rules.extend(self.get_rules_by_scope(RuleScope.CUSTOM))
        
        # Filter by engine if specified
        engine_name = context.get("engine")
        if engine_name and engine_name in self.engines:
            # Could filter by engine-specific config
            pass
            
        return [r for r in rules if r.enabled]
    
    def evaluate_rules(self, context: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
        """Evaluate all applicable rules against context."""
        rules = self.get_applicable_rules(context)
        results = {}
        
        for rule in rules:
            engine_name = rule.config.get("engine", "modernize_ai")
            engine = self.engines.get(engine_name)
            if engine:
                results[rule.rule_id] = engine.evaluate(rule, context)
                
        return results
    
    def apply_rules(self, context: Dict[str, Any], dry_run: bool = True) -> Dict[str, Dict[str, Any]]:
        """Apply all applicable rules."""
        rules = self.get_applicable_rules(context)
        results = {}
        
        for rule in rules:
            engine_name = rule.config.get("engine", "modernize_ai")
            engine = self.engines.get(engine_name)
            if engine:
                results[rule.rule_id] = engine.apply(rule, context, dry_run)
                
        return results
    
    def add_rule(self, rule: PolicyRule, persist: bool = True) -> bool:
        """Add a new rule to registry."""
        if rule.rule_id in self.rules:
            return False
            
        self.rules[rule.rule_id] = rule
        if persist:
            self._persist_rule(rule)
        return True
    
    def update_rule(self, rule_id: str, updates: Dict[str, Any], persist: bool = True) -> bool:
        """Update an existing rule."""
        if rule_id not in self.rules:
            return False
            
        rule = self.rules[rule_id]
        for key, value in updates.items():
            if hasattr(rule, key):
                setattr(rule, key, value)
        rule.updated_at = datetime.datetime.utcnow().isoformat()
        
        if persist:
            self._persist_rule(rule)
        return True
    
    def approve_rule(self, rule_id: str, approved_by: str) -> bool:
        """Approve a rule that requires approval."""
        if rule_id not in self.rules:
            return False
        rule = self.rules[rule_id]
        rule.approved_by = approved_by
        rule.approved_at = datetime.datetime.utcnow().isoformat()
        rule.updated_at = datetime.datetime.utcnow().isoformat()
        self._persist_rule(rule)
        return True
    
    def _persist_rule(self, rule: PolicyRule):
        """Persist a rule to its policy pack file."""
        # Determine pack file based on provenance/tenant
        pack_dir = os.path.join(self.registry_path, "policy_packs")
        if rule.tenant_id:
            pack_file = os.path.join(pack_dir, f"{rule.tenant_id}_pack.yaml")
        elif rule.scope == RuleScope.PROJECT:
            pack_file = os.path.join(pack_dir, "project_pack.yaml")
        else:
            pack_file = os.path.join(pack_dir, "global_pack.yaml")
            
        os.makedirs(pack_dir, exist_ok=True)
        
        # Load existing pack
        pack_data = {"pack_name": os.path.basename(pack_file).replace(".yaml", ""), 
                     "version": "1.0", "rules": []}
        if os.path.exists(pack_file):
            with open(pack_file, "r") as f:
                pack_data = yaml.safe_load(f) or pack_data
                
        # Update or add rule
        rule_dict = rule.to_dict()
        existing_idx = next((i for i, r in enumerate(pack_data["rules"]) if r["rule_id"] == rule.rule_id), None)
        if existing_idx is not None:
            pack_data["rules"][existing_idx] = rule_dict
        else:
            pack_data["rules"].append(rule_dict)
            
        # Write back
        with open(pack_file, "w") as f:
            yaml.dump(pack_data, f, default_flow_style=False, sort_keys=False)
            
    def export_audit_trail(self, rule_ids: List[str] = None) -> List[Dict[str, Any]]:
        """Export audit trail for specified rules or all rules."""
        rules = [self.rules[rid] for rid in rule_ids] if rule_ids else list(self.rules.values())
        return [r.to_dict() for r in rules]


# Example policy pack structure
EXAMPLE_POLICY_PACK = """
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

  - rule_id: "trace-root-keyerror-handler"
    name: "KeyError Auto-Healing"
    description: "Automatically synthesize .get() fallback for KeyError incidents"
    scope: "tenant"
    provenance: "tenant_pack"
    enabled: true
    priority: 10
    config:
      error_type: "KeyError"
      engine: "trace_root_ai"
      auto_stage: false
    dry_run_only: false
    requires_approval: false
    tenant_id: "acme_corp"

  - rule_id: "custom-security-scan"
    name: "Custom Security Scan Hook"
    description: "Run custom security analysis via Python hook"
    scope: "tenant"
    provenance: "custom_hook"
    enabled: true
    priority: 100
    config:
      hook: "/opt/algorise/hooks/security_scan.py"
      engine: "modernize_ai"
    dry_run_only: true
    requires_approval: true
    tenant_id: "acme_corp"
"""


@contextmanager
def policy_context(tenant_id: str = None, project_path: str = None, 
                   scope: RuleScope = RuleScope.GLOBAL, engine: str = "modernize_ai",
                   dry_run: bool = True):
    """Context manager for policy evaluation."""
    context = {
        "tenant_id": tenant_id,
        "project_path": project_path,
        "scope": scope,
        "engine": engine,
        "dry_run": dry_run,
    }
    try:
        yield context
    finally:
        pass


# Usage example
def example_usage():
    """Example of using the policy registry."""
    # Initialize registry
    registry = PolicyRegistry()
    
    # Register engines
    registry.register_engine("modernize_ai", ModernizeAIRuleEngine())
    registry.register_engine("trace_root_ai", TraceRootRuleEngine())
    
    # Load policy packs (from YAML files)
    # registry._load_registry()  # Called in __init__
    
    # Evaluate rules for a tenant
    with policy_context(tenant_id="acme_corp", scope=RuleScope.TENANT) as ctx:
        results = registry.evaluate_rules(ctx)
        print(f"Evaluation results: {results}")
        
        # Apply rules
        apply_results = registry.apply_rules(ctx, dry_run=True)
        print(f"Apply results: {apply_results}")
    
    # Add a custom rule
    custom_rule = PolicyRule(
        rule_id="custom-no-print",
        name="Ban print() in production code",
        description="Flag print() statements in production code paths",
        scope=RuleScope.PROJECT,
        provenance=RuleProvenance.CUSTOM_HOOK,
        config={
            "hook": "./hooks/no_print_hook.py",
            "engine": "modernize_ai",
        },
        dry_run_only=True,
        requires_approval=True,
    )
    registry.add_rule(custom_rule)
    
    # Export audit trail
    audit = registry.export_audit_trail()
    print(f"Audit trail: {len(audit)} rules")


if __name__ == "__main__":
    example_usage()