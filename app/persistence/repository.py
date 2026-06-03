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
class ScenarioExportRecord:
    export_id: str
    scenario_id: Optional[str]
    project_id: Optional[str]
    user_id: str
    export_type: str
    artifact_name: str
    artifact_path: Optional[str]
    project_code: str
    governance_state: dict[str, Any]
    runtime_snapshot_id: Optional[str]
    replay_metadata: dict[str, Any]
    created_at: datetime

    @classmethod
    def from_row(cls, row) -> "ScenarioExportRecord":
        return cls(
            export_id=row["export_id"],
            scenario_id=row["scenario_id"],
            project_id=row["project_id"],
            user_id=row["user_id"],
            export_type=row["export_type"],
            artifact_name=row["artifact_name"],
            artifact_path=row["artifact_path"],
            project_code=row["project_code"],
            governance_state=_from_json(row["governance_state_json"], {}),
            runtime_snapshot_id=row["runtime_snapshot_id"],
            replay_metadata=_from_json(row["replay_metadata_json"], {}),
            created_at=_from_iso(row["created_at"]),
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


def save_project(
    user_id: str,
    project_code: str,
    project_name: str,
    source_project_template: str,
    project_type: Optional[str] = None,
    project_origin: str = "factory_template",
    template_source: Optional[str] = None,
    baseline_snapshot: Optional[dict[str, Any]] = None,
    archived: bool = False,
    is_readonly: bool = False,
    governance_state: Optional[dict[str, Any]] = None,
    last_run_summary: Optional[dict[str, Any]] = None,
    replay_metadata: Optional[dict[str, Any]] = None,
) -> ProjectRecord:
    now = _now_utc()
    governance_state = governance_state or {}
    last_run_summary = last_run_summary or {}
    baseline_snapshot = baseline_snapshot or {}
    replay_metadata = dict(replay_metadata or {})
    effective_template_source = template_source or source_project_template

    with get_cursor() as cur:
        cur.execute(
            """
            SELECT project_id, created_at, project_type, project_origin, template_source, baseline_snapshot_json, archived
            FROM projects
            WHERE user_id=? AND project_code=?
            """,
            (user_id, project_code),
        )
        existing = cur.fetchone()
        if existing:
            project_id = existing["project_id"]
            created_at = _from_iso(existing["created_at"])
            project_type = project_type or existing["project_type"]
            project_origin = project_origin or existing["project_origin"] or "factory_template"
            effective_template_source = effective_template_source or existing["template_source"] or source_project_template
            if not baseline_snapshot:
                baseline_snapshot = _from_json(existing["baseline_snapshot_json"], {})
            archived = bool(existing["archived"]) if archived is None else archived
            replay_metadata.setdefault("project_id", project_id)
            cur.execute(
                """
                UPDATE projects
                SET project_name=?, project_type=?, project_origin=?, source_project_template=?, template_source=?,
                    baseline_snapshot_json=?, archived=?, is_readonly=?, governance_state_json=?, last_run_summary_json=?,
                    replay_metadata_json=?, updated_at=?
                WHERE project_id=? AND user_id=?
                """,
                (
                    project_name,
                    project_type,
                    project_origin,
                    source_project_template,
                    effective_template_source,
                    _to_json(baseline_snapshot),
                    int(bool(archived)),
                    int(bool(is_readonly)),
                    _to_json(governance_state),
                    _to_json(last_run_summary),
                    _to_json(replay_metadata),
                    now.isoformat(),
                    project_id,
                    user_id,
                ),
            )
        else:
            project_id = uuid.uuid4().hex[:16]
            created_at = now
            replay_metadata.setdefault("project_id", project_id)
            cur.execute(
                """
                INSERT INTO projects (
                    project_id, user_id, project_code, project_name, project_type, project_origin,
                    source_project_template, template_source, baseline_snapshot_json, archived, is_readonly,
                    governance_state_json, last_run_summary_json, replay_metadata_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    project_id,
                    user_id,
                    project_code,
                    project_name,
                    project_type,
                    project_origin,
                    source_project_template,
                    effective_template_source,
                    _to_json(baseline_snapshot),
                    int(bool(archived)),
                    int(bool(is_readonly)),
                    _to_json(governance_state),
                    _to_json(last_run_summary),
                    _to_json(replay_metadata),
                    created_at.isoformat(),
                    now.isoformat(),
                ),
            )

    return ProjectRecord(
        project_id=project_id,
        user_id=user_id,
        project_code=project_code,
        project_name=project_name,
        project_type=project_type,
        project_origin=project_origin,
        source_project_template=source_project_template,
        template_source=effective_template_source,
        baseline_snapshot=baseline_snapshot,
        archived=bool(archived),
        is_readonly=bool(is_readonly),
        governance_state=governance_state,
        last_run_summary=last_run_summary,
        replay_metadata=replay_metadata,
        created_at=created_at,
        updated_at=now,
    )


def get_project(project_id: str, user_id: str) -> Optional[ProjectRecord]:
    with get_cursor() as cur:
        cur.execute("SELECT * FROM projects WHERE project_id=? AND user_id=?", (project_id, user_id))
        row = cur.fetchone()
    return ProjectRecord.from_row(row) if row else None


def get_project_by_code(user_id: str, project_code: str) -> Optional[ProjectRecord]:
    with get_cursor() as cur:
        cur.execute(
            "SELECT * FROM projects WHERE user_id=? AND project_code=?",
            (user_id, project_code),
        )
        row = cur.fetchone()
    return ProjectRecord.from_row(row) if row else None


def list_projects(user_id: str) -> list[ProjectRecord]:
    with get_cursor() as cur:
        cur.execute(
            "SELECT * FROM projects WHERE user_id=? AND archived=0 ORDER BY updated_at DESC",
            (user_id,),
        )
        return [ProjectRecord.from_row(row) for row in cur.fetchall()]


def list_baseline_records(user_id: str) -> list[ProjectRecord]:
    """Return saved-baseline records (project_origin='saved_baseline') for a user."""
    with get_cursor() as cur:
        cur.execute(
            "SELECT * FROM projects WHERE user_id=? AND project_origin='saved_baseline' AND archived=0 ORDER BY project_name",
            (user_id,),
        )
        return [ProjectRecord.from_row(row) for row in cur.fetchall()]


def seed_baseline_projects_if_needed(user_id: str) -> list[ProjectRecord]:
    """
    Ensure TUHO Baseline and Oborovo Baseline exist for user.
    Idempotent — does not overwrite existing baseline records.
    """
    seeded = []
    for code, name, project_type, template_source in [
        ("tuho-baseline", "TUHO — Baseline", "Wind", "tuho"),
        ("oborovo-baseline", "Oborovo — Baseline", "Solar", "oborovo"),
    ]:
        existing = get_project_by_code(user_id, code)
        if existing is not None:
            continue  # already exists
        snapshot = _compute_baseline_snapshot(project_type, template_source)
        record = save_project(
            user_id=user_id,
            project_code=code,
            project_name=name,
            project_type=project_type,
            project_origin="saved_baseline",
            source_project_template=template_source,
            template_source=template_source,
            baseline_snapshot=snapshot,
            is_readonly=True,
            governance_state={"g20": "BLOCKED", "r99_r102": "NOT_APPROVED", "lender_ready": False},
        )
        seeded.append(record)
    return seeded


def _compute_baseline_snapshot(project_type: str, template_source: str) -> dict[str, Any]:
    """
    Build a workspace-ready snapshot dict for a saved baseline project.
    Mirrors the logic in main_web._project_baseline_snapshot.
    """
    from app.project_factories import (
        create_default_tuho_wind1,
        create_default_oborovo,
        create_default_wind_project,
        create_default_solar_project,
    )
    from app.persistence.db import get_cursor

    canonical_type = project_type
    normalized_source = template_source

    baseline = {
        "active_project": "",
        "project_name": "",
        "project_type": canonical_type,
        "project_origin": "saved_baseline",
        "template_source": normalized_source,
        "country_market": "",
        "scenario": "Base",
        "capacity_mw": "",
        "tariff_eur_mwh": "",
        "p50_hours": "",
        "total_capex_keur": "",
        "opex_y1_keur": "",
        "gearing_pct": "",
        "target_dscr": "",
        "interest_rate_pct": "",
        "tenor_years": "",
        "cod_date": "",
        "construction_months": "",
        "horizon_years": "",
        "capacity_factor": "",
        "ppa_term_years": "",
    }

    def _sum_opex(items):
        """Sum y1_amount_keur from an opex iterable."""
        total = 0.0
        for item in items:
            total += float(getattr(item, "y1_amount_keur", 0) or 0)
        return total

    if normalized_source == "tuho":
        pi = create_default_tuho_wind1()
        baseline.update({
            "active_project": "tuho-baseline",
            "project_name": pi.info.name,
            "project_type": "Wind",
            "template_source": "tuho",
            "country_market": pi.info.country_iso,
            "capacity_mw": str(pi.technical.capacity_mw),
            "tariff_eur_mwh": str(pi.revenue.ppa_base_tariff),
            "p50_hours": str(pi.technical.operating_hours_p50),
            "total_capex_keur": str(pi.capex.total_capex),
            "opex_y1_keur": str(_sum_opex(pi.opex)),
            "target_dscr": str(pi.financing.target_dscr),
            "interest_rate_pct": str(pi.financing.base_rate + pi.financing.margin_bps / 10_000),
            "tenor_years": str(pi.financing.senior_tenor_years),
            "cod_date": str(pi.info.cod_date),
            "construction_months": str(pi.info.construction_months),
            "horizon_years": str(pi.info.horizon_years),
            "capacity_factor": f"{(pi.technical.operating_hours_p50 / 8760) * 100:.2f}",
            "ppa_term_years": str(int(pi.revenue.ppa_term_years)),
        })
        return baseline

    if normalized_source == "oborovo":
        pi = create_default_oborovo()
        baseline.update({
            "active_project": "oborovo-baseline",
            "project_name": pi.info.name,
            "project_type": "Solar",
            "template_source": "oborovo",
            "country_market": pi.info.country_iso,
            "capacity_mw": str(pi.technical.capacity_mw),
            "tariff_eur_mwh": str(pi.revenue.ppa_base_tariff),
            "p50_hours": str(pi.technical.operating_hours_p50),
            "total_capex_keur": str(pi.capex.total_capex),
            "opex_y1_keur": str(_sum_opex(pi.opex)),
            "gearing_pct": str(float(getattr(pi.financing, "gearing_ratio", 0.0) or 0.0) * 100),
            "target_dscr": str(pi.financing.target_dscr),
            "interest_rate_pct": str(pi.financing.base_rate + pi.financing.margin_bps / 10_000),
            "tenor_years": str(pi.financing.senior_tenor_years),
            "cod_date": str(pi.info.cod_date),
            "construction_months": str(pi.info.construction_months),
            "horizon_years": str(pi.info.horizon_years),
            "capacity_factor": f"{(pi.technical.operating_hours_p50 / 8760) * 100:.2f}",
            "ppa_term_years": str(int(pi.revenue.ppa_term_years)),
        })
        return baseline

    # generic_wind / generic_solar fallback
    if canonical_type == "Solar":
        pi = create_default_solar_project()
    else:
        pi = create_default_wind_project()
    baseline.update({
        "active_project": normalized_source,
        "project_name": pi.info.name,
        "template_source": normalized_source,
        "country_market": pi.info.country_iso,
        "capacity_mw": str(pi.technical.capacity_mw),
        "tariff_eur_mwh": str(pi.revenue.ppa_base_tariff),
        "p50_hours": str(pi.technical.operating_hours_p50),
        "total_capex_keur": str(pi.capex.total_capex),
        "opex_y1_keur": str(_sum_opex(pi.opex)),
        "gearing_pct": str(float(getattr(pi.financing, "gearing_ratio", 0.0) or 0.0) * 100),
        "target_dscr": str(pi.financing.target_dscr),
        "interest_rate_pct": str(pi.financing.base_rate + pi.financing.margin_bps / 10_000),
        "tenor_years": str(pi.financing.senior_tenor_years),
        "cod_date": str(pi.info.cod_date),
        "construction_months": str(pi.info.construction_months),
        "horizon_years": str(pi.info.horizon_years),
        "capacity_factor": f"{(pi.technical.operating_hours_p50 / 8760) * 100:.2f}",
        "ppa_term_years": str(int(pi.revenue.ppa_term_years)),
    })
    return baseline


def _build_default_snapshot(project_code: str, defaults: dict[str, Any]) -> dict[str, Any]:
    """Build a workspace-ready snapshot from factory defaults."""
    from app.input_adapter import build_projectinputs_from_snapshot
    snapshot = dict(defaults)
    snapshot["active_project"] = project_code
    snapshot["project_origin"] = "saved_baseline"
    # Ensure runtime-usable fields are present
    _fill_missing_defaults(snapshot)
    return snapshot


def _fill_missing_defaults(snapshot: dict[str, Any]) -> None:
    """Ensure required snapshot fields exist with safe defaults."""
    defaults = {
        "scenario": "Base",
        "project_type": "Wind",
        "capacity_mw": 50.0,
        "p50_hours": 2500.0,
        "tariff_eur_mwh": 80.0,
        "total_capex_keur": 50000.0,
        "opex_y1_keur": 5000.0,
        "gearing_pct": 75.0,
        "target_dscr": 1.4,
        "interest_rate_pct": 7.0,
        "tenor_years": 20,
    }
    for k, v in defaults.items():
        if k not in snapshot:
            snapshot[k] = v


def create_project_record(
    *,
    user_id: str,
    project_code: str,
    project_name: str,
    project_type: str,
    project_origin: str,
    template_source: str,
    baseline_snapshot: dict[str, Any],
    governance_state: Optional[dict[str, Any]] = None,
    last_run_summary: Optional[dict[str, Any]] = None,
    replay_metadata: Optional[dict[str, Any]] = None,
    is_readonly: bool = False,
) -> ProjectRecord:
    return save_project(
        user_id=user_id,
        project_code=project_code,
        project_name=project_name,
        project_type=project_type,
        project_origin=project_origin,
        source_project_template=template_source,
        template_source=template_source,
        baseline_snapshot=baseline_snapshot,
        governance_state=governance_state,
        last_run_summary=last_run_summary,
        replay_metadata=replay_metadata,
        is_readonly=is_readonly,
    )


def get_project_record(
    *,
    user_id: str,
    project_id: Optional[str] = None,
    project_code: Optional[str] = None,
) -> Optional[ProjectRecord]:
    if project_id:
        return get_project(project_id, user_id)
    if project_code:
        return get_project_by_code(user_id, project_code)
    return None


def list_project_records(
    *,
    user_id: str,
    include_archived: bool = False,
) -> list[ProjectRecord]:
    query = "SELECT * FROM projects WHERE user_id=?"
    params: list[Any] = [user_id]
    if not include_archived:
        query += " AND archived=0"
    query += " ORDER BY updated_at DESC"
    with get_cursor() as cur:
        cur.execute(query, tuple(params))
        return [ProjectRecord.from_row(row) for row in cur.fetchall()]


def update_project_record(
    *,
    user_id: str,
    project_code: str,
    project_name: Optional[str] = None,
    project_type: Optional[str] = None,
    template_source: Optional[str] = None,
    baseline_snapshot: Optional[dict[str, Any]] = None,
    archived: Optional[bool] = None,
    governance_state: Optional[dict[str, Any]] = None,
    last_run_summary: Optional[dict[str, Any]] = None,
    replay_metadata: Optional[dict[str, Any]] = None,
) -> Optional[ProjectRecord]:
    existing = get_project_by_code(user_id, project_code)
    if existing is None:
        return None
    return save_project(
        user_id=user_id,
        project_code=existing.project_code,
        project_name=project_name or existing.project_name,
        project_type=project_type or existing.project_type,
        project_origin=existing.project_origin,
        source_project_template=template_source or existing.source_project_template,
        template_source=template_source or existing.template_source or existing.source_project_template,
        baseline_snapshot=baseline_snapshot if baseline_snapshot is not None else existing.baseline_snapshot,
        archived=existing.archived if archived is None else archived,
        governance_state=governance_state or existing.governance_state,
        last_run_summary=last_run_summary or existing.last_run_summary,
        replay_metadata=replay_metadata or existing.replay_metadata,
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


def get_workspace_state(user_id: str, project_id: str) -> Optional[WorkspaceStateRecord]:
    with get_cursor() as cur:
        cur.execute(
            "SELECT * FROM workspace_states WHERE user_id=? AND project_id=?",
            (user_id, project_id),
        )
        row = cur.fetchone()
    return WorkspaceStateRecord.from_row(row) if row else None


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
) -> WorkspaceStateRecord:
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


def bind_workspace_to_scenario(
    user_id: str,
    project_id: str,
    project_code: str,
    record: ScenarioRecord,
    governance_state: Optional[dict[str, Any]] = None,
    replay_metadata: Optional[dict[str, Any]] = None,
) -> WorkspaceStateRecord:
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


def discard_workspace_draft(user_id: str, project_id: str) -> Optional[WorkspaceStateRecord]:
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


def record_export(
    user_id: str,
    project_code: str,
    export_type: str,
    artifact_name: str,
    artifact_path: Optional[str] = None,
    project_id: Optional[str] = None,
    scenario_id: Optional[str] = None,
    governance_state: Optional[dict[str, Any]] = None,
    runtime_snapshot_id: Optional[str] = None,
    replay_metadata: Optional[dict[str, Any]] = None,
) -> ScenarioExportRecord:
    export_id = uuid.uuid4().hex[:16]
    created_at = _now_utc()
    governance_state = governance_state or {}
    replay_metadata = dict(replay_metadata or {})
    replay_metadata.setdefault("project_id", project_id)
    replay_metadata.setdefault("scenario_id", scenario_id)
    replay_metadata.setdefault("export_id", export_id)
    replay_metadata.setdefault("runtime_snapshot_id", runtime_snapshot_id)
    replay_metadata.setdefault("export_timestamp", created_at.isoformat())

    with get_cursor() as cur:
        cur.execute(
            """
            INSERT INTO scenario_exports (
                export_id, scenario_id, project_id, user_id, export_type, artifact_name,
                artifact_path, project_code, governance_state_json, runtime_snapshot_id, replay_metadata_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                export_id,
                scenario_id,
                project_id,
                user_id,
                export_type,
                artifact_name,
                artifact_path,
                project_code,
                _to_json(governance_state),
                runtime_snapshot_id,
                _to_json(replay_metadata),
                created_at.isoformat(),
            ),
        )

    return ScenarioExportRecord(
        export_id=export_id,
        scenario_id=scenario_id,
        project_id=project_id,
        user_id=user_id,
        export_type=export_type,
        artifact_name=artifact_name,
        artifact_path=artifact_path,
        project_code=project_code,
        governance_state=governance_state,
        runtime_snapshot_id=runtime_snapshot_id,
        replay_metadata=replay_metadata,
        created_at=created_at,
    )


def list_exports(
    user_id: str,
    project_id: Optional[str] = None,
    scenario_id: Optional[str] = None,
    limit: int = 20,
) -> list[ScenarioExportRecord]:
    query = "SELECT * FROM scenario_exports WHERE user_id=?"
    params: list[Any] = [user_id]
    if project_id:
        query += " AND project_id=?"
        params.append(project_id)
    if scenario_id:
        query += " AND scenario_id=?"
        params.append(scenario_id)
    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)

    with get_cursor() as cur:
        cur.execute(query, tuple(params))
        return [ScenarioExportRecord.from_row(row) for row in cur.fetchall()]


