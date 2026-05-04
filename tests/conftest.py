"""Pytest configuration and fixtures for Oborovo model tests."""
import importlib.util
import sys
from pathlib import Path

# Add domain to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


CORE_LEGACY_TEST_FILES = {
    "test_hybrid_clipping.py",
    "test_wind1_fixture.py",
    "test_bess_engine.py",
    "test_capex_tree.py",
    "test_equity.py",
    "test_generic_tax.py",
    "test_goal_seek.py",
    "test_hybrid_engine.py",
    "test_hybrid_lp_engine.py",
    "test_monte_carlo.py",
    "test_waterfall_dscr.py",
    "test_wind_engine.py",
}

SQLALCHEMY_TEST_FILES = {
    "test_persistence.py",
    "test_repository.py",
}

OPENPYXL_TEST_FILES = {
    "test_fid_deck_excel.py",
}

_CALIBRATION_DISABLED_FILES = frozenset([
    "test_debt_dscr_schedule_policy.py",
    "test_debt_excel_alignment.py",
    "test_finco_gpt_calibration_runner.py",
    "test_finco_gpt_calibration_serialization.py",
    "test_finco_gpt_headless_core.py",
    "test_headless_calibration_runner.py",
    "test_oborovo_excel_reconciliation.py",
    "test_opex_excel_alignment.py",
    "test_period_engine_excel_alignment.py",
    "test_pl_tax_excel_alignment.py",
    "test_project_irr_excel_alignment.py",
    "test_regression.py",
    "test_revenue_excel_alignment.py",
    "test_revenue_formula_units.py",
    "test_shl_excel_alignment.py",
    "test_tuho_excel_reconciliation.py",
])


def _module_available(module_name: str) -> bool:
    return importlib.util.find_spec(module_name) is not None


def _app_calibration_available() -> bool:
    """Check if app.calibration can be imported (not disabled by guard)."""
    spec = importlib.util.find_spec("app.calibration")
    if spec is None:
        return False
    try:
        importlib.import_module("app.calibration")
        return True
    except ImportError:
        return False


def pytest_ignore_collect(collection_path, config):
    """Skip optional legacy test modules when their runtime package is absent,
    or when app.calibration is disabled in industry-engine-refactor."""
    path = Path(str(collection_path))
    name = path.name
    full_path = str(path)

    # Skip files that require app.calibration when it's disabled
    if name in _CALIBRATION_DISABLED_FILES and not _app_calibration_available():
        return True

    # Skip integration test that uses ProjectInputs.create_default_oborovo
    # which requires app.calibration (oborovo shim imports from there)
    if "integration/test_fid_deck_excel.py" in full_path:
        return True

    if name in CORE_LEGACY_TEST_FILES and not _module_available("core"):
        return True
    if name in SQLALCHEMY_TEST_FILES and not _module_available("sqlalchemy"):
        return True
    if name in OPENPYXL_TEST_FILES and not _module_available("openpyxl"):
        return True
    return False
