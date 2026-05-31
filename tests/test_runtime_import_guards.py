"""Runtime import guards for the current FastAPI/HTMX production stack."""
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent

PRODUCTION_RUNTIME_FILES = [
    "main_web.py",
    "app/cache.py",
    "app/ui_runner.py",
    "app/input_forms.py",
    "app/input_helpers.py",
    "app/excel_export.py",
    "app/output_tables.py",
    "app/waterfall_core.py",
    "app/waterfall_runner.py",
    "app/portfolio_runner.py",
    "domain/inputs.py",
    "domain/validation.py",
]

FORBIDDEN = [
    "/root/.openclaw",
    "ProjectInputs.create_default_oborovo",
    "ProjectInputs.create_default_tuho_wind1",
]


def test_current_runtime_files_exist():
    for filename in PRODUCTION_RUNTIME_FILES:
        assert (REPO_ROOT / filename).exists(), f"Missing runtime file: {filename}"


def test_runtime_files_do_not_contain_forbidden_strings():
    for filename in PRODUCTION_RUNTIME_FILES:
        content = (REPO_ROOT / filename).read_text(encoding="utf-8")
        for token in FORBIDDEN:
            assert token not in content, f"{filename} must not contain {token!r}"


def test_app_cache_does_not_use_module_level_st_cache_decorators():
    content = (REPO_ROOT / "app" / "cache.py").read_text(encoding="utf-8")
    assert "@st.cache_data" not in content
    assert "def cache_data(" in content
    assert "get_streamlit" in content


def test_utils_cache_remains_streamlit_free_shim():
    content = (REPO_ROOT / "utils" / "cache.py").read_text(encoding="utf-8")
    assert "@st.cache_data" not in content
    assert "import streamlit" not in content
    assert "from streamlit" not in content


def test_legacy_streamlit_shell_is_not_production_entrypoint():
    content = (REPO_ROOT / "streamlit_app.py").read_text(encoding="utf-8")
    assert "import streamlit as st" in content
    service_content = (REPO_ROOT / "deploy" / "systemd" / "finco-web.service").read_text(encoding="utf-8")
    assert "streamlit_app.py" not in service_content
    assert "main_web:app" in service_content
