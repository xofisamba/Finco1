from __future__ import annotations

import builtins
import importlib
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
DOC_PATH = REPO_ROOT / "docs" / "phase36_legacy_streamlit_cleanup_clean_env_ci.md"
MATRIX_PATH = REPO_ROOT / "docs" / "phase36_legacy_streamlit_cleanup_matrix.md"
TARGET_MODULE_FILES = [
    REPO_ROOT / "app" / "cache.py",
    REPO_ROOT / "app" / "input_forms.py",
    REPO_ROOT / "app" / "ui" / "components.py",
]
DEPENDENCY_FILES = [
    REPO_ROOT / "requirements.txt",
    REPO_ROOT / "pyproject.toml",
    REPO_ROOT / "constraints.txt",
]


def _block_streamlit_imports():
    original_import = builtins.__import__

    def guarded_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "streamlit" or name.startswith("streamlit."):
            raise ModuleNotFoundError("No module named 'streamlit'")
        return original_import(name, globals, locals, fromlist, level)

    return guarded_import


def _import_without_streamlit(module_name: str):
    original_import = builtins.__import__
    builtins.__import__ = _block_streamlit_imports()
    try:
        sys.modules.pop("streamlit", None)
        sys.modules.pop(module_name, None)
        return importlib.import_module(module_name)
    finally:
        builtins.__import__ = original_import


def test_phase36_docs_exist():
    assert DOC_PATH.exists()
    assert MATRIX_PATH.exists()


def test_target_modules_have_no_direct_streamlit_import_statements():
    for path in TARGET_MODULE_FILES:
        content = path.read_text(encoding="utf-8")
        assert "import streamlit" not in content
        assert "from streamlit" not in content


def test_streamlit_not_added_to_dependency_files():
    for path in DEPENDENCY_FILES:
        if path.exists():
            content = path.read_text(encoding="utf-8").lower()
            assert "streamlit" not in content, f"Unexpected streamlit dependency in {path.name}"


def test_app_cache_imports_without_streamlit():
    module = _import_without_streamlit("app.cache")
    assert hasattr(module, "cache_data")
    assert callable(module.clear_all_caches)


def test_app_input_forms_imports_without_streamlit():
    module = _import_without_streamlit("app.input_forms")
    assert hasattr(module, "apply_project_overrides")
    assert callable(module.apply_project_overrides)


def test_app_ui_components_imports_without_streamlit():
    module = _import_without_streamlit("app.ui.components")
    assert hasattr(module, "format_metric_value")
    assert module.format_metric_value(1234, "currency") == "1k"
    assert module.STATUS_LABELS["ok"] == "✅ Full model"
    assert module.STATUS_LABELS["warning"] == "⚠️ Warning"
    assert module.STATUS_LABELS["error"] == "❌ Error"


def test_app_ui_components_contains_no_mojibake_markers():
    content = (REPO_ROOT / "app" / "ui" / "components.py").read_text(encoding="utf-8")
    markers = tuple(bytes.fromhex(hex_bytes).decode("utf-8", errors="ignore") for hex_bytes in (
        "c3a2c593",
        "c3a2c5a1",
        "c3b0c5b8",
        "c3a2c29d",
    ))
    for marker in markers:
        assert marker not in content


def test_pytest_collect_only_succeeds_without_streamlit():
    env = dict(**__import__("os").environ)
    env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        env=env,
    )
    output = result.stdout + "\n" + result.stderr
    assert "No module named 'streamlit'" not in output
    if result.returncode != 0:
        assert "No module named 'sqlalchemy'" in output or "No module named 'scipy'" in output, output


def test_docs_state_no_formula_runtime_changes_and_non_claims():
    content = DOC_PATH.read_text(encoding="utf-8")
    assert "No financial formula changes" in content
    assert "No runtime calculation changes" in content
    assert "No lender-ready claim" in content
    assert "No bank-ready claim" in content
    assert "No audit-ready claim" in content
    assert "No certification-ready claim" in content
    assert "No SaaS-ready claim" in content
    assert "G20 remains BLOCKED" in content
    assert "R99/R102 remain NOT APPROVED" in content
