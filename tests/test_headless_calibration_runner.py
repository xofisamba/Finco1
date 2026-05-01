"""Tests for the headless Excel calibration path.

The key contract is architectural: calibration modules must be importable and
inspectable without Streamlit. Full numeric Excel parity is handled by later
calibration tests once all workbook line items are mapped.
"""
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read_repo_file(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_calibration_module_does_not_import_streamlit_or_cache_wrapper() -> None:
    source = _read_repo_file("app/calibration.py")

    assert "import streamlit" not in source
    assert "from app.cache" not in source
    assert "import app.cache" not in source
    assert "WaterfallRunner" not in source
    assert "run_waterfall_v3_core" in source


def test_legacy_calibration_runner_stays_streamlit_free() -> None:
    source = _read_repo_file("app/calibration_runner.py")

    assert "import streamlit" not in source
    assert "from app.cache" not in source
    assert "import app.cache" not in source
    assert "WaterfallRunner" not in source
    assert "run_project_calibration" in source


def test_waterfall_core_stays_streamlit_free() -> None:
    source = _read_repo_file("app/waterfall_core.py")

    assert "import streamlit" not in source
    assert "@st.cache_data" not in source
    assert "run_waterfall_v3_core" in source


def test_cache_wrapper_delegates_to_uncached_core() -> None:
    source = _read_repo_file("app/cache.py")

    assert "@st.cache_data" in source
    assert "from app.waterfall_core import run_waterfall_v3_core" in source
    assert "return run_waterfall_v3_core(" in source
