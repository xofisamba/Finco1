"""Phase 53I-3 — Remove record lazy imports + guardrail.

After 53I-2, all record dataclasses live in app/persistence/records.py.
This phase replaces lazy imports of records from
app.persistence.repository with direct imports from
app.persistence.records, and adds a guardrail that prevents
app/persistence/*_repository.py from importing record dataclasses
from app.persistence.repository.

Guardrail: tests/test_phase53i3_guardrail_no_record_imports_from_repository.py
- Verifies NO app/persistence/*_repository.py imports any record
  dataclass from app.persistence.repository
- If this test ever fails, someone re-introduced a lazy import
  that should be a direct import from records
"""
from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCENARIOS_PY = REPO_ROOT / "app" / "persistence" / "scenarios_repository.py"
PROJECTS_PY = REPO_ROOT / "app" / "persistence" / "projects_repository.py"
WORKSPACE_PY = REPO_ROOT / "app" / "persistence" / "workspace_repository.py"
RUNS_PY = REPO_ROOT / "app" / "persistence" / "runs_repository.py"
EXPORTS_PY = REPO_ROOT / "app" / "persistence" / "exports_repository.py"
RECORDS_PY = REPO_ROOT / "app" / "persistence" / "records.py"

RECORD_NAMES = ["ProjectRecord", "ScenarioRecord", "WorkspaceStateRecord",
                "RunRecord", "ScenarioExportRecord"]


def _read(path):
    return path.read_text(encoding="utf-8")


def _count_record_lazy_imports_from_repository(text):
    """Count lines in text where a record dataclass is imported
    from app.persistence.repository (the stale pattern)."""
    count = 0
    for line in text.splitlines():
        if "from app.persistence.repository import" in line:
            for r in RECORD_NAMES:
                if r in line:
                    count += 1
                    break
    return count


# ============================================================
# 1. Direct imports from records exist
# ============================================================


class TestDirectImportsFromRecords:
    def test_scenarios_repository_imports_scenario_record_from_records(self):
        text = _read(SCENARIOS_PY)
        assert "from app.persistence.records import ScenarioRecord" in text

    def test_projects_repository_imports_project_record_from_records(self):
        text = _read(PROJECTS_PY)
        assert "from app.persistence.records import ProjectRecord" in text

    def test_workspace_repository_imports_workspace_state_record_from_records(self):
        text = _read(WORKSPACE_PY)
        assert "from app.persistence.records import WorkspaceStateRecord" in text

    def test_runs_repository_imports_run_record_from_records(self):
        text = _read(RUNS_PY)
        assert "from app.persistence.records import RunRecord" in text

    def test_exports_repository_imports_scenario_export_record_from_records(self):
        text = _read(EXPORTS_PY)
        assert "from app.persistence.records import ScenarioExportRecord" in text


# ============================================================
# 2. Lazy imports from repository (for records) are GONE
# ============================================================


class TestNoRecordLazyImportsFromRepository:
    def test_scenarios_repository_no_record_lazy_imports_from_repository(self):
        text = _read(SCENARIOS_PY)
        n = _count_record_lazy_imports_from_repository(text)
        assert n == 0, f"scenarios_repository.py has {n} record lazy imports from repository.py (should be 0)"

    def test_projects_repository_no_record_lazy_imports_from_repository(self):
        text = _read(PROJECTS_PY)
        n = _count_record_lazy_imports_from_repository(text)
        assert n == 0, f"projects_repository.py has {n} record lazy imports from repository.py (should be 0)"

    def test_workspace_repository_no_record_lazy_imports_from_repository(self):
        text = _read(WORKSPACE_PY)
        n = _count_record_lazy_imports_from_repository(text)
        assert n == 0, f"workspace_repository.py has {n} record lazy imports from repository.py (should be 0)"

    def test_runs_repository_no_record_lazy_imports_from_repository(self):
        text = _read(RUNS_PY)
        n = _count_record_lazy_imports_from_repository(text)
        assert n == 0

    def test_exports_repository_no_record_lazy_imports_from_repository(self):
        text = _read(EXPORTS_PY)
        n = _count_record_lazy_imports_from_repository(text)
        assert n == 0

    def test_repository_py_no_longer_defines_records(self):
        # repository.py must not re-define the records
        text = _read(REPO_ROOT / "app" / "persistence" / "repository.py")
        for r in RECORD_NAMES:
            assert f"class {r}" not in text, \
                f"repository.py should not define class {r} (it lives in records.py)"


# ============================================================
# 3. Object identity preserved
# ============================================================


class TestObjectIdentityPreserved:
    """Object identity: app.persistence.records.X must be the same class
    as app.persistence.repository.X. Domain modules use records.X
    internally; the re-export from repository provides the public path."""

    def test_scenario_record_identity_preserved(self):
        from app.persistence.records import ScenarioRecord as B
        from app.persistence.repository import ScenarioRecord as C
        assert B is C

    def test_project_record_identity_preserved(self):
        from app.persistence.records import ProjectRecord as B
        from app.persistence.repository import ProjectRecord as C
        assert B is C

    def test_workspace_state_record_identity_preserved(self):
        from app.persistence.records import WorkspaceStateRecord as B
        from app.persistence.repository import WorkspaceStateRecord as C
        assert B is C

    def test_run_record_identity_preserved(self):
        from app.persistence.records import RunRecord as B
        from app.persistence.repository import RunRecord as C
        assert B is C

    def test_scenario_export_record_identity_preserved(self):
        from app.persistence.records import ScenarioExportRecord as B
        from app.persistence.repository import ScenarioExportRecord as C
        assert B is C


# ============================================================
# 4. SQL unchanged
# ============================================================


class TestSqlUnchanged:
    def test_save_scenario_sql_unchanged(self):
        import inspect
        from app.persistence.scenarios_repository import save_scenario
        src = inspect.getsource(save_scenario)
        assert "INSERT INTO scenarios" in src
        assert "scenario_id, project_id, user_id, scenario_name, project_code" in src

    def test_update_scenario_overrides_sql_unchanged(self):
        import inspect
        from app.persistence.scenarios_repository import update_scenario_overrides
        src = inspect.getsource(update_scenario_overrides)
        assert "UPDATE scenarios" in src
        assert "SET overrides_json=?, snapshot_json=?, updated_at=?" in src


# ============================================================
# 5. No new circular import
# ============================================================


class TestNoNewCircularImport:
    def test_all_persistence_modules_import_cleanly(self):
        # Should not raise ImportError
        import app.persistence.records
        import app.persistence.repository
        import app.persistence.scenarios_repository
        import app.persistence.projects_repository
        import app.persistence.workspace_repository
        import app.persistence.runs_repository
        import app.persistence.exports_repository

    def test_records_module_independent(self):
        # records.py should be importable on its own (no circular deps)
        import app.persistence.records as r
        # All 5 records should be accessible
        for cls in RECORD_NAMES:
            assert hasattr(r, cls)
