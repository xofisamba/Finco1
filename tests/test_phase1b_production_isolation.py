"""
tests/test_phase1b_production_isolation.py — Production isolation guardrails.

Strengthens the Phase 1A AST import-boundary scan to cover Phase 1B modules.

Scans:
  app/, domain/, finco_core/, main_web.py, main_api.py

Fails if any of those files import:
  finco_parity
  finco_parity.baselines
  finco_parity.comparison
  finco_parity.generate_baselines
  finco_parity.manifest
  finco_parity.canonical

Also proves:
  - Baseline JSON files are not opened from production code (string scan).
  - No production route exposes baseline artifacts (string scan).
  - No application startup imports finco_parity (import-boundary test).
  - No package import causes an engine run (via module-level import test).
"""
from __future__ import annotations

import ast
import importlib
import sys
from pathlib import Path
from typing import Iterator

import pytest

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).parent.parent

# Production source trees to scan.
_PRODUCTION_DIRS = [
    _REPO_ROOT / "app",
    _REPO_ROOT / "domain",
    _REPO_ROOT / "finco_core",
]
_PRODUCTION_FILES = [
    _REPO_ROOT / "main_web.py",
    _REPO_ROOT / "main_api.py",
]

# Forbidden finco_parity module names (any import of these in production code fails).
_FORBIDDEN_IMPORTS = frozenset({
    "finco_parity",
    "finco_parity.baselines",
    "finco_parity.canonical",
    "finco_parity.comparison",
    "finco_parity.generate_baselines",
    "finco_parity.legacy_snapshot",
    "finco_parity.manifest",
    "finco_parity.normalization",
    "finco_parity.schema",
})

