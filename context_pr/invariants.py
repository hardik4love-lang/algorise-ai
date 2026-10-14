"""
ContextPR: Contract & Invariant Extractor
Inspects AST function signatures and type contracts between git commits to flag breaking API shifts.
"""

from __future__ import annotations

import ast
from typing import Dict, List, Optional, Tuple

from .models import ChangedSymbol, ChangeType


class SignatureVisitor(ast.NodeVisitor):
    """Extracts function and method signatures with parameter definitions."""

    def __init__(self, file_path: str):
        self.file_path = file_path
        self.signatures: Dict[str, Tuple[ast.FunctionDef, int]] = {}

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self.signatures[node.name] = (node, node.lineno)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self.signatures[node.name] = (node, node.lineno)
        self.generic_visit(node)


class InvariantExtractor:
    """
    Compares AST structures between base and head versions of a file to detect interface regressions.
    """

    def analyze_diff(
        self,
        file_path: str,
        old_source: str,
        new_source: str,
    ) -> List[ChangedSymbol]:
        """Compares old and new source code of a file and returns all changed symbols."""
        changed: List[ChangedSymbol] = []

        try:
            old_tree = ast.parse(old_source, filename=file_path) if old_source else None
            new_tree = ast.parse(new_source, filename=file_path) if new_source else None
        except SyntaxError:
            return changed

        old_vis = SignatureVisitor(file_path)
        if old_tree:
            old_vis.visit(old_tree)

        new_vis = SignatureVisitor(file_path)
        if new_tree:
            new_vis.visit(new_tree)

        # 1. Check for deleted or modified symbols
        for name, (old_fn, line_no) in old_vis.signatures.items():
            old_sig = self._format_signature(old_fn)

            if name not in new_vis.signatures:
                # Deleted symbol
                changed.append(
                    ChangedSymbol(
                        symbol_name=name,
                        file_path=file_path,
                        change_type=ChangeType.DELETED_SYMBOL,
                        line_number=line_no,
                        old_signature=old_sig,
                        new_signature=None,
                        is_breaking=True,
                        details=f"Function or method '{name}' was deleted or renamed.",
                    )
                )
            else:
                new_fn, new_line = new_vis.signatures[name]
                new_sig = self._format_signature(new_fn)

                if old_sig != new_sig:
                    is_breaking, reason = self._check_breaking_signature(old_fn, new_fn)
                    changed.append(
                        ChangedSymbol(
                            symbol_name=name,
                            file_path=file_path,
                            change_type=(
                                ChangeType.SIGNATURE_BREAK if is_breaking
                                else ChangeType.FUNCTION_MODIFIED
                            ),
                            line_number=new_line,
                            old_signature=old_sig,
                            new_signature=new_sig,
                            is_breaking=is_breaking,
                            details=reason,
                        )
                    )

        # 2. Check for newly introduced symbols
        for name, (new_fn, line_no) in new_vis.signatures.items():
            if name not in old_vis.signatures:
                changed.append(
                    ChangedSymbol(
                        symbol_name=name,
                        file_path=file_path,
                        change_type=ChangeType.NEW_SYMBOL,
                        line_number=line_no,
                        old_signature=None,
                        new_signature=self._format_signature(new_fn),
                        is_breaking=False,
                        details=f"New function '{name}' added.",
                    )
                )

        return changed

    def _format_signature(self, fn: ast.FunctionDef) -> str:
        args = []
        for a in fn.args.args:
            ann = f": {ast.unparse(a.annotation)}" if a.annotation else ""
            args.append(f"{a.arg}{ann}")
        ret = f" -> {ast.unparse(fn.returns)}" if fn.returns else ""
        return f"{fn.name}({', '.join(args)}){ret}"

    def _check_breaking_signature(
        self, old_fn: ast.FunctionDef, new_fn: ast.FunctionDef
    ) -> Tuple[bool, str]:
        """Evaluates whether changes in arguments constitute a breaking change."""
        old_args = [a.arg for a in old_fn.args.args if a.arg != "self"]
        new_args = [a.arg for a in new_fn.args.args if a.arg != "self"]

        # Number of default arguments in new function
        new_defaults_count = len(new_fn.args.defaults)
        new_required_args = new_args[:-new_defaults_count] if new_defaults_count > 0 else new_args

        # If new required arguments were added that old callers don't provide:
        added_required = [arg for arg in new_required_args if arg not in old_args]
        if added_required:
            return True, f"New required argument(s) without defaults added: {', '.join(added_required)}"

        # If parameters were removed
        removed_args = [arg for arg in old_args if arg not in new_args]
        if removed_args:
            return True, f"Existing argument(s) removed: {', '.join(removed_args)}"

        return False, "Signature updated backward-compatibly (default arguments or annotations added)."
