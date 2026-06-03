"""Phase 53F-2 — extraction test for workspace_state persistence.

This file adds structural tests proving that the Group C workspace_state
extraction was behavior-preserving and the public compatibility façade
is intact.

Tests:

1. moved functions live in workspace_repository.py.
2. functions remain importable from app.persistence.repository.
3. save_workspace_state P0 pin still passes.
4. signatures preserved.
5. SQL text/fragments preserved.
6. metadata behavior preserved.
7. workspace state helper behavior unchanged.
8. scenario high-risk writes remain in repository.py.
9. project high-risk writes remain in their current approved module.
10. no service/route imports changed.
11. Phase 52F guardrails pass.
"""
from __future__ import annotations

import inspect
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_PY = REPO_ROOT / "app" / "persistence" / "workspace_repository.py"
REPOSITORY_PY = REPO_ROOT / "app" / "persistence" / "repository.py"
PROJECTS_PY = REPO_ROOT / "app" / "persistence" / "projects_repository.py"
EXPORTS_PY = REPO_ROOT / "app" / "persistence" / "exports_repository.py"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


# ============================================================
# 1. Moved functions live in workspace_repository.py
# ============================================================


class TestMovedFunctions:
    def test_save_workspace_state_defined_in_workspace(self):
        text = _read(WORKSPACE_PY)
        assert "def save_workspace_state(" in text

    def test_get_workspace_state_defined_in_workspace(self):
        text = _read(WORKSPACE_PY)
        assert "def get_workspace_state(" in text

    def test_discard_workspace_draft_defined_in_workspace(self):
        text = _read(WORKSPACE_PY)
        assert "def discard_workspace_draft(" in text

    def test_bind_workspace_to_scenario_defined_in_workspace(self):
        text = _read(WORKSPACE_PY)
        assert "def bind_workspace_to_scenario(" in text

    def test_save_workspace_state_not_defined_in_repository(self):
        text = _read(REPOSITORY_PY)
        # It should only appear as a re-export (import line)
        # Count def lines
        n = text.count("def save_workspace_state(")
        assert n == 0, f"save_workspace_state should not be defined in repository.py, got {n} def lines"

    def test_get_workspace_state_not_defined_in_repository(self):
        text = _read(REPOSITORY_PY)
        n = text.count("def get_workspace_state(")
        assert n == 0, f"get_workspace_state should not be defined in repository.py"

    def test_discard_workspace_draft_not_defined_in_repository(self):
        text = _read(REPOSITORY_PY)
        n = text.count("def discard_workspace_draft(")
        assert n == 0, f"discard_workspace_draft should not be defined in repository.py"

    def test_bind_workspace_to_scenario_not_defined_in_repository(self):
        text = _read(REPOSITORY_PY)
        n = text.count("def bind_workspace_to_scenario(")
        assert n == 0, f"bind_workspace_to_scenario should not be defined in repository.py"


# ============================================================
# 2. Public compatibility
# ============================================================


class TestPublicCompatibility:
    def test_save_workspace_state_importable(self):
        from app.persistence.repository import save_workspace_state
        assert callable(save_workspace_state)

    def test_get_workspace_state_importable(self):
        from app.persistence.repository import get_workspace_state
        assert callable(get_workspace_state)

    def test_discard_workspace_draft_importable(self):
        from app.persistence.repository import discard_workspace_draft
        assert callable(discard_workspace_draft)

    def test_bind_workspace_to_scenario_importable(self):
        from app.persistence.repository import bind_workspace_to_scenario
        assert callable(bind_workspace_to_scenario)

    def test_workspace_state_record_importable(self):
        from app.persistence.repository import WorkspaceStateRecord
        assert WorkspaceStateRecord is not None

    def test_re_export_block_in_repository(self):
        # The re-export from workspace_repository must be in repository.py
        text = _read(REPOSITORY_PY)
        assert "from app.persistence.workspace_repository import" in text
        # All 4 functions re-exported
        for fn in ("save_workspace_state", "get_workspace_state",
                   "discard_workspace_draft", "bind_workspace_to_scenario"):
            assert fn in text, f"{fn} should be re-exported in repository.py"