# Snippets that must not appear in production code (heuristic string scan).
_FORBIDDEN_STRINGS = [
    "baselines/snapshots",
    "finco_parity/baselines",
    "generate_baselines",
    "finco_parity.comparison",
    "finco_parity.canonical",
    "finco_parity.manifest",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _collect_python_files() -> list[Path]:
    """Collect all .py files from production dirs and standalone files."""
    files: list[Path] = []
    for d in _PRODUCTION_DIRS:
        if d.exists():
            files.extend(d.rglob("*.py"))
    for f in _PRODUCTION_FILES:
        if f.exists():
            files.append(f)
    return files


def _extract_imports(source: str) -> Iterator[str]:
    """Yield all module names imported by *source* via import/from...import."""
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
                # Also yield the fully qualified sub-name for from X import Y patterns.
                for alias in node.names:
                    yield f"{node.module}.{alias.name}"


# ---------------------------------------------------------------------------
# AST-based import boundary scan
# ---------------------------------------------------------------------------

def test_production_code_does_not_import_finco_parity() -> None:
    """No production file may import any finco_parity module (AST scan)."""
    violations: list[str] = []

    for path in _collect_python_files():
        try:
            source = path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue

        for mod_name in _extract_imports(source):
            # Check exact match or prefix match (e.g. finco_parity.schema).
            top = mod_name.split(".")[0]
            if top == "finco_parity" or mod_name in _FORBIDDEN_IMPORTS:
                rel = path.relative_to(_REPO_ROOT)
                violations.append(f"{rel}: imports {mod_name!r}")

    assert not violations, (
        "Production code imports finco_parity (forbidden):\n"
        + "\n".join(f"  {v}" for v in sorted(violations))
    )


# ---------------------------------------------------------------------------
# String scan: baseline JSON not opened from production code
# ---------------------------------------------------------------------------

def test_production_code_does_not_reference_baseline_files() -> None:
    """No production file contains references to baseline artifact paths."""
    violations: list[str] = []

    for path in _collect_python_files():
        try:
            source = path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue

        for snippet in _FORBIDDEN_STRINGS:
            if snippet in source:
                rel = path.relative_to(_REPO_ROOT)
                violations.append(f"{rel}: contains {snippet!r}")

    assert not violations, (
        "Production code references finco_parity baseline artifacts:\n"
        + "\n".join(f"  {v}" for v in sorted(violations))
    )


# ---------------------------------------------------------------------------
# Import-safe: importing finco_parity package-level must not trigger engine run
# ---------------------------------------------------------------------------

def test_importing_finco_parity_does_not_run_engine(monkeypatch) -> None:
    """Importing finco_parity.* at module level must not execute any engine code."""
    # We verify this indirectly: if ui_runner.run_demo_project is called during
    # import of finco_parity.* modules, it would raise (since we monkeypatch it).
    called: list[str] = []

    # Patch the engine entry point to detect any call during import.
    import unittest.mock as _mock

    try:
        import app.ui_runner as _ui  # type: ignore[import]
        original = _ui.run_demo_project

        def _sentinel(*args, **kwargs):
            called.append(f"run_demo_project({args!r})")
            return original(*args, **kwargs)

        monkeypatch.setattr(_ui, "run_demo_project", _sentinel)
    except ImportError:
        pass  # app not importable in this environment — skip engine guard

    # Import all finco_parity modules.
    import finco_parity
    import finco_parity.schema
    import finco_parity.normalization
    import finco_parity.canonical
    import finco_parity.comparison
    import finco_parity.manifest

    assert not called, (
        "Importing finco_parity modules triggered engine execution:\n"
        + "\n".join(f"  {c}" for c in called)
    )


# ---------------------------------------------------------------------------
# CLI check mode: --check must not write files
# ---------------------------------------------------------------------------

def test_check_mode_does_not_write_files(tmp_path: Path, monkeypatch) -> None:
    """python -m finco_parity.generate_baselines --check must not write any file."""
    # Redirect SNAPSHOTS_DIR and write-through to a monitored location.
    writes: list[str] = []
    original_write = Path.write_bytes

    def _recording_write(self, data):
        writes.append(str(self))
        return original_write(self, data)

    monkeypatch.setattr(Path, "write_bytes", _recording_write)
    monkeypatch.setattr(Path, "write_text", lambda self, *a, **kw: writes.append(str(self)))

    from finco_parity.generate_baselines import cmd_check
    from finco_parity.legacy_snapshot import ALL_BASELINE_IDS

    # cmd_check uses a TemporaryDirectory internally — writes there are allowed.
    # We only care that files outside tmp are not written.
    # Run the check (may pass or fail — we don't care about the result here,
    # just that it doesn't write to committed paths).
    try:
        cmd_check(list(ALL_BASELINE_IDS), verbose=False)
    except Exception:
        pass

    # Any writes that happened must be inside a temp dir, not to the repo.
    from finco_parity.manifest import SNAPSHOTS_DIR
    repo_writes = [w for w in writes if str(SNAPSHOTS_DIR) in w]
    assert not repo_writes, (
        "--check mode wrote to committed snapshot paths:\n"
        + "\n".join(f"  {w}" for w in repo_writes)
    )


# ---------------------------------------------------------------------------
# Workflow contract: no paths filter
# ---------------------------------------------------------------------------

def test_phase1b_workflow_has_no_paths_filter() -> None:
    """Phase 1B baseline check workflow must trigger on all PRs to main — no paths filter."""
    import re

    wf_path = Path(__file__).parent.parent / ".github" / "workflows" / "phase1b_baseline_check.yml"
    assert wf_path.exists(), f"Workflow file not found: {wf_path}"
    text = wf_path.read_text(encoding="utf-8")

    # Must NOT have a 'paths:' key under the pull_request trigger.
    # A paths filter would restrict the guardrail to only certain file changes.
    assert "paths:" not in text, (
        "Phase 1B baseline check workflow must not have a 'paths:' filter; "
        "it must run on every PR to main to catch engine changes."
    )

    # Must trigger on pull_request to main.
    assert "pull_request" in text, "Workflow must have a pull_request trigger."
    assert "branches: [main]" in text or "branches:\n      - main" in text, (
        "Workflow must target the main branch."
    )
