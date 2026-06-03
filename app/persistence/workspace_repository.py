"""Workspace state persistence functions extracted from app.persistence.repository.

This module holds Group C (workspace_state) persistence functions extracted
during Phase 53F-2. The functions are re-exported from
app.persistence.repository for backward compatibility.

Function inventory (Group C, from Phase 52A/52C/52E/52G + 53F-1):

- save_workspace_state          (high-risk write, P0 pinned in 53F-1)
- get_workspace_state
- discard_workspace_draft
- bind_workspace_to_scenario

Functions NOT in this module:

- record_workspace_runtime      (stays in repository.py; runtime helper)
- runtime_guard_for_snapshot    (stays in repository.py; runtime guard)

Behavior is preserved exactly as it was in repository.py. The only
differences from the originals are:

1. TYPE_CHECKING forward-reference for WorkspaceStateRecord and ScenarioRecord
   to avoid circular imports. The class objects themselves are still
   resolved at runtime via lazy import inside function bodies where needed.
2. Module-level import of helper functions (_now_utc, _to_json) is local
   to this module.

Public surface preserved:

- app.persistence.repository.save_workspace_state     ✓
- app.persistence.repository.get_workspace_state      ✓
- app.persistence.repository.discard_workspace_draft  ✓
- app.persistence.repository.bind_workspace_to_scenario ✓
- app.persistence.repository.WorkspaceStateRecord     (re-exported)
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional

from app.persistence.db import get_cursor
from app.persistence._helpers import _now_utc, _to_json

if TYPE_CHECKING:
    from app.persistence.records import ScenarioRecord, WorkspaceStateRecord


# -----------------------------------------------------------------
# get_workspace_state
# -----------------------------------------------------------------

def get_workspace_state(user_id: str, project_id: str) -> "Optional[WorkspaceStateRecord]":
    from app.persistence.records import WorkspaceStateRecord
    with get_cursor() as cur:
        cur.execute(
            "SELECT * FROM workspace_states WHERE user_id=? AND project_id=?",
            (user_id, project_id),
        )
        row = cur.fetchone()
    return WorkspaceStateRecord.from_row(row) if row else None


# -----------------------------------------------------------------
# save_workspace_state
# -----------------------------------------------------------------

def save_workspace_state(
    *,
    user_id: str,
    project_id: str,
    project_code: str,
    draft_snapshot: dict[str, Any],
    saved_snapshot: dict[str, Any],
    governance_state: Optional[dict[str, Any]] = None,
    active_scenario_id: Optional[str] = None,
    active_scenario_name: Optional[str] = None,
    last_runtime_snapshot: Optional[dict[str, Any]] = None,
    last_runtime_summary: Optional[dict[str, Any]] = None,
    last_runtime_snapshot_id: Optional[str] = None,
    last_runtime_origin: Optional[str] = None,
    last_runtime_scenario_id: Optional[str] = None,
    dirty: bool = False,
    replay_metadata: Optional[dict[str, Any]] = None,
    last_runtime_at: Optional[datetime] = None,
) -> "WorkspaceStateRecord":
    from app.persistence.records import WorkspaceStateRecord
    now = _now_utc()
    governance_state = governance_state or {}
    replay_metadata = dict(replay_metadata or {})
    existing = get_workspace_state(user_id, project_id)
    if existing is not None:
        workspace_id = existing.workspace_id
        created_at = existing.created_at
        if last_runtime_snapshot is None:
            last_runtime_snapshot = existing.last_runtime_snapshot
        if last_runtime_summary is None:
            last_runtime_summary = existing.last_runtime_summary
        if last_runtime_snapshot_id is None:
            last_runtime_snapshot_id = existing.last_runtime_snapshot_id
        if last_runtime_origin is None:
            last_runtime_origin = existing.last_runtime_origin
        if last_runtime_scenario_id is None:
            last_runtime_scenario_id = existing.last_runtime_scenario_id
        if last_runtime_at is None:
            last_runtime_at = existing.last_runtime_at
        if not governance_state:
            governance_state = existing.governance_state
        merged_replay_metadata = dict(existing.replay_metadata or {})
        merged_replay_metadata.update(replay_metadata)
        replay_metadata = merged_replay_metadata
        with get_cursor() as cur:
            cur.execute(
                """
                UPDATE workspace_states
                SET project_code=?, active_scenario_id=?, active_scenario_name=?, draft_snapshot_json=?,
                    saved_snapshot_json=?, last_runtime_snapshot_json=?, last_runtime_summary_json=?,
                    last_runtime_snapshot_id=?, last_runtime_origin=?, last_runtime_scenario_id=?,
                    dirty=?, governance_state_json=?, replay_metadata_json=?, updated_at=?, last_runtime_at=?
                WHERE workspace_id=? AND user_id=?
                """,
                (
                    project_code,
                    active_scenario_id,
                    active_scenario_name,
                    _to_json(draft_snapshot or {}),
                    _to_json(saved_snapshot or {}),
                    _to_json(last_runtime_snapshot or {}),
                    _to_json(last_runtime_summary or {}),
                    last_runtime_snapshot_id,
                    last_runtime_origin,
                    last_runtime_scenario_id,
                    int(dirty),
                    _to_json(governance_state),
                    _to_json(replay_metadata),
                    now.isoformat(),
                    last_runtime_at.isoformat() if last_runtime_at else None,
                    workspace_id,
                    user_id,
                ),
            )
    else:
        workspace_id = uuid.uuid4().hex[:16]
        created_at = now
        replay_metadata.setdefault("workspace_id", workspace_id)
        with get_cursor() as cur:
            cur.execute(
                """
                INSERT INTO workspace_states (
                    workspace_id, project_id, user_id, project_code, active_scenario_id, active_scenario_name,
                    draft_snapshot_json, saved_snapshot_json, last_runtime_snapshot_json, last_runtime_summary_json,
                    last_runtime_snapshot_id, last_runtime_origin, last_runtime_scenario_id, dirty,
                    governance_state_json, replay_metadata_json, created_at, updated_at, last_runtime_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    workspace_id,
                    project_id,
                    user_id,
                    project_code,
                    active_scenario_id,
                    active_scenario_name,
                    _to_json(draft_snapshot or {}),
                    _to_json(saved_snapshot or {}),
                    _to_json(last_runtime_snapshot or {}),
                    _to_json(last_runtime_summary or {}),
                    last_runtime_snapshot_id,
                    last_runtime_origin,
                    last_runtime_scenario_id,
                    int(dirty),
                    _to_json(governance_state),
                    _to_json(replay_metadata),
                    created_at.isoformat(),
                    now.isoformat(),
                    last_runtime_at.isoformat() if last_runtime_at else None,
                ),
            )

    return WorkspaceStateRecord(
        workspace_id=workspace_id,
        project_id=project_id,
        user_id=user_id,
        project_code=project_code,
        active_scenario_id=active_scenario_id,
        active_scenario_name=active_scenario_name,
        draft_snapshot=draft_snapshot or {},
        saved_snapshot=saved_snapshot or {},
        last_runtime_snapshot=last_runtime_snapshot or {},
        last_runtime_summary=last_runtime_summary or {},
        last_runtime_snapshot_id=last_runtime_snapshot_id,
        last_runtime_origin=last_runtime_origin,
        last_runtime_scenario_id=last_runtime_scenario_id,
        dirty=dirty,
        governance_state=governance_state,
        replay_metadata=replay_metadata,
        created_at=created_at,
        updated_at=now,
        last_runtime_at=last_runtime_at,
    )


