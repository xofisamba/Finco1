"""Repository helpers for lightweight project, scenario, run, and export persistence.

This module is the authoritative persistence repository for the web app.
It persists snapshots and review metadata, but never computes or overrides
financial model outputs.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

from app.persistence.db import get_cursor


# Phase 53A: Group F helpers re-exported from app.persistence._helpers for
# backward compatibility. The original implementations live in
# app/persistence/_helpers.py.
from app.persistence._helpers import (
    _now_utc,
    _to_json,
    _from_json,
    _from_iso,
    SCENARIO_INPUT_FIELDS,
    _safe_number,
    _metric_value,
    snapshots_equal,
    _strip_empty_fields,
    _get_least_created_scenario_for_project,
)


# Phase 53B: Group D (runs) re-exported from app.persistence.runs_repository
# for backward compatibility. The original implementations live in
# app/persistence/runs_repository.py.
from app.persistence.runs_repository import (
    RunRecord,
    save_run,
    get_run,
    list_runs,
    delete_run,
    count_runs,
)


# Phase 53C: Group E (exports+audit) re-exported from
# app.persistence.exports_repository for backward compatibility.
# The original implementations live in app/persistence/exports_repository.py.
from app.persistence.exports_repository import (
    ScenarioExportRecord,
    record_export,
    list_exports,
    get_scenario_history,
    compare_scenarios,
    build_export_lineage,
    base_vs_active_compare,
    _scenario_runtime_dict,
    _build_compare_metrics,
    _delta_sign_class,
    _format_db_timestamp,
)


# Phase 53D: Group A-reads (project reads) re-exported from
# app.persistence.projects_repository for backward compatibility.
# The original implementations live in app/persistence/projects_repository.py.
# Project writes (save_project, create_project_record, update_project_record,
# seed_baseline_projects_if_needed, etc.) remain in repository.py for now
# and will move in Group A-2 with the P0 pin for save_project.
from app.persistence.projects_repository import (
    get_project,
    get_project_by_code,
    list_projects,
    list_baseline_records,
    get_project_record,
    list_project_records,
)


# Phase 53E-2: Group A-2 (project writes) re-exported from
# app.persistence.projects_repository for backward compatibility.
# The original implementations live in app/persistence/projects_repository.py.
from app.persistence.projects_repository import (
    save_project,
    create_project_record,
    update_project_record,
    seed_baseline_projects_if_needed,
    _compute_baseline_snapshot,
    _build_default_snapshot,
    _fill_missing_defaults,
)


# Phase 53F-2: Group C (workspace_state) re-exported from
# app.persistence.workspace_repository for backward compatibility.
# The original implementations live in app/persistence/workspace_repository.py.
from app.persistence.workspace_repository import (
    save_workspace_state,
    get_workspace_state,
    discard_workspace_draft,
    bind_workspace_to_scenario,
)





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


def get_or_create_base_case_scenario(
    user_id: str,
    project_id: str,
    project_code: str,
    project_name: str,
    project_type: str,
    source_project_template: str,
    base_input_set: dict[str, Any],
    governance_state: dict[str, Any],
    replay_metadata: Optional[dict[str, Any]] = None,
) -> "ScenarioRecord":
    """Return the existing Base Case scenario for a project, or create one."""
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT * FROM scenarios
            WHERE user_id=? AND project_id=? AND is_base_case=1 AND archived=0
            LIMIT 1
            """,
            (user_id, project_id),
        )
        row = cur.fetchone()

    if row:
        return ScenarioRecord.from_row(row)

    scenario_id = uuid.uuid4().hex[:16]
    now = _now_utc()
    governance_state = dict(governance_state or {})
    rm = dict(replay_metadata or {})
    rm.setdefault("project_id", project_id)
    rm.setdefault("scenario_id", scenario_id)
    rm["is_base_case"] = True

    with get_cursor() as cur:
        cur.execute(
            """
            INSERT INTO scenarios (
                scenario_id, project_id, user_id, scenario_name, project_code,
                source_project_template, copied_from_scenario_id, archived,
                is_base_case, parent_scenario_id,
                base_input_set_json, overrides_json, schema_version,
                snapshot_json, governance_state_json, last_run_summary_json,
                replay_metadata_json, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, NULL, 0, 1, NULL, ?, ?, '1.0', ?, ?, ?, ?, ?, ?)
            """,
            (
                scenario_id,
                project_id,
                user_id,
                project_name or "Base Case",
                project_code,
                source_project_template,
                _to_json(base_input_set),
                _to_json({}),  # overrides_json
                _to_json(governance_state),
                _to_json(base_input_set),  # snapshot_json = full input (effective = base + empty overrides)
                _to_json({}),  # last_run_summary_json
                _to_json(rm),
                now.isoformat(),
                now.isoformat(),
            ),
        )

    return ScenarioRecord(
        scenario_id=scenario_id,
        project_id=project_id,
        user_id=user_id,
        scenario_name=project_name or "Base Case",
        project_code=project_code,
        source_project_template=source_project_template,
        copied_from_scenario_id=None,
        archived=False,
        is_base_case=True,
        parent_scenario_id=None,
        base_input_set=base_input_set,
        overrides={},
        schema_version="1.0",
        snapshot=base_input_set,
        governance_state=governance_state,
        last_run_summary={},
        replay_metadata=rm,
        created_at=now,
        updated_at=now,
    )


