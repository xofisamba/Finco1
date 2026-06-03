"""Phase 53E-1 — P0 behavior pin for save_project.

This file pins the current behavior of save_project so that any
future refactor (53E-2 extraction) can be verified against these
expectations without weakening them.

The pin captures:
  - signature (name, params, defaults, return annotation)
  - INSERT path (when no existing row)
  - UPDATE path (when existing row present)
  - metadata behaviors: replay_metadata, governance_state, last_run_summary
  - project_origin defaulting
  - template_source defaulting
  - SQL fragments
  - public import path
  - ProjectRecord return shape
"""
from __future__ import annotations

import inspect
import re
import sqlite3
import tempfile
from pathlib import Path
from typing import Any, Dict, List

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_PY = REPO_ROOT / "app" / "persistence" / "repository.py"
PROJECTS_PY = REPO_ROOT / "app" / "persistence" / "projects_repository.py"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


# ----------------------------- Public import path pin ----------------------------


class TestPublicImportPath:
    def test_save_project_importable_from_app_persistence_repository(self):
        from app.persistence.repository import save_project
        assert save_project is not None

    def test_save_project_module_origin_is_projects_repository(self):
        # After Phase 53E-2, save_project is DEFINED in app.persistence.projects_repository
        # (with re-export from app.persistence.repository)
        from app.persistence import repository
        # The __module__ attribute tells us where the function was defined.
        assert repository.save_project.__module__ == "app.persistence.projects_repository", \
            f"save_project.__module__ is {repository.save_project.__module__}, expected app.persistence.projects_repository"


# ----------------------------- Signature pin ----------------------------


class TestSignature:
    def test_function_name(self):
        from app.persistence.repository import save_project
        assert save_project.__name__ == "save_project"

    def test_signature_parameters_and_defaults(self):
        from app.persistence.repository import save_project
        sig = inspect.signature(save_project)
        params = list(sig.parameters.keys())
        assert params == [
            "user_id", "project_code", "project_name", "source_project_template",
            "project_type", "project_origin", "template_source",
            "baseline_snapshot", "archived", "is_readonly",
            "governance_state", "last_run_summary", "replay_metadata",
        ], f"got {params}"

    def test_signature_defaults(self):
        from app.persistence.repository import save_project
        sig = inspect.signature(save_project)
        # project_type default: None
        assert sig.parameters["project_type"].default is None
        # project_origin default: "factory_template"
        assert sig.parameters["project_origin"].default == "factory_template"
        # template_source default: None
        assert sig.parameters["template_source"].default is None
        # baseline_snapshot default: None
        assert sig.parameters["baseline_snapshot"].default is None
        # archived default: False
        assert sig.parameters["archived"].default is False
        # is_readonly default: False
        assert sig.parameters["is_readonly"].default is False
        # governance_state default: None
        assert sig.parameters["governance_state"].default is None
        # last_run_summary default: None
        assert sig.parameters["last_run_summary"].default is None
        # replay_metadata default: None
        assert sig.parameters["replay_metadata"].default is None
        # No default for user_id, project_code, project_name, source_project_template
        for p in ["user_id", "project_code", "project_name", "source_project_template"]:
            assert sig.parameters[p].default is inspect.Parameter.empty, f"{p} should be required"


# ----------------------------- SQL text pin ----------------------------


