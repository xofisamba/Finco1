"""Runtime import guard — reject forbidden imports in production modules."""
import ast
import os
import inspect
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).parent.parent

# Files to check (runtime modules, not tests/docs/tools/legacy)
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
]

FORBIDDEN = [
    "/root/.openclaw",
    "core.tax.generic_tax",
    "tools.calibration_legacy",
    "from app.calibration",
    "import app.calibration",
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