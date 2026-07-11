"""
app.v2.capex_commands — CAPEX custom-row command layer.

Each command function enforces:
  - Protected-reference guard (factory_template → PermissionError)
  - Category eligibility (C.17/C.18 → ValueError; C.13 contingency → ValueError)
  - Workbook version check (browser registry must match server)
  - Row-level optimistic concurrency (updated_at token)
  - Atomic DB write covering both capex_sub_lines and workspace_states
    (BEGIN EXCLUSIVE — row mutation + dirty-state update in one transaction)

Commands do NOT route through WorkbookUpdateService or the scalar field
endpoint.  They write only to capex_sub_lines; the workspace draft_snapshot
is not touched.  The CapexViewModel is rebuilt from DB state after each
command so UI totals reflect the mutation.

Dirty-state guarantee
---------------------
Every successful command sets workspace_states.dirty=1 inside the same
exclusive transaction as the capex_sub_lines write.  The workspace
draft_snapshot and saved_snapshot are not modified; the existing
RuntimeResult is preserved.  The UI will show "Draft changed — Run required"
on next page load.  If the dirty-state UPDATE fails the whole transaction
rolls back — the caller never receives a success response for a partially
committed state.
"""
from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator, List, Mapping, Optional, Sequence

from app.persistence.capex_sub_lines import (
    REJECTED_PARENT_CATEGORIES,
    CapexSubLine,
    ReorderConflictError,
    assert_project_allows_capex_sub_lines,
    create_sub_line,
    deactivate_sub_line_with_version,
    list_sub_lines_for_project,
    reorder_sub_lines,
    update_sub_line,
    validate_parent_category,
)
from app.persistence.db import get_connection
from app.persistence.workspace_repository import mark_workspace_dirty_cursor
from app.workbook.registry import WORKBOOK

# Groups that are derived/computed — no custom rows allowed even though the
# persistence layer permits C.13 in its allowed list.
_DERIVED_GROUP_CODES: frozenset[str] = frozenset({"C.13"})


# ---------------------------------------------------------------------------
# Error hierarchy
# ---------------------------------------------------------------------------

class CapexCommandError(ValueError):
    """Base for all CAPEX command errors."""


class CapexProtectedReferenceError(CapexCommandError):
    """Project is a factory_template and cannot be mutated."""


class CapexProtectedGroupError(CapexCommandError):
    """The target CAPEX group does not accept custom rows."""


class CapexConcurrentEditError(CapexCommandError):
    """Row version is stale — concurrent edit detected."""


class CapexVersionMismatchError(CapexCommandError):
    """Workbook version submitted by browser is stale."""


class CapexRowNotFoundError(CapexCommandError):
    """Sub-line not found or not active for this project."""


# ---------------------------------------------------------------------------
# Guard helpers
# ---------------------------------------------------------------------------

def _check_project_allows(project_record: Any) -> None:
    try:
        assert_project_allows_capex_sub_lines(project_record)
    except PermissionError as exc:
        raise CapexProtectedReferenceError(str(exc)) from exc


def _check_workbook_version(submitted_version: str) -> None:
    current = WORKBOOK.version
    if submitted_version != current:
        raise CapexVersionMismatchError(
            f"Browser workbook version {submitted_version!r} is stale "
            f"(server: {current!r}). Reload the page before editing."
        )


def _check_group_eligible(parent_category_code: str) -> None:
    """Raise if the group is rejected or derived."""
    if parent_category_code in REJECTED_PARENT_CATEGORIES:
        raise CapexProtectedGroupError(
            f"Group {parent_category_code!r} is read-only "
            "(C.17 and C.18 do not accept custom rows)."
        )
    if parent_category_code in _DERIVED_GROUP_CODES:
        raise CapexProtectedGroupError(
            f"Group {parent_category_code!r} is a derived/contingency group "
            "and does not accept custom rows."
        )
    try:
        validate_parent_category(parent_category_code)
    except ValueError as exc:
        raise CapexProtectedGroupError(str(exc)) from exc


# ---------------------------------------------------------------------------
# Atomic transaction context manager
# ---------------------------------------------------------------------------

