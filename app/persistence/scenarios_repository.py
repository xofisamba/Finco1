"""Scenario persistence functions extracted from app.persistence.repository.

This module holds Group B scenario persistence functions extracted
during Phase 53G-2 (reads) and Phase 53G-3 (low-risk actions). The
functions are re-exported from app.persistence.repository for
backward compatibility.

Function inventory (Group B-reads, Phase 53G-2):

- get_scenario
- list_scenarios
- resolve_scenario_snapshot
- resolve_active_scenario_runtime_snapshot

Function inventory (Group B low-risk actions, Phase 53G-3):

- rename_scenario
- archive_scenario
- select_scenario
- duplicate_scenario
- promote_scenario_to_base_case

Functions NOT in this module (stay in repository.py until their own
extraction PR):

- save_scenario                         (Group B high-risk write, 53G-4)
- add_scenario                          (Group B high-risk write, 53G-5)
- update_scenario_overrides             (Group B high-risk write, 53G-6)
- get_or_create_base_case_scenario      (Group B high-risk write, 53G-7)
- seed_scenarios_if_needed              (NOT Group B, stays in repository.py)
- get_scenario_provenance               (NOT Group B, stays in repository.py)
- get_base_case_scenario                (NOT Group B, stays in repository.py)
- record_workspace_runtime              (NOT Group B, stays in repository.py)
- runtime_guard_for_snapshot            (NOT Group B, stays in repository.py)

Behavior is preserved exactly as it was in repository.py. The only
differences from the originals are:

1. TYPE_CHECKING forward-reference for ScenarioRecord to avoid circular
   imports. The class object is resolved at runtime via lazy import
   inside function bodies where needed.

Public surface preserved:

- app.persistence.repository.get_scenario                 ✓
- app.persistence.repository.list_scenarios               ✓
- app.persistence.repository.resolve_scenario_snapshot     ✓
- app.persistence.repository.resolve_active_scenario_runtime_snapshot ✓
- app.persistence.repository.rename_scenario              ✓
- app.persistence.repository.archive_scenario             ✓
- app.persistence.repository.select_scenario              ✓
- app.persistence.repository.duplicate_scenario           ✓
- app.persistence.repository.promote_scenario_to_base_case ✓
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

from app.persistence._helpers import _now_utc, SCENARIO_INPUT_FIELDS
from app.persistence.db import get_cursor

if TYPE_CHECKING:
    from app.persistence.repository import ScenarioRecord


# ============================================================
# Group B-reads (Phase 53G-2)
# ============================================================


def resolve_scenario_snapshot(
    base_input_set: dict[str, Any],
    overrides: dict[str, Any],
) -> dict[str, Any]:
    """Resolve effective snapshot: base + overrides.

    Missing override keys inherit from base_input_set.
    Unknown keys in overrides are silently dropped.
    Empty overrides returns a copy of base_input_set.
    """
    base = dict(base_input_set)
    for key, value in overrides.items():
        if key in SCENARIO_INPUT_FIELDS:
            base[key] = value
    return base


def get_scenario(scenario_id: str, user_id: str) -> "Optional[ScenarioRecord]":
    from app.persistence.repository import ScenarioRecord
    with get_cursor() as cur:
        cur.execute("SELECT * FROM scenarios WHERE scenario_id=? AND user_id=?", (scenario_id, user_id))
        row = cur.fetchone()
    return ScenarioRecord.from_row(row) if row else None


def list_scenarios(
    user_id: str,
    project_id: Optional[str] = None,
    include_archived: bool = False,
    limit: int = 25,
) -> "list[ScenarioRecord]":
    from app.persistence.repository import ScenarioRecord
    query = "SELECT * FROM scenarios WHERE user_id=?"
    params: list[Any] = [user_id]
    if project_id:
        query += " AND project_id=?"
        params.append(project_id)
    if not include_archived:
        query += " AND archived=0"
    query += " ORDER BY updated_at DESC LIMIT ?"
    params.append(limit)

    with get_cursor() as cur:
        cur.execute(query, tuple(params))
        return [ScenarioRecord.from_row(row) for row in cur.fetchall()]


def resolve_active_scenario_runtime_snapshot(
    user_id: str,
    project_id: str,
    active_scenario_id: Optional[str],
) -> tuple[Optional["ScenarioRecord"], Optional[dict[str, Any]], Optional[str]]:
    """Resolve the clean saved runtime snapshot for the active scenario.

    Returns a tuple of:
      (scenario_record, resolved_snapshot, warning_message)

    Rules:
    - Base Case => full base_input_set / snapshot
    - Non-base => resolve_scenario_snapshot(base_case.base_input_set, overrides_json)
    - Missing / invalid scenario => (None, None, warning)
    """
    from app.persistence.repository import get_base_case_scenario

    if not active_scenario_id:
        return None, None, None

    scenario_record = get_scenario(active_scenario_id, user_id)
    if scenario_record is None or scenario_record.archived or scenario_record.project_id != project_id:
        return None, None, (
            "Selected saved scenario was unavailable, so runtime fell back to the last clean saved boundary."
        )

    if scenario_record.is_base_case:
        snapshot = dict(scenario_record.base_input_set or scenario_record.snapshot or {})
        return scenario_record, snapshot, None

    base_case = None
    if scenario_record.parent_scenario_id:
        parent = get_scenario(scenario_record.parent_scenario_id, user_id)
        if parent is not None and parent.project_id == project_id and parent.is_base_case and not parent.archived:
            base_case = parent
    if base_case is None:
        base_case = get_base_case_scenario(user_id, project_id)

    base_input_set = {}
    if base_case is not None:
        base_input_set = dict(base_case.base_input_set or base_case.snapshot or {})
    elif scenario_record.base_input_set:
        base_input_set = dict(scenario_record.base_input_set)

    snapshot = resolve_scenario_snapshot(base_input_set, scenario_record.overrides or {})
    warning = None
    if base_case is None:
        warning = (
            "Selected scenario did not have a resolvable Base Case record, so runtime used the scenario's saved base input set."
        )
    return scenario_record, snapshot, warning


# ============================================================
# Group B low-risk actions (Phase 53G-3)
# ============================================================


def rename_scenario(user_id: str, scenario_id: str, new_name: str) -> bool:
    with get_cursor() as cur:
        cur.execute(
            "UPDATE scenarios SET scenario_name=?, updated_at=? WHERE scenario_id=? AND user_id=?",
            (new_name, _now_utc().isoformat(), scenario_id, user_id),
        )
        return cur.rowcount > 0


def archive_scenario(user_id: str, scenario_id: str) -> bool:
    with get_cursor() as cur:
        cur.execute(
            "UPDATE scenarios SET archived=1, updated_at=? WHERE scenario_id=? AND user_id=?",
            (_now_utc().isoformat(), scenario_id, user_id),
        )
        return cur.rowcount > 0


def promote_scenario_to_base_case(user_id: str, scenario_id: str) -> "Optional[ScenarioRecord]":
    """Promote an existing scenario to be the project's Base Case.

    Clears is_base_case flag from all other scenarios for this project first,
    then sets it on the target scenario.
    Idempotent: safe to call on a scenario that is already the base case.
    """
    with get_cursor() as cur:
        # Clear any existing base case — scoped via subquery so it only clears
        # one of the user's scenarios (not a different user's scenario accidentally)
        cur.execute(
            """
            UPDATE scenarios
            SET is_base_case=0, updated_at=?
            WHERE scenario_id=(
                SELECT scenario_id FROM scenarios
                WHERE user_id=? AND is_base_case=1
                LIMIT 1
            )
            """,
            (_now_utc().isoformat(), user_id),
        )
        # Promote the target scenario
        cur.execute(
            """
            UPDATE scenarios
            SET is_base_case=1, updated_at=?
            WHERE scenario_id=? AND user_id=?
            """,
            (_now_utc().isoformat(), scenario_id, user_id),
        )
        if cur.rowcount == 0:
            return None
    return get_scenario(scenario_id, user_id)


def duplicate_scenario(user_id: str, scenario_id: str, new_name: Optional[str] = None) -> "Optional[ScenarioRecord]":
    from app.persistence.repository import save_scenario
    record = get_scenario(scenario_id, user_id)
    if record is None:
        return None
    copy_name = new_name or f"{record.scenario_name} Copy"
    return save_scenario(
        user_id=user_id,
        project_id=record.project_id,
        scenario_name=copy_name,
        project_code=record.project_code,
        source_project_template=record.source_project_template,
        snapshot=record.snapshot,
        governance_state=record.governance_state,
        last_run_summary=record.last_run_summary,
        copied_from_scenario_id=record.scenario_id,
        replay_metadata=record.replay_metadata,
    )


def select_scenario(
    user_id: str,
    project_id: str,
    scenario_id: str,
) -> bool:
    """Set the active scenario for the given project in workspace_state."""
    from app.persistence.repository import get_workspace_state, save_workspace_state
    record = get_scenario(scenario_id, user_id)
    if record is None:
        return False
    ws = get_workspace_state(user_id, project_id)
    if ws is None:
        return False
    save_workspace_state(
        user_id=user_id,
        project_id=project_id,
        project_code=ws.project_code,
        active_scenario_id=scenario_id,
        active_scenario_name=record.scenario_name,
        draft_snapshot=ws.draft_snapshot,
        saved_snapshot=ws.saved_snapshot if ws.saved_snapshot else ws.draft_snapshot,
        governance_state=ws.governance_state,
        replay_metadata={"action": "select_scenario", "scenario_id": scenario_id},
    )
    return True
