"""
Unit and Integration Tests for ModernizeAI
Validates rule engine catalog, AST code transformer, import/decorator rewriting,
and autonomous migration agent execution.
"""

from __future__ import annotations

import os
import tempfile
import pytest

from modernize_ai.agent import ModernizeAgent
from modernize_ai.models import MigrationRule, RuleType
from modernize_ai.rule_engine import CodemodRuleEngine
from modernize_ai.transformer import ASTCodeTransformer


def test_rule_engine_catalog():
    engine = CodemodRuleEngine()
    pkgs = engine.list_supported_packages()
    assert "pydantic" in pkgs
    assert "datetime" in pkgs
    assert "langchain" in pkgs

    plan = engine.get_plan("pydantic", target_version="2.0")
    assert plan is not None
    assert len(plan.rules) >= 4
    rule_ids = [r.rule_id for r in plan.rules]
    assert "pydantic-v2-dict-to-model-dump" in rule_ids


def test_transformer_method_call_rename():
    transformer = ASTCodeTransformer()
    rule = MigrationRule(
        rule_id="test-dict-rename",
        package_name="pydantic",
        target_version="2.0",
        rule_type=RuleType.RENAME_METHOD_CALL,
        source_symbol="dict",
        target_symbol="model_dump",
        description="Rename dict() to model_dump()",
    )

    source = """
def serialize_user(user):
    payload = user.dict()
    return payload
"""
    result = transformer.transform_code("user_service.py", source, [rule])
    assert result.transformations_applied == 1
    assert result.syntax_valid is True
    assert "user.model_dump()" in result.modified_code
    assert result.unified_diff is not None
    assert "-    payload = user.dict()" in result.unified_diff
    assert "+    payload = user.model_dump()" in result.unified_diff


def test_transformer_import_and_decorator_rewrite():
    transformer = ASTCodeTransformer()
    rules = [
        MigrationRule(
            rule_id="validator-import",
            package_name="pydantic",
            target_version="2.0",
            rule_type=RuleType.REPLACE_IMPORT,
            source_symbol="validator",
            target_symbol="field_validator",
            description="Replace validator import",
            old_module="pydantic",
            new_module="pydantic",
        ),
        MigrationRule(
            rule_id="validator-dec",
            package_name="pydantic",
            target_version="2.0",
            rule_type=RuleType.REFACTOR_DECORATOR,
            source_symbol="validator",
            target_symbol="field_validator",
            description="Replace @validator decorator",
        ),
    ]

    source = """
from pydantic import BaseModel, validator

class UserModel(BaseModel):
    name: str

    @validator('name')
    def validate_name(cls, v):
        return v.strip()
"""
    result = transformer.transform_code("model.py", source, rules)
    assert result.transformations_applied == 2
    assert result.syntax_valid is True
    assert "from pydantic import BaseModel, field_validator" in result.modified_code
    assert "@field_validator('name')" in result.modified_code


def test_transformer_datetime_utcnow():
    transformer = ASTCodeTransformer()
    rule = MigrationRule(
        rule_id="datetime-deprecate",
        package_name="datetime",
        target_version="3.12",
        rule_type=RuleType.REPLACE_CALL_WITH_EXPR,
        source_symbol="utcnow",
        target_symbol="now(timezone.utc)",
        description="Replace datetime.utcnow",
    )

    source = """
import datetime

def get_current_timestamp():
    return datetime.utcnow()
"""
    result = transformer.transform_code("time_util.py", source, [rule])
    assert result.transformations_applied == 1
    assert result.syntax_valid is True
    assert "datetime.now(timezone.utc)" in result.modified_code


def test_modernize_agent_dry_run_and_write():
    with tempfile.TemporaryDirectory() as tmpdir:
        sample_file = os.path.join(tmpdir, "legacy_model.py")
        with open(sample_file, "w") as f:
            f.write("def dump(obj):\n    return obj.dict()\n")

        engine = CodemodRuleEngine()
        plan = engine.get_plan("pydantic", target_version="2.0")
        agent = ModernizeAgent(root_dir=tmpdir)

        # 1. Dry run
        dry_results = agent.execute_plan(plan, write=False)
        assert len(dry_results) == 1
        assert dry_results[0].transformations_applied == 1
        # Confirm file was NOT modified on disk
        with open(sample_file, "r") as f:
            assert "obj.dict()" in f.read()

        # 2. Write mode
        write_results = agent.execute_plan(plan, write=True)
        assert len(write_results) == 1
        # Confirm file WAS modified on disk
        with open(sample_file, "r") as f:
            content = f.read()
            assert "obj.model_dump()" in content

        # 3. Report generation
        report = agent.generate_markdown_report(plan, write_results, write_mode=True)
        assert "# 🚀 ModernizeAI: Autonomous SDK Migration Report" in report
        assert "Applied & Written to Disk" in report
        assert "legacy_model.py" in report
