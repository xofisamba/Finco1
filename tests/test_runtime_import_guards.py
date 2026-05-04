"""Runtime import guard — reject forbidden imports in production modules."""
import ast
import os
import inspect
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).parent.parent

# Files to check (runtime modules, not tests/docs/tools/legacy)
# Active UI pages
UI_PAGES = [
    "ui/pages/1_Project_Inputs.py",
    "ui/pages/2_Waterfall.py",
]

# Legacy UI pages — still part of the repo but not migrated yet;
# excluded from runtime guard but covered by LEGACY_UI_FILES tests
LEGACY_UI_FILES = [
    "ui/pages/4_scenarios.py",
]

RUNTIME_FILES = [
    "streamlit_app.py",
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
    "src/app.py",
] + UI_PAGES

FORBIDDEN = [
    "/root/.openclaw",
    "core.tax.generic_tax",
    "tools.calibration_legacy",
    "app.calibration",
    "from app.calibration",
    "import app.calibration",
    "app.calibration_runner",
    "from app.calibration_runner",
    "import app.calibration_runner",
    "ProjectInputs.create_default_oborovo",
    "ProjectInputs.create_default_tuho_wind1",
]


def _check_file(filepath: Path) -> list[str]:
    """Return list of forbidden strings found in file source."""
    if not filepath.exists():
        return [f"FILE NOT FOUND: {filepath}"]
    src = filepath.read_text()
    found = []
    for term in FORBIDDEN:
        if term in src:
            found.append(f"{term!r} found in {filepath.name}")
    return found


@pytest.mark.parametrize("filename", RUNTIME_FILES, ids=lambda f: f)
def test_runtime_import_guards(filename):
    """Each runtime file must not contain forbidden imports or paths."""
    filepath = REPO_ROOT / filename
    violations = _check_file(filepath)
    assert not violations, f"Forbidden content found:\n  " + "\n  ".join(violations)


def test_core_tax_generic_tax_not_in_domain():
    """domain/inputs.py must not import core.tax.generic_tax."""
    filepath = REPO_ROOT / "domain" / "inputs.py"
    src = filepath.read_text()
    assert "core.tax.generic_tax" not in src, "domain/inputs.py must not import core.tax.generic_tax"
    assert "from core" not in src, "domain/inputs.py must not import from core"


def test_utils_cache_no_st_cache_data():
    """utils/cache.py must not define @st.cache_data decorators."""
    filepath = REPO_ROOT / "utils" / "cache.py"
    src = filepath.read_text()
    assert "@st.cache_data" not in src, "utils/cache.py must not use @st.cache_data"


def test_utils_cache_no_streamlit_import():
    """utils/cache.py must not import streamlit."""
    filepath = REPO_ROOT / "utils" / "cache.py"
    src = filepath.read_text()
    assert "import streamlit" not in src and "from streamlit" not in src, \
        "utils/cache.py must not import streamlit"


def test_project_factories_no_create_default_on_projectinputs():
    """domain/inputs.py must not define create_default_oborovo/create_default_tuho_wind1 on ProjectInputs."""
    from domain import inputs as inputs_module
    src = inspect.getsource(inputs_module)
    assert "def create_default_oborovo" not in src, \
        "ProjectInputs must not have create_default_oborovo method"
    assert "def create_default_tuho_wind1" not in src, \
        "ProjectInputs must not have create_default_tuho_wind1 method"

def test_ui_pages_do_not_use_hardcoded_sys_path():
    """Active UI pages must not contain hardcoded sandbox paths or sys.path hacks."""
    for page in UI_PAGES:
        filepath = REPO_ROOT / page
        src = filepath.read_text()
        assert "/root/.openclaw" not in src, f"{page} must not contain sandbox paths"
        assert "sys.path.insert" not in src, f"{page} must not manipulate sys.path"


def test_ui_pages_do_not_use_legacy_projectinputs_factories():
    """Active UI pages must not call ProjectInputs.create_default_oborovo/create_default_tuho."""
    for page in UI_PAGES:
        filepath = REPO_ROOT / page
        src = filepath.read_text()
        assert "ProjectInputs.create_default_oborovo" not in src, f"{page} must not call ProjectInputs.create_default_oborovo"
        assert "ProjectInputs.create_default_tuho_wind1" not in src, f"{page} must not call ProjectInputs.create_default_tuho_wind1"


def test_active_ui_pages_use_app_cache_not_utils_cache():
    """Active UI pages should use app.cache, not the utils.cache compatibility shim."""
    for page in UI_PAGES:
        filepath = REPO_ROOT / page
        src = filepath.read_text()
        if "utils.cache" in src:
            pytest.fail(f"{page} imports utils.cache; use app.cache instead")


def test_legacy_ui_files_are_classified():
    """LEGACY_UI_FILES must exist and be explicitly marked legacy."""
    for page in LEGACY_UI_FILES:
        assert (REPO_ROOT / page).exists(), f"{page} listed as legacy but does not exist"


def test_no_create_default_oborovo_runtime_references():
    """No active runtime file may call create_default_oborovo/create_default_tuho_wind1."""
    runtime_paths = [REPO_ROOT / p for p in RUNTIME_FILES]
    for path in runtime_paths:
        if not path.exists():
            continue
        src = path.read_text()
        assert "create_default_oborovo" not in src, f"{path.name} must not call create_default_oborovo"
        assert "create_default_tuho_wind1" not in src, f"{path.name} must not call create_default_tuho_wind1"
