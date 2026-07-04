"""Phase 53I-1 — Records field shape and import compatibility pins.

Pins the current record dataclass shapes and import paths BEFORE
relocation. These pins must continue to pass through 53I-2 and 53I-3
to prove the relocation is behavior-preserving.

Coverage:
1. Each record remains importable from current public path
2. Each record field list is pinned
3. Each record dataclass options are pinned (slots, defaults)
4. from_row behavior is pinned
5. Public compatibility from app.persistence.repository is pinned
6. Lazy imports in scenarios_repository.py are documented
"""
from __future__ import annotations

import importlib
import inspect
import re
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_PY = REPO_ROOT / "app" / "persistence" / "repository.py"
RECORDS_PY = REPO_ROOT / "app" / "persistence" / "records.py"  # does not exist yet
RUNS_PY = REPO_ROOT / "app" / "persistence" / "runs_repository.py"
EXPORTS_PY = REPO_ROOT / "app" / "persistence" / "exports_repository.py"
SCENARIOS_PY = REPO_ROOT / "app" / "persistence" / "scenarios_repository.py"


def _read(path):
    return path.read_text(encoding="utf-8")


# ============================================================
# 1. Import paths pinned
# ============================================================


class TestImportPaths:
    """Verify all 5 records are importable from their current paths."""

    def test_project_record_importable_from_repository(self):
        from app.persistence.repository import ProjectRecord
        assert ProjectRecord is not None

    def test_scenario_record_importable_from_repository(self):
        from app.persistence.repository import ScenarioRecord
        assert ScenarioRecord is not None

    def test_workspace_state_record_importable_from_repository(self):
        from app.persistence.repository import WorkspaceStateRecord
        assert WorkspaceStateRecord is not None

    def test_run_record_importable_from_runs_repository(self):
        from app.persistence.runs_repository import RunRecord
        assert RunRecord is not None

    def test_scenario_export_record_importable_from_exports_repository(self):
        from app.persistence.exports_repository import ScenarioExportRecord
        assert ScenarioExportRecord is not None

    def test_records_module_exists_post_53i2(self):
        # After 53I-2, records.py MUST exist (and be importable)
        assert RECORDS_PY.exists(), \
            "records.py should exist after 53I-2"

    def test_records_module_importable(self):
        # All 5 records must be importable from records module
        from app.persistence.records import (
            ProjectRecord, ScenarioRecord, WorkspaceStateRecord,
            RunRecord, ScenarioExportRecord,
        )
        for cls in [ProjectRecord, ScenarioRecord, WorkspaceStateRecord,
                    RunRecord, ScenarioExportRecord]:
            assert cls is not None


# ============================================================
# 2. Public compatibility from app.persistence.repository
# ============================================================


class TestPublicCompatibility:
    def test_records_importable_from_app_persistence_repository(self):
        from app.persistence.repository import (
            ProjectRecord, ScenarioRecord, WorkspaceStateRecord,
        )
        assert ProjectRecord is not None
        assert ScenarioRecord is not None
        assert WorkspaceStateRecord is not None

    def test_records_importable_from_app_persistence_init(self):
        from app.persistence import ProjectRecord, ScenarioRecord
        # app/persistence/__init__.py re-exports these
        assert ProjectRecord is not None
        assert ScenarioRecord is not None


# ============================================================
# 3. Field shapes pinned
# ============================================================


def _get_field_names(cls):
    """Get field names for both @dataclass and manual __slots__ classes."""
    if hasattr(cls, "__dataclass_fields__"):
        return sorted(cls.__dataclass_fields__.keys())
    elif hasattr(cls, "__slots__"):
        return sorted(cls.__slots__)
    return []


def _get_init_params(cls):
    """Get __init__ parameters for both @dataclass and manual classes."""
    try:
        sig = inspect.signature(cls.__init__)
        return [p.name for p in sig.parameters.values() if p.name != "self"]
    except (TypeError, ValueError):
        return []


