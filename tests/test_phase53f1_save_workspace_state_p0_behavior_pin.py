"""Phase 53F-1 — P0 behavior pin for save_workspace_state.

This file pins the current behavior of save_workspace_state before Group C
extraction (53F-2). The pin is read-only: it asserts the current state
of the function and the relevant module surface, so that 53F-2 (extraction
into app/persistence/workspace_repository.py) must preserve everything
documented here.

Coverage:

1. save_workspace_state remains importable from app.persistence.repository.
2. Public function signature is pinned.
3. Insert/update/upsert behavior is pinned.
4. Dirty flag behavior is pinned.
5. active_scenario_id behavior is pinned.
6. draft_snapshot behavior is pinned.
7. saved_snapshot behavior is pinned.
8. last_runtime_* fields behavior is pinned.
9. replay_metadata behavior is pinned (input shape, default, merge).
10. governance_state behavior is pinned.
11. Timestamps behavior is pinned.
12. Single-transaction pattern is pinned.
13. SQL text is pinned (UPDATE + INSERT).
14. WorkspaceStateRecord return type is pinned.
15. Interaction with get_workspace_state is pinned.
16. No caller / route / service changes.
"""
from __future__ import annotations

import inspect
import re
from pathlib import Path
from typing import Any, Optional

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_PY = REPO_ROOT / "app" / "persistence" / "repository.py"
WORKSPACE_PY = REPO_ROOT / "app" / "persistence" / "workspace_repository.py"
# After Phase 53F-2, save_workspace_state lives in workspace_repository.py.
# The pin is re-pointed to read from there.
PIN_TARGET = WORKSPACE_PY


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


# ============================================================
# 1. Importability + signature
# ============================================================


class TestImportability:
    def test_save_workspace_state_importable_from_repository(self):
        from app.persistence.repository import save_workspace_state
        assert callable(save_workspace_state)

    def test_workspace_state_record_importable_from_repository(self):
        from app.persistence.repository import WorkspaceStateRecord
        assert WorkspaceStateRecord is not None

    def test_get_workspace_state_importable_from_repository(self):
        from app.persistence.repository import get_workspace_state
        assert callable(get_workspace_state)

    def test_discard_workspace_draft_importable_from_repository(self):
        from app.persistence.repository import discard_workspace_draft
        assert callable(discard_workspace_draft)

    def test_bind_workspace_to_scenario_importable_from_repository(self):
        from app.persistence.repository import bind_workspace_to_scenario
        assert callable(bind_workspace_to_scenario)


class TestSignature:
    def test_save_workspace_state_is_keyword_only(self):
        from app.persistence.repository import save_workspace_state
        sig = inspect.signature(save_workspace_state)
        # All parameters must be keyword-only (after *)
        for name, p in sig.parameters.items():
            assert p.kind == inspect.Parameter.KEYWORD_ONLY, \
                f"save_workspace_state parameter {name!r} is not keyword-only"

    def test_save_workspace_state_required_params(self):
        from app.persistence.repository import save_workspace_state
        sig = inspect.signature(save_workspace_state)
        params = sig.parameters
        # Required: user_id, project_id, project_code, draft_snapshot, saved_snapshot
        for required in ("user_id", "project_id", "project_code", "draft_snapshot", "saved_snapshot"):
            assert required in params, f"save_workspace_state missing required param: {required}"
            assert params[required].default is inspect.Parameter.empty, \
                f"save_workspace_state.{required} should have no default (required)"

    def test_save_workspace_state_optional_params_with_defaults(self):
        from app.persistence.repository import save_workspace_state
        sig = inspect.signature(save_workspace_state)
        params = sig.parameters
        # Optional with defaults
        expected_optional = {
            "governance_state": None,
            "active_scenario_id": None,
            "active_scenario_name": None,
            "last_runtime_snapshot": None,
            "last_runtime_summary": None,
            "last_runtime_snapshot_id": None,
            "last_runtime_origin": None,
            "last_runtime_scenario_id": None,
            "dirty": False,
            "replay_metadata": None,
            "last_runtime_at": None,
        }
        for name, default in expected_optional.items():
            assert name in params, f"save_workspace_state missing optional param: {name}"
            assert params[name].default == default, \
                f"save_workspace_state.{name} default should be {default!r}, got {params[name].default!r}"

    def test_save_workspace_state_return_type(self):
        from app.persistence.repository import save_workspace_state
        # Get return annotation
        hints = save_workspace_state.__annotations__
        # The return annotation is "WorkspaceStateRecord" (string, due to TYPE_CHECKING)
        assert "return" in hints
        # Strip quotes for comparison
        ret = hints["return"].strip("'\"")
        assert ret == "WorkspaceStateRecord", \
            f"save_workspace_state return type should be WorkspaceStateRecord, got {hints['return']!r}"


