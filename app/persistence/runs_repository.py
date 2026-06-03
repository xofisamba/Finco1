"""Run persistence functions extracted from app/persistence/repository.py.

This module holds Group D run-related persistence functions extracted
during Phase 53B. The functions are re-exported from
app.persistence.repository for backward compatibility.

Function inventory (Group D, from Phase 52A/52C/52E/52G):

- RunRecord (dataclass)
- save_run
- get_run
- list_runs
- delete_run
- count_runs

Behavior is preserved exactly as it was in repository.py. The only
change is the file location.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

from app.persistence._helpers import _from_iso, _from_json, _now_utc, _to_json
from app.persistence.db import get_cursor


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
    replay_metadata: dict[str, Any] | None = None

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
            "replay_metadata": self.replay_metadata or {},
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
            replay_metadata=_from_json(row["replay_metadata_json"], {}),
        )


def save_run(
    user_id: str,
    project_type: str,
    scenario: str,
    inputs: dict,
    kpis: dict,
    excel_path: Optional[str] = None,
    notes: Optional[str] = None,
    replay_metadata: Optional[dict[str, Any]] = None,
) -> RunRecord:
    run_id = uuid.uuid4().hex[:16]
    created_at = _now_utc()
    replay_metadata = dict(replay_metadata or {})
    replay_metadata.setdefault("run_id", run_id)
    replay_metadata.setdefault("runtime_timestamp", created_at.isoformat())

    with get_cursor() as cur:
        cur.execute(
            """
            INSERT INTO runs (run_id, user_id, project_type, scenario, created_at, inputs_json, kpis_json, excel_path, notes, replay_metadata_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                _to_json(replay_metadata),
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
        replay_metadata=replay_metadata,
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