def seed_scenarios_if_needed(
    user_id: str,
    project_id: str,
    project_code: str,
    project_type: str,
    source_project_template: str,
    baseline_snapshot: dict[str, Any],
    governance_state: dict[str, Any],
    template_origin: str,
) -> "ScenarioRecord":
    """Seed (or return existing) Base Case scenario for a project."""
    rm = {
        "baseline_source": True,
        "template_origin": template_origin,
    }
    return get_or_create_base_case_scenario(
        user_id=user_id,
        project_id=project_id,
        project_code=project_code,
        project_name=baseline_snapshot.get("project_name", project_code),
        project_type=project_type,
        source_project_template=source_project_template,
        base_input_set=baseline_snapshot,
        governance_state=governance_state,
        replay_metadata=rm,
    )


def get_scenario_provenance(
    scenario_record: "ScenarioRecord",
    project_record: Optional["ProjectRecord"],
    template_origin: str,
) -> dict[str, Any]:
    """Build scenario provenance dict for export replay_metadata."""
    return {
        "project_id": scenario_record.project_id,
        "project_name": (
            project_record.project_name if project_record else scenario_record.project_code
        ),
        "scenario_id": scenario_record.scenario_id,
        "scenario_name": scenario_record.scenario_name,
        "is_base_case": scenario_record.is_base_case,
        "parent_scenario_id": scenario_record.parent_scenario_id,
        "override_field_list": (
            sorted(scenario_record.overrides.keys())
            if not scenario_record.is_base_case
            else []
        ),
        "baseline_source": (
            (project_record.project_origin == "saved_baseline")
            if project_record
            else False
        ),
        "template_origin": template_origin,
    }


