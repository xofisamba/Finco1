"""
app.v2.capex_commands — CAPEX custom-row command layer.

Each command function enforces:
  - Protected-reference guard (factory_template → PermissionError)
  - Category eligibility (C.17/C.18 → ValueError; C.13 contingency → ValueError)
  - Workbook version check (browser registry must match server)
  - Row-level optimistic concurrency (updated_at token)
  - Atomic DB write (BEGIN EXCLUSIVE via get_cursor)

Commands do NOT route through WorkbookUpdateService or the scalar field
endpoint.  They write only to capex_sub_lines; the workspace draft_snapshot
is not touched.  The CapexViewModel is rebuilt from DB state after each
command so UI totals reflect the mutation.
"""
from __future__ import annotations

from typing import Optional

from app.persistence.capex_sub_lines import (
    REJECTED_PARENT_CATEGORIES,
    CapexSubLine,
    assert_project_allows_capex_sub_lines,
    create_sub_line,
    deactivate_sub_line_with_version,
    reorder_sub_lines,
    update_sub_line,
    validate_parent_category,
)
from app.persistence.db import get_cursor
from app.workbook.registry import WORKBOOK

# Groups that are derived/computed — no custom rows allowed even though the
# persistence layer permits C.13 in its allowed list.
_DERIVED_GROUP_CODES: frozenset[str] = frozenset({"C.13"})


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


def _check_project_allows(project_record) -> None:
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
    # validate_parent_category rejects C.17/C.18 and any unknown code.
    try:
        validate_parent_category(parent_category_code)
    except ValueError as exc:
        raise CapexProtectedGroupError(str(exc)) from exc


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


def add_capex_line(
    *,
    project_record,
    label: str,
    parent_category_code: str,
    amount_keur: float = 0.0,
    notes: str = "",
    workbook_version: str,
) -> CapexSubLine:
    """Add a custom sub-line to an eligible CAPEX group.

    Returns the persisted CapexSubLine (with UUID, business_code,
    display_order, timestamps).

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
    with get_cursor() as cur:
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
    project_record,
    sub_line_id: str,
    label: str,
    amount_keur: float,
    notes: str = "",
    row_version: str,
    workbook_version: str,
) -> CapexSubLine:
    """Update an existing custom sub-line's label, amount, and notes.

    Returns the updated CapexSubLine.

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
    with get_cursor() as cur:
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
        # Check whether the row exists at all.
        from app.persistence.capex_sub_lines import list_sub_lines_for_project
        with get_cursor() as cur2:
            rows = list_sub_lines_for_project(cur2, project_id, include_inactive=True)
        exists = any(r.sub_line_id == sub_line_id for r in rows)
        if not exists:
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
    project_record,
    sub_line_id: str,
    row_version: str,
    workbook_version: str,
) -> bool:
    """Deactivate (soft-delete) a custom sub-line.

    Returns True on success.

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
    with get_cursor() as cur:
        ok = deactivate_sub_line_with_version(
            cur,
            project_id=project_id,
            sub_line_id=sub_line_id,
            row_version=row_version,
        )
    if not ok:
        from app.persistence.capex_sub_lines import list_sub_lines_for_project
        with get_cursor() as cur2:
            rows = list_sub_lines_for_project(cur2, project_id, include_inactive=True)
        exists = any(r.sub_line_id == sub_line_id for r in rows)
        if not exists:
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
    project_record,
    parent_category_code: str,
    ordered_ids: list[str],
    workbook_version: str,
) -> list[CapexSubLine]:
    """Reorder custom sub-lines within a group.

    ``ordered_ids`` is the desired order of sub-line UUIDs. Unknown or
    inactive IDs are silently ignored.  Returns the updated active sub-lines
    in their new order.

    Raises
    ------
    CapexProtectedReferenceError
        Project is a factory_template.
    CapexProtectedGroupError
        Group does not accept custom rows.
    CapexVersionMismatchError
        Browser workbook version is stale.
    """
    _check_project_allows(project_record)
    _check_workbook_version(workbook_version)
    _check_group_eligible(parent_category_code)

    project_id: str = project_record.project_id
    with get_cursor() as cur:
        return reorder_sub_lines(
            cur,
            project_id=project_id,
            parent_category_code=parent_category_code,
            ordered_ids=ordered_ids,
        )