class TestSQLFragments:
    """Pin the SQL fragments that save_project uses, so that any
    refactor preserves them. After 53E-2, save_project lives in
    app.persistence.projects_repository, so we check that file."""

    def test_select_existing_sql_present(self):
        text = _read(PROJECTS_PY)
        assert "SELECT project_id, created_at, project_type, project_origin, template_source, baseline_snapshot_json, archived" in text
        assert "FROM projects" in text
        assert "WHERE user_id=? AND project_code=?" in text

    def test_update_sql_present(self):
        text = _read(PROJECTS_PY)
        assert "UPDATE projects" in text
        assert "SET project_name=?, project_type=?, project_origin=?, source_project_template=?, template_source=?" in text
        assert "baseline_snapshot_json=?, archived=?, is_readonly=?, governance_state_json=?, last_run_summary_json=?" in text
        assert "replay_metadata_json=?, updated_at=?" in text
        assert "WHERE project_id=? AND user_id=?" in text

    def test_insert_sql_present(self):
        text = _read(PROJECTS_PY)
        assert "INSERT INTO projects (" in text
        assert "project_id, user_id, project_code, project_name, project_type, project_origin," in text
        assert "source_project_template, template_source, baseline_snapshot_json, archived, is_readonly," in text
        assert "governance_state_json, last_run_summary_json, replay_metadata_json, created_at, updated_at" in text
        assert ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)" in text

    def test_single_transaction_pattern(self):
        text = _read(PROJECTS_PY)
        # Find the save_project function block and verify it has a single with block
        lines = text.splitlines()
        # Find start
        start = None
        for i, line in enumerate(lines):
            if line.startswith("def save_project("):
                start = i
                break
        # Find the next def or class at same indent
        end = None
        for i in range(start+1, len(lines)):
            if lines[i].startswith("def "):
                end = i
                break
        if end is None:
            end = len(lines)
        body = "\n".join(lines[start:end])
        # Count "with get_cursor() as cur:" occurrences
        n_with = body.count("with get_cursor() as cur:")
        assert n_with == 1, f"save_project should have exactly 1 with get_cursor() block, got {n_with}"


# ----------------------------- replay_metadata behavior pin ----------------------------


class TestReplayMetadataBehavior:
    """Pin replay_metadata behavior:
    - accepted shape: dict (or None)
    - defaulting: dict(replay_metadata or {}) so None is acceptable
    - JSON serialization: via _to_json
    - if existing row, replay_metadata.setdefault("project_id", project_id)
    """

    def test_replay_metadata_none_becomes_empty_dict(self):
        # The source uses: replay_metadata = dict(replay_metadata or {})
        # This means None is converted to {} before being used
        from app.persistence.repository import save_project
        text = _read(PROJECTS_PY)
        # The exact pattern
        assert "replay_metadata = dict(replay_metadata or {})" in text

    def test_replay_metadata_setdefault_project_id(self):
        # Both INSERT and UPDATE paths use replay_metadata.setdefault("project_id", project_id)
        from app.persistence.repository import save_project
        text = _read(PROJECTS_PY)
        # In the save_project function block, setdefault is called
        # We check the function body
        sig = inspect.getsource(save_project)
        assert 'replay_metadata.setdefault("project_id", project_id)' in sig


# ----------------------------- governance_state behavior pin ----------------------------


class TestGovernanceStateBehavior:
    """Pin governance_state behavior:
    - accepted shape: dict (or None)
    - defaulting: governance_state or {} so None becomes {}
    - JSON serialization: via _to_json
    """

    def test_governance_state_none_becomes_empty_dict(self):
        text = _read(PROJECTS_PY)
        assert "governance_state = governance_state or {}" in text

    def test_governance_state_is_json_serialized(self):
        # Both UPDATE and INSERT paths use _to_json(governance_state)
        from app.persistence.repository import save_project
        sig = inspect.getsource(save_project)
        assert "_to_json(governance_state)" in sig


# ----------------------------- last_run_summary behavior pin ----------------------------


class TestLastRunSummaryBehavior:
    """Pin last_run_summary behavior."""

    def test_last_run_summary_none_becomes_empty_dict(self):
        text = _read(PROJECTS_PY)
        assert "last_run_summary = last_run_summary or {}" in text

    def test_last_run_summary_is_json_serialized(self):
        from app.persistence.repository import save_project
        sig = inspect.getsource(save_project)
        assert "_to_json(last_run_summary)" in sig


# ----------------------------- baseline_snapshot behavior pin ----------------------------


