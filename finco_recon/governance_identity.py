"""AST guard for project-identity driven financial dispatch."""
from __future__ import annotations

import ast
from pathlib import Path


_IDENTITY_ATTRIBUTES = {"name", "code", "baseline_id", "source_workbook"}
_IDENTITY_NAMES = {"baseline_id", "project_name", "project_code", "source_workbook"}


def _is_identity_reference(node: ast.AST) -> bool:
    if isinstance(node, ast.Name):
        return node.id in _IDENTITY_NAMES
    if isinstance(node, ast.Attribute):
        return node.attr in _IDENTITY_ATTRIBUTES and (
            isinstance(node.value, ast.Name)
            and node.value.id in {"project", "project_info", "info", "inputs"}
        )
    return False


def _contains_string_literal(node: ast.AST) -> bool:
    return any(
        isinstance(child, ast.Constant) and isinstance(child.value, str)
        for child in ast.walk(node)
    )


def find_identity_dispatch(source: str, *, filename: str = "<unknown>") -> list[str]:
    """Return line-oriented findings for identity comparisons that control execution."""
    tree = ast.parse(source, filename=filename)
    findings: list[str] = []
    for control in ast.walk(tree):
        if isinstance(control, (ast.If, ast.IfExp, ast.While)):
            test = control.test
        elif isinstance(control, ast.comprehension):
            for test in control.ifs:
                if _contains_string_literal(test) and any(
                    _is_identity_reference(node) for node in ast.walk(test)
                ):
                    findings.append(f"{filename}:{test.lineno}: identity-based execution filter")
            continue
        else:
            continue
        if _contains_string_literal(test) and any(
            _is_identity_reference(node) for node in ast.walk(test)
        ):
            findings.append(f"{filename}:{test.lineno}: identity-based execution branch")
    return findings


def scan_identity_dispatch(paths: list[Path]) -> list[str]:
    findings: list[str] = []
    for path in paths:
        findings.extend(
            find_identity_dispatch(path.read_text(encoding="utf-8"), filename=str(path))
        )
    return findings
