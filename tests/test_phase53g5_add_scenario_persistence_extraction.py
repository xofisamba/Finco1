"""Phase 53G-5 — extraction test for add_scenario persistence."""
from __future__ import annotations
import re
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCENARIOS_PY = REPO_ROOT / "app" / "persistence" / "scenarios_repository.py"
REPOSITORY_PY = REPO_ROOT / "app" / "persistence" / "repository.py"

def _read(path):
    return Path(path).read_text(encoding="utf-8")

class TestMovedFunction:
    def test_add_scenario_defined_in_scenarios(self):
        assert "def add_scenario(" in _read(SCENARIOS_PY)
    def test_add_scenario_not_defined_in_repository(self):
        text = _read(REPOSITORY_PY)
        n = text.count("def add_scenario(")
        assert n == 0

class TestPublicCompatibility:
    def test_add_scenario_importable(self):
        from app.persistence.repository import add_scenario
        assert callable(add_scenario)
    def test_re_export_includes_add_scenario(self):
        text = _read(REPOSITORY_PY)
        assert "add_scenario," in text

class TestP0PinStillPasses:
    def test_add_scenario_pin_re_pointed(self):
        text = _read(REPO_ROOT / "tests/test_phase53g1_add_scenario_p0_behavior_pin.py")
        assert "PIN_TARGET = SCENARIOS_PY" in text

class TestOtherHighRiskWritesUntouched:
    @pytest.mark.parametrize("fn_name", [
        "update_scenario_overrides",
        "get_or_create_base_case_scenario",
    ])
    def test_other_high_risk_write_still_in_repository_body(self, fn_name):
        from app.persistence import repository
        assert hasattr(repository, fn_name)
        text = _read(REPOSITORY_PY)
        assert f"def {fn_name}" in text

class TestDataclassesUntouched:
    @pytest.mark.parametrize("cls_name", ["ProjectRecord", "ScenarioRecord", "WorkspaceStateRecord"])
    def test_dataclass_still_in_repository(self, cls_name):
        assert f"class {cls_name}" in _read(REPOSITORY_PY)

class TestRepositoryPyShrank:
    def test_repository_py_under_700_lines(self):
        text = _read(REPOSITORY_PY)
        n = len(text.splitlines())
        assert n < 700, f"repository.py should be < 700 lines after 53G-5, got {n}"