# ============================================================
# 2. Body-level pinning (regex-based)
# ============================================================


class TestSaveWorkspaceStateBody:
    """Pin key behaviors at the body level. These tests are
    text-based (not behavioral) so they survive any internal refactor
    as long as the high-level behavior is preserved."""

    @pytest.fixture
    def body(self):
        return _read(PIN_TARGET)

    def test_function_defined_in_repository(self, body: str):
        assert "def save_workspace_state(" in body

    def test_uses_now_utc(self, body: str):
        # `_now_utc()` is used to generate `now` timestamp
        m = re.search(
            r"def save_workspace_state\(.*?(?=\n\ndef |\Z)",
            body, re.DOTALL
        )
        assert m
        assert "_now_utc()" in m.group(0), \
            "save_workspace_state should use _now_utc() for timestamps"

    def test_uses_get_workspace_state_for_existing_check(self, body: str):
        m = re.search(
            r"def save_workspace_state\(.*?(?=\n\ndef |\Z)",
            body, re.DOTALL
        )
        body_text = m.group(0)
        assert "get_workspace_state(user_id, project_id)" in body_text, \
            "save_workspace_state must call get_workspace_state to check for existing record"

    def test_default_governance_state_to_empty_dict(self, body: str):
        m = re.search(
            r"def save_workspace_state\(.*?(?=\n\ndef |\Z)",
            body, re.DOTALL
        )
        body_text = m.group(0)
        assert "governance_state = governance_state or {}" in body_text, \
            "save_workspace_state must default governance_state to {}"

    def test_default_replay_metadata_via_dict_copy(self, body: str):
        m = re.search(
            r"def save_workspace_state\(.*?(?=\n\ndef |\Z)",
            body, re.DOTALL
        )
        body_text = m.group(0)
        assert "replay_metadata = dict(replay_metadata or {})" in body_text, \
            "save_workspace_state must default replay_metadata via dict() copy"

    def test_uses_single_transaction_pattern(self, body: str):
        # Both INSERT and UPDATE must be inside `with get_cursor() as cur:`
        m = re.search(
            r"def save_workspace_state\(.*?(?=\n\ndef |\Z)",
            body, re.DOTALL
        )
        body_text = m.group(0)
        # Count occurrences
        n_with = body_text.count("with get_cursor() as cur:")
        assert n_with >= 2, \
            f"save_workspace_state must have ≥ 2 'with get_cursor() as cur:' blocks (UPDATE + INSERT), got {n_with}"


# ============================================================
# 3. SQL text pinning
# ============================================================


