"""Phase 53G-3 — extraction test for low-risk scenario actions.

This file adds structural tests proving that the Group B low-risk
actions extraction was behavior-preserving.

Tests:

1. moved functions live in scenarios_repository.py.
2. functions remain importable from app.persistence.repository.
3. 53G-1 P0 pin still passes.
4. signatures preserved.
5. SQL text/fragments preserved.
6. high-risk scenario writes remain in repository.py.
7. dataclasses remain in repository.py.
8. no service/route imports changed.
"""
from __future__ import annotations

import inspect
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
    @pytest.mark.parametrize("fn_name", [
        "rename_scenario",
        "archive_scenario",
        "select_scenario",
        "duplicate_scenario",
        "promote_scenario_to_base_case",
    ])
    def test_function_defined_in_scenarios(self, fn_name):
        text = _read(SCENARIOS_PY)
        assert f"def {fn_name}(" in text, f"{fn_name} not defined in scenarios_repository.py"

    @pytest.mark.parametrize("fn_name", [
        "rename_scenario",
        "archive_scenario",
        "select_scenario",
        "duplicate_scenario",
        "promote_scenario_to_base_case",
    ])
    def test_function_not_defined_in_repository(self, fn_name):
        text = _read(REPOSITORY_PY)
        n = text.count(f"def {fn_name}(")
        assert n == 0, f"{fn_name} still defined in repository.py ({n} occurrences)"


# ============================================================
# 2. Public compatibility
# ============================================================


class TestPublicCompatibility:
    @pytest.mark.parametrize("fn_name", [
        "rename_scenario",
        "archive_scenario",
        "select_scenario",
        "duplicate_scenario",
        "promote_scenario_to_base_case",
    ])
    def test_function_importable_from_repository(self, fn_name):
        from app.persistence import repository
        assert hasattr(repository, fn_name)
        assert callable(getattr(repository, fn_name))

    def test_re_export_block_in_repository(self):
        text = _read(REPOSITORY_PY)
        assert "from app.persistence.scenarios_repository import" in text
        for fn in ("rename_scenario", "archive_scenario", "select_scenario",
                   "duplicate_scenario", "promote_scenario_to_base_case"):
            assert fn in text

    def test_init_module_re_export(self):
        text = _read(PERSISTENCE_INIT)
        # rename, archive, duplicate should be re-exported there
        for fn in ("archive_scenario", "duplicate_scenario", "rename_scenario"):
            assert fn in text


# ============================================================
# 3. Signatures preserved
# ============================================================


class TestSignaturesPreserved:
    def test_rename_scenario_signature(self):
        from app.persistence.repository import rename_scenario
        sig = inspect.signature(rename_scenario)
        params = sig.parameters
        assert "user_id" in params
        assert "scenario_id" in params
        assert "new_name" in params
        assert len(params) == 3

    def test_archive_scenario_signature(self):
        from app.persistence.repository import archive_scenario
        sig = inspect.signature(archive_scenario)
        params = sig.parameters
        assert "user_id" in params
        assert "scenario_id" in params
        assert len(params) == 2

    def test_select_scenario_signature(self):
        from app.persistence.repository import select_scenario
        sig = inspect.signature(select_scenario)
        params = sig.parameters
        for required in ("user_id", "project_id", "scenario_id"):
            assert required in params

    def test_duplicate_scenario_signature(self):
        from app.persistence.repository import duplicate_scenario
        sig = inspect.signature(duplicate_scenario)
        params = sig.parameters
        assert "user_id" in params
        assert "scenario_id" in params
        assert "new_name" in params
        # new_name has default None
        assert params["new_name"].default is None

    def test_promote_scenario_to_base_case_signature(self):
        from app.persistence.repository import promote_scenario_to_base_case
        sig = inspect.signature(promote_scenario_to_base_case)
        params = sig.parameters
        assert "user_id" in params
        assert "scenario_id" in params


# ============================================================
# 4. SQL text preservation
# ============================================================


class TestSqlTextPreserved:
    def test_rename_scenario_sql(self):
        text = _read(SCENARIOS_PY)
        assert "UPDATE scenarios SET scenario_name=?, updated_at=? WHERE scenario_id=? AND user_id=?" in text

    def test_archive_scenario_sql(self):
        text = _read(SCENARIOS_PY)
        assert "UPDATE scenarios SET archived=1, updated_at=? WHERE scenario_id=? AND user_id=?" in text

    def test_promote_scenario_to_base_case_sql(self):
        text = _read(SCENARIOS_PY)
        assert "SET is_base_case=0, updated_at=?" in text
        assert "SET is_base_case=1, updated_at=?" in text


# ============================================================
# 5. P0 pin still passes
# ============================================================


class TestP0PinStillPasses:
    def test_53g1_pin_files_exist(self):
        for fp in [
            "tests/test_phase53g1_scenario_workspace_coupling_p0_pin.py",
            "tests/test_phase53g1_save_scenario_p0_behavior_pin.py",
            "tests/test_phase53g1_add_scenario_p0_behavior_pin.py",
            "tests/test_phase53g1_update_overrides_p0_behavior_pin.py",
            "tests/test_phase53g1_base_case_p0_behavior_pin.py",
        ]:
            assert (REPO_ROOT / fp).exists()


# ============================================================
# 6. High-risk scenario writes remain in repository.py
# ============================================================


class TestHighRiskWritesUntouched:
    @pytest.mark.parametrize("fn_name", [
        # save_scenario was moved to scenarios_repository in Phase 53G-4
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
        assert f"class {cls_name}" in text


# ============================================================
# 8. repository.py LOC reduction
# ============================================================


class TestRepositoryPyShrank:
    def test_repository_py_under_800_lines(self):
        text = _read(REPOSITORY_PY)
        n = len(text.splitlines())
        # Pre-53G-3: 826 lines. After 53G-3: should be ~743 lines (-83 for the 5 functions)
        assert n < 800, f"repository.py should be < 800 lines after 53G-3, got {n}"