def get_base_case_scenario(user_id: str, project_id: str) -> Optional["ScenarioRecord"]:
    """Return the non-archived Base Case scenario for a project, if present."""
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT * FROM scenarios
            WHERE user_id=? AND project_id=? AND is_base_case=1 AND archived=0
            LIMIT 1
            """,
            (user_id, project_id),
        )
        row = cur.fetchone()
    return ScenarioRecord.from_row(row) if row else None


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


@dataclass(slots=True)
class ProjectRecord:
    project_id: str
    user_id: str
    project_code: str
    project_name: str
    project_type: Optional[str]
    project_origin: str
    source_project_template: str
    template_source: Optional[str]
    baseline_snapshot: dict[str, Any]
    archived: bool
    is_readonly: bool
    governance_state: dict[str, Any]
    last_run_summary: dict[str, Any]
    replay_metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_row(cls, row) -> "ProjectRecord":
        return cls(
            project_id=row["project_id"],
            user_id=row["user_id"],
            project_code=row["project_code"],
            project_name=row["project_name"],
            project_type=row["project_type"],
            project_origin=row["project_origin"] or "factory_template",
            source_project_template=row["source_project_template"],
            template_source=row["template_source"],
            baseline_snapshot=_from_json(row["baseline_snapshot_json"], {}),
            archived=bool(row["archived"]),
            is_readonly=bool(row["is_readonly"]) if "is_readonly" in row.keys() else False,
            governance_state=_from_json(row["governance_state_json"], {}),
            last_run_summary=_from_json(row["last_run_summary_json"], {}),
            replay_metadata=_from_json(row["replay_metadata_json"], {}),
            created_at=_from_iso(row["created_at"]),
            updated_at=_from_iso(row["updated_at"]),
        )


class ScenarioRecord:
    __slots__ = (
        "scenario_id", "project_id", "user_id", "scenario_name", "project_code",
        "source_project_template", "copied_from_scenario_id", "archived",
        "is_base_case", "parent_scenario_id", "base_input_set", "overrides",
        "schema_version", "snapshot", "governance_state", "last_run_summary",
        "replay_metadata", "created_at", "updated_at",
    )

    def __init__(
        self,
        scenario_id: str,
        project_id: str,
        user_id: str,
        scenario_name: str,
        project_code: str,
        source_project_template: str,
        copied_from_scenario_id: Optional[str],
        archived: bool,
        is_base_case: bool = False,
        parent_scenario_id: Optional[str] = None,
        base_input_set: Optional[dict] = None,
        overrides: Optional[dict] = None,
        schema_version: str = "1.0",
        snapshot: Optional[dict] = None,
        governance_state: Optional[dict] = None,
        last_run_summary: Optional[dict] = None,
        replay_metadata: Optional[dict] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ):
        self.scenario_id = scenario_id
        self.project_id = project_id
        self.user_id = user_id
        self.scenario_name = scenario_name
        self.project_code = project_code
        self.source_project_template = source_project_template
        self.copied_from_scenario_id = copied_from_scenario_id
        self.archived = archived
        self.is_base_case = is_base_case
        self.parent_scenario_id = parent_scenario_id
        self.base_input_set = base_input_set or {}
        self.overrides = overrides or {}
        self.schema_version = schema_version
        self.snapshot = snapshot or {}
        self.governance_state = governance_state or {}
        self.last_run_summary = last_run_summary or {}
        self.replay_metadata = replay_metadata or {}
        self.created_at = created_at
        self.updated_at = updated_at

    @classmethod
    def from_row(cls, row) -> "ScenarioRecord":
        return cls(
            scenario_id=row["scenario_id"],
            project_id=row["project_id"],
            user_id=row["user_id"],
            scenario_name=row["scenario_name"],
            project_code=row["project_code"],
            source_project_template=row["source_project_template"],
            copied_from_scenario_id=row["copied_from_scenario_id"],
            archived=bool(row["archived"]),
            is_base_case=bool(row["is_base_case"]) if "is_base_case" in row.keys() else False,
            parent_scenario_id=row["parent_scenario_id"] if "parent_scenario_id" in row.keys() else None,
            base_input_set=_from_json(row["base_input_set_json"] if "base_input_set_json" in row.keys() else "{}", {}),
            overrides=_from_json(row["overrides_json"] if "overrides_json" in row.keys() else "{}", {}),
            schema_version=row["schema_version"] if "schema_version" in row.keys() else "1.0",
            snapshot=_from_json(row["snapshot_json"], {}),
            governance_state=_from_json(row["governance_state_json"], {}),
            last_run_summary=_from_json(row["last_run_summary_json"], {}),
            replay_metadata=_from_json(row["replay_metadata_json"], {}),
            created_at=_from_iso(row["created_at"]),
            updated_at=_from_iso(row["updated_at"]),
        )


@dataclass(slots=True)
class WorkspaceStateRecord:
    workspace_id: str
    project_id: str
    user_id: str
    project_code: str
    active_scenario_id: Optional[str]
    active_scenario_name: Optional[str]
    draft_snapshot: dict[str, Any]
    saved_snapshot: dict[str, Any]
    last_runtime_snapshot: dict[str, Any]
    last_runtime_summary: dict[str, Any]
    last_runtime_snapshot_id: Optional[str]
    last_runtime_origin: Optional[str]
    last_runtime_scenario_id: Optional[str]
    dirty: bool
    governance_state: dict[str, Any]
    replay_metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime
    last_runtime_at: Optional[datetime]

    @classmethod
    def from_row(cls, row) -> "WorkspaceStateRecord":
        return cls(
            workspace_id=row["workspace_id"],
            project_id=row["project_id"],
            user_id=row["user_id"],
            project_code=row["project_code"],
            active_scenario_id=row["active_scenario_id"],
            active_scenario_name=row["active_scenario_name"],
            draft_snapshot=_from_json(row["draft_snapshot_json"], {}),
            saved_snapshot=_from_json(row["saved_snapshot_json"], {}),
            last_runtime_snapshot=_from_json(row["last_runtime_snapshot_json"], {}),
            last_runtime_summary=_from_json(row["last_runtime_summary_json"], {}),
            last_runtime_snapshot_id=row["last_runtime_snapshot_id"],
            last_runtime_origin=row["last_runtime_origin"],
            last_runtime_scenario_id=row["last_runtime_scenario_id"],
            dirty=bool(row["dirty"]),
            governance_state=_from_json(row["governance_state_json"], {}),
            replay_metadata=_from_json(row["replay_metadata_json"], {}),
            created_at=_from_iso(row["created_at"]),
            updated_at=_from_iso(row["updated_at"]),
            last_runtime_at=_from_iso(row["last_runtime_at"]) if row["last_runtime_at"] else None,
        )


def runtime_guard_for_snapshot(workspace_state: Optional[WorkspaceStateRecord], current_snapshot: dict[str, Any]) -> tuple[bool, str, str]:
    if workspace_state is None:
        return True, "workspace_base", ""
    saved = workspace_state.saved_snapshot
    has_prior_save = saved and snapshots_equal(saved, {}) is False

    if not has_prior_save:
        if workspace_state.dirty:
            return False, "preview_only", (
                "Unsaved edits are active. Save the scenario or discard edits before running so runtime results stay bound to an immutable snapshot."
            )
        return True, "workspace_base", ""

    # Normalize empty-string fields before comparing so that new form fields
    # (e.g. capex_* fields added by _collect_form_snapshot) don't cause a
    # false mismatch with workspace snapshots saved before those fields existed.
    saved_norm = _strip_empty_fields(saved)
    current_norm = _strip_empty_fields(current_snapshot)
    if snapshots_equal(saved_norm, current_norm):
        if workspace_state.active_scenario_id:
            return True, "saved_state", ""
        return True, "workspace_base", ""
    if workspace_state.dirty:
        return False, "preview_only", (
            "Unsaved edits are active. Save the scenario or discard edits before running so runtime results stay bound to an immutable snapshot."
        )
    return False, "preview_only", (
        "Current form state no longer matches the last saved runtime boundary. Refresh or discard edits before running."
    )


def save_scenario(
    user_id: str,
    project_id: str,
    scenario_name: str,
    project_code: str,
    source_project_template: str,
    snapshot: dict[str, Any],
    governance_state: Optional[dict[str, Any]] = None,
    last_run_summary: Optional[dict[str, Any]] = None,
    copied_from_scenario_id: Optional[str] = None,
    replay_metadata: Optional[dict[str, Any]] = None,
) -> ScenarioRecord:
    scenario_id = uuid.uuid4().hex[:16]
    now = _now_utc()
    governance_state = governance_state or {}
    last_run_summary = last_run_summary or {}
    replay_metadata = dict(replay_metadata or {})
    replay_metadata.setdefault("project_id", project_id)
    replay_metadata.setdefault("scenario_id", scenario_id)

    with get_cursor() as cur:
        cur.execute(
            """
            INSERT INTO scenarios (
                scenario_id, project_id, user_id, scenario_name, project_code,
                source_project_template, copied_from_scenario_id, archived,
                snapshot_json, governance_state_json, last_run_summary_json, replay_metadata_json,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?, ?, ?, ?)
            """,
            (
                scenario_id,
                project_id,
                user_id,
                scenario_name,
                project_code,
                source_project_template,
                copied_from_scenario_id,
                _to_json(snapshot),
                _to_json(governance_state),
                _to_json(last_run_summary),
                _to_json(replay_metadata),
                now.isoformat(),
                now.isoformat(),
            ),
        )

    return ScenarioRecord(
        scenario_id=scenario_id,
        project_id=project_id,
        user_id=user_id,
        scenario_name=scenario_name,
        project_code=project_code,
        source_project_template=source_project_template,
        copied_from_scenario_id=copied_from_scenario_id,
        archived=False,
        snapshot=snapshot,
        governance_state=governance_state,
        last_run_summary=last_run_summary,
        replay_metadata=replay_metadata,
        created_at=now,
        updated_at=now,
    )


def get_scenario(scenario_id: str, user_id: str) -> Optional[ScenarioRecord]:
    with get_cursor() as cur:
        cur.execute("SELECT * FROM scenarios WHERE scenario_id=? AND user_id=?", (scenario_id, user_id))
        row = cur.fetchone()
    return ScenarioRecord.from_row(row) if row else None


def list_scenarios(
    user_id: str,
    project_id: Optional[str] = None,
    include_archived: bool = False,
    limit: int = 25,
) -> list[ScenarioRecord]:
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


def promote_scenario_to_base_case(user_id: str, scenario_id: str) -> Optional["ScenarioRecord"]:
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


def duplicate_scenario(user_id: str, scenario_id: str, new_name: Optional[str] = None) -> Optional[ScenarioRecord]:
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


def add_scenario(
    user_id: str,
    project_id: str,
    project_code: str,
    scenario_name: str,
    parent_scenario_id: str,
    base_input_set: dict[str, Any],
    overrides: Optional[dict[str, Any]] = None,
    governance_state: Optional[dict[str, Any]] = None,
    replay_metadata: Optional[dict[str, Any]] = None,
) -> Optional[ScenarioRecord]:
    """Add a non-base scenario inheriting from a parent (typically the Base Case).

    The new scenario starts with empty overrides, so its effective snapshot
    is identical to the parent's base_input_set.
    """
    # Resolve effective snapshot = base_input_set merged with overrides
    resolved = resolve_scenario_snapshot(base_input_set, overrides or {})

    scenario_id = uuid.uuid4().hex[:16]
    now = _now_utc()
    governance_state = dict(governance_state or {})
    replay_metadata = dict(replay_metadata or {})
    replay_metadata.setdefault("scenario_id", scenario_id)
    replay_metadata["parent_scenario_id"] = parent_scenario_id
    replay_metadata["action"] = "add_scenario"

    with get_cursor() as cur:
        cur.execute(
            """
            INSERT INTO scenarios (
                scenario_id, project_id, user_id, scenario_name, project_code,
                source_project_template, copied_from_scenario_id, archived,
                is_base_case, parent_scenario_id,
                base_input_set_json, overrides_json,
                snapshot_json, governance_state_json,
                last_run_summary_json, replay_metadata_json,
                schema_version, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, NULL, 0, 0, ?, ?, ?, ?, ?, ?, ?, '1.0', ?, ?)
            """,
            (
                scenario_id,
                project_id,
                user_id,
                scenario_name,
                project_code,
                "",
                parent_scenario_id,
                _to_json(dict(base_input_set)),
                _to_json(dict(overrides or {})),
                _to_json(resolved),
                _to_json(governance_state),
                _to_json({}),
                _to_json(replay_metadata),
                now.isoformat(),
                now.isoformat(),
            ),
        )

    return ScenarioRecord(
        scenario_id=scenario_id,
        project_id=project_id,
        user_id=user_id,
        scenario_name=scenario_name,
        project_code=project_code,
        source_project_template="",
        copied_from_scenario_id=None,
        archived=False,
        is_base_case=False,
        parent_scenario_id=parent_scenario_id,
        base_input_set=dict(base_input_set),
        overrides=dict(overrides or {}),
        schema_version="1.0",
        snapshot=resolved,
        governance_state=governance_state,
        last_run_summary={},
        replay_metadata=replay_metadata,
        created_at=now,
        updated_at=now,
    )


def update_scenario_last_run_summary(
    user_id: str,
    scenario_id: str,
    last_run_summary: dict[str, Any],
    replay_metadata: Optional[dict[str, Any]] = None,
) -> bool:
    record = get_scenario(scenario_id, user_id)
    if record is None:
        return False
    merged_replay_metadata = dict(record.replay_metadata or {})
    if replay_metadata:
        merged_replay_metadata.update(replay_metadata)
    with get_cursor() as cur:
        cur.execute(
            """
            UPDATE scenarios
            SET last_run_summary_json=?, replay_metadata_json=?, updated_at=?
            WHERE scenario_id=? AND user_id=?
            """,
            (
                _to_json(last_run_summary or {}),
                _to_json(merged_replay_metadata),
                _now_utc().isoformat(),
                scenario_id,
                user_id,
            ),
        )
        return cur.rowcount > 0


def update_scenario_overrides(
    user_id: str,
    scenario_id: str,
    overrides: dict[str, Any],
) -> Optional[ScenarioRecord]:
    """Patch the overrides_json of a non-base scenario.

    Only keys in SCENARIO_INPUT_FIELDS are accepted; everything else is dropped.
    Returns the updated ScenarioRecord or None if the scenario doesn't exist.
    """
    record = get_scenario(scenario_id, user_id)
    if record is None:
        return None
    if record.is_base_case:
        return None  # base-case overrides are stored in base_input_set; use Inputs tab

    # Merge: existing overrides + new ones (new ones win)
    merged = dict(record.overrides)
    for key, value in overrides.items():
        if key in SCENARIO_INPUT_FIELDS:
            merged[key] = value
        # else: silently drop unknown keys per Phase 20B rules

    # Re-resolve effective snapshot
    resolved = resolve_scenario_snapshot(record.base_input_set, merged)
    now = _now_utc()

    with get_cursor() as cur:
        cur.execute(
            """
            UPDATE scenarios
            SET overrides_json=?, snapshot_json=?, updated_at=?
            WHERE scenario_id=? AND user_id=?
            """,
            (
                _to_json(merged),
                _to_json(resolved),
                now.isoformat(),
                scenario_id,
                user_id,
            ),
        )

    record.overrides = merged
    record.snapshot = resolved
    record.updated_at = now
    return record


def select_scenario(
    user_id: str,
    project_id: str,
    scenario_id: str,
) -> bool:
    """Set the active scenario for the given project in workspace_state."""
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


def record_workspace_runtime(
    *,
    user_id: str,
    project_id: str,
    project_code: str,
    runtime_snapshot: dict[str, Any],
    runtime_summary: dict[str, Any],
    runtime_snapshot_id: str,
    runtime_origin: str,
    governance_state: Optional[dict[str, Any]] = None,
    active_scenario_id: Optional[str] = None,
    active_scenario_name: Optional[str] = None,
    replay_metadata: Optional[dict[str, Any]] = None,
) -> WorkspaceStateRecord:
    existing = get_workspace_state(user_id, project_id)
    saved_snapshot = existing.saved_snapshot if existing else runtime_snapshot
    draft_snapshot = existing.draft_snapshot if existing else runtime_snapshot
    dirty = existing.dirty if existing else False
    return save_workspace_state(
        user_id=user_id,
        project_id=project_id,
        project_code=project_code,
        active_scenario_id=active_scenario_id if active_scenario_id is not None else (existing.active_scenario_id if existing else None),
        active_scenario_name=active_scenario_name if active_scenario_name is not None else (existing.active_scenario_name if existing else None),
        draft_snapshot=draft_snapshot,
        saved_snapshot=saved_snapshot,
        last_runtime_snapshot=runtime_snapshot,
        last_runtime_summary=runtime_summary,
        last_runtime_snapshot_id=runtime_snapshot_id,
        last_runtime_origin=runtime_origin,
        last_runtime_scenario_id=active_scenario_id if runtime_origin == "saved_state" else None,
        dirty=dirty,
        governance_state=governance_state or (existing.governance_state if existing else {}),
        replay_metadata=replay_metadata,
        last_runtime_at=_now_utc(),
    )


