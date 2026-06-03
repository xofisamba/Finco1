"""Project read persistence functions extracted from app/persistence/repository.py.

This module holds Group A-reads (project read) persistence functions
extracted during Phase 53D. The functions are re-exported from
app.persistence.repository for backward compatibility.

Function inventory (Group A-reads, from Phase 52A/52C/52E/52G):

- get_project
- get_project_by_code
- list_projects
- list_baseline_records
- get_project_record
- list_project_records

DO NOT TOUCH (stay in repository.py, will be moved in Group A-2 with
the P0 pin for save_project):

- save_project
- seed_baseline_projects_if_needed
- _compute_baseline_snapshot
- _sum_opex
- _build_default_snapshot
- _fill_missing_defaults
- create_project_record
- update_project_record
- ProjectRecord (dataclass, shared)

Behavior is preserved exactly as it was in repository.py. The only
change is the file location.

Note on circular import: ProjectRecord is a dataclass defined inside
app.persistence.repository. To avoid a circular import, the type
annotations in this module use string forward references, and the
ProjectRecord.from_row() call is resolved at runtime via
app.persistence.repository's import of this module.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

from app.persistence.db import get_cursor

if TYPE_CHECKING:
    from app.persistence.repository import ProjectRecord


def get_project(project_id: str, user_id: str) -> "Optional[ProjectRecord]":
    with get_cursor() as cur:
        cur.execute("SELECT * FROM projects WHERE project_id=? AND user_id=?", (project_id, user_id))
        row = cur.fetchone()
    # Local import to avoid circular import at module load time
    from app.persistence.repository import ProjectRecord
    return ProjectRecord.from_row(row) if row else None


def get_project_by_code(user_id: str, project_code: str) -> "Optional[ProjectRecord]":
    with get_cursor() as cur:
        cur.execute(
            "SELECT * FROM projects WHERE user_id=? AND project_code=?",
            (user_id, project_code),
        )
        row = cur.fetchone()
    from app.persistence.repository import ProjectRecord
    return ProjectRecord.from_row(row) if row else None


def list_projects(user_id: str) -> "list[ProjectRecord]":
    with get_cursor() as cur:
        cur.execute(
            "SELECT * FROM projects WHERE user_id=? AND archived=0 ORDER BY updated_at DESC",
            (user_id,),
        )
        from app.persistence.repository import ProjectRecord
        return [ProjectRecord.from_row(row) for row in cur.fetchall()]


def list_baseline_records(user_id: str) -> "list[ProjectRecord]":
    """Return saved-baseline records (project_origin='saved_baseline') for a user."""
    with get_cursor() as cur:
        cur.execute(
            "SELECT * FROM projects WHERE user_id=? AND project_origin='saved_baseline' AND archived=0 ORDER BY project_name",
            (user_id,),
        )
        from app.persistence.repository import ProjectRecord
        return [ProjectRecord.from_row(row) for row in cur.fetchall()]


def get_project_record(
    *,
    user_id: str,
    project_id: Optional[str] = None,
    project_code: Optional[str] = None,
) -> "Optional[ProjectRecord]":
    if project_id:
        return get_project(project_id, user_id)
    if project_code:
        return get_project_by_code(user_id, project_code)
    return None


def list_project_records(
    *,
    user_id: str,
    include_archived: bool = False,
) -> "list[ProjectRecord]":
    query = "SELECT * FROM projects WHERE user_id=?"
    params: list[Any] = [user_id]
    if not include_archived:
        query += " AND archived=0"
    query += " ORDER BY updated_at DESC"
    with get_cursor() as cur:
        cur.execute(query, tuple(params))
        from app.persistence.repository import ProjectRecord
        return [ProjectRecord.from_row(row) for row in cur.fetchall()]