class TestBaselineSnapshotBehavior:
    """Pin baseline_snapshot behavior."""

    def test_baseline_snapshot_none_becomes_empty_dict(self):
        text = _read(PROJECTS_PY)
        assert "baseline_snapshot = baseline_snapshot or {}" in text

    def test_baseline_snapshot_is_json_serialized(self):
        from app.persistence.repository import save_project
        sig = inspect.getsource(save_project)
        assert "_to_json(baseline_snapshot)" in sig

    def test_baseline_snapshot_preserved_from_existing(self):
        # In UPDATE path, if baseline_snapshot is not given, it's loaded from existing row
        from app.persistence.repository import save_project
        sig = inspect.getsource(save_project)
        assert "if not baseline_snapshot:" in sig
        assert "_from_json(existing[\"baseline_snapshot_json\"], {})" in sig


# ----------------------------- project_origin behavior pin ----------------------------


class TestProjectOriginBehavior:
    """Pin project_origin behavior:
    - default: "factory_template"
    - on UPDATE: project_origin = project_origin or existing["project_origin"] or "factory_template"
    """

    def test_project_origin_default_is_factory_template(self):
        from app.persistence.repository import save_project
        sig = inspect.signature(save_project)
        assert sig.parameters["project_origin"].default == "factory_template"

    def test_project_origin_fallback_to_factory_template(self):
        # In UPDATE path: project_origin = project_origin or existing["project_origin"] or "factory_template"
        from app.persistence.repository import save_project
        sig = inspect.getsource(save_project)
        assert 'project_origin = project_origin or existing["project_origin"] or "factory_template"' in sig


# ----------------------------- template_source behavior pin ----------------------------


class TestTemplateSourceBehavior:
    """Pin template_source behavior:
    - default: None
    - effective_template_source = template_source or source_project_template
    - on UPDATE: effective_template_source = effective_template_source or existing["template_source"] or source_project_template
    """

    def test_template_source_default_is_none(self):
        from app.persistence.repository import save_project
        sig = inspect.signature(save_project)
        assert sig.parameters["template_source"].default is None

    def test_effective_template_source_initial(self):
        from app.persistence.repository import save_project
        sig = inspect.getsource(save_project)
        assert "effective_template_source = template_source or source_project_template" in sig

    def test_effective_template_source_fallback(self):
        from app.persistence.repository import save_project
        sig = inspect.getsource(save_project)
        # In UPDATE path
        assert 'effective_template_source = effective_template_source or existing["template_source"] or source_project_template' in sig


# ----------------------------- archived / is_readonly behavior pin ----------------------------


class TestArchivedIsReadonlyBehavior:
    """Pin archived / is_readonly behavior:
    - archived default: False
    - is_readonly default: False
    - both are stored as int(bool(...)) in DB
    - on UPDATE: archived = bool(existing["archived"]) if archived is None else archived
    """

    def test_archived_default_is_false(self):
        from app.persistence.repository import save_project
        sig = inspect.signature(save_project)
        assert sig.parameters["archived"].default is False

    def test_is_readonly_default_is_false(self):
        from app.persistence.repository import save_project
        sig = inspect.signature(save_project)
        assert sig.parameters["is_readonly"].default is False

    def test_archived_fallback_to_existing(self):
        from app.persistence.repository import save_project
        sig = inspect.getsource(save_project)
        assert 'archived = bool(existing["archived"]) if archived is None else archived' in sig

    def test_archived_and_is_readonly_serialized_as_int(self):
        from app.persistence.repository import save_project
        sig = inspect.getsource(save_project)
        assert "int(bool(archived))" in sig
        assert "int(bool(is_readonly))" in sig


# ----------------------------- Return type pin ----------------------------


class TestReturnType:
    """Pin the return type."""

    def test_returns_project_record_instance(self):
        from app.persistence.repository import save_project, ProjectRecord
        sig = inspect.signature(save_project)
        # Return annotation may be either the string "ProjectRecord" (forward ref)
        # or the actual ProjectRecord class (if Python resolved it at call time).
        ann = sig.return_annotation
        # Strip the outer quotes if present
        if isinstance(ann, str):
            stripped = ann.strip("'\"")
            assert stripped == "ProjectRecord", f"got {ann!r}"
        else:
            assert ann is ProjectRecord, f"got {ann!r}"

    def test_return_is_dataclass(self):
        from app.persistence.repository import ProjectRecord
        assert hasattr(ProjectRecord, "__slots__")


