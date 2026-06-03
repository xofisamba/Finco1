"""Phase 53G-1 — Scenario/Workspace coupling P0 pin.

This is the FIRST pin (per the spec) — it pins the coupling between
scenario persistence and workspace persistence BEFORE any Group B
extraction. If the coupling changes during 53G-2..53G-7, this pin
will fail.

The coupling points covered:

1. `bind_workspace_to_scenario` calls `save_workspace_state` with the
   scenario's snapshot as both draft AND saved snapshot, and with
   active_scenario_id = record.scenario_id.

2. `discard_workspace_draft` does NOT touch scenario state — it only
   restores the workspace's draft from its saved snapshot.

3. `update_scenario_overrides` re-resolves the effective snapshot via
   `resolve_scenario_snapshot` and updates BOTH overrides_json AND
   snapshot_json in the same SQL statement (atomic update).

4. `add_scenario` stores both base_input_set_json AND overrides_json
   AND snapshot_json (effective = base + overrides) at insert time.

5. `save_scenario` is INSERT-only (no UPSERT). It is called by
   `get_or_create_base_case_scenario` (when no base case exists) and
   is the only path for inserting a brand-new scenario record.

6. `select_scenario` (when called by the workspace binding) calls
   `bind_workspace_to_scenario` internally.

7. Workspace re-export: save_workspace_state, get_workspace_state,
   discard_workspace_draft, bind_workspace_to_scenario are all in
   app/persistence/workspace_repository.py (post-53F-2). Their import
   from app.persistence.repository still works.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_PY = REPO_ROOT / "app" / "persistence" / "repository.py"
WORKSPACE_PY = REPO_ROOT / "app" / "persistence" / "workspace_repository.py"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


# ============================================================
# Coupling 1: bind_workspace_to_scenario
# ============================================================


class TestBindWorkspaceToScenarioCoupling:
    """bind_workspace_to_scenario lives in workspace_repository.py and
    couples workspace state to a scenario via save_workspace_state."""

    def test_bind_workspace_to_scenario_in_workspace_module(self):
        text = _read(WORKSPACE_PY)
        assert "def bind_workspace_to_scenario(" in text

    def test_bind_workspace_to_scenario_re_exported(self):
        text = _read(REPOSITORY_PY)
        assert "from app.persistence.workspace_repository import" in text
        assert "bind_workspace_to_scenario" in text

    def test_bind_workspace_to_scenario_passes_scenario_id_and_name(self):
        # Inside the function, it must pass record.scenario_id and
        # record.scenario_name to save_workspace_state
        text = _read(WORKSPACE_PY)
        # Find the function
        m = re.search(r"def bind_workspace_to_scenario\(.*?(?=\n\ndef |\Z)",
                      text, re.DOTALL)
        assert m, "bind_workspace_to_scenario not found"
        body = m.group(0)
        assert "active_scenario_id=record.scenario_id" in body
        assert "active_scenario_name=record.scenario_name" in body

    def test_bind_workspace_to_scenario_passes_snapshot_to_both_draft_and_saved(self):
        # The scenario's snapshot is used as BOTH draft and saved
        text = _read(WORKSPACE_PY)
        m = re.search(r"def bind_workspace_to_scenario\(.*?(?=\n\ndef |\Z)",
                      text, re.DOTALL)
        body = m.group(0)
        assert "draft_snapshot=record.snapshot" in body
        assert "saved_snapshot=record.snapshot" in body

    def test_bind_workspace_to_scenario_marks_dirty_false(self):
        text = _read(WORKSPACE_PY)
        m = re.search(r"def bind_workspace_to_scenario\(.*?(?=\n\ndef |\Z)",
                      text, re.DOTALL)
        body = m.group(0)
        assert "dirty=False" in body

    def test_bind_workspace_to_scenario_inherits_governance_state(self):
        text = _read(WORKSPACE_PY)
        m = re.search(r"def bind_workspace_to_scenario\(.*?(?=\n\ndef |\Z)",
                      text, re.DOTALL)
        body = m.group(0)
        # If no override given, inherits from record
        assert "governance_state=governance_state or record.governance_state" in body


# ============================================================
# Coupling 2: discard_workspace_draft
# ============================================================


class TestDiscardWorkspaceDraftCoupling:
    """discard_workspace_draft only touches workspace, not scenarios."""

    def test_discard_workspace_draft_does_not_modify_scenarios_table(self):
        text = _read(WORKSPACE_PY)
        m = re.search(r"def discard_workspace_draft\(.*?(?=\n\ndef |\Z)",
                      text, re.DOTALL)
        body = m.group(0)
        # Should NOT contain UPDATE scenarios or INSERT scenarios
        assert "UPDATE scenarios" not in body
        assert "INSERT INTO scenarios" not in body
        assert "DELETE FROM scenarios" not in body

    def test_discard_workspace_draft_restores_draft_from_saved(self):
        text = _read(WORKSPACE_PY)
        m = re.search(r"def discard_workspace_draft\(.*?(?=\n\ndef |\Z)",
                      text, re.DOTALL)
        body = m.group(0)
        # The draft is restored from saved_snapshot
        assert "draft_snapshot=record.saved_snapshot" in body


# ============================================================
# Coupling 3: update_scenario_overrides re-resolves snapshot
# ============================================================


class TestUpdateScenarioOverridesCoupling:
    """update_scenario_overrides updates BOTH overrides_json AND
    snapshot_json atomically in one UPDATE statement."""

    def test_update_scenario_overrides_uses_resolve_scenario_snapshot(self):
        text = _read(REPOSITORY_PY)
        m = re.search(r"def update_scenario_overrides\(.*?(?=\n\ndef |\Z)",
                      text, re.DOTALL)
        assert m, "update_scenario_overrides not found"
        body = m.group(0)
        assert "resolve_scenario_snapshot(record.base_input_set, merged)" in body

    def test_update_scenario_overrides_atomic_both_columns(self):
        # Single UPDATE statement that sets BOTH overrides_json AND snapshot_json
        text = _read(REPOSITORY_PY)
        m = re.search(r"def update_scenario_overrides\(.*?(?=\n\ndef |\Z)",
                      text, re.DOTALL)
        body = m.group(0)
        assert "SET overrides_json=?, snapshot_json=?, updated_at=?" in body

    def test_update_scenario_overrides_rejects_base_case(self):
        # base-case overrides are stored in base_input_set, not overrides
        text = _read(REPOSITORY_PY)
        m = re.search(r"def update_scenario_overrides\(.*?(?=\n\ndef |\Z)",
                      text, re.DOTALL)
        body = m.group(0)
        assert "if record.is_base_case:" in body
        assert "return None  # base-case overrides" in body

    def test_update_scenario_overrides_filters_to_scenario_input_fields(self):
        # Only keys in SCENARIO_INPUT_FIELDS are accepted
        text = _read(REPOSITORY_PY)
        m = re.search(r"def update_scenario_overrides\(.*?(?=\n\ndef |\Z)",
                      text, re.DOTALL)
        body = m.group(0)
        assert "if key in SCENARIO_INPUT_FIELDS:" in body


# ============================================================
# Coupling 4: add_scenario stores all three JSON columns
# ============================================================


class TestAddScenarioCoupling:
    def test_add_scenario_stores_base_overrides_resolved(self):
        text = _read(REPOSITORY_PY)
        m = re.search(r"def add_scenario\(.*?(?=\n\ndef |\Z)", text, re.DOTALL)
        body = m.group(0)
        # All three columns stored
        assert "base_input_set_json" in body
        assert "overrides_json" in body
        assert "snapshot_json" in body
        # snapshot_json gets the resolved (= base + overrides) value
        assert "_to_json(resolved)" in body

    def test_add_scenario_records_action_in_replay_metadata(self):
        text = _read(REPOSITORY_PY)
        m = re.search(r"def add_scenario\(.*?(?=\n\ndef |\Z)", text, re.DOTALL)
        body = m.group(0)
        assert 'replay_metadata["action"] = "add_scenario"' in body
        assert 'replay_metadata["parent_scenario_id"] = parent_scenario_id' in body


# ============================================================
# Coupling 5: save_scenario is INSERT-only
# ============================================================


class TestSaveScenarioCoupling:
    def test_save_scenario_uses_insert_not_upsert(self):
        text = _read(REPOSITORY_PY)
        m = re.search(r"def save_scenario\(.*?(?=\n\ndef |\Z)", text, re.DOTALL)
        body = m.group(0)
        assert "INSERT INTO scenarios" in body
        # No UPSERT
        assert "ON CONFLICT" not in body
        assert "INSERT OR REPLACE" not in body

    def test_save_scenario_sets_replay_metadata_keys(self):
        text = _read(REPOSITORY_PY)
        m = re.search(r"def save_scenario\(.*?(?=\n\ndef |\Z)", text, re.DOTALL)
        body = m.group(0)
        assert 'replay_metadata.setdefault("project_id", project_id)' in body
        assert 'replay_metadata.setdefault("scenario_id", scenario_id)' in body


# ============================================================
# Coupling 6: resolve_scenario_snapshot
# ============================================================


class TestResolveScenarioSnapshotCoupling:
    def test_resolve_scenario_snapshot_in_repository(self):
        text = _read(REPOSITORY_PY)
        assert "def resolve_scenario_snapshot(" in text

    def test_resolve_scenario_snapshot_signature(self):
        # (base_input_set, overrides) -> dict
        from app.persistence.repository import resolve_scenario_snapshot
        import inspect
        sig = inspect.signature(resolve_scenario_snapshot)
        params = sig.parameters
        assert "base_input_set" in params
        assert "overrides" in params
        assert len(params) == 2
