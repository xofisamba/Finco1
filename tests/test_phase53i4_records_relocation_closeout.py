"""Phase 53I-4 — Records relocation closeout tests (final guardrails).

These are the permanent guardrails for the records.py relocation.
They prevent future regressions:

1. repository.py must not re-introduce record dataclass definitions
2. All 5 records must be in records.py
3. Compatibility re-exports must exist in repository.py
4. Public import paths must work
5. Object identity must be preserved
"""
from __future__ import annotations

import inspect
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
RECORDS_PY = REPO_ROOT / "app" / "persistence" / "records.py"
REPOSITORY_PY = REPO_ROOT / "app" / "persistence" / "repository.py"
RUNS_PY = REPO_ROOT / "app" / "persistence" / "runs_repository.py"
EXPORTS_PY = REPO_ROOT / "app" / "persistence" / "exports_repository.py"
SCENARIOS_PY = REPO_ROOT / "app" / "persistence" / "scenarios_repository.py"
PROJECTS_PY = REPO_ROOT / "app" / "persistence" / "projects_repository.py"
WORKSPACE_PY = REPO_ROOT / "app" / "persistence" / "workspace_repository.py"

ALL_5_RECORDS = ["ProjectRecord", "ScenarioRecord", "WorkspaceStateRecord",
                 "RunRecord", "ScenarioExportRecord"]


def _read(path):
    return path.read_text(encoding="utf-8")


# ============================================================
# 1. No record class definitions in repository.py
# ============================================================


class TestNoRecordDefinitionsInRepository:
    """PERMANENT GUARDRAIL: No record class may be defined in repository.py.
    If this test ever fails, someone re-introduced a record definition
    that should be in records.py."""

    @pytest.mark.parametrize("record_name", ALL_5_RECORDS)
    def test_no_record_class_definition_in_repository(self, record_name):
        text = _read(REPOSITORY_PY)
        assert f"class {record_name}" not in text, (
            f"{record_name} must NOT be defined in repository.py. "
            "It belongs in records.py."
        )


class TestNoRecordDefinitionsInRunsOrExports:
    """PERMANENT GUARDRAIL: No record class may be defined in
    runs_repository.py or exports_repository.py."""

    @pytest.mark.parametrize("record_name", ["RunRecord"])
    def test_no_run_record_class_definition_in_runs(self, record_name):
        text = _read(RUNS_PY)
        assert f"class {record_name}" not in text

    @pytest.mark.parametrize("record_name", ["ScenarioExportRecord"])
    def test_no_export_record_class_definition_in_exports(self, record_name):
        text = _read(EXPORTS_PY)
        assert f"class {record_name}" not in text


# ============================================================
# 2. All 5 records must be in records.py
# ============================================================


class TestAllRecordsInRecordsPy:
    @pytest.mark.parametrize("record_name", ALL_5_RECORDS)
    def test_record_class_in_records_py(self, record_name):
        text = _read(RECORDS_PY)
        assert f"class {record_name}" in text, (
            f"{record_name} must be defined in records.py"
        )

    def test_records_py_is_under_400_lines(self):
        text = _read(RECORDS_PY)
        n = len(text.splitlines())
        assert n < 400, f"records.py unexpectedly large: {n} lines"

    def test_records_py_has_docstring(self):
        text = _read(RECORDS_PY)
        assert '"""' in text or "'''" in text, "records.py should have a module docstring"


# ============================================================
# 3. Compatibility re-exports must exist
# ============================================================


class TestCompatibilityReExports:
    """PERMANENT GUARDRAIL: repository.py must re-export all 5 records
    for backward compatibility."""

    @pytest.mark.parametrize("record_name", ALL_5_RECORDS)
    def test_repository_re_exports_record(self, record_name):
        text = _read(REPOSITORY_PY)
        # Either: `from app.persistence.records import <Record>`
        # Or: `__all__` with the record name
        assert f"from app.persistence.records import" in text
        # The record name must appear in an import statement
        assert record_name in text, (
            f"{record_name} should be re-exported from repository.py"
        )


# ============================================================
# 4. Public import paths must work
# ============================================================


class TestPublicImportPaths:
    @pytest.mark.parametrize("record_name", ALL_5_RECORDS)
    def test_record_importable_from_records_module(self, record_name):
        mod = __import__("app.persistence.records", fromlist=[record_name])
        assert hasattr(mod, record_name)

    @pytest.mark.parametrize("record_name", ALL_5_RECORDS)
    def test_record_importable_from_repository_module(self, record_name):
        mod = __import__("app.persistence.repository", fromlist=[record_name])
        assert hasattr(mod, record_name)

    def test_records_4_of_5_importable_from_app_persistence_init(self):
        # WorkspaceStateRecord is the one NOT re-exported from __init__
        # (pre-existing behavior, documented)
        import app.persistence as p
        assert hasattr(p, "ProjectRecord")
        assert hasattr(p, "ScenarioRecord")
        assert hasattr(p, "RunRecord")
        assert hasattr(p, "ScenarioExportRecord")


