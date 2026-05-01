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


def _module_available(module_name: str) -> bool:
    return importlib.util.find_spec(module_name) is not None


def pytest_ignore_collect(collection_path, config):
    """Skip optional legacy test modules when their runtime package is absent."""
    path = Path(str(collection_path))
    name = path.name
    if name in CORE_LEGACY_TEST_FILES and not _module_available("core"):
        return True
    if name in SQLALCHEMY_TEST_FILES and not _module_available("sqlalchemy"):
        return True
    if name in OPENPYXL_TEST_FILES and not _module_available("openpyxl"):
        return True
    return False