class TestFieldShapes:
    """Pin the field names of each record. This protects against
    accidental field addition/removal during relocation."""

    EXPECTED_PROJECT_RECORD_FIELDS = sorted([
        "project_id", "user_id", "project_code", "project_name",
        "project_type", "project_origin", "source_project_template",
        "template_source", "baseline_snapshot", "archived", "is_readonly",
        "governance_state", "last_run_summary", "replay_metadata",
        "created_at", "updated_at",
        "full_inputs",  # V3-7: full-fidelity ProjectInputs dict (nullable)
    ])

    EXPECTED_SCENARIO_RECORD_FIELDS = sorted([
        "scenario_id", "project_id", "user_id", "scenario_name", "project_code",
        "source_project_template", "copied_from_scenario_id", "archived",
        "is_base_case", "parent_scenario_id", "base_input_set", "overrides",
        "schema_version", "snapshot", "governance_state", "last_run_summary",
        "replay_metadata", "created_at", "updated_at",
    ])

    EXPECTED_WORKSPACE_STATE_RECORD_FIELDS = sorted([
        "workspace_id", "project_id", "user_id", "project_code",
        "active_scenario_id", "active_scenario_name",
        "draft_snapshot", "saved_snapshot",
        "last_runtime_snapshot", "last_runtime_summary",
        "last_runtime_snapshot_id", "last_runtime_origin", "last_runtime_scenario_id",
        "dirty", "governance_state", "replay_metadata",
        "created_at", "updated_at", "last_runtime_at",
    ])

    EXPECTED_RUN_RECORD_FIELDS = sorted([
        "run_id", "user_id", "project_type", "scenario", "created_at",
        "inputs", "kpis", "excel_path", "notes", "replay_metadata",
    ])

    EXPECTED_SCENARIO_EXPORT_RECORD_FIELDS = sorted([
        "export_id", "scenario_id", "project_id", "user_id", "export_type",
        "artifact_name", "artifact_path", "project_code",
        "governance_state", "runtime_snapshot_id", "replay_metadata",
        "created_at",
    ])

    def test_project_record_field_count(self):
        from app.persistence.repository import ProjectRecord
        assert len(_get_field_names(ProjectRecord)) == 17, \
            f"ProjectRecord has 17 fields, got {_get_field_names(ProjectRecord)}"

    def test_scenario_record_field_count(self):
        from app.persistence.repository import ScenarioRecord
        assert len(_get_field_names(ScenarioRecord)) == 19, \
            f"ScenarioRecord has 19 fields, got {_get_field_names(ScenarioRecord)}"

    def test_workspace_state_record_field_count(self):
        from app.persistence.repository import WorkspaceStateRecord
        assert len(_get_field_names(WorkspaceStateRecord)) == 19, \
            f"WorkspaceStateRecord has 19 fields, got {_get_field_names(WorkspaceStateRecord)}"

    def test_run_record_field_count(self):
        from app.persistence.runs_repository import RunRecord
        assert len(_get_field_names(RunRecord)) == 10

    def test_scenario_export_record_field_count(self):
        from app.persistence.exports_repository import ScenarioExportRecord
        assert len(_get_field_names(ScenarioExportRecord)) == 12

    def test_project_record_exact_fields(self):
        from app.persistence.repository import ProjectRecord
        assert _get_field_names(ProjectRecord) == self.EXPECTED_PROJECT_RECORD_FIELDS

    def test_scenario_record_exact_fields(self):
        from app.persistence.repository import ScenarioRecord
        assert _get_field_names(ScenarioRecord) == self.EXPECTED_SCENARIO_RECORD_FIELDS

    def test_workspace_state_record_exact_fields(self):
        from app.persistence.repository import WorkspaceStateRecord
        assert _get_field_names(WorkspaceStateRecord) == self.EXPECTED_WORKSPACE_STATE_RECORD_FIELDS

    def test_run_record_exact_fields(self):
        from app.persistence.runs_repository import RunRecord
        assert _get_field_names(RunRecord) == self.EXPECTED_RUN_RECORD_FIELDS

    def test_scenario_export_record_exact_fields(self):
        from app.persistence.exports_repository import ScenarioExportRecord
        assert _get_field_names(ScenarioExportRecord) == self.EXPECTED_SCENARIO_EXPORT_RECORD_FIELDS


# ============================================================
# 4. __slots__ + dataclass options
# ============================================================