@contextmanager
def _exclusive_tx(user_id: str, project_id: str) -> Iterator[Any]:
    """Open a BEGIN EXCLUSIVE transaction covering capex_sub_lines and
    workspace_states; mark the workspace dirty on successful commit.

    Yields a cursor.  On clean exit: marks workspace dirty (raises
    CapexCommandError if no workspace row exists, which also triggers
    rollback), then COMMITs.  On any exception: ROLLBACKs — both the
    row mutation and the dirty-state update are rolled back atomically.
    """
    conn = get_connection()
    conn.execute("BEGIN EXCLUSIVE")
    cur = conn.cursor()
    try:
        yield cur
        marked = mark_workspace_dirty_cursor(cur, user_id=user_id, project_id=project_id)
        if not marked:
            raise CapexCommandError(
                "Workspace state is missing; CAPEX row mutation was not committed."
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

def add_capex_line(
    *,
    project_record: Any,
    user_id: str,
    label: str,
    parent_category_code: str,
    amount_keur: float = 0.0,
    notes: str = "",
    workbook_version: str,
) -> CapexSubLine:
    """Add a custom sub-line to an eligible CAPEX group.

    Returns the persisted CapexSubLine (with UUID, business_code,
    display_order, timestamps).  The workspace is marked dirty in the
    same exclusive transaction.

    Raises
    ------
    CapexProtectedReferenceError
        Project is a factory_template.
    CapexProtectedGroupError
        Group does not accept custom rows (C.13, C.17, C.18, unknown).
    CapexVersionMismatchError
        Browser workbook version is stale.
    ValueError
        label is empty or amount_keur is not numeric.
    """
    _check_project_allows(project_record)
    _check_workbook_version(workbook_version)
    _check_group_eligible(parent_category_code)

    project_id: str = project_record.project_id
    with _exclusive_tx(user_id, project_id) as cur:
        return create_sub_line(
            cur,
            project_id=project_id,
            parent_category_code=parent_category_code,
            label=label,
            amount_keur=float(amount_keur),
            comments=notes,
        )


def update_capex_line(
    *,
    project_record: Any,
    user_id: str,
    sub_line_id: str,
    label: str,
    amount_keur: float,
    notes: str = "",
    row_version: str,
    workbook_version: str,
) -> CapexSubLine:
    """Update an existing custom sub-line's label, amount, and notes.

    Returns the updated CapexSubLine.  The workspace is marked dirty in
    the same exclusive transaction.

    Raises
    ------
    CapexProtectedReferenceError
        Project is a factory_template.
    CapexVersionMismatchError
        Browser workbook version is stale.
    CapexConcurrentEditError
        row_version does not match current updated_at (concurrent edit).
    CapexRowNotFoundError
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
            comments=notes,
            row_version=row_version,
        )
        if result is None:
            # Check whether the row exists at all (to distinguish not-found vs stale).
            rows = list_sub_lines_for_project(cur, project_id, include_inactive=True)
            if not any(r.sub_line_id == sub_line_id for r in rows):
                raise CapexRowNotFoundError(
                    f"Sub-line {sub_line_id!r} not found for project {project_id!r}."
                )
            raise CapexConcurrentEditError(
                f"Sub-line {sub_line_id!r} was modified concurrently. "
                "Reload and try again."
            )
    return result


def deactivate_capex_line(
    *,
    project_record: Any,
    user_id: str,
    sub_line_id: str,
    row_version: str,
    workbook_version: str,
) -> bool:
    """Deactivate (soft-delete) a custom sub-line.

    Returns True on success.  The workspace is marked dirty in the same
    exclusive transaction.

    Raises
    ------
    CapexProtectedReferenceError
        Project is a factory_template.
    CapexVersionMismatchError
        Browser workbook version is stale.
    CapexConcurrentEditError
        row_version does not match current updated_at.
    CapexRowNotFoundError
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
                raise CapexRowNotFoundError(
                    f"Sub-line {sub_line_id!r} not found for project {project_id!r}."
                )
            raise CapexConcurrentEditError(
                f"Sub-line {sub_line_id!r} was modified concurrently. "
                "Reload and try again."
            )
    return True


def reorder_capex_lines(
    *,
    project_record: Any,
    user_id: str,
    parent_category_code: str,
    ordered_rows: Sequence[Mapping[str, str]],
    workbook_version: str,
) -> list[CapexSubLine]:
    """Reorder custom sub-lines within a group (atomic, fully validated).

    ``ordered_rows`` must be the COMPLETE active set for the group, each
    entry as ``{"sub_line_id": str, "row_version": str}``.

    All rows are verified inside a BEGIN EXCLUSIVE transaction:
    - No duplicates, no unknown IDs, no missing active IDs.
    - Every row_version must match the current updated_at.
    - If any check fails the transaction rolls back and
      CapexConcurrentEditError is raised.

    On success display_order values are set to 1..N (contiguous, no gaps)
    and the workspace is marked dirty in the same transaction.

    Raises
    ------
    CapexProtectedReferenceError / CapexProtectedGroupError /
    CapexVersionMismatchError / CapexConcurrentEditError
    """
    _check_project_allows(project_record)
    _check_workbook_version(workbook_version)
    _check_group_eligible(parent_category_code)

    project_id: str = project_record.project_id
    with _exclusive_tx(user_id, project_id) as cur:
        try:
            return reorder_sub_lines(
                cur,
                project_id=project_id,
                parent_category_code=parent_category_code,
                ordered_rows=ordered_rows,
            )
        except ReorderConflictError as exc:
            raise CapexConcurrentEditError(str(exc)) from exc
