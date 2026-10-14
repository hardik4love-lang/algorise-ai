"""
ModernizeAI: AST Code Transformer
Executes AST-level code rewriting according to migration rules and produces verifiable diffs.
"""

from __future__ import annotations

import ast
import difflib
from typing import List, Optional

from .models import MigrationRule, RuleType, TransformResult


class CodemodVisitor(ast.NodeTransformer):
    """AST NodeTransformer that rewrites imports, calls, and decorators."""

    def __init__(self, rules: List[MigrationRule]):
        self.rules = rules
        self.transformations_count = 0

    def visit_ImportFrom(self, node: ast.ImportFrom) -> ast.AST:
        # If importing from datetime and replacing utcnow with timezone.utc, ensure timezone is imported
        if node.module == "datetime":
            has_utcnow_rule = any(
                r.source_symbol == "utcnow" and r.rule_type == RuleType.REPLACE_CALL_WITH_EXPR
                for r in self.rules
            )
            if has_utcnow_rule:
                imported_names = {alias.name for alias in node.names}
                if "timezone" not in imported_names:
                    node.names.append(ast.alias(name="timezone"))
                    self.transformations_count += 1

        for rule in self.rules:
            if rule.rule_type == RuleType.REPLACE_IMPORT:
                if rule.old_module and node.module == rule.old_module:
                    for alias in node.names:
                        if alias.name == rule.source_symbol:
                            alias.name = rule.target_symbol
                            if rule.new_module:
                                node.module = rule.new_module
                            self.transformations_count += 1
        return self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> ast.AST:
        for rule in self.rules:
            # 1. Method call rename: e.g. obj.dict() -> obj.model_dump()
            if rule.rule_type == RuleType.RENAME_METHOD_CALL:
                if isinstance(node.func, ast.Attribute) and node.func.attr == rule.source_symbol:
                    node.func.attr = rule.target_symbol
                    self.transformations_count += 1

            # 2. Call replacement: e.g. datetime.utcnow() -> datetime.now(timezone.utc)
            elif rule.rule_type == RuleType.REPLACE_CALL_WITH_EXPR:
                if (
                    isinstance(node.func, ast.Attribute)
                    and isinstance(node.func.value, ast.Name)
                    and node.func.attr == rule.source_symbol
                ):
                    # Replace with datetime.now(timezone.utc)
                    node.func.attr = "now"
                    # Add timezone.utc argument
                    tz_arg = ast.Attribute(
                        value=ast.Name(id="timezone", ctx=ast.Load()),
                        attr="utc",
                        ctx=ast.Load(),
                    )
                    node.args = [tz_arg]
                    self.transformations_count += 1

        return self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.AST:
        for rule in self.rules:
            if rule.rule_type == RuleType.REFACTOR_DECORATOR:
                new_decorator_list = []
                for dec in node.decorator_list:
                    # e.g. @validator('name') or @validator
                    target_name = None
                    if isinstance(dec, ast.Name) and dec.id == rule.source_symbol:
                        dec.id = rule.target_symbol
                        self.transformations_count += 1
                    elif (
                        isinstance(dec, ast.Call)
                        and isinstance(dec.func, ast.Name)
                        and dec.func.id == rule.source_symbol
                    ):
                        dec.func.id = rule.target_symbol
                        self.transformations_count += 1
                    new_decorator_list.append(dec)
                node.decorator_list = new_decorator_list

        return self.generic_visit(node)


class ASTCodeTransformer:
    """
    Applies codemods to source files and synthesizes verified unified diffs.
    """

    def transform_code(
        self, file_path: str, source_code: str, rules: List[MigrationRule]
    ) -> TransformResult:
        """Parses, modifies, and unparses Python source code."""
        if not source_code.strip() or not rules:
            return TransformResult(
                file_path=file_path,
                transformations_applied=0,
                modified_code=source_code,
                original_code=source_code,
                syntax_valid=True,
            )

        try:
            tree = ast.parse(source_code, filename=file_path)
        except SyntaxError as e:
            return TransformResult(
                file_path=file_path,
                transformations_applied=0,
                modified_code=source_code,
                original_code=source_code,
                syntax_valid=False,
                error_message=f"Initial source has syntax error: {str(e)}",
            )

        visitor = CodemodVisitor(rules)
        modified_tree = visitor.visit(tree)
        ast.fix_missing_locations(modified_tree)

        if visitor.transformations_count == 0:
            return TransformResult(
                file_path=file_path,
                transformations_applied=0,
                modified_code=source_code,
                original_code=source_code,
                syntax_valid=True,
            )

        try:
            unparsed = ast.unparse(modified_tree)
            # Verify the transformed code parses without syntax errors
            ast.parse(unparsed)
            syntax_valid = True
            error_msg = None
        except Exception as e:
            syntax_valid = False
            unparsed = source_code
            error_msg = f"Codemod generated invalid syntax: {str(e)}"

        diff = None
        if visitor.transformations_count > 0 and syntax_valid:
            orig_lines = source_code.splitlines(keepends=True)
            mod_lines = (unparsed + "\n").splitlines(keepends=True)
            diff_lines = list(
                difflib.unified_diff(
                    orig_lines,
                    mod_lines,
                    fromfile=f"a/{file_path}",
                    tofile=f"b/{file_path}",
                )
            )
            diff = "".join(diff_lines)

        return TransformResult(
            file_path=file_path,
            transformations_applied=visitor.transformations_count,
            modified_code=unparsed,
            original_code=source_code,
            unified_diff=diff,
            syntax_valid=syntax_valid,
            error_message=error_msg,
        )