def get_scenario_history(
    user_id: str,
    project_id: Optional[str] = None,
    limit: int = 40,
) -> list[ScenarioRecord]:
    """Return saved-scenario history including archived items."""
    return list_scenarios(
        user_id=user_id,
        project_id=project_id,
        include_archived=True,
        limit=limit,
    )


def compare_scenarios(
    user_id: str,
    left_scenario_id: str,
    right_scenario_id: str,
) -> Optional[dict[str, Any]]:
    """Build a lightweight comparison matrix for two saved scenarios."""
    left = get_scenario(left_scenario_id, user_id)
    right = get_scenario(right_scenario_id, user_id)
    if left is None or right is None:
        return None

    metrics = []
    for metric in [
        "Revenue",
        "OPEX",
        "EBITDA",
        "Senior Debt",
        "SHL",
        "DSCR",
        "Project IRR",
        "Equity IRR",
        "CAPEX",
        "Distributions",
    ]:
        left_value = _metric_value(left, metric)
        right_value = _metric_value(right, metric)
        left_num = _safe_number(left_value)
        right_num = _safe_number(right_value)
        delta = None if left_num is None or right_num is None else right_num - left_num
        metrics.append(
            {
                "metric": metric,
                "left_value": left_value,
                "right_value": right_value,
                "delta": delta,
            }
        )

    governance_rows = [
        {
            "label": "G20",
            "left_value": left.governance_state.get("g20_status", "BLOCKED"),
            "right_value": right.governance_state.get("g20_status", "BLOCKED"),
        },
        {
            "label": "R99/R102",
            "left_value": left.governance_state.get("r99_r102_status", "NOT APPROVED"),
            "right_value": right.governance_state.get("r99_r102_status", "NOT APPROVED"),
        },
    ]

    return {
        "left": left,
        "right": right,
        "metrics": metrics,
        "governance_rows": governance_rows,
    }


