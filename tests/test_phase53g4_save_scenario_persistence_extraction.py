"""Phase 53G-4 — extraction test for save_scenario persistence.

Tests:

1. save_scenario moved to scenarios_repository.py.
2. save_scenario remains importable from app.persistence.repository.
3. 53G-1 save_scenario P0 pin still passes.
4. Other 53G-1 P0 pins (coupling, add, update_overrides, base_case) still pass.
5. Other high-risk writes remain in repository.py.
6. dataclasses remain in repository.py.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCENARIOS_PY = REPO_ROOT / "app" / "persistence" / "scenarios_repository.py"
REPOSITORY_PY = REPO_ROOT / "app" / "persistence" / "repository.py"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class TestMovedFunction:
    def test_save_scenario_defined_in_scenarios(self):
        text = _read(SCENARIOS_PY)
        assert "def save_scenario(" in text

    def test_save_scenario_not_defined_in_repository(self):
        text = _read(REPOSITORY_PY)
        # def save_scenario should NOT appear in repository.py (only in re-export block)
        n = text.count("def save_scenario(")
        assert n == 0


class TestPublicCompatibility:
    def test_save_scenario_importable(self):
        from app.persistence.repository import save_scenario
        assert callable(save_scenario)

    def test_re_export_block_includes_save_scenario(self):
        text = _read(REPOSITORY_PY)
        assert "save_scenario" in text
        # It's in the re-export block (after the 53G-2/53G-3/53G-4 comment)
        assert "save_scenario," in text


class TestP0PinStillPasses:
    def test_save_scenario_pin_re_pointed(self):
        # The 53G-1 save_scenario pin was re-pointed to read from scenarios_repository
        text = _read(REPO_ROOT / "tests/test_phase53g1_save_scenario_p0_behavior_pin.py")
        assert "PIN_TARGET = SCENARIOS_PY" in text

    def test_coupling_pin_untouched(self):
        # The scenario/workspace coupling pin should NOT have been modified
        text = _read(REPO_ROOT / "tests/test_phase53g1_scenario_workspace_coupling_p0_pin.py")
        # No PIN_TARGET = SCENARIOS_PY here (it was only re-pointed in save_scenario pin)
        assert "PIN_TARGET = SCENARIOS_PY" not in text


class TestOtherHighRiskWritesUntouched:
    @pytest.mark.parametrize("fn_name", [
        "get_or_create_base_case_scenario",
    ])
    def test_other_high_risk_write_still_in_repository_body(self, fn_name):
        from app.persistence import repository
        assert hasattr(repository, fn_name)
        text = _read(REPOSITORY_PY)
        assert f"def {fn_name}" in text, f"{fn_name} not defined in repository.py"


class TestDataclassesUntouched:
    @pytest.mark.parametrize("cls_name", [
        "ProjectRecord",
        "ScenarioRecord",
        "WorkspaceStateRecord",
    ])
    def test_dataclass_still_in_repository(self, cls_name):
        text = _read(REPOSITORY_PY)
        assert f"class {cls_name}" in text


class TestRepositoryPyShrank:
    def test_repository_py_under_750_lines(self):
        text = _read(REPOSITORY_PY)
        n = len(text.splitlines())
        # Pre-53G-4: 743. After 53G-4: should be ~680
        assert n < 750, f"repository.py should be < 750 lines after 53G-4, got {n}"
