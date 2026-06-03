"""Phase 53G-6 — extraction test for update_scenario_overrides persistence."""
from __future__ import annotations
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCENARIOS_PY = REPO_ROOT / "app" / "persistence" / "scenarios_repository.py"
REPOSITORY_PY = REPO_ROOT / "app" / "persistence" / "repository.py"

def _read(p):
    return Path(p).read_text(encoding="utf-8")

class TestMovedFunction:
    def test_uso_defined_in_scenarios(self):
        assert "def update_scenario_overrides(" in _read(SCENARIOS_PY)
    def test_uso_not_defined_in_repository(self):
        text = _read(REPOSITORY_PY)
        n = text.count("def update_scenario_overrides(")
        assert n == 0

class TestPublicCompatibility:
    def test_uso_importable(self):
        from app.persistence.repository import update_scenario_overrides
        assert callable(update_scenario_overrides)
    def test_re_export_includes_uso(self):
        assert "update_scenario_overrides," in _read(REPOSITORY_PY)

class TestP0PinStillPasses:
    def test_uso_pin_re_pointed(self):
        text = _read(REPO_ROOT / "tests/test_phase53g1_update_overrides_p0_behavior_pin.py")
        assert "PIN_TARGET = SCENARIOS_PY" in text

class TestOtherHighRiskWritesUntouched:
    @pytest.mark.parametrize("fn_name", [
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
    def test_repository_py_under_610_lines(self):
        text = _read(REPOSITORY_PY)
        n = len(text.splitlines())
        assert n < 610, f"repository.py should be < 610 lines after 53G-6, got {n}"
