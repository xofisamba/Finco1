"""
app.v2.opex_commands — OPEX custom-row command layer.

Mirrors capex_commands.py for the OPEX domain.

Each command function enforces:
  - Protected-reference guard (factory_template → PermissionError)
  - Group eligibility (B.13 → ValueError; unknown → ValueError)
  - Workbook version check (browser registry must match server)
  - Row-level optimistic concurrency (updated_at token)
  - Atomic DB write covering both opex_sub_lines and workspace_states
    (BEGIN EXCLUSIVE — row mutation + dirty-state update in one transaction)

Commands do NOT route through WorkbookUpdateService or the scalar field
endpoint.  They write only to opex_sub_lines; the workspace draft_snapshot
is not touched.  The OpexViewModel is rebuilt from DB state after each
command so UI totals reflect the mutation.

Dirty-state guarantee
---------------------
Every successful command sets workspace_states.dirty=1 inside the same
exclusive transaction as the opex_sub_lines write.  If the dirty-state
UPDATE fails the whole transaction rolls back.
"""
from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator, List, Mapping, Optional, Sequence

from app.persistence.opex_sub_lines import (
    REJECTED_PARENT_GROUPS,
    OpexSubLine,
    ReorderConflictError,
    assert_project_allows_opex_sub_lines,
    create_sub_line,
    deactivate_sub_line_with_version,
    list_sub_lines_for_project,
    reorder_sub_lines,
    update_sub_line,
    validate_parent_group,
)
from app.persistence.db import get_connection
from app.persistence.workspace_repository import mark_workspace_dirty_cursor
from app.workbook.registry import WORKBOOK

# B.13 Contingencies is always DERIVED — no custom rows allowed.
_DERIVED_GROUP_CODES: frozenset[str] = frozenset({"B.13"})


# ---------------------------------------------------------------------------
# Error hierarchy
# ---------------------------------------------------------------------------

class OpexCommandError(ValueError):
    """Base for all OPEX command errors."""


class OpexProtectedReferenceError(OpexCommandError):
    """Project is a factory_template and cannot be mutated."""


class OpexProtectedGroupError(OpexCommandError):
    """The target OPEX group does not accept custom rows."""


class OpexConcurrentEditError(OpexCommandError):
    """Row version is stale — concurrent edit detected."""


class OpexVersionMismatchError(OpexCommandError):
    """Workbook version submitted by browser is stale."""


class OpexRowNotFoundError(OpexCommandError):
    """Sub-line not found or not active for this project."""


# ---------------------------------------------------------------------------
# Guard helpers
# ---------------------------------------------------------------------------

def _check_project_allows(project_record: Any) -> None:
    try:
        assert_project_allows_opex_sub_lines(project_record)
    except PermissionError as exc:
        raise OpexProtectedReferenceError(str(exc)) from exc


def _check_workbook_version(submitted_version: str) -> None:
    current = WORKBOOK.version
    if submitted_version != current:
        raise OpexVersionMismatchError(
            f"Browser workbook version {submitted_version!r} is stale "
            f"(server: {current!r}). Reload the page before editing."
        )


def _check_group_eligible(parent_group_code: str) -> None:
    """Raise if the group is rejected or derived."""
    if parent_group_code in REJECTED_PARENT_GROUPS:
        raise OpexProtectedGroupError(
            f"Group {parent_group_code!r} is read-only "
            "(B.13 Contingencies does not accept custom rows)."
        )
    if parent_group_code in _DERIVED_GROUP_CODES:
        raise OpexProtectedGroupError(
            f"Group {parent_group_code!r} is a derived/contingency group "
            "and does not accept custom rows."
        )
    try:
        validate_parent_group(parent_group_code)
    except ValueError as exc:
        raise OpexProtectedGroupError(str(exc)) from exc


# ---------------------------------------------------------------------------
# Atomic transaction context manager
# ---------------------------------------------------------------------------

@contextmanager
def _exclusive_tx(user_id: str, project_id: str) -> Iterator[Any]:
    """BEGIN EXCLUSIVE transaction covering opex_sub_lines and workspace_states.

    Yields a cursor.  On clean exit: marks workspace dirty (raises
    OpexCommandError if no workspace row exists), then COMMITs.
    On any exception: ROLLBACKs atomically.
    """
    conn = get_connection()
    conn.execute("BEGIN EXCLUSIVE")
    cur = conn.cursor()
    try:
        yield cur
        marked = mark_workspace_dirty_cursor(cur, user_id=user_id, project_id=project_id)
        if not marked:
            raise OpexCommandError(
                "Workspace state is missing; OPEX row mutation was not committed."
            )
        conn.execute("COMMIT")
    except Exception:
        try:
            conn.execute("ROLLBACK")
        except Exception:
            pass
        raise
    finally:
        cur.close()
        conn.close()


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def add_opex_line(
    *,
    project_record: Any,
    user_id: str,
    label: str,
    parent_group_code: str,
    amount_keur: float = 0.0,
    inflation_pct: float = 0.0,
    notes: str = "",
    workbook_version: str,
) -> OpexSubLine:
    """Add a custom sub-line to an eligible OPEX group.

    Returns the persisted OpexSubLine (with UUID, business_code,
    display_order, timestamps).  The workspace is marked dirty in the
    same exclusive transaction.

    Raises
    ------
    OpexProtectedReferenceError
        Project is a factory_template.
    OpexProtectedGroupError
        Group does not accept custom rows (B.13, unknown).
    OpexVersionMismatchError
        Browser workbook version is stale.
    ValueError
        label is empty or amount_keur is not numeric.
    """
    _check_project_allows(project_record)
    _check_workbook_version(workbook_version)
    _check_group_eligible(parent_group_code)

    project_id: str = project_record.project_id
    with _exclusive_tx(user_id, project_id) as cur:
        return create_sub_line(
            cur,
            project_id=project_id,
            parent_group_code=parent_group_code,
            label=label,
            amount_keur=float(amount_keur),
            inflation_pct=float(inflation_pct),
            comments=notes,
        )


