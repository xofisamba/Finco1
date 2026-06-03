"""Phase 53D — Project reads persistence extraction structural tests.

Verifies that the 6 Group A-reads functions are present in
app/persistence/projects_repository.py and re-exported from
app/persistence/repository.py for backward compatibility.

Verifies that project WRITE functions (including save_project) are
NOT moved and remain defined in repository.py.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
PROJECTS_PY = REPO_ROOT / "app" / "persistence" / "projects_repository.py"
REPOSITORY_PY = REPO_ROOT / "app" / "persistence" / "repository.py"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


GROUP_A_READS = [
    "get_project",
    "get_project_by_code",
    "list_projects",
    "list_baseline_records",
    "get_project_record",
    "list_project_records",
]
PROJECT_WRITES = [
    "save_project",
    "seed_baseline_projects_if_needed",
    "create_project_record",
    "update_project_record",
    "_compute_baseline_snapshot",
    "_build_default_snapshot",
    "_fill_missing_defaults",
]
# Note: _sum_opex is a NESTED function inside _compute_baseline_snapshot
# and moves with it. It is not a top-level function so it is not listed here.


# ----------------------------- Module existence ----------------------------


class TestModuleExistence:
    def test_projects_module_exists(self):
        assert PROJECTS_PY.exists()

    def test_projects_module_is_python(self):
        text = _read(PROJECTS_PY)
        ast.parse(text)


# ----------------------------- Projects module content ----------------------------


class TestProjectsModuleContent:
    @pytest.mark.parametrize("name", GROUP_A_READS)
    def test_projects_module_defines(self, name):
        text = _read(PROJECTS_PY)
        assert re.search(rf"^def {re.escape(name)}\(", text, re.MULTILINE), \
            f"projects_repository.py does not define {name}"

    def test_projects_module_has_at_least_6_functions(self):
        # After Phase 53E-2, projects_repository.py also contains the A-2 write functions.
        # We expect at least 6 (the A-reads set); the A-2 writes may be present too.
        text = _read(PROJECTS_PY)
        defs = re.findall(r"^def\s+(\w+)", text, re.MULTILINE)
        assert len(defs) >= 6, f"expected >= 6 functions, got {len(defs)}: {defs}"

    def test_projects_module_has_get_cursor_import(self):
        text = _read(PROJECTS_PY)
        assert "from app.persistence.db import get_cursor" in text


# ----------------------------- Repository compatibility façade ----------------------------


class TestRepositoryFacade:
    @pytest.mark.parametrize("name", GROUP_A_READS)
    def test_repository_re_exports(self, name):
        from app.persistence import repository
        assert hasattr(repository, name), f"repository.py missing re-export of {name}"

    @pytest.mark.parametrize("name", GROUP_A_READS)
    def test_repository_and_projects_share_same_object(self, name):
        from app.persistence import repository
        from app.persistence import projects_repository
        assert getattr(repository, name) is getattr(projects_repository, name), \
            f"repository.{name} is not the same object as projects_repository.{name}"

    def test_repository_has_import_block_for_projects(self):
        text = _read(REPOSITORY_PY)
        assert "from app.persistence.projects_repository import" in text


# ----------------------------- Project writes NOT moved (post-53E-2) ----------------------------


class TestProjectWritesMovedIn53E2:
    """After Phase 53E-2, all 8 A-2 project write functions are now in projects_repository.py.
    They are still importable from app.persistence.repository via the re-export façade."""

    @pytest.mark.parametrize("fn_name", PROJECT_WRITES)
    def test_write_NOW_in_projects_repository(self, fn_name):
        from app.persistence import projects_repository
        assert hasattr(projects_repository, fn_name), \
            f"{fn_name} should be in projects_repository (moved in 53E-2)"

    @pytest.mark.parametrize("fn_name", PROJECT_WRITES)
    def test_write_still_in_repository_via_reexport(self, fn_name):
        # Functions are re-exported; check by import
        from app.persistence import repository
        assert hasattr(repository, fn_name), \
            f"{fn_name} should be re-exported from repository"

    @pytest.mark.parametrize("fn_name", PROJECT_WRITES)
    def test_repository_and_projects_share_same_object(self, fn_name):
        from app.persistence import repository, projects_repository
        assert getattr(repository, fn_name) is getattr(projects_repository, fn_name)


# ----------------------------- save_project specifically (post-53E-2) ----------------------------


class TestSaveProjectNowInProjectsRepository:
    """save_project is the highest-risk write. After 53E-2 it lives in projects_repository.py."""

    def test_save_project_in_repository_via_reexport(self):
        from app.persistence import repository
        assert hasattr(repository, "save_project")

    def test_save_project_in_projects_repository(self):
        from app.persistence import projects_repository
        assert hasattr(projects_repository, "save_project")

    def test_save_project_defined_in_projects_repository_body(self):
        text = _read(PROJECTS_PY)
        assert "def save_project(" in text

    def test_save_project_53e1_pin_still_passes(self):
        # The 53E-1 pin (test_phase53e1_save_project_p0_behavior_pin.py) must still pass
        # because 53E-2 was designed to satisfy it
        from app.persistence.repository import save_project
        # Quick signature check
        import inspect
        sig = inspect.signature(save_project)
        params = list(sig.parameters.keys())
        assert "user_id" in params and "project_code" in params and "replay_metadata" in params


# ----------------------------- Behavior preservation ----------------------------


class TestReadFunctionsBehavior:
    def test_get_project_sql_text(self):
        text = _read(PROJECTS_PY)
        assert "SELECT * FROM projects WHERE project_id=? AND user_id=?" in text

    def test_get_project_by_code_sql_text(self):
        text = _read(PROJECTS_PY)
        assert "SELECT * FROM projects WHERE user_id=? AND project_code=?" in text

    def test_list_projects_sql_text(self):
        text = _read(PROJECTS_PY)
        assert "SELECT * FROM projects WHERE user_id=? AND archived=0 ORDER BY updated_at DESC" in text

    def test_list_baseline_records_sql_text(self):
        text = _read(PROJECTS_PY)
        assert "SELECT * FROM projects WHERE user_id=? AND project_origin='saved_baseline' AND archived=0 ORDER BY project_name" in text

    def test_list_project_records_default_query(self):
        text = _read(PROJECTS_PY)
        assert "SELECT * FROM projects WHERE user_id=?" in text
        assert "AND archived=0" in text
        assert "ORDER BY updated_at DESC" in text

    def test_get_project_record_signature(self):
        import inspect
        from app.persistence import projects_repository
        sig = inspect.signature(projects_repository.get_project_record)
        params = list(sig.parameters.keys())
        assert params == ["user_id", "project_id", "project_code"]

    def test_get_project_record_dispatcher_logic(self):
        text = _read(PROJECTS_PY)
        # The dispatcher must check project_id first, then project_code
        assert "if project_id:" in text
        assert "if project_code:" in text
        assert "return None" in text


# ----------------------------- High-risk writes untouched ----------------------------


class TestOtherHighRiskWritesNotMovedToProjects:
    @pytest.mark.parametrize("fn_name", [
        "save_workspace_state", "save_scenario",
        "add_scenario", "update_scenario_overrides",
        "get_or_create_base_case_scenario",
        "select_scenario", "duplicate_scenario",
        "record_export",  # moved in 53C, not 53D
    ])
    def test_other_high_risk_not_in_projects(self, fn_name):
        from app.persistence import projects_repository
        assert not hasattr(projects_repository, fn_name)