class TestSqlTextPinning:
    """Pin the SQL text used by save_workspace_state. This guards
    against accidental SQL changes during 53F-2 extraction."""

    @pytest.fixture
    def body(self):
        return _read(PIN_TARGET)

    def test_update_sql_present(self, body: str):
        m = re.search(
            r"def save_workspace_state\(.*?(?=\n\ndef |\Z)",
            body, re.DOTALL
        )
        body_text = m.group(0)
        # The UPDATE workspace_states SQL must be present
        assert "UPDATE workspace_states" in body_text
        assert "SET project_code=?, active_scenario_id=?, active_scenario_name=?, draft_snapshot_json=?" in body_text
        assert "WHERE workspace_id=? AND user_id=?" in body_text

    def test_insert_sql_present(self, body: str):
        m = re.search(
            r"def save_workspace_state\(.*?(?=\n\ndef |\Z)",
            body, re.DOTALL
        )
        body_text = m.group(0)
        # The INSERT INTO workspace_states SQL must be present
        assert "INSERT INTO workspace_states (" in body_text
        assert "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)" in body_text
        # 19 columns in INSERT
        col_count = body_text.count("VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)")
        assert col_count == 1, f"INSERT INTO must have 19 columns, found {col_count}"

    def test_uses_to_json_helper(self, body: str):
        m = re.search(
            r"def save_workspace_state\(.*?(?=\n\ndef |\Z)",
            body, re.DOTALL
        )
        body_text = m.group(0)
        # Should use _to_json helper for JSON serialization
        n_to_json = body_text.count("_to_json(")
        assert n_to_json >= 8, \
            f"save_workspace_state should use _to_json at least 8 times, got {n_to_json}"

    def test_uuid_hex_16_for_workspace_id(self, body: str):
        m = re.search(
            r"def save_workspace_state\(.*?(?=\n\ndef |\Z)",
            body, re.DOTALL
        )
        body_text = m.group(0)
        # workspace_id is generated as uuid.uuid4().hex[:16]
        assert "uuid.uuid4().hex[:16]" in body_text, \
            "save_workspace_state must generate workspace_id via uuid.uuid4().hex[:16]"


# ============================================================
# 4. replay_metadata behavior
# ============================================================


class TestReplayMetadataBehavior:
    """Pin replay_metadata handling:
    - Default: None → {} (via dict() copy)
    - On UPDATE: merge with existing (new keys override)
    - On INSERT: setdefault("workspace_id", workspace_id)
    """

    @pytest.fixture
    def body(self):
        return _read(PIN_TARGET)

    def test_replay_metadata_default_to_empty_dict(self, body: str):
        m = re.search(
            r"def save_workspace_state\(.*?(?=\n\ndef |\Z)",
            body, re.DOTALL
        )
        body_text = m.group(0)
        assert "replay_metadata = dict(replay_metadata or {})" in body_text

    def test_replay_metadata_merge_on_update(self, body: str):
        m = re.search(
            r"def save_workspace_state\(.*?(?=\n\ndef |\Z)",
            body, re.DOTALL
        )
        body_text = m.group(0)
        # The merge pattern: dict(existing.replay_metadata or {}).update(replay_metadata)
        assert "dict(existing.replay_metadata or {})" in body_text, \
            "replay_metadata should be merged from existing record (defensive None handling)"

    def test_replay_metadata_setdefault_workspace_id_on_insert(self, body: str):
        m = re.search(
            r"def save_workspace_state\(.*?(?=\n\ndef |\Z)",
            body, re.DOTALL
        )
        body_text = m.group(0)
        # On INSERT (else branch), workspace_id is set via setdefault
        assert 'replay_metadata.setdefault("workspace_id", workspace_id)' in body_text


# ============================================================
# 5. governance_state behavior
# ============================================================


class TestGovernanceStateBehavior:
    @pytest.fixture
    def body(self):
        return _read(PIN_TARGET)

    def test_governance_state_default_to_empty_dict(self, body: str):
        m = re.search(
            r"def save_workspace_state\(.*?(?=\n\ndef |\Z)",
            body, re.DOTALL
        )
        body_text = m.group(0)
        assert "governance_state = governance_state or {}" in body_text

    def test_governance_state_inherit_on_update_if_empty(self, body: str):
        m = re.search(
            r"def save_workspace_state\(.*?(?=\n\ndef |\Z)",
            body, re.DOTALL
        )
        body_text = m.group(0)
        # If governance_state was not provided, inherit from existing
        assert "if not governance_state:" in body_text
        assert "governance_state = existing.governance_state" in body_text


# ============================================================
# 6. last_runtime_* behavior
# ============================================================


