"""
tests/test_phase1c_production_isolation.py — Production isolation guardrails for Phase 1C.

Extends Phase 1B isolation tests to cover the new Phase 1C modules:
  finco_parity.candidate
  finco_parity.dual_run
  finco_parity.compare_candidate

Scans production source trees (app/, domain/, finco_core/, main_web.py, main_api.py)
and asserts that none of them import the Phase 1C candidate comparison modules.
"""
from __future__ import annotations

import ast
from pathlib import Path
from typing import Iterator

import pytest

pytestmark = pytest.mark.unit

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).parent.parent

_PRODUCTION_DIRS = [
    _REPO_ROOT / "app",
    _REPO_ROOT / "domain",
    _REPO_ROOT / "finco_core",
]
_PRODUCTION_FILES = [
    _REPO_ROOT / "main_web.py",
    _REPO_ROOT / "main_api.py",
]

# Phase 1C modules that must not appear in production code.
_FORBIDDEN_PHASE1C_IMPORTS = frozenset({
    "finco_parity.candidate",
    "finco_parity.dual_run",
    "finco_parity.compare_candidate",
})

# String snippets that must not appear in production code.
_FORBIDDEN_PHASE1C_STRINGS = [
    "finco_parity.candidate",
    "finco_parity.dual_run",
    "finco_parity.compare_candidate",
    "CandidateSnapshotProvider",
    "FileCandidateSnapshotProvider",
    "compare_candidate_directory",
    "compare_candidate_snapshot",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _collect_python_files() -> list[Path]:
    files: list[Path] = []
    for d in _PRODUCTION_DIRS:
        if d.exists():
            files.extend(d.rglob("*.py"))
    for f in _PRODUCTION_FILES:
        if f.exists():
            files.append(f)
    return files


def _extract_imports(source: str) -> Iterator[str]:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                yield node.module
                for alias in node.names:
                    yield f"{node.module}.{alias.name}"


# ---------------------------------------------------------------------------
# AST-based import boundary scan
# ---------------------------------------------------------------------------

def test_production_code_does_not_import_phase1c_modules() -> None:
    """No production file may import finco_parity.candidate, .dual_run, or .compare_candidate."""
    violations: list[str] = []

    for path in _collect_python_files():
        try:
            source = path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue

        for mod_name in _extract_imports(source):
            if mod_name in _FORBIDDEN_PHASE1C_IMPORTS:
                rel = path.relative_to(_REPO_ROOT)
                violations.append(f"{rel}: imports {mod_name!r}")

    assert not violations, (
        "Production code imports Phase 1C candidate comparison modules (forbidden):\n"
        + "\n".join(f"  {v}" for v in sorted(violations))
    )


# ---------------------------------------------------------------------------
# String scan
# ---------------------------------------------------------------------------

def test_production_code_does_not_reference_phase1c_symbols() -> None:
    """No production file contains references to Phase 1C candidate symbols."""
    violations: list[str] = []

    for path in _collect_python_files():
        try:
            source = path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue

        for snippet in _FORBIDDEN_PHASE1C_STRINGS:
            if snippet in source:
                rel = path.relative_to(_REPO_ROOT)
                violations.append(f"{rel}: contains {snippet!r}")

    assert not violations, (
        "Production code references Phase 1C candidate comparison symbols:\n"
        + "\n".join(f"  {v}" for v in sorted(violations))
    )


# ---------------------------------------------------------------------------
# Module-level import safety
# ---------------------------------------------------------------------------

def test_importing_phase1c_modules_does_not_run_engine(monkeypatch) -> None:
    """Importing finco_parity Phase 1C modules must not execute any engine code."""
    called: list[str] = []

    try:
        import app.ui_runner as _ui  # type: ignore[import]
        original = _ui.run_demo_project

        def _sentinel(*args, **kwargs):
            called.append(f"run_demo_project({args!r})")
            return original(*args, **kwargs)

        monkeypatch.setattr(_ui, "run_demo_project", _sentinel)
    except ImportError:
        pass  # app not importable — skip engine guard

    import finco_parity.candidate
    import finco_parity.dual_run
    import finco_parity.compare_candidate

    assert not called, (
        "Importing Phase 1C modules triggered engine execution:\n"
        + "\n".join(f"  {c}" for c in called)
    )
