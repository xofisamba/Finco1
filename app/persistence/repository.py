"""Repository helpers for lightweight project, scenario, run, and export persistence."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

from app.persistence.db import get_cursor


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _to_json(value: Any) -> str:
    return json.dumps(value if value is not None else {}, default=str, sort_keys=True)


def _from_json(value: Optional[str], default: Any) -> Any:
    if not value:
        return default
    return json.loads(value)


def _from_iso(value: str | datetime) -> datetime:
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(value)


@dataclass(slots=True)
class RunRecord:
    run_id: str
    user_id: str
    project_type: str
    scenario: str
    created_at: datetime
    inputs: dict[str, Any]
    kpis: dict[str, Any]
    excel_path: Optional[str] = None
    notes: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "user_id": self.user_id,
            "project_type": self.project_type,
            "scenario": self.scenario,
            "created_at": self.created_at.isoformat(),
            "inputs": self.inputs,
            "kpis": self.kpis,
            "excel_path": self.excel_path,
            "notes": self.notes,
        }

    @classmethod
    def from_row(cls, row) -> "RunRecord":
        return cls(
            run_id=row["run_id"],
            user_id=row["user_id"],
            project_type=row["project_type"],
            scenario=row["scenario"],
            created_at=_from_iso(row["created_at"]),
            inputs=_from_json(row["inputs_json"], {}),
            kpis=_from_json(row["kpis_json"], {}),
            excel_path=row["excel_path"],
            notes=row["notes"],
        )


@dataclass(slots=True)
class ProjectRecord:
    project_id: str
    user_id: str
    project_code: str
    project_name: str
    source_project_template: str
    governance_state: dict[str, Any]
    last_run_summary: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_row(cls, row) -> "ProjectRecord":
        return cls(
            project_id=row["project_id"],
            user_id=row["user_id"],
            project_code=row["project_code"],
            project_name=row["project_name"],
            source_project_template=row["source_project_template"],
            governance_state=_from_json(row["governance_state_json"], {}),
            last_run_summary=_from_json(row["last_run_summary_json"], {}),
            created_at=_from_iso(row["created_at"]),
            updated_at=_from_iso(row["updated_at"]),
        )


@dataclass(slots=True)
class ScenarioRecord:
    scenario_id: str
    project_id: str
    user_id: str
    scenario_name: str
    project_code: str
    source_project_template: str
    copied_from_scenario_id: Optional[str]
    archived: bool
    snapshot: dict[str, Any]
    governance_state: dict[str, Any]
    last_run_summary: dict[str, Any]
    created_at: datetime
    updated_at: datetime

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
            snapshot=_from_json(row["snapshot_json"], {}),
            governance_state=_from_json(row["governance_state_json"], {}),
            last_run_summary=_from_json(row["last_run_summary_json"], {}),
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
            created_at=_from_iso(row["created_at"]),
        )


def _safe_number(value: Any) -> Optional[float]:
    if value in (None, "", "NOT_AVAILABLE", "MISSING"):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _metric_value(record: ScenarioRecord, key: str) -> Any:
    snapshot = record.snapshot or {}
    summary = record.last_run_summary or {}
    metric_map = {
        "Revenue": summary.get("total_revenue_keur"),
        "OPEX": snapshot.get("opex_y1_keur"),
        "EBITDA": summary.get("total_ebitda_keur"),
        "Senior Debt": summary.get("senior_debt_keur"),
        "SHL": summary.get("shl_balance_keur"),
        "DSCR": summary.get("avg_dscr"),
        "Project IRR": summary.get("project_irr"),
        "Equity IRR": summary.get("equity_irr"),
        "CAPEX": snapshot.get("total_capex_keur"),
        "Distributions": summary.get("distribution_keur"),
    }
    return metric_map.get(key)


def save_run(
    user_id: str,
    project_type: str,
    scenario: str,
    inputs: dict,
    kpis: dict,
    excel_path: Optional[str] = None,
    notes: Optional[str] = None,
) -> RunRecord:
    run_id = uuid.uuid4().hex[:16]
    created_at = _now_utc()

    with get_cursor() as cur:
        cur.execute(
            """
            INSERT INTO runs (run_id, user_id, project_type, scenario, created_at, inputs_json, kpis_json, excel_path, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                user_id,
                project_type,
                scenario,
                created_at.isoformat(),
                _to_json(inputs),
                _to_json(kpis),
                excel_path,
                notes,
            ),
        )

    return RunRecord(
        run_id=run_id,
        user_id=user_id,
        project_type=project_type,
        scenario=scenario,
        created_at=created_at,
        inputs=inputs,
        kpis=kpis,
        excel_path=excel_path,
        notes=notes,
    )


