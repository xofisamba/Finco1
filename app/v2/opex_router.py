"""
app.v2.opex_router — OPEX custom-row command endpoints.

Mirrors capex_router.py for the OPEX domain.
Mounted at /v2/opex by main_web.py (under the same FINCO_WORKBOOK_V2 flag).

Endpoints
---------
POST /v2/opex/line/add
    Add a custom row to an eligible OPEX group (B.01–B.12).

POST /v2/opex/line/update
    Update label, Y1 amount, inflation_pct, and notes on an existing
    custom row. Requires row_version for optimistic concurrency.

POST /v2/opex/line/deactivate
    Soft-delete a custom row (excluded from future projections).
    Requires row_version for optimistic concurrency.

POST /v2/opex/line/reorder
    Atomically reorder all rows in an OPEX group.
    Accepts the COMPLETE active set as ordered pairs of
    sub_line_id[] + row_version[] (parallel repeated form fields).
    Any unknown, missing, duplicate, or stale entry → 409.

All endpoints
  - Require authentication (finco_session cookie).
  - Check project ownership.
  - Enforce protected-reference guard.
  - Check workbook_version against WORKBOOK.version.
  - Return the re-rendered OPEX sheet partial + OOB status banner (HTMX).
  - Return 409 JSON for protected-reference, stale version, or concurrent edit.
  - Return 404 JSON for unknown project or workspace.
  - Return 422 JSON for validation errors.

Row commands do NOT route through WorkbookUpdateService or /v2/workbook/update.
They mutate opex_sub_lines only; the workspace draft_snapshot is untouched.
The workspace is marked dirty inside the same exclusive transaction as the
row mutation.
"""
from __future__ import annotations

from typing import List

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from app.auth import COOKIE_NAME, decode_session_token
from app.v2.opex_commands import (
    OpexCommandError,
    OpexConcurrentEditError,
    OpexProtectedGroupError,
    OpexProtectedReferenceError,
    OpexRowNotFoundError,
    OpexVersionMismatchError,
    add_opex_line,
    deactivate_opex_line,
    reorder_opex_lines,
    update_opex_line,
)

opex_router = APIRouter()


def _get_current_user(request: Request):
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return None
    return decode_session_token(token)


def _render_opex_sheet(
    request: Request, project_record, pis, ws, project: str, field_error: str = ""
) -> HTMLResponse:
    """Delegate to the main V2 router's OPEX partial renderer."""
    from app.v2.router import _render_opex_htmx_sheet
    return _render_opex_htmx_sheet(request, pis, ws, project_record, project, field_error=field_error)


def _load_project_and_ws(user, project: str):
    """Return (project_record, ws, pis) or raise LookupError."""
    from app.persistence.projects_repository import get_project_record
    from app.persistence.workspace_repository import get_workspace_state
    from app.workbook.service import WorkbookService

    project_record = get_project_record(user_id=user.user_id, project_code=project)
    if project_record is None:
        raise LookupError(f"Project {project!r} not found.")
    ws = get_workspace_state(user_id=user.user_id, project_id=project_record.project_id)
    if ws is None:
        raise LookupError("Workspace not found.")
    pis = WorkbookService.build_draft_input_set_from_workspace(ws)
    return project_record, ws, pis


def _handle_command_error(exc: OpexCommandError) -> JSONResponse:
    if isinstance(exc, OpexProtectedReferenceError):
        return JSONResponse({"error": str(exc)}, status_code=409)
    if isinstance(exc, OpexVersionMismatchError):
        return JSONResponse({"error": str(exc), "reload": True}, status_code=409)
    if isinstance(exc, OpexConcurrentEditError):
        return JSONResponse({"error": str(exc)}, status_code=409)
    if isinstance(exc, OpexProtectedGroupError):
        return JSONResponse({"error": str(exc)}, status_code=422)
    if isinstance(exc, OpexRowNotFoundError):
        return JSONResponse({"error": str(exc)}, status_code=404)
    return JSONResponse({"error": str(exc)}, status_code=422)


@opex_router.post("/line/add")
async def opex_line_add(
    request: Request,
    project: str = Form(...),
    parent_group_code: str = Form(...),
    label: str = Form(...),
    amount_keur: float = Form(default=0.0),
    inflation_pct: float = Form(default=0.0),
    notes: str = Form(default=""),
    workbook_version: str = Form(...),
):
    """Add a custom OPEX row to an eligible group."""
    user = _get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    try:
        project_record, ws, pis = _load_project_and_ws(user, project)
    except LookupError as exc:
        return JSONResponse({"error": str(exc)}, status_code=404)

    is_htmx = request.headers.get("HX-Request") == "true"

    try:
        add_opex_line(
            project_record=project_record,
            user_id=user.user_id,
            label=label.strip(),
            parent_group_code=parent_group_code,
            amount_keur=amount_keur,
            inflation_pct=inflation_pct,
            notes=notes,
            workbook_version=workbook_version,
        )
    except OpexCommandError as exc:
        if is_htmx:
            return _render_opex_sheet(request, project_record, pis, ws, project, field_error=str(exc))
        return _handle_command_error(exc)
    except ValueError as exc:
        if is_htmx:
            return _render_opex_sheet(request, project_record, pis, ws, project, field_error=str(exc))
        return JSONResponse({"error": str(exc)}, status_code=422)

    from app.persistence.workspace_repository import get_workspace_state
    ws = get_workspace_state(user_id=user.user_id, project_id=project_record.project_id) or ws
    if is_htmx:
        return _render_opex_sheet(request, project_record, pis, ws, project)
    return RedirectResponse(url=f"/v2/workbook?project={project}", status_code=303)


