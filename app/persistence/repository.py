"""Repository for project run persistence."""

import json
import os
import uuid
from datetime import datetime, timezone
from typing import Optional, List

from app.persistence.db import get_cursor, get_connection


# ── Run record ────────────────────────────────────────────────────────────────

class RunRecord:
    """Represents a saved project run."""
    __slots__ = (
        "run_id", "user_id", "project_type", "scenario", "created_at",
        "inputs", "kpis", "excel_path", "notes",
    )

    def __init__(
        self, run_id, user_id, project_type, scenario, created_at,
        inputs, kpis, excel_path=None, notes=None,
    ):
        self.run_id = run_id
        self.user_id = user_id
        self.project_type = project_type
        self.scenario = scenario
        self.created_at = created_at
        self.inputs = inputs  # dict
        self.kpis = kpis      # dict
        self.excel_path = excel_path
        self.notes = notes

    def to_dict(self):
        return {
            "run_id": self.run_id,
            "user_id": self.user_id,
            "project_type": self.project_type,
            "scenario": self.scenario,
            "created_at": self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at,
            "inputs": self.inputs,
            "kpis": self.kpis,
            "excel_path": self.excel_path,
            "notes": self.notes,
        }

    @classmethod
    def from_row(cls, row) -> "RunRecord":
        created = row["created_at"]
        if isinstance(created, str):
            created = datetime.fromisoformat(created)
        return cls(
            run_id=row["run_id"],
            user_id=row["user_id"],
            project_type=row["project_type"],
            scenario=row["scenario"],
            created_at=created,
            inputs=json.loads(row["inputs_json"]),
            kpis=json.loads(row["kpis_json"]),
            excel_path=row["excel_path"],
            notes=row["notes"],
        )


# ── Repository functions ───────────────────────────────────────────────────────

def save_run(
    user_id: str,
    project_type: str,
    scenario: str,
    inputs: dict,
    kpis: dict,
    excel_path: Optional[str] = None,
    notes: Optional[str] = None,
) -> RunRecord:
    """Save a new project run. Returns RunRecord.

    user_id comes from the authenticated session — never from client input.
    """
    run_id = uuid.uuid4().hex[:16]
    created_at = datetime.now(timezone.utc)

    with get_cursor() as cur:
        cur.execute("""
            INSERT INTO runs (run_id, user_id, project_type, scenario, created_at, inputs_json, kpis_json, excel_path, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            run_id,
            user_id,
            project_type,
            scenario,
            created_at.isoformat(),
            json.dumps(inputs, default=str),
            json.dumps(kpis, default=str),
            excel_path,
            notes,
        ))

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
    """Get a run by ID, scoped to user (user isolation). Returns None if not found."""
    with get_cursor() as cur:
        cur.execute(
            "SELECT * FROM runs WHERE run_id=? AND user_id=?",
            (run_id, user_id)
        )
        row = cur.fetchone()
    if row is None:
        return None
    return RunRecord.from_row(row)


def list_runs(user_id: str, limit: int = 20) -> List[RunRecord]:
    """List recent runs for a user (most recent first)."""
    with get_cursor() as cur:
        cur.execute(
            "SELECT * FROM runs WHERE user_id=? ORDER BY created_at DESC LIMIT ?",
            (user_id, limit)
        )
        return [RunRecord.from_row(row) for row in cur.fetchall()]


def delete_run(run_id: str, user_id: str) -> bool:
    """Delete a run. Returns True if deleted, False if not found."""
    with get_cursor() as cur:
        cur.execute(
            "DELETE FROM runs WHERE run_id=? AND user_id=?",
            (run_id, user_id)
        )
        return cur.rowcount > 0


def count_runs(user_id: str) -> int:
    """Count total runs for a user."""
    with get_cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM runs WHERE user_id=?", (user_id,))
        return cur.fetchone()[0]