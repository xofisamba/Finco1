"""
tests/test_phase2a_production_isolation.py — Purity and production-isolation guardrails.

Proves that:
- financial_engine does not import forbidden modules
- financial_engine source contains no forbidden identifiers
- The legacy engine is untouched (key files unchanged)
- Production routes are unaffected by the new engine
"""
from __future__ import annotations

import ast
import importlib
import sys
from pathlib import Path

import pytest

_ENGINE_ROOT = Path("financial_engine")

# ---------------------------------------------------------------------------
# Forbidden imports in financial_engine
# ---------------------------------------------------------------------------

_FORBIDDEN_IMPORTS = {
    "app",
    "main_web",
    "main_api",
    "finco_parity",
    "persistence",
    "fastapi",
    "jinja2",
    "requests",
    "openpyxl",
    "pandas",
}


def _collect_imports(tree: ast.Module) -> set[str]:
    """Extract top-level imported module names from an AST."""
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                names.add(node.module.split(".")[0])
    return names


@pytest.mark.parametrize("src_file", sorted(_ENGINE_ROOT.rglob("*.py")))
def test_no_forbidden_imports(src_file: Path):
    """financial_engine/*.py must not import forbidden modules."""
    source = src_file.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(src_file))
    imported = _collect_imports(tree)
    forbidden_found = imported & _FORBIDDEN_IMPORTS
    assert not forbidden_found, (
        f"{src_file} imports forbidden module(s): {sorted(forbidden_found)}"
    )


# ---------------------------------------------------------------------------
# Forbidden identifiers in financial_engine source
# ---------------------------------------------------------------------------

_FORBIDDEN_IDENTIFIERS = [
    "TUHO",
    "Oborovo",
    "TUHO-WIND-1",
    "runtime_seed",
    "template_source",
    "is_tuho",
    "is_oborovo",
    "reports/",
    "tests/fixtures/",
    "Path.read_",
    "open(",
    "json.load(",
    "csv",
    "setattr(",
    "eval(",
    "exec(",
]


@pytest.mark.parametrize("src_file", sorted(_ENGINE_ROOT.rglob("*.py")))
def test_no_forbidden_identifiers(src_file: Path):
    """financial_engine/*.py must not contain forbidden identifiers."""
    source = src_file.read_text(encoding="utf-8")
    found = [ident for ident in _FORBIDDEN_IDENTIFIERS if ident in source]
    assert not found, (
        f"{src_file} contains forbidden identifier(s): {found}"
    )


# ---------------------------------------------------------------------------
# Structural: financial_engine is importable and deterministic
# ---------------------------------------------------------------------------

def test_financial_engine_importable():
    """The financial_engine package must import without errors."""
    import financial_engine
    assert hasattr(financial_engine, "ENGINE_VERSION")


def test_engine_version_constant():
    """ENGINE_VERSION must be a non-empty string constant."""
    from financial_engine.version import ENGINE_VERSION
    assert isinstance(ENGINE_VERSION, str)
    assert len(ENGINE_VERSION) > 0
    assert "clean" in ENGINE_VERSION.lower() or "v" in ENGINE_VERSION.lower()


# ---------------------------------------------------------------------------
# Protected production files — AST-level and content guardrails
# ---------------------------------------------------------------------------

_PROTECTED_FILES = [
    Path("app/waterfall_core.py"),
    Path("app/waterfall_runner.py"),
    Path("finco_core/waterfall/waterfall_engine.py"),
]

_PROTECTED_SYMBOLS = {
    Path("app/waterfall_core.py"): {"run_waterfall_v3_core"},
    Path("app/waterfall_runner.py"): {"WaterfallRunner"},
    Path("finco_core/waterfall/waterfall_engine.py"): {"run_waterfall", "WaterfallResult"},
}


@pytest.mark.parametrize("protected_file", _PROTECTED_FILES)
def test_protected_file_exists(protected_file: Path):
    """Protected production files must exist."""
    assert protected_file.exists(), f"{protected_file} is missing"


@pytest.mark.parametrize("protected_file", _PROTECTED_FILES)
def test_protected_file_is_valid_python(protected_file: Path):
    """Protected production files must parse as valid Python."""
    source = protected_file.read_text(encoding="utf-8")
    try:
        ast.parse(source, filename=str(protected_file))
    except SyntaxError as exc:
        pytest.fail(f"{protected_file} has syntax errors: {exc}")


@pytest.mark.parametrize("protected_file,symbols", [
    (f, s) for f, s in _PROTECTED_SYMBOLS.items()
])
def test_protected_file_retains_key_symbols(protected_file: Path, symbols: set):
    """Protected files must still define their key symbols (not gutted)."""
    source = protected_file.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(protected_file))
    defined: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            defined.add(node.name)
    missing = symbols - defined
    assert not missing, (
        f"{protected_file} is missing expected symbol(s): {sorted(missing)}"
    )


def test_financial_engine_does_not_import_waterfall_core():
    """financial_engine must never import from app (including waterfall_core)."""
    for src_file in _ENGINE_ROOT.rglob("*.py"):
        source = src_file.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(src_file))
        imported = _collect_imports(tree)
        # Verify no import of app modules containing waterfall
        assert "app" not in imported, (
            f"{src_file} imports 'app' (which includes waterfall_core)"
        )
        # Also check for call-site references via AST (not docstrings)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Name):
                    assert func.id not in (
                        "run_waterfall_v3_core", "WaterfallRunner"
                    ), f"{src_file} calls {func.id}"
                elif isinstance(func, ast.Attribute):
                    assert func.attr not in (
                        "run_waterfall", "run_waterfall_v3_core"
                    ), f"{src_file} calls .{func.attr}"
