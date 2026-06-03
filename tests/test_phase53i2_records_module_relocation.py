"""Phase 53I-2 — Records module relocation structural tests.

Verifies that records.py was created and the 5 records were moved
with byte-for-byte behavior preservation.
"""
from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
RECORDS_PY = REPO_ROOT / "app" / "persistence" / "records.py"
REPOSITORY_PY = REPO_ROOT / "app" / "persistence" / "repository.py"
RUNS_PY = REPO_ROOT / "app" / "persistence" / "runs_repository.py"
EXPORTS_PY = REPO_ROOT / "app" / "persistence" / "exports_repository.py"


class TestRecordsModuleExists:
    def test_records_py_exists(self):
        assert RECORDS_PY.exists()

    def test_records_py_has_all_5_records(self):
        text = RECORDS_PY.read_text()
        for cls in ["ProjectRecord", "ScenarioRecord", "WorkspaceStateRecord",
                    "RunRecord", "ScenarioExportRecord"]:
            assert f"class {cls}" in text, f"{cls} not in records.py"


class TestRecordsNoLongerInDomainModules:
    def test_project_record_not_in_repository(self):
        text = REPOSITORY_PY.read_text()
        assert "class ProjectRecord" not in text, \
            "ProjectRecord should be in records.py, not repository.py"

    def test_scenario_record_not_in_repository(self):
        text = REPOSITORY_PY.read_text()
        assert "class ScenarioRecord" not in text

    def test_workspace_state_record_not_in_repository(self):
        text = REPOSITORY_PY.read_text()
        assert "class WorkspaceStateRecord" not in text

    def test_run_record_not_in_runs_repository(self):
        text = RUNS_PY.read_text()
        assert "class RunRecord" not in text

    def test_scenario_export_record_not_in_exports_repository(self):
        text = EXPORTS_PY.read_text()
        assert "class ScenarioExportRecord" not in text


class TestPublicCompatibility:
    """All records must still be importable from app.persistence.repository."""

    def test_project_record_from_repository(self):
        from app.persistence.repository import ProjectRecord as A
        from app.persistence.records import ProjectRecord as B
        assert A is B, "ProjectRecord must be same class via both paths"

    def test_scenario_record_from_repository(self):
        from app.persistence.repository import ScenarioRecord as A
        from app.persistence.records import ScenarioRecord as B
        assert A is B

    def test_workspace_state_record_from_repository(self):
        from app.persistence.repository import WorkspaceStateRecord as A
        from app.persistence.records import WorkspaceStateRecord as B
        assert A is B

    def test_run_record_from_runs_repository(self):
        from app.persistence.runs_repository import RunRecord as A
        from app.persistence.records import RunRecord as B
        assert A is B

    def test_scenario_export_record_from_exports_repository(self):
        from app.persistence.exports_repository import ScenarioExportRecord as A
        from app.persistence.records import ScenarioExportRecord as B
        assert A is B


class TestRepositoryFaadeReExports:
    def test_repository_re_exports_all_5_records(self):
        text = REPOSITORY_PY.read_text()
        assert "from app.persistence.records import" in text
        for cls in ["ProjectRecord", "ScenarioRecord", "WorkspaceStateRecord",
                    "RunRecord", "ScenarioExportRecord"]:
            assert cls in text, f"{cls} should be re-exported from repository.py"


class TestNoCircularImport:
    def test_records_module_imports_cleanly(self):
        # Should not raise ImportError
        import app.persistence.records
        assert app.persistence.records is not None

    def test_repository_imports_after_relocation(self):
        # Should not raise ImportError
        import app.persistence.repository
        assert app.persistence.repository is not None

    def test_runs_repository_imports_after_relocation(self):
        import app.persistence.runs_repository
        assert app.persistence.runs_repository is not None

    def test_exports_repository_imports_after_relocation(self):
        import app.persistence.exports_repository
        assert app.persistence.exports_repository is not None


class TestSQLNotChanged:
    """Pin that 53I-2 did not change any SQL text. SQL must be byte-for-byte
    identical to pre-relocation (53H-2)."""

    @pytest.fixture
    def sql_in_scenarios(self):
        from app.persistence import scenarios_repository
        return scenarios_repository

    def test_save_scenario_sql_unchanged(self, sql_in_scenarios):
        import inspect
        src = inspect.getsource(sql_in_scenarios.save_scenario)
        # The INSERT INTO scenarios should still be there
        assert "INSERT INTO scenarios" in src
        # The column list is unchanged
        assert "scenario_id, project_id, user_id, scenario_name, project_code" in src

    def test_get_or_create_base_case_sql_unchanged(self, sql_in_scenarios):
        import inspect
        src = inspect.getsource(sql_in_scenarios.get_or_create_base_case_scenario)
        assert "SELECT * FROM scenarios" in src
        assert "is_base_case=1 AND archived=0" in src
        assert "INSERT INTO scenarios" in src

    def test_update_scenario_overrides_sql_unchanged(self, sql_in_scenarios):
        import inspect
        src = inspect.getsource(sql_in_scenarios.update_scenario_overrides)
        assert "UPDATE scenarios" in src
        assert "SET overrides_json=?, snapshot_json=?, updated_at=?" in src


class TestRepositoryPyShrank:
    def test_repository_py_under_330_lines(self):
        text = REPOSITORY_PY.read_text()
        n = len(text.splitlines())
        # Pre-53I-2: 295 (post-53G-8). After 53I-2: should be ~305 (3 re-exports added)
        assert n < 330, f"repository.py should be < 330 lines after 53I-2, got {n}"