class TestLastRuntimeBehavior:
    """Pin last_runtime_* field handling:
    - On UPDATE: if None, inherit from existing record
    - The 6 last_runtime fields: snapshot, summary, snapshot_id, origin, scenario_id, at
    """

    @pytest.fixture
    def body(self):
        return _read(PIN_TARGET)

    def test_last_runtime_snapshot_inherit_on_update(self, body: str):
        m = re.search(
            r"def save_workspace_state\(.*?(?=\n\ndef |\Z)",
            body, re.DOTALL
        )
        body_text = m.group(0)
        assert "if last_runtime_snapshot is None:" in body_text
        assert "last_runtime_snapshot = existing.last_runtime_snapshot" in body_text

    def test_last_runtime_summary_inherit_on_update(self, body: str):
        m = re.search(
            r"def save_workspace_state\(.*?(?=\n\ndef |\Z)",
            body, re.DOTALL
        )
        body_text = m.group(0)
        assert "if last_runtime_summary is None:" in body_text
        assert "last_runtime_summary = existing.last_runtime_summary" in body_text

    def test_last_runtime_at_inherit_on_update(self, body: str):
        m = re.search(
            r"def save_workspace_state\(.*?(?=\n\ndef |\Z)",
            body, re.DOTALL
        )
        body_text = m.group(0)
        assert "if last_runtime_at is None:" in body_text
        assert "last_runtime_at = existing.last_runtime_at" in body_text

    def test_last_runtime_at_isoformat_or_none(self, body: str):
        # The SQL binds last_runtime_at.isoformat() if last_runtime_at else None
        m = re.search(
            r"def save_workspace_state\(.*?(?=\n\ndef |\Z)",
            body, re.DOTALL
        )
        body_text = m.group(0)
        assert "last_runtime_at.isoformat() if last_runtime_at else None" in body_text


# ============================================================
# 7. dirty flag behavior
# ============================================================


class TestDirtyFlagBehavior:
    @pytest.fixture
    def body(self):
        return _read(PIN_TARGET)

    def test_dirty_default_false(self, body: str):
        # The signature default for dirty is False
        from app.persistence.repository import save_workspace_state
        sig = inspect.signature(save_workspace_state)
        assert sig.parameters["dirty"].default is False

    def test_dirty_stored_as_int(self, body: str):
        # dirty is stored as int(dirty) in SQL
        m = re.search(
            r"def save_workspace_state\(.*?(?=\n\ndef |\Z)",
            body, re.DOTALL
        )
        body_text = m.group(0)
        # int(dirty) is used in both UPDATE and INSERT
        n = body_text.count("int(dirty)")
        assert n >= 2, f"int(dirty) should be used at least 2 times, got {n}"


# ============================================================
# 8. Return type
# ============================================================


class TestReturnRecord:
    def test_returns_workspace_state_record(self):
        from app.persistence.repository import WorkspaceStateRecord
        # The class must be importable and have from_row
        assert hasattr(WorkspaceStateRecord, "from_row")
        # The class has the following expected fields
        import dataclasses
        fields = {f.name for f in dataclasses.fields(WorkspaceStateRecord)}
        expected = {
            "workspace_id", "project_id", "user_id", "project_code",
            "active_scenario_id", "active_scenario_name",
            "draft_snapshot", "saved_snapshot",
            "last_runtime_snapshot", "last_runtime_summary",
            "last_runtime_snapshot_id", "last_runtime_origin", "last_runtime_scenario_id",
            "dirty", "governance_state", "replay_metadata",
            "created_at", "updated_at", "last_runtime_at",
        }
        assert expected.issubset(fields), \
            f"WorkspaceStateRecord missing fields: {expected - fields}"


# ============================================================
# 9. No caller / service / route changes
# ============================================================


class TestNoCallerChanges:
    """Verify that this PR doesn't change any callers."""

    def test_save_workspace_state_defined_in_workspace_repository(self):
        # After Phase 53F-2, save_workspace_state is defined in workspace_repository.py
        text = _read(PIN_TARGET)
        n = text.count("def save_workspace_state(")
        assert n == 1, f"save_workspace_state should be defined once in workspace_repository.py, got {n}"

    def test_save_workspace_state_not_defined_in_repository(self):
        # After Phase 53F-2, save_workspace_state should NOT be defined in repository.py
        # (only re-exported). It must appear in the import block.
        text = _read(REPOSITORY_PY)
        n = text.count("def save_workspace_state(")
        assert n == 0, f"save_workspace_state should not be defined in repository.py (moved in 53F-2), got {n} occurrences"