def build_export_lineage(
    user_id: str,
    project_id: Optional[str] = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Return export history with scenario lineage context."""
    exports = list_exports(user_id=user_id, project_id=project_id, limit=limit)
    lineage = []
    for item in exports:
        scenario = get_scenario(item.scenario_id, user_id) if item.scenario_id else None
        lineage.append(
            {
                "export_id": item.export_id,
                "artifact_name": item.artifact_name,
                "export_type": item.export_type,
                "project_code": item.project_code,
                "scenario_name": scenario.scenario_name if scenario else "Workspace export",
                "copied_from_scenario_id": scenario.copied_from_scenario_id if scenario else None,
                "created_at": item.created_at,
                "governance_state": item.governance_state,
                "replay_metadata": item.replay_metadata,
            }
        )
    return lineage


# ─── Phase 20G: Base vs Active Scenario Compare ─────────────────────────────────────


def base_vs_active_compare(user_id: str, project_id: str) -> Optional[dict[str, Any]]:
    """Pre-compute Base Case vs Active Scenario comparison for the Compare workspace tab.

    Returns a dict with 'base' and 'active' ScenarioRecords (or None), plus
    computed metrics/deltas when both are available, and an 'empty_state' string
    when only partial context is available.
    """
    # Get workspace state to find the active scenario
    ws = get_workspace_state(user_id, project_id)
    active_scenario_id = ws.active_scenario_id if ws else None

    # Ensure base case exists
    seed_scenarios_if_needed(
        user_id=user_id,
        project_id=project_id,
        project_code=ws.project_code if ws else "",
        project_type="solar",
        source_project_template=ws.saved_snapshot.get("template_source", "") if ws and ws.saved_snapshot else "",
        baseline_snapshot=ws.saved_snapshot if ws and ws.saved_snapshot else {},
        governance_state={},
        template_origin="workspace",
    )
    base_scenario = get_base_case_scenario(user_id, project_id)

    if base_scenario is None:
        return None

    result = {"base": base_scenario, "active": None}

    if not active_scenario_id:
        result["empty_state"] = "No active scenario selected — select a saved scenario to compare against Base Case."
        return result

    active = get_scenario(active_scenario_id, user_id)
    if active is None:
        result["empty_state"] = "Active scenario not found."
        return result

    result["active"] = active

    # Build metrics for both
    base_metrics = _build_compare_metrics(base_scenario)
    active_metrics = _build_compare_metrics(active)

    # Compute deltas
    metrics = []
    for key in base_metrics:
        b_val = base_metrics[key]
        a_val = active_metrics.get(key)
        delta = None
        sign_class = "delta-neutral"
        if b_val is not None and a_val is not None:
            delta = a_val - b_val
            if delta > 0:
                sign_class = "delta-positive"
            elif delta < 0:
                sign_class = "delta-negative"
            else:
                sign_class = "delta-neutral"
        metrics.append({
            "key": key,
            "base_value": b_val,
            "active_value": a_val,
            "delta": delta,
            "sign_class": sign_class,
        })

    result["metrics"] = metrics
    return result


def _scenario_runtime_dict(record: "ScenarioRecord") -> dict[str, Any]:
    """Build a runtime provenance dict from a ScenarioRecord for display in Compare tab provenance cards."""
    snapshot = record.snapshot or {}
    last_run = record.last_run_summary or {}
    replay = record.replay_metadata or {}
    overrides = record.overrides or {}
    return {
        "scenario_id": record.scenario_id,
        "scenario_name": record.scenario_name,
        "is_base_case": record.is_base_case,
        "last_run_summary": last_run,
        "total_revenue_keur": last_run.get("total_revenue_keur"),
        "total_opex_keur": last_run.get("total_opex_keur"),
        "total_ebitda_keur": last_run.get("total_ebitda_keur"),
        "senior_debt_keur": last_run.get("senior_debt_keur"),
        "shl_balance_keur": last_run.get("shl_balance_keur"),
        "project_irr": last_run.get("project_irr"),
        "equity_irr": last_run.get("equity_irr"),
        "avg_dscr": last_run.get("avg_dscr"),
        "min_dscr": last_run.get("min_dscr"),
        "total_capex_keur": float(snapshot.get("total_capex_keur", 0) or 0),
        "replay_metadata": replay,
        "runtime_origin": replay.get("runtime_origin", "workspace"),
        "runtime_timestamp": replay.get("runtime_timestamp"),
        "run_id": replay.get("run_id"),
        "override_field_count": len(overrides),
        "override_field_list": sorted(overrides.keys()),
    }


def _build_compare_metrics(record: "ScenarioRecord") -> dict[str, Optional[float]]:
    """Build a flat metrics dict from a ScenarioRecord for scenario comparison."""
    last_run = record.last_run_summary or {}
    snapshot = record.snapshot or {}
    return {
        "total_revenue_keur": _safe_number(last_run.get("total_revenue_keur")),
        "total_opex_keur": _safe_number(last_run.get("total_opex_keur")),
        "total_ebitda_keur": _safe_number(last_run.get("total_ebitda_keur")),
        "senior_debt_keur": _safe_number(last_run.get("senior_debt_keur")),
        "shl_balance_keur": _safe_number(last_run.get("shl_balance_keur")),
        "project_irr": _safe_number(last_run.get("project_irr")),
        "equity_irr": _safe_number(last_run.get("equity_irr")),
        "avg_dscr": _safe_number(last_run.get("avg_dscr")),
        "min_dscr": _safe_number(last_run.get("min_dscr")),
        "total_capex_keur": _safe_number(snapshot.get("total_capex_keur")),
    }


def _delta_sign_class(delta: Optional[float]) -> str:
    """Return Bootstrap color class for a delta value."""
    if delta is None:
        return "delta-neutral"
    if delta > 0:
        return "delta-positive"
    if delta < 0:
        return "delta-negative"
    return "delta-neutral"


def _format_db_timestamp(value: Any) -> str:
    """Format a timestamp from the DB (datetime or ISO string) for display."""
    if value is None:
        return "—"
    if hasattr(value, "strftime"):
        return value.strftime("%d %b %Y %H:%M")
    # Already a string
    try:
        from datetime import datetime
        dt = datetime.fromisoformat(str(value))
        return dt.strftime("%d %b %Y %H:%M")
    except Exception:
        return str(value)