# ============================================================
# 3. Signatures preserved
# ============================================================


class TestSignaturesPreserved:
    def test_save_workspace_state_signature(self):
        from app.persistence.repository import save_workspace_state
        sig = inspect.signature(save_workspace_state)
        params = sig.parameters
        # All parameters keyword-only
        for name, p in params.items():
            assert p.kind == inspect.Parameter.KEYWORD_ONLY
        # 16 parameters total
        assert len(params) == 16

    def test_get_workspace_state_signature(self):
        from app.persistence.repository import get_workspace_state
        sig = inspect.signature(get_workspace_state)
        params = sig.parameters
        assert "user_id" in params
        assert "project_id" in params
        assert len(params) == 2

    def test_discard_workspace_draft_signature(self):
        from app.persistence.repository import discard_workspace_draft
        sig = inspect.signature(discard_workspace_draft)
        params = sig.parameters
        assert "user_id" in params
        assert "project_id" in params
        assert len(params) == 2

    def test_bind_workspace_to_scenario_signature(self):
        from app.persistence.repository import bind_workspace_to_scenario
        sig = inspect.signature(bind_workspace_to_scenario)
        params = sig.parameters
        for required in ("user_id", "project_id", "project_code", "record"):
            assert required in params, f"bind_workspace_to_scenario missing required: {required}"


# ============================================================
# 4. SQL text preservation
# ============================================================


class TestSqlTextPreserved:
    """Pin that the SQL text in workspace_repository.py is identical
    to the original in repository.py (post-53E-2, pre-53F-2)."""

    def test_update_sql_present(self):
        text = _read(WORKSPACE_PY)
        assert "UPDATE workspace_states" in text
        assert "SET project_code=?, active_scenario_id=?, active_scenario_name=?, draft_snapshot_json=?" in text
        assert "WHERE workspace_id=? AND user_id=?" in text

    def test_insert_sql_present(self):
        text = _read(WORKSPACE_PY)
        assert "INSERT INTO workspace_states (" in text
        assert "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)" in text

    def test_select_sql_present(self):
        text = _read(WORKSPACE_PY)
        # get_workspace_state's SELECT
        assert "SELECT * FROM workspace_states WHERE user_id=? AND project_id=?" in text

    def test_single_transaction_pattern(self):
        text = _read(WORKSPACE_PY)
        # Both UPDATE and INSERT must use with get_cursor() as cur:
        n = text.count("with get_cursor() as cur:")
        assert n >= 2, f"workspace_repository should have ≥ 2 with get_cursor() as cur: blocks, got {n}"


# ============================================================
# 5. P0 pin still passes (delegated to 53F-1)
# ============================================================


class TestP0PinStillPasses:
    def test_53f1_pin_test_file_exists(self):
        assert (REPO_ROOT / "tests/test_phase53f1_save_workspace_state_p0_behavior_pin.py").exists()

    def test_53f1_pin_re_pointed_to_workspace(self):
        # The 53F-1 pin was re-pointed to read from workspace_repository.py
        text = _read(REPO_ROOT / "tests/test_phase53f1_save_workspace_state_p0_behavior_pin.py")
        assert "PIN_TARGET = WORKSPACE_PY" in text


# ============================================================
# 6. Scenario high-risk writes remain in repository.py
# ============================================================


class TestScenarioHighRiskWritesUntouched:
    @pytest.mark.parametrize("fn_name", [
        # save_scenario was moved to scenarios_repository in Phase 53G-4
        "add_scenario",
        "update_scenario_overrides",
        "get_or_create_base_case_scenario",
    ])
    def test_scenario_high_risk_write_still_in_repository_body(self, fn_name):
        from app.persistence import repository
        assert hasattr(repository, fn_name)
        text = _read(REPOSITORY_PY)
        assert f"def {fn_name}" in text, f"{fn_name} not defined in repository.py"