def update_opex_line(
    *,
    project_record: Any,
    user_id: str,
    sub_line_id: str,
    label: str,
    amount_keur: float,
    inflation_pct: float = 0.0,
    notes: str = "",
    row_version: str,
    workbook_version: str,
) -> OpexSubLine:
    """Update an existing custom OPEX sub-line's label, amount, inflation, and notes.

    Returns the updated OpexSubLine.  The workspace is marked dirty in the
    same exclusive transaction.

    Raises
    ------
    OpexProtectedReferenceError
        Project is a factory_template.
    OpexVersionMismatchError
        Browser workbook version is stale.
    OpexConcurrentEditError
        row_version does not match current updated_at (concurrent edit).
    OpexRowNotFoundError
        sub_line_id does not exist or is not active for this project.
    """
    _check_project_allows(project_record)
    _check_workbook_version(workbook_version)

    project_id: str = project_record.project_id
    with _exclusive_tx(user_id, project_id) as cur:
        result = update_sub_line(
            cur,
            project_id=project_id,
            sub_line_id=sub_line_id,
            label=label,
            amount_keur=float(amount_keur),
            inflation_pct=float(inflation_pct),
            comments=notes,
            row_version=row_version,
        )
        if result is None:
            rows = list_sub_lines_for_project(cur, project_id, include_inactive=True)
            if not any(r.sub_line_id == sub_line_id for r in rows):
                raise OpexRowNotFoundError(
                    f"Sub-line {sub_line_id!r} not found for project {project_id!r}."
                )
            raise OpexConcurrentEditError(
                f"Sub-line {sub_line_id!r} was modified concurrently. "
                "Reload and try again."
            )
    return result


def deactivate_opex_line(
    *,
    project_record: Any,
    user_id: str,
    sub_line_id: str,
    row_version: str,
    workbook_version: str,
) -> bool:
    """Deactivate (soft-delete) a custom OPEX sub-line.

    Returns True on success.  The workspace is marked dirty in the same
    exclusive transaction.

    Raises
    ------
    OpexProtectedReferenceError
        Project is a factory_template.
    OpexVersionMismatchError
        Browser workbook version is stale.
    OpexConcurrentEditError
        row_version does not match current updated_at.
    OpexRowNotFoundError
        sub_line_id not found or already inactive.
    """
    _check_project_allows(project_record)
    _check_workbook_version(workbook_version)

    project_id: str = project_record.project_id
    with _exclusive_tx(user_id, project_id) as cur:
        ok = deactivate_sub_line_with_version(
            cur,
            project_id=project_id,
            sub_line_id=sub_line_id,
            row_version=row_version,
        )
        if not ok:
            rows = list_sub_lines_for_project(cur, project_id, include_inactive=True)
            if not any(r.sub_line_id == sub_line_id for r in rows):
                raise OpexRowNotFoundError(
                    f"Sub-line {sub_line_id!r} not found for project {project_id!r}."
                )
            raise OpexConcurrentEditError(
                f"Sub-line {sub_line_id!r} was modified concurrently. "
                "Reload and try again."
            )
    return True


def reorder_opex_lines(
    *,
    project_record: Any,
    user_id: str,
    parent_group_code: str,
    ordered_rows: Sequence[Mapping[str, str]],
    workbook_version: str,
) -> list[OpexSubLine]:
    """Reorder custom sub-lines within a group (atomic, fully validated).

    ``ordered_rows`` must be the COMPLETE active set for the group, each
    entry as ``{"sub_line_id": str, "row_version": str}``.

    All rows are verified inside a BEGIN EXCLUSIVE transaction.
    Any unknown, missing, duplicate, or stale entry → OpexConcurrentEditError.

    On success display_order values are set to 1..N and the workspace is
    marked dirty in the same transaction.

    Raises
    ------
    OpexProtectedReferenceError / OpexProtectedGroupError /
    OpexVersionMismatchError / OpexConcurrentEditError
    """
    _check_project_allows(project_record)
    _check_workbook_version(workbook_version)
    _check_group_eligible(parent_group_code)

    project_id: str = project_record.project_id
    with _exclusive_tx(user_id, project_id) as cur:
        try:
            return reorder_sub_lines(
                cur,
                project_id=project_id,
                parent_group_code=parent_group_code,
                ordered_rows=ordered_rows,
            )
        except ReorderConflictError as exc:
            raise OpexConcurrentEditError(str(exc)) from exc
