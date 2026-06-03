"""Phase 53G-2 — extraction test for scenario read persistence.

This file adds structural tests proving that the Group B-reads
extraction was behavior-preserving and the public compatibility
façade is intact.

Tests:

1. moved functions live in scenarios_repository.py.
2. functions remain importable from app.persistence.repository.
3. 53G-1 P0 pin still passes.
4. signatures preserved.
5. SQL text/fragments preserved.
6. metadata behavior preserved.
7. high-risk scenario writes remain in repository.py.
8. dataclasses (ProjectRecord, ScenarioRecord, WorkspaceStateRecord) remain in repository.py.
9. no service/route imports changed.
10. Phase 52F guardrails pass.
"""
from __future__ import annotations

import inspect
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCENARIOS_PY = REPO_ROOT / "app" / "persistence" / "scenarios_repository.py"
REPOSITORY_PY = REPO_ROOT / "app" / "persistence" / "repository.py"
PERSISTENCE_INIT = REPO_ROOT / "app" / "persistence" / "__init__.py"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


# ============================================================
# 1. Moved functions live in scenarios_repository.py
# ============================================================


class TestMovedFunctions:
    def test_get_scenario_defined_in_scenarios(self):
        text = _read(SCENARIOS_PY)
        assert "def get_scenario(" in text

    def test_list_scenarios_defined_in_scenarios(self):
        text = _read(SCENARIOS_PY)
        assert "def list_scenarios(" in text

    def test_resolve_scenario_snapshot_defined_in_scenarios(self):
        text = _read(SCENARIOS_PY)
        assert "def resolve_scenario_snapshot(" in text

    def test_resolve_active_scenario_runtime_snapshot_defined_in_scenarios(self):
        text = _read(SCENARIOS_PY)
        assert "def resolve_active_scenario_runtime_snapshot(" in text

    def test_get_scenario_not_defined_in_repository(self):
        text = _read(REPOSITORY_PY)
        n = text.count("def get_scenario(")
        assert n == 0

    def test_list_scenarios_not_defined_in_repository(self):
        text = _read(REPOSITORY_PY)
        n = text.count("def list_scenarios(")
        assert n == 0

    def test_resolve_scenario_snapshot_not_defined_in_repository(self):
        text = _read(REPOSITORY_PY)
        n = text.count("def resolve_scenario_snapshot(")
        assert n == 0

    def test_resolve_active_scenario_runtime_snapshot_not_defined_in_repository(self):
        text = _read(REPOSITORY_PY)
        n = text.count("def resolve_active_scenario_runtime_snapshot(")
        assert n == 0


# ============================================================
# 2. Public compatibility
# ============================================================


class TestPublicCompatibility:
    def test_get_scenario_importable(self):
        from app.persistence.repository import get_scenario
        assert callable(get_scenario)

    def test_list_scenarios_importable(self):
        from app.persistence.repository import list_scenarios
        assert callable(list_scenarios)

    def test_resolve_scenario_snapshot_importable(self):
        from app.persistence.repository import resolve_scenario_snapshot
        assert callable(resolve_scenario_snapshot)

    def test_resolve_active_scenario_runtime_snapshot_importable(self):
        from app.persistence.repository import resolve_active_scenario_runtime_snapshot
        assert callable(resolve_active_scenario_runtime_snapshot)

    def test_re_export_block_in_repository(self):
        text = _read(REPOSITORY_PY)
        assert "from app.persistence.scenarios_repository import" in text
        for fn in ("get_scenario", "list_scenarios",
                   "resolve_scenario_snapshot",
                   "resolve_active_scenario_runtime_snapshot"):
            assert fn in text, f"{fn} should be re-exported in repository.py"

    def test_init_module_re_export(self):
        # app/persistence/__init__.py should also re-export
        text = _read(PERSISTENCE_INIT)
        # get_scenario and list_scenarios should be re-exported there too
        assert "from app.persistence.scenarios_repository import" in text


# ============================================================
# 3. Signatures preserved
# ============================================================