def get_run(run_id: str, user_id: str) -> Optional[RunRecord]:
    with get_cursor() as cur:
        cur.execute("SELECT * FROM runs WHERE run_id=? AND user_id=?", (run_id, user_id))
        row = cur.fetchone()
    return RunRecord.from_row(row) if row else None


def list_runs(user_id: str, limit: int = 20) -> list[RunRecord]:
    with get_cursor() as cur:
        cur.execute(
            "SELECT * FROM runs WHERE user_id=? ORDER BY created_at DESC LIMIT ?",
            (user_id, limit),
        )
        return [RunRecord.from_row(row) for row in cur.fetchall()]


def delete_run(run_id: str, user_id: str) -> bool:
    with get_cursor() as cur:
        cur.execute("DELETE FROM runs WHERE run_id=? AND user_id=?", (run_id, user_id))
        return cur.rowcount > 0


def count_runs(user_id: str) -> int:
    with get_cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM runs WHERE user_id=?", (user_id,))
        return cur.fetchone()[0]


def save_project(
    user_id: str,
    project_code: str,
    project_name: str,
    source_project_template: str,
    governance_state: Optional[dict[str, Any]] = None,
    last_run_summary: Optional[dict[str, Any]] = None,
) -> ProjectRecord:
    now = _now_utc()
    governance_state = governance_state or {}
    last_run_summary = last_run_summary or {}

    with get_cursor() as cur:
        cur.execute(
            "SELECT project_id, created_at FROM projects WHERE user_id=? AND project_code=?",
            (user_id, project_code),
        )
        existing = cur.fetchone()
        if existing:
            project_id = existing["project_id"]
            created_at = _from_iso(existing["created_at"])
            cur.execute(
                """
                UPDATE projects
                SET project_name=?, source_project_template=?, governance_state_json=?, last_run_summary_json=?, updated_at=?
                WHERE project_id=? AND user_id=?
                """,
                (
                    project_name,
                    source_project_template,
                    _to_json(governance_state),
                    _to_json(last_run_summary),
                    now.isoformat(),
                    project_id,
                    user_id,
                ),
            )
        else:
            project_id = uuid.uuid4().hex[:16]
            created_at = now
            cur.execute(
                """
                INSERT INTO projects (
                    project_id, user_id, project_code, project_name, source_project_template,
                    governance_state_json, last_run_summary_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    project_id,
                    user_id,
                    project_code,
                    project_name,
                    source_project_template,
                    _to_json(governance_state),
                    _to_json(last_run_summary),
                    created_at.isoformat(),
                    now.isoformat(),
                ),
            )

    return ProjectRecord(
        project_id=project_id,
        user_id=user_id,
        project_code=project_code,
        project_name=project_name,
        source_project_template=source_project_template,
        governance_state=governance_state,
        last_run_summary=last_run_summary,
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
            "SELECT * FROM projects WHERE user_id=? ORDER BY updated_at DESC",
            (user_id,),
        )
        return [ProjectRecord.from_row(row) for row in cur.fetchall()]


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
) -> ScenarioRecord:
    scenario_id = uuid.uuid4().hex[:16]
    now = _now_utc()
    governance_state = governance_state or {}
    last_run_summary = last_run_summary or {}

    with get_cursor() as cur:
        cur.execute(
            """
            INSERT INTO scenarios (
                scenario_id, project_id, user_id, scenario_name, project_code,
                source_project_template, copied_from_scenario_id, archived,
                snapshot_json, governance_state_json, last_run_summary_json,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?, ?, ?)
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
) -> ScenarioExportRecord:
    export_id = uuid.uuid4().hex[:16]
    created_at = _now_utc()
    governance_state = governance_state or {}

    with get_cursor() as cur:
        cur.execute(
            """
            INSERT INTO scenario_exports (
                export_id, scenario_id, project_id, user_id, export_type, artifact_name,
                artifact_path, project_code, governance_state_json, runtime_snapshot_id, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            }
        )
    return lineage