@opex_router.post("/line/update")
async def opex_line_update(
    request: Request,
    project: str = Form(...),
    sub_line_id: str = Form(...),
    label: str = Form(...),
    amount_keur: float = Form(default=0.0),
    inflation_pct: float = Form(default=0.0),
    notes: str = Form(default=""),
    row_version: str = Form(...),
    workbook_version: str = Form(...),
):
    """Update an existing custom OPEX row (optimistic-lock on row_version)."""
    user = _get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    try:
        project_record, ws, pis = _load_project_and_ws(user, project)
    except LookupError as exc:
        return JSONResponse({"error": str(exc)}, status_code=404)

    is_htmx = request.headers.get("HX-Request") == "true"

    try:
        update_opex_line(
            project_record=project_record,
            user_id=user.user_id,
            sub_line_id=sub_line_id,
            label=label.strip(),
            amount_keur=amount_keur,
            inflation_pct=inflation_pct,
            notes=notes,
            row_version=row_version,
            workbook_version=workbook_version,
        )
    except OpexCommandError as exc:
        if is_htmx:
            err = str(exc)
            if isinstance(exc, OpexConcurrentEditError):
                err = "Row was modified concurrently — values refreshed. Try again."
            return _render_opex_sheet(request, project_record, pis, ws, project, field_error=err)
        return _handle_command_error(exc)
    except ValueError as exc:
        if is_htmx:
            return _render_opex_sheet(request, project_record, pis, ws, project, field_error=str(exc))
        return JSONResponse({"error": str(exc)}, status_code=422)

    from app.persistence.workspace_repository import get_workspace_state
    ws = get_workspace_state(user_id=user.user_id, project_id=project_record.project_id) or ws
    if is_htmx:
        return _render_opex_sheet(request, project_record, pis, ws, project)
    return RedirectResponse(url=f"/v2/workbook?project={project}", status_code=303)


@opex_router.post("/line/deactivate")
async def opex_line_deactivate(
    request: Request,
    project: str = Form(...),
    sub_line_id: str = Form(...),
    row_version: str = Form(...),
    workbook_version: str = Form(...),
):
    """Deactivate (soft-delete) a custom OPEX row."""
    user = _get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    try:
        project_record, ws, pis = _load_project_and_ws(user, project)
    except LookupError as exc:
        return JSONResponse({"error": str(exc)}, status_code=404)

    is_htmx = request.headers.get("HX-Request") == "true"

    try:
        deactivate_opex_line(
            project_record=project_record,
            user_id=user.user_id,
            sub_line_id=sub_line_id,
            row_version=row_version,
            workbook_version=workbook_version,
        )
    except OpexCommandError as exc:
        if is_htmx:
            err = str(exc)
            if isinstance(exc, OpexConcurrentEditError):
                err = "Row was modified concurrently — values refreshed. Try again."
            return _render_opex_sheet(request, project_record, pis, ws, project, field_error=err)
        return _handle_command_error(exc)

    from app.persistence.workspace_repository import get_workspace_state
    ws = get_workspace_state(user_id=user.user_id, project_id=project_record.project_id) or ws
    if is_htmx:
        return _render_opex_sheet(request, project_record, pis, ws, project)
    return RedirectResponse(url=f"/v2/workbook?project={project}", status_code=303)


@opex_router.post("/line/reorder")
async def opex_line_reorder(
    request: Request,
    project: str = Form(...),
    parent_group_code: str = Form(...),
    sub_line_id: List[str] = Form(default=[]),
    row_version: List[str] = Form(default=[]),
    workbook_version: str = Form(...),
):
    """Atomically reorder all custom rows within an OPEX group.

    Accepts two parallel repeated form fields:
    - sub_line_id[] — ordered list of sub-line UUIDs (desired new order)
    - row_version[]  — matching updated_at tokens (must align 1-to-1)

    The submitted set must be COMPLETE (all active rows for the group).
    Any mismatch → 409.
    """
    user = _get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    try:
        project_record, ws, pis = _load_project_and_ws(user, project)
    except LookupError as exc:
        return JSONResponse({"error": str(exc)}, status_code=404)

    is_htmx = request.headers.get("HX-Request") == "true"

    if len(sub_line_id) != len(row_version):
        err = "sub_line_id and row_version lists must have equal length."
        if is_htmx:
            return _render_opex_sheet(request, project_record, pis, ws, project, field_error=err)
        return JSONResponse({"error": err}, status_code=422)

    ordered_rows = [
        {"sub_line_id": sid, "row_version": rv}
        for sid, rv in zip(sub_line_id, row_version)
    ]

    try:
        reorder_opex_lines(
            project_record=project_record,
            user_id=user.user_id,
            parent_group_code=parent_group_code,
            ordered_rows=ordered_rows,
            workbook_version=workbook_version,
        )
    except OpexCommandError as exc:
        if is_htmx:
            return _render_opex_sheet(request, project_record, pis, ws, project, field_error=str(exc))
        return _handle_command_error(exc)

    from app.persistence.workspace_repository import get_workspace_state
    ws = get_workspace_state(user_id=user.user_id, project_id=project_record.project_id) or ws
    if is_htmx:
        return _render_opex_sheet(request, project_record, pis, ws, project)
    return RedirectResponse(url=f"/v2/workbook?project={project}", status_code=303)