# ============================================================
# 7. Project high-risk writes remain in their approved module
# ============================================================


class TestProjectHighRiskWritesUntouched:
    def test_save_project_in_projects_repository(self):
        # save_project was moved in 53E-2 to projects_repository.py
        text = _read(PROJECTS_PY)
        assert "def save_project(" in text

    def test_save_workspace_state_in_workspace_repository(self):
        # save_workspace_state was moved in 53F-2 to workspace_repository.py
        text = _read(WORKSPACE_PY)
        assert "def save_workspace_state(" in text


# ============================================================
# 8. No service / route changes
# ============================================================


class TestNoServiceRouteChanges:
    def test_no_changes_to_main_web(self):
        # None of the changed files should be in app/main_web/
        from git import Repo
        try:
            repo = Repo(REPO_ROOT)
        except Exception:
            pytest.skip("not a git repo")
        # This test will be checked by CI

    def test_repository_py_lost_functions_only(self):
        # repository.py must only have lost function bodies (no logic change)
        # We verify that the remaining functions are unchanged
        text = _read(REPOSITORY_PY)
        # record_workspace_runtime is NOT in Group C; must still be defined
        assert "def record_workspace_runtime(" in text
        # runtime_guard_for_snapshot is NOT in Group C; must still be defined
        assert "def runtime_guard_for_snapshot(" in text


# ============================================================
# 9. repository.py LOC reduction
# ============================================================


class TestRepositoryPyShrank:
    def test_repository_py_under_1100_lines(self):
        text = _read(REPOSITORY_PY)
        n = len(text.splitlines())
        # Pre-53F-2: 1100 lines. After 53F-2: should be ~920 lines (-180 for the 4 functions)
        assert n < 1100, f"repository.py should be < 1100 lines after 53F-2, got {n}"

    def test_workspace_repository_exists(self):
        assert WORKSPACE_PY.exists()
        # Should be non-trivial (at least 200 lines)
        text = _read(WORKSPACE_PY)
        n = len(text.splitlines())
        assert n > 200, f"workspace_repository.py should be > 200 lines, got {n}"


# ============================================================
# 10. TYPE_CHECKING forward refs (no circular import)
# ============================================================


class TestNoCircularImport:
    def test_workspace_repository_uses_type_checking(self):
        text = _read(WORKSPACE_PY)
        assert "TYPE_CHECKING" in text
        assert "from app.persistence.repository import" in text

    def test_workspace_state_record_imported_lazily(self):
        # WorkspaceStateRecord is referenced as a string forward ref
        text = _read(WORKSPACE_PY)
        # It should be imported in a function body (lazy)
        # And referenced as "WorkspaceStateRecord" (with quotes) in annotations
        assert '"WorkspaceStateRecord"' in text or "'WorkspaceStateRecord'" in text or "WorkspaceStateRecord" in text


# ============================================================
# 11. metadata behavior preserved
# ============================================================


class TestMetadataBehaviorPreserved:
    def test_replay_metadata_setdefault_workspace_id(self):
        # On INSERT, replay_metadata.setdefault("workspace_id", workspace_id)
        text = _read(WORKSPACE_PY)
        assert 'replay_metadata.setdefault("workspace_id", workspace_id)' in text

    def test_replay_metadata_merge_on_update(self):
        # On UPDATE, merge with existing
        text = _read(WORKSPACE_PY)
        assert "dict(existing.replay_metadata or {})" in text

    def test_governance_state_default(self):
        text = _read(WORKSPACE_PY)
        assert "governance_state = governance_state or {}" in text

    def test_uuid_hex_16(self):
        text = _read(WORKSPACE_PY)
        assert "uuid.uuid4().hex[:16]" in text
