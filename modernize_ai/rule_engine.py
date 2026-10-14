"""
ModernizeAI: Codemod Rule Engine
Maintains catalog of breaking SDK migrations and synthesizes execution plans.
"""

from __future__ import annotations

import json
import os
from typing import Dict, List, Optional

from .models import MigrationPlan, MigrationRule, RuleType


class CodemodRuleEngine:
    """
    Manages library migration specifications and returns matched rule plans.
    """

    def __init__(self, custom_rules_path: Optional[str] = None):
        self.rules: Dict[str, List[MigrationRule]] = {}
        self._load_builtin_rules()
        if custom_rules_path and os.path.exists(custom_rules_path):
            self._load_custom_rules(custom_rules_path)

    def _load_builtin_rules(self):
        # 1. Pydantic v1 to v2 Migration Pack
        pydantic_rules = [
            MigrationRule(
                rule_id="pydantic-v2-dict-to-model-dump",
                package_name="pydantic",
                target_version="2.0",
                rule_type=RuleType.RENAME_METHOD_CALL,
                source_symbol="dict",
                target_symbol="model_dump",
                description="Replace deprecated Model.dict() with Model.model_dump()",
            ),
            MigrationRule(
                rule_id="pydantic-v2-json-to-model-dump-json",
                package_name="pydantic",
                target_version="2.0",
                rule_type=RuleType.RENAME_METHOD_CALL,
                source_symbol="json",
                target_symbol="model_dump_json",
                description="Replace deprecated Model.json() with Model.model_dump_json()",
            ),
            MigrationRule(
                rule_id="pydantic-v2-parse-obj-to-model-validate",
                package_name="pydantic",
                target_version="2.0",
                rule_type=RuleType.RENAME_METHOD_CALL,
                source_symbol="parse_obj",
                target_symbol="model_validate",
                description="Replace deprecated Model.parse_obj(data) with Model.model_validate(data)",
            ),
            MigrationRule(
                rule_id="pydantic-v2-validator-to-field-validator",
                package_name="pydantic",
                target_version="2.0",
                rule_type=RuleType.REFACTOR_DECORATOR,
                source_symbol="validator",
                target_symbol="field_validator",
                description="Replace @validator with @field_validator",
                old_module="pydantic",
                new_module="pydantic",
            ),
            MigrationRule(
                rule_id="pydantic-v2-validator-import-rewrite",
                package_name="pydantic",
                target_version="2.0",
                rule_type=RuleType.REPLACE_IMPORT,
                source_symbol="validator",
                target_symbol="field_validator",
                description="Update import from validator to field_validator",
                old_module="pydantic",
                new_module="pydantic",
            ),
        ]
        self.rules["pydantic"] = pydantic_rules

        # 2. Python Standard Library 3.12+ Deprecations Pack
        stdlib_rules = [
            MigrationRule(
                rule_id="python-datetime-utcnow-deprecate",
                package_name="datetime",
                target_version="3.12",
                rule_type=RuleType.REPLACE_CALL_WITH_EXPR,
                source_symbol="utcnow",
                target_symbol="now(timezone.utc)",
                description="Replace deprecated datetime.utcnow() with datetime.now(timezone.utc)",
            )
        ]
        self.rules["datetime"] = stdlib_rules

        # 3. LangChain v0.1 to v0.3 Decomposition Pack
        langchain_rules = [
            MigrationRule(
                rule_id="langchain-chat-openai-import",
                package_name="langchain",
                target_version="0.3",
                rule_type=RuleType.REPLACE_IMPORT,
                source_symbol="ChatOpenAI",
                target_symbol="ChatOpenAI",
                description="Migrate ChatOpenAI to langchain_openai partner package",
                old_module="langchain.chat_models",
                new_module="langchain_openai",
            ),
            MigrationRule(
                rule_id="langchain-embeddings-openai-import",
                package_name="langchain",
                target_version="0.3",
                rule_type=RuleType.REPLACE_IMPORT,
                source_symbol="OpenAIEmbeddings",
                target_symbol="OpenAIEmbeddings",
                description="Migrate OpenAIEmbeddings to langchain_openai partner package",
                old_module="langchain.embeddings",
                new_module="langchain_openai",
            ),
        ]
        self.rules["langchain"] = langchain_rules

    def _load_custom_rules(self, file_path: str):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for item in data.get("rules", []):
                rule = MigrationRule(
                    rule_id=item["rule_id"],
                    package_name=item["package_name"],
                    target_version=item.get("target_version", "latest"),
                    rule_type=RuleType(item["rule_type"]),
                    source_symbol=item["source_symbol"],
                    target_symbol=item["target_symbol"],
                    description=item.get("description", ""),
                    old_module=item.get("old_module"),
                    new_module=item.get("new_module"),
                    is_breaking=item.get("is_breaking", True),
                )
                self.rules.setdefault(rule.package_name, []).append(rule)
        except Exception:
            pass

    def get_plan(
        self, package_name: str, target_version: Optional[str] = None
    ) -> Optional[MigrationPlan]:
        """Synthesizes a migration plan for a target package."""
        pkg_rules = self.rules.get(package_name.lower())
        if not pkg_rules:
            return None

        # Filter by version if specified
        matched_rules = [
            r for r in pkg_rules
            if not target_version or r.target_version == target_version
        ]

        return MigrationPlan(
            package_name=package_name,
            from_version="legacy",
            to_version=target_version or "latest",
            rules=matched_rules,
        )

    def list_supported_packages(self) -> List[str]:
        return sorted(list(self.rules.keys()))