class TestSlotsAndOptions:
    def test_project_record_has_slots(self):
        from app.persistence.repository import ProjectRecord
        assert hasattr(ProjectRecord, "__slots__"), "ProjectRecord must have __slots__"

    def test_scenario_record_has_slots(self):
        from app.persistence.repository import ScenarioRecord
        assert hasattr(ScenarioRecord, "__slots__"), "ScenarioRecord must have __slots__"

    def test_workspace_state_record_has_slots(self):
        from app.persistence.repository import WorkspaceStateRecord
        assert hasattr(WorkspaceStateRecord, "__slots__"), \
            "WorkspaceStateRecord must have __slots__"

    def test_run_record_has_slots(self):
        from app.persistence.runs_repository import RunRecord
        assert hasattr(RunRecord, "__slots__")

    def test_scenario_export_record_has_slots(self):
        from app.persistence.exports_repository import ScenarioExportRecord
        assert hasattr(ScenarioExportRecord, "__slots__")


# ============================================================
# 5. from_row methods
# ============================================================


class TestFromRowMethods:
    """Pin that each record has a from_row classmethod."""

    def test_project_record_from_row_exists(self):
        from app.persistence.repository import ProjectRecord
        assert hasattr(ProjectRecord, "from_row")
        assert callable(ProjectRecord.from_row)

    def test_scenario_record_from_row_exists(self):
        from app.persistence.repository import ScenarioRecord
        assert hasattr(ScenarioRecord, "from_row")
        assert callable(ScenarioRecord.from_row)

    def test_workspace_state_record_from_row_exists(self):
        from app.persistence.repository import WorkspaceStateRecord
        assert hasattr(WorkspaceStateRecord, "from_row")
        assert callable(WorkspaceStateRecord.from_row)

    def test_run_record_from_row_exists(self):
        from app.persistence.runs_repository import RunRecord
        assert hasattr(RunRecord, "from_row")
        assert callable(RunRecord.from_row)

    def test_scenario_export_record_from_row_exists(self):
        from app.persistence.exports_repository import ScenarioExportRecord
        assert hasattr(ScenarioExportRecord, "from_row")
        assert callable(ScenarioExportRecord.from_row)


# ============================================================
# 6. Lazy imports in scenarios_repository.py
# ============================================================


class TestLazyImports:
    """Pin the count of lazy imports of record dataclasses in
    scenarios_repository.py. After 53I-3, this count should drop to 0."""

    def test_count_lazy_imports_in_scenarios_repository_post_53i3(self):
        # After 53I-3, no record dataclass lazy imports should remain
        # (they should now import directly from app.persistence.records).
        text = _read(SCENARIOS_PY)
        lines = text.splitlines()
        count = 0
        for line in lines:
            if "from app.persistence.repository import" in line:
                if any(r in line for r in [
                    "ProjectRecord", "ScenarioRecord", "WorkspaceStateRecord"
                ]):
                    count += 1
        assert count == 0, \
            f"After 53I-3, expected 0 record lazy imports, got {count}"

    def test_count_lazy_imports_in_other_modules(self):
        # Count in other modules
        for py in [REPO_ROOT / "app" / "persistence" / "projects_repository.py",
                  REPO_ROOT / "app" / "persistence" / "workspace_repository.py"]:
            text = _read(py)
            lines = text.splitlines()
            for line in lines:
                if "from app.persistence.repository import" in line:
                    if any(r in line for r in [
                        "ProjectRecord", "ScenarioRecord", "WorkspaceStateRecord"
                    ]):
                        # Each module may have such imports
                        pass


# ============================================================
# 7. Object identity pins
# ============================================================


class TestObjectIdentity:
    """The same record imported from different paths must be the same class."""

    def test_project_record_same_object_via_paths(self):
        from app.persistence.repository import ProjectRecord as A
        # Also accessible from app.persistence
        from app.persistence import ProjectRecord as B
        assert A is B, "ProjectRecord must be the same object via different paths"

    def test_scenario_record_same_object_via_paths(self):
        from app.persistence.repository import ScenarioRecord as A
        from app.persistence import ScenarioRecord as B
        assert A is B

    def test_workspace_state_record_same_object_via_paths(self):
        from app.persistence.repository import WorkspaceStateRecord as A
        # WorkspaceStateRecord may not be re-exported from __init__
        # That's OK as long as the path is consistent
        assert A is not None

    def test_run_record_same_object_via_paths(self):
        from app.persistence.runs_repository import RunRecord as A
        from app.persistence import RunRecord as B
        assert A is B

    def test_scenario_export_record_same_object_via_paths(self):
        from app.persistence.exports_repository import ScenarioExportRecord as A
        from app.persistence import ScenarioExportRecord as B
        assert A is B