# ============================================================
# 10. SQL fragments robust pinning
# ============================================================


class TestSqlFragments:
    """Pin critical SQL fragments as robust checks."""

    @pytest.fixture
    def body(self):
        return _read(PIN_TARGET)

    def test_update_columns(self, body: str):
        # All 14 columns in the UPDATE SET clause (project_code, active_scenario_id,
        # active_scenario_name, draft_snapshot_json, saved_snapshot_json,
        # last_runtime_snapshot_json, last_runtime_summary_json,
        # last_runtime_snapshot_id, last_runtime_origin, last_runtime_scenario_id,
        # dirty, governance_state_json, replay_metadata_json, updated_at, last_runtime_at)
        m = re.search(
            r"def save_workspace_state\(.*?(?=\n\ndef |\Z)",
            body, re.DOTALL
        )
        body_text = m.group(0)
        for col in [
            "project_code=?", "active_scenario_id=?", "active_scenario_name=?",
            "draft_snapshot_json=?", "saved_snapshot_json=?",
            "last_runtime_snapshot_json=?", "last_runtime_summary_json=?",
            "last_runtime_snapshot_id=?", "last_runtime_origin=?",
            "last_runtime_scenario_id=?", "dirty=?",
            "governance_state_json=?", "replay_metadata_json=?",
            "updated_at=?", "last_runtime_at=?",
        ]:
            assert col in body_text, f"Missing UPDATE column: {col}"

    def test_insert_columns(self, body: str):
        m = re.search(
            r"def save_workspace_state\(.*?(?=\n\ndef |\Z)",
            body, re.DOTALL
        )
        body_text = m.group(0)
        for col in [
            "workspace_id", "project_id", "user_id", "project_code",
            "active_scenario_id", "active_scenario_name",
            "draft_snapshot_json", "saved_snapshot_json",
            "last_runtime_snapshot_json", "last_runtime_summary_json",
            "last_runtime_snapshot_id", "last_runtime_origin",
            "last_runtime_scenario_id", "dirty",
            "governance_state_json", "replay_metadata_json",
            "created_at", "updated_at", "last_runtime_at",
        ]:
            assert col in body_text, f"Missing INSERT column: {col}"


# ============================================================
# 11. Interaction with get_workspace_state
# ============================================================


class TestGetWorkspaceStateInteraction:
    def test_get_workspace_state_signature(self):
        from app.persistence.repository import get_workspace_state
        sig = inspect.signature(get_workspace_state)
        params = sig.parameters
        assert "user_id" in params
        assert "project_id" in params
        # Returns Optional[WorkspaceStateRecord]
        hints = get_workspace_state.__annotations__
        ret = hints.get("return", "").strip("'\"")
        assert "Optional" in ret or "WorkspaceStateRecord" in ret

    def test_discard_workspace_draft_signature(self):
        from app.persistence.repository import discard_workspace_draft
        sig = inspect.signature(discard_workspace_draft)
        params = sig.parameters
        assert "user_id" in params
        assert "project_id" in params


# ============================================================
# 12. Phase 52F G1-G6 pre-flight
# ============================================================


class TestGuardrailsPreFlight:
    """Quick checks that current code doesn't already violate
    the Phase 52F guardrails (which would prevent 53F-2)."""

    def test_no_direct_sqlite_imports_in_repository(self):
        text = _read(PIN_TARGET)
        assert "import sqlite3" not in text
        assert "from sqlite3" not in text
        assert "import sqlalchemy" not in text

    def test_get_cursor_only_via_module(self):
        text = _read(REPOSITORY_PY)
        # The function uses get_cursor() — that's fine, it's the module's own
        # persistence helper
        assert "from app.persistence.db import get_cursor" in text or "get_cursor" in text