# -----------------------------------------------------------------
# bind_workspace_to_scenario
# -----------------------------------------------------------------

def bind_workspace_to_scenario(
    user_id: str,
    project_id: str,
    project_code: str,
    record: "ScenarioRecord",
    governance_state: Optional[dict[str, Any]] = None,
    replay_metadata: Optional[dict[str, Any]] = None,
) -> "WorkspaceStateRecord":
    return save_workspace_state(
        user_id=user_id,
        project_id=project_id,
        project_code=project_code,
        active_scenario_id=record.scenario_id,
        active_scenario_name=record.scenario_name,
        draft_snapshot=record.snapshot,
        saved_snapshot=record.snapshot,
        dirty=False,
        governance_state=governance_state or record.governance_state,
        replay_metadata=replay_metadata,
    )


# -----------------------------------------------------------------
# discard_workspace_draft
# -----------------------------------------------------------------

def discard_workspace_draft(user_id: str, project_id: str) -> "Optional[WorkspaceStateRecord]":
    record = get_workspace_state(user_id, project_id)
    if record is None:
        return None
    return save_workspace_state(
        user_id=user_id,
        project_id=project_id,
        project_code=record.project_code,
        active_scenario_id=record.active_scenario_id,
        active_scenario_name=record.active_scenario_name,
        draft_snapshot=record.saved_snapshot,
        saved_snapshot=record.saved_snapshot,
        last_runtime_snapshot=record.last_runtime_snapshot,
        last_runtime_summary=record.last_runtime_summary,
        last_runtime_snapshot_id=record.last_runtime_snapshot_id,
        last_runtime_origin=record.last_runtime_origin,
        last_runtime_scenario_id=record.last_runtime_scenario_id,
        dirty=False,
        governance_state=record.governance_state,
        replay_metadata=record.replay_metadata,
        last_runtime_at=record.last_runtime_at,
    )
