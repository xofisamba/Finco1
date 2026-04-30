"""FincoGPT headless-calibration smoke tests.

These tests enforce the first enterprise-grade boundary: the production
calculation core must be importable without Streamlit and Excel calibration
anchors must be committed as structured fixtures rather than raw workbooks.
"""
from __future__ import annotations

import ast
import importlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _imports_from_file(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".")[0])
    return imports


def test_waterfall_core_does_not_import_streamlit() -> None:
    """The uncached calculation path must not import Streamlit."""
    imports = _imports_from_file(ROOT / "app" / "waterfall_core.py")
    assert "streamlit" not in imports


def test_waterfall_core_importable_without_streamlit_runtime() -> None:
    """Importing the core module should not require Streamlit runtime."""
    module = importlib.import_module("app.waterfall_core")
    assert hasattr(module, "run_waterfall_v3_core")


def test_excel_calibration_targets_fixture_shape() -> None:
    """Excel calibration anchors are stored in a structured JSON fixture."""
    fixture_path = ROOT / "tests" / "fixtures" / "excel_calibration_targets.json"
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))

    assert "metadata" in payload
    assert set(payload) >= {"oborovo", "tuho"}

    for project_key in ("oborovo", "tuho"):
        project = payload[project_key]
        assert project["calibration_status"] == "anchor_only"
        assert isinstance(project["anchors"], dict)
        assert "senior_debt_keur" in project["anchors"]
        assert project["anchors"]["senior_debt_keur"]["value"] > 0
        assert project["anchors"]["senior_debt_keur"]["source"]


def test_raw_xlsm_files_are_not_committed() -> None:
    """Raw Excel workbooks should not be committed to the public repository."""
    committed_xlsm = [p for p in ROOT.rglob("*.xlsm") if ".git" not in p.parts]
    assert committed_xlsm == []