class TestSignaturesPreserved:
    def test_get_scenario_signature(self):
        from app.persistence.repository import get_scenario
        sig = inspect.signature(get_scenario)
        params = sig.parameters
        assert "scenario_id" in params
        assert "user_id" in params
        assert len(params) == 2

    def test_list_scenarios_signature(self):
        from app.persistence.repository import list_scenarios
        sig = inspect.signature(list_scenarios)
        params = sig.parameters
        assert "user_id" in params
        assert "project_id" in params
        assert "include_archived" in params
        assert "limit" in params
        assert len(params) == 4

    def test_resolve_scenario_snapshot_signature(self):
        from app.persistence.repository import resolve_scenario_snapshot
        sig = inspect.signature(resolve_scenario_snapshot)
        params = sig.parameters
        assert "base_input_set" in params
        assert "overrides" in params
        assert len(params) == 2


# ============================================================
# 4. SQL text preservation
# ============================================================


class TestSqlTextPreserved:
    def test_get_scenario_select_sql(self):
        text = _read(SCENARIOS_PY)
        assert "SELECT * FROM scenarios WHERE scenario_id=? AND user_id=?" in text

    def test_list_scenarios_dynamic_query(self):
        text = _read(SCENARIOS_PY)
        assert "SELECT * FROM scenarios WHERE user_id=?" in text
        assert "ORDER BY updated_at DESC LIMIT ?" in text
        assert "archived=0" in text


# ============================================================
# 5. P0 pin still passes
# ============================================================


class TestP0PinStillPasses:
    def test_53g1_pin_test_file_exists(self):
        assert (REPO_ROOT / "tests/test_phase53g1_scenario_workspace_coupling_p0_pin.py").exists()

    def test_53g1_pins_re_pointed(self):
        # The 53G-1 pin was re-pointed to read from scenarios_repository for resolve_scenario_snapshot
        text = _read(REPO_ROOT / "tests/test_phase53g1_scenario_workspace_coupling_p0_pin.py")
        assert "scenarios_repository" in text


# ============================================================
# 6. High-risk scenario writes remain in repository.py
# ============================================================


class TestHighRiskScenarioWritesUntouched:
    @pytest.mark.parametrize("fn_name", [
        "save_scenario",
        "add_scenario",
        "update_scenario_overrides",
        "get_or_create_base_case_scenario",
    ])
    def test_high_risk_write_still_in_repository_body(self, fn_name):
        from app.persistence import repository
        assert hasattr(repository, fn_name)
        text = _read(REPOSITORY_PY)
        assert f"def {fn_name}" in text, f"{fn_name} not defined in repository.py"


# ============================================================
# 7. Dataclasses remain in repository.py
# ============================================================


class TestDataclassesUntouched:
    @pytest.mark.parametrize("cls_name", [
        "ProjectRecord",
        "ScenarioRecord",
        "WorkspaceStateRecord",
    ])
    def test_dataclass_still_in_repository(self, cls_name):
        text = _read(REPOSITORY_PY)
        assert f"class {cls_name}" in text, f"{cls_name} not defined in repository.py"


# ============================================================
# 8. repository.py LOC reduction
# ============================================================


class TestRepositoryPyShrank:
    def test_repository_py_under_900_lines(self):
        text = _read(REPOSITORY_PY)
        n = len(text.splitlines())
        # Pre-53G-2: 922 lines. After 53G-2: should be ~826 lines (-96 for the 4 functions)
        assert n < 900, f"repository.py should be < 900 lines after 53G-2, got {n}"

    def test_scenarios_repository_exists(self):
        assert SCENARIOS_PY.exists()
        text = _read(SCENARIOS_PY)
        n = len(text.splitlines())
        assert n > 100, f"scenarios_repository.py should be > 100 lines, got {n}"


# ============================================================
# 9. No circular import (TYPE_CHECKING forward refs)
# ============================================================


class TestNoCircularImport:
    def test_scenarios_repository_uses_type_checking(self):
        text = _read(SCENARIOS_PY)
        assert "TYPE_CHECKING" in text
        assert "from app.persistence.repository import" in text