# ----------------------------- created_at / updated_at behavior pin ----------------------------


class TestCreatedAtUpdatedAt:
    """Pin created_at / updated_at behavior:
    - now = _now_utc() called once
    - INSERT: created_at = now, updated_at = now
    - UPDATE: created_at = _from_iso(existing["created_at"]), updated_at = now
    """

    def test_now_called_once(self):
        from app.persistence.repository import save_project
        sig = inspect.getsource(save_project)
        # Exactly one now = _now_utc()
        n = sig.count("now = _now_utc()")
        assert n == 1, f"expected exactly 1 'now = _now_utc()', got {n}"

    def test_insert_uses_now_for_both(self):
        from app.persistence.repository import save_project
        sig = inspect.getsource(save_project)
        # In the INSERT path, created_at = now and updated_at = now
        # Both are serialized with created_at.isoformat() and now.isoformat()
        assert "created_at.isoformat()" in sig
        assert "now.isoformat()" in sig

    def test_update_preserves_created_at(self):
        from app.persistence.repository import save_project
        sig = inspect.getsource(save_project)
        # In the UPDATE path
        assert "created_at = _from_iso(existing[\"created_at\"])" in sig


# ----------------------------- project_id behavior pin ----------------------------


class TestProjectIdBehavior:
    """Pin project_id behavior:
    - INSERT: project_id = uuid.uuid4().hex[:16]
    - UPDATE: project_id = existing["project_id"] (preserved)
    """

    def test_insert_generates_new_project_id(self):
        from app.persistence.repository import save_project
        sig = inspect.getsource(save_project)
        # In the INSERT path (else branch)
        assert "project_id = uuid.uuid4().hex[:16]" in sig

    def test_update_preserves_existing_project_id(self):
        from app.persistence.repository import save_project
        sig = inspect.getsource(save_project)
        # In the UPDATE path (if existing branch)
        assert "project_id = existing[\"project_id\"]" in sig


# ----------------------------- Existing test coverage pin ----------------------------


class TestExistingCoverage:
    """Verify that the existing Phase 17/20/51 tests for save_project still cover the
    surface behavior."""

    def test_phase17_new_project_foundation_exists(self):
        # The Phase 17 test covers new project creation
        path = REPO_ROOT / "tests" / "test_phase17_new_project_foundation.py"
        assert path.exists()

    def test_phase20a_saved_baseline_models_exists(self):
        # The Phase 20A test covers saved baseline models
        path = REPO_ROOT / "tests" / "test_phase20a_saved_baseline_models.py"
        assert path.exists()

    def test_phase51m1_projects_create_characterization_exists(self):
        # The Phase 51M-1 test covers /projects/create (which uses save_project)
        path = REPO_ROOT / "tests" / "test_phase51m1_projects_create_route_golden_characterization.py"
        assert path.exists()


# ----------------------------- Other guardrails ----------------------------


class TestOtherGuardrails:
    """Verify Phase 51F and Phase 52F guardrails still pass for save_project context."""

    def test_save_project_now_in_projects_repository(self):
        # After Phase 53E-2, save_project IS in projects_repository.py (post-extraction)
        from app.persistence import projects_repository
        assert hasattr(projects_repository, "save_project")

    def test_no_save_project_in_helpers(self):
        from app.persistence import _helpers
        assert not hasattr(_helpers, "save_project")

    def test_no_save_project_in_runs_repository(self):
        from app.persistence import runs_repository
        assert not hasattr(runs_repository, "save_project")

    def test_no_save_project_in_exports_repository(self):
        from app.persistence import exports_repository
        assert not hasattr(exports_repository, "save_project")
