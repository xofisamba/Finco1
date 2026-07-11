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

import hashlib
import json
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional

from app.persistence.db import get_cursor
from app.persistence._helpers import _now_utc, _to_json


def _draft_content_hash(draft_snapshot: dict) -> str:
    """Stable SHA-256 over the serialised draft snapshot.

    Fallback hash for rows that pre-date the draft_content_hash column.
    The V2 edit pipeline stores pis.content_hash instead (passed explicitly
    via the draft_content_hash parameter of save_workspace_state / v2_atomic_draft_update).
    """
    raw = json.dumps(draft_snapshot or {}, sort_keys=True, ensure_ascii=True)
    return hashlib.sha256(raw.encode()).hexdigest()

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
    # Workbook V2 PR 3: full schedule payloads — DB is now authoritative.
    last_financial_statements: Optional[dict[str, Any]] = None,
    last_debt_schedule: Optional[dict[str, Any]] = None,
    last_tax_schedule: Optional[dict[str, Any]] = None,
    last_distribution_schedule: Optional[dict[str, Any]] = None,
    last_sponsor_schedule: Optional[dict[str, Any]] = None,
    dirty: bool = False,
    replay_metadata: Optional[dict[str, Any]] = None,
    last_runtime_at: Optional[datetime] = None,
    # Workbook V2 PR 7: caller-supplied content hash for atomic CAS.
    # Pass pis.content_hash here when saving from the V2 edit pipeline.
    # Falls back to a raw JSON hash if not provided (for legacy callers).
    v2_draft_content_hash: Optional[str] = None,
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
        if last_financial_statements is None:
            last_financial_statements = existing.last_financial_statements
        if last_debt_schedule is None:
            last_debt_schedule = existing.last_debt_schedule
        if last_tax_schedule is None:
            last_tax_schedule = existing.last_tax_schedule
        if last_distribution_schedule is None:
            last_distribution_schedule = existing.last_distribution_schedule
        if last_sponsor_schedule is None:
            last_sponsor_schedule = existing.last_sponsor_schedule
        if not governance_state:
            governance_state = existing.governance_state
        merged_replay_metadata = dict(existing.replay_metadata or {})
        merged_replay_metadata.update(replay_metadata)
        replay_metadata = merged_replay_metadata
        _dch = v2_draft_content_hash or _draft_content_hash(draft_snapshot or {})
        with get_cursor() as cur:
            cur.execute(
                """
                UPDATE workspace_states
                SET project_code=?, active_scenario_id=?, active_scenario_name=?, draft_snapshot_json=?,
                    saved_snapshot_json=?, last_runtime_snapshot_json=?, last_runtime_summary_json=?,
                    last_runtime_snapshot_id=?, last_runtime_origin=?, last_runtime_scenario_id=?,
                    last_financial_statements_json=?, last_debt_schedule_json=?,
                    last_tax_schedule_json=?, last_distribution_schedule_json=?,
                    last_sponsor_schedule_json=?, draft_content_hash=?,
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
                    _to_json(last_financial_statements or {}),
                    _to_json(last_debt_schedule or {}),
                    _to_json(last_tax_schedule or {}),
                    _to_json(last_distribution_schedule or {}),
                    _to_json(last_sponsor_schedule or {}),
                    _dch,
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
                    last_runtime_snapshot_id, last_runtime_origin, last_runtime_scenario_id,
                    last_financial_statements_json, last_debt_schedule_json, last_tax_schedule_json,
                    last_distribution_schedule_json, last_sponsor_schedule_json, draft_content_hash,
                    dirty, governance_state_json, replay_metadata_json, created_at, updated_at, last_runtime_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    _to_json(last_financial_statements or {}),
                    _to_json(last_debt_schedule or {}),
                    _to_json(last_tax_schedule or {}),
                    _to_json(last_distribution_schedule or {}),
                    _to_json(last_sponsor_schedule or {}),
                    v2_draft_content_hash or _draft_content_hash(draft_snapshot or {}),
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
        last_financial_statements=last_financial_statements or {},
        last_debt_schedule=last_debt_schedule or {},
        last_tax_schedule=last_tax_schedule or {},
        last_distribution_schedule=last_distribution_schedule or {},
        last_sponsor_schedule=last_sponsor_schedule or {},
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
        last_financial_statements=record.last_financial_statements,
        last_debt_schedule=record.last_debt_schedule,
        last_tax_schedule=record.last_tax_schedule,
        last_distribution_schedule=record.last_distribution_schedule,
        last_sponsor_schedule=record.last_sponsor_schedule,
        dirty=False,
        governance_state=record.governance_state,
        replay_metadata=record.replay_metadata,
        last_runtime_at=record.last_runtime_at,
    )


# -----------------------------------------------------------------
# v2_atomic_draft_update
# -----------------------------------------------------------------

def v2_atomic_draft_update(
    *,
    user_id: str,
    project_id: str,
    expected_content_hash: str,
    new_draft_snapshot: dict,
    new_content_hash: str,
) -> "Optional[WorkspaceStateRecord]":
    """Atomic compare-and-swap for Workbook V2 single-field draft edits.

    Opens a single SQLite connection, acquires an exclusive write lock via
    ``BEGIN EXCLUSIVE``, reads the current ``draft_content_hash``, and only
    updates ``draft_snapshot_json`` if it still matches ``expected_content_hash``.

    Returns the updated WorkspaceStateRecord on success, or None if the
    expected hash does not match the current persisted state (stale read).
    The caller must raise StaleContentError on None.

    Guarantees
    ----------
    - Two concurrent callers with the same expected_content_hash will serialize:
      whichever acquires the exclusive lock first wins; the second sees a
      mismatched hash and receives None.
    - saved_snapshot and all runtime fields are not touched.
    - dirty is always set to True on success.
    """
    from app.persistence.db import get_connection
    from app.persistence.records import WorkspaceStateRecord

    now = _now_utc()
    conn = get_connection()
    try:
        # Exclusive lock: prevents any concurrent read or write until COMMIT/ROLLBACK.
        conn.execute("BEGIN EXCLUSIVE")
        cur = conn.cursor()

        cur.execute(
            "SELECT * FROM workspace_states WHERE user_id=? AND project_id=?",
            (user_id, project_id),
        )
        row = cur.fetchone()
        if row is None:
            conn.execute("ROLLBACK")
            return None

        # Compare expected hash against persisted draft_content_hash.
        #
        # Two cases where we treat the write as unconditional (first V2 edit):
        #   1. draft_content_hash IS NULL — row predates the column.
        #   2. draft_content_hash is a raw-JSON fallback hash (stored by
        #      save_workspace_state callers that predate the V2 pipeline, i.e.
        #      project creation and legacy draft saves).  We detect this by
        #      recomputing _draft_content_hash over the current snapshot_json and
        #      comparing; if they match the stored value is a raw hash, not a
        #      pis.content_hash, so no real concurrency conflict exists yet.
        #
        # After a successful V2 write the stored hash is always pis.content_hash,
        # so subsequent edits use proper CAS.
        keys = row.keys()
        persisted_hash = row["draft_content_hash"] if "draft_content_hash" in keys else None

        if persisted_hash is not None and persisted_hash != expected_content_hash:
            import json as _json
            raw = _json.loads(row["draft_snapshot_json"] or "{}")
            raw_json_hash = _draft_content_hash(raw)
            if persisted_hash != raw_json_hash:
                # Genuine stale conflict: stored hash is a pis.content_hash that
                # no longer matches what the browser saw.
                conn.execute("ROLLBACK")
                return None  # stale — caller raises StaleContentError
            # persisted_hash == raw_json_hash: legacy first-write, proceed.

        cur.execute(
            """
            UPDATE workspace_states
            SET draft_snapshot_json=?, draft_content_hash=?, dirty=1, updated_at=?
            WHERE workspace_id=? AND user_id=?
            """,
            (
                _to_json(new_draft_snapshot),
                new_content_hash,
                now.isoformat(),
                row["workspace_id"],
                user_id,
            ),
        )
        conn.execute("COMMIT")

        cur.execute(
            "SELECT * FROM workspace_states WHERE user_id=? AND project_id=?",
            (user_id, project_id),
        )
        updated_row = cur.fetchone()
        return WorkspaceStateRecord.from_row(updated_row) if updated_row else None
    except Exception:
        try:
            conn.execute("ROLLBACK")
        except Exception:
            pass
        raise
    finally:
        cur.close()
        conn.close()
