"""Phase 53G-7 — extraction test for get_or_create_base_case_scenario persistence.

Also covers get_base_case_scenario helper which moved with it
(used by resolve_active_scenario_runtime_snapshot).
"""
from __future__ import annotations
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCENARIOS_PY = REPO_ROOT / "app" / "persistence" / "scenarios_repository.py"
REPOSITORY_PY = REPO_ROOT / "app" / "persistence" / "repository.py"

def _read(p):
    return Path(p).read_text(encoding="utf-8")


class TestMovedFunctions:
    def test_get_or_create_defined_in_scenarios(self):
        assert "def get_or_create_base_case_scenario(" in _read(SCENARIOS_PY)

    def test_get_or_create_not_in_repository(self):
        text = _read(REPOSITORY_PY)
        n = text.count("def get_or_create_base_case_scenario(")
        assert n == 0

    def test_get_base_case_defined_in_scenarios(self):
        # get_base_case_scenario moved with it (helper for resolve_active_scenario_runtime_snapshot)
        assert "def get_base_case_scenario(" in _read(SCENARIOS_PY)

    def test_get_base_case_not_in_repository(self):
        text = _read(REPOSITORY_PY)
        n = text.count("def get_base_case_scenario(")
        assert n == 0


class TestPublicCompatibility:
    def test_get_or_create_importable(self):
        from app.persistence.repository import get_or_create_base_case_scenario
        assert callable(get_or_create_base_case_scenario)

    def test_get_base_case_importable(self):
        from app.persistence.repository import get_base_case_scenario
        assert callable(get_base_case_scenario)

    def test_re_export_block(self):
        text = _read(REPOSITORY_PY)
        assert "get_or_create_base_case_scenario," in text
        assert "get_base_case_scenario," in text


class TestP0PinStillPasses:
    def test_base_case_pin_re_pointed(self):
        text = _read(REPO_ROOT / "tests/test_phase53g1_base_case_p0_behavior_pin.py")
        assert "PIN_TARGET = SCENARIOS_PY" in text


class TestNoHighRiskWritesRemain:
    """After 53G-7, there are NO high-risk scenario writes left in repository.py."""

    def test_save_scenario_not_in_repository(self):
        text = _read(REPOSITORY_PY)
        n = text.count("def save_scenario(")
        assert n == 0, "save_scenario should be in scenarios_repository.py (moved in 53G-4)"

    def test_add_scenario_not_in_repository(self):
        text = _read(REPOSITORY_PY)
        n = text.count("def add_scenario(")
        assert n == 0, "add_scenario should be in scenarios_repository.py (moved in 53G-5)"

    def test_update_scenario_overrides_not_in_repository(self):
        text = _read(REPOSITORY_PY)
        n = text.count("def update_scenario_overrides(")
        assert n == 0, "update_scenario_overrides should be in scenarios_repository.py (moved in 53G-6)"

    def test_get_or_create_base_case_scenario_not_in_repository(self):
        text = _read(REPOSITORY_PY)
        n = text.count("def get_or_create_base_case_scenario(")
        assert n == 0


class TestDataclassesUntouched:
    @pytest.mark.parametrize("cls_name", ["ProjectRecord", "ScenarioRecord", "WorkspaceStateRecord"])
    def test_dataclass_still_in_repository(self, cls_name):
        assert f"class {cls_name}" in _read(REPOSITORY_PY)


class TestRepositoryPyShrank:
    def test_repository_py_under_500_lines(self):
        text = _read(REPOSITORY_PY)
        n = len(text.splitlines())
        # Pre-53G-7: 552. After 53G-7: should be ~453 lines
        assert n < 500, f"repository.py should be < 500 lines after 53G-7, got {n}"