# ============================================================
# 5. Object identity must be preserved
# ============================================================


class TestObjectIdentityAcrossPaths:
    """PERMANENT GUARDRAIL: same class object via different paths."""

    @pytest.mark.parametrize("record_name", ALL_5_RECORDS)
    def test_object_identity(self, record_name):
        from app.persistence.records import __dict__ as r_dict
        from app.persistence.repository import __dict__ as repo_dict
        cls_a = r_dict[record_name]
        cls_b = repo_dict[record_name]
        assert cls_a is cls_b, (
            f"{record_name} must be the same class object via "
            "app.persistence.records and app.persistence.repository"
        )


# ============================================================
# 6. No lazy imports of records from repository in domain modules
# ============================================================


class TestNoRecordLazyImportsInDomainModules:
    """PERMANENT GUARDRAIL: app/persistence/*_repository.py must NOT
    import record dataclasses from app.persistence.repository.
    They must import directly from app.persistence.records."""

    @pytest.mark.parametrize("module_path,record_names", [
        (SCENARIOS_PY, ["ProjectRecord", "ScenarioRecord", "WorkspaceStateRecord"]),
        (PROJECTS_PY, ["ProjectRecord", "ScenarioRecord", "WorkspaceStateRecord"]),
        (WORKSPACE_PY, ["ProjectRecord", "ScenarioRecord", "WorkspaceStateRecord"]),
        (RUNS_PY, ALL_5_RECORDS),
        (EXPORTS_PY, ALL_5_RECORDS),
    ])
    def test_no_record_lazy_imports_from_repository(self, module_path, record_names):
        text = _read(module_path)
        for line in text.splitlines():
            if "from app.persistence.repository import" in line:
                for r in record_names:
                    if r in line:
                        pytest.fail(
                            f"{module_path.name} imports {r} from "
                            "app.persistence.repository (lazy import). "
                            "Should import directly from app.persistence.records."
                        )


# ============================================================
# 7. repository.py facade structure
# ============================================================


class TestRepositoryFacadeStructure:
    def test_repository_has_module_docstring(self):
        text = _read(REPOSITORY_PY)
        assert '"""' in text[:200] or "'''" in text[:200], \
            "repository.py should have a module docstring at the top"

    def test_repository_under_350_lines(self):
        text = _read(REPOSITORY_PY)
        n = len(text.splitlines())
        assert n < 350, f"repository.py unexpectedly large: {n} lines"

    def test_repository_re_exports_from_separate_modules(self):
        text = _read(REPOSITORY_PY)
        # Should re-export from all 6 separate modules
        expected_modules = [
            "from app.persistence.records",
            "from app.persistence._helpers",
            "from app.persistence.runs_repository",
            "from app.persistence.exports_repository",
            "from app.persistence.projects_repository",
            "from app.persistence.workspace_repository",
            "from app.persistence.scenarios_repository",
        ]
        for m in expected_modules:
            assert m in text, f"repository.py should re-export from {m}"

    def test_repository_has_residual_functions(self):
        text = _read(REPOSITORY_PY)
        # 5 NOT-Group-B functions remain in repository.py
        expected = [
            "seed_scenarios_if_needed",
            "get_scenario_provenance",
            "runtime_guard_for_snapshot",
            "update_scenario_last_run_summary",
            "record_workspace_runtime",
        ]
        for fn in expected:
            assert f"def {fn}" in text, f"repository.py should still define {fn}"


# ============================================================
# 8. No new persistence modules
# ============================================================


class TestNoNewPersistenceModules:
    def test_no_new_persistence_files(self):
        # Count persistence files
        persistence_dir = REPO_ROOT / "app" / "persistence"
        py_files = sorted(persistence_dir.glob("*.py"))
        # Expected: 11 .py files (excluding __init__.py)
        # _helpers.py, db.py, exports_repository.py, projects_repository.py,
        # provenance.py, records.py, repository.py, runs_repository.py,
        # scenarios_repository.py, workspace_repository.py, backup_restore.py
        # = 11 .py files
        non_init = [f for f in py_files if f.name != "__init__.py"]
        assert len(non_init) == 11, (
            f"Expected 11 persistence .py files (excluding __init__.py), "
            f"found {len(non_init)}: {[f.name for f in non_init]}"
        )
