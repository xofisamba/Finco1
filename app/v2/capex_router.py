"""
app.v2.capex_router — CAPEX custom-row command endpoints.

Mounted at /v2/capex by main_web.py (under the same FINCO_WORKBOOK_V2 flag
as the main V2 router).

Endpoints
---------
POST /v2/capex/line/add
    Add a custom row to an eligible CAPEX group.

POST /v2/capex/line/update
    Update label, amount, and notes on an existing custom row.
    Requires row_version (updated_at token) for optimistic concurrency.

POST /v2/capex/line/deactivate
    Soft-delete a custom row (excluded from future projections).
    Requires row_version for optimistic concurrency.

POST /v2/capex/line/reorder
    Update display_order for rows in a group.
    Accepts ordered_ids as repeated form values.

All endpoints
  - Require authentication (finco_session cookie).
  - Check project ownership.
  - Enforce protected-reference guard.
  - Check workbook_version against WORKBOOK.version.
  - Return the re-rendered CAPEX sheet partial + OOB status banner (HTMX).
  - Return 409 JSON for protected-reference, stale version, or concurrent edit.
  - Return 404 JSON for unknown project or workspace.
  - Return 422 JSON for validation errors.

Row commands do NOT route through WorkbookUpdateService or /v2/workbook/update.
They mutate capex_sub_lines only; the workspace draft_snapshot is untouched.
"""
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from app.auth import COOKIE_NAME, decode_session_token
from app.v2.capex_commands import (
    CapexCommandError,
    CapexConcurrentEditError,
    CapexProtectedGroupError,
    CapexProtectedReferenceError,
    CapexRowNotFoundError,
    CapexVersionMismatchError,
    add_capex_line,
    deactivate_capex_line,
    reorder_capex_lines,
    update_capex_line,
)

capex_router = APIRouter()


def _get_current_user(request: Request):
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return None
    return decode_session_token(token)


def _render_capex_sheet(request: Request, project_record, pis, ws, project: str, field_error: str = "") -> HTMLResponse:
    """Delegate to the main V2 router's CAPEX partial renderer."""
    from app.v2.router import _render_capex_htmx_sheet
    return _render_capex_htmx_sheet(request, pis, ws, project_record, project, field_error=field_error)


def _load_project_and_ws(user, project: str):
    """Return (project_record, ws, pis) or raise RuntimeError with a message."""
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


def _handle_command_error(exc: CapexCommandError) -> JSONResponse:
    if isinstance(exc, CapexProtectedReferenceError):
        return JSONResponse({"error": str(exc)}, status_code=409)
    if isinstance(exc, CapexVersionMismatchError):
        return JSONResponse({"error": str(exc), "reload": True}, status_code=409)
    if isinstance(exc, CapexConcurrentEditError):
        return JSONResponse({"error": str(exc)}, status_code=409)
    if isinstance(exc, CapexProtectedGroupError):
        return JSONResponse({"error": str(exc)}, status_code=422)
    if isinstance(exc, CapexRowNotFoundError):
        return JSONResponse({"error": str(exc)}, status_code=404)
    return JSONResponse({"error": str(exc)}, status_code=422)


@capex_router.post("/line/add")
async def capex_line_add(
    request: Request,
    project: str = Form(...),
    parent_category_code: str = Form(...),
    label: str = Form(...),
    amount_keur: float = Form(default=0.0),
    notes: str = Form(default=""),
    workbook_version: str = Form(...),
):
    """Add a custom CAPEX row to an eligible group."""
    user = _get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    try:
        project_record, ws, pis = _load_project_and_ws(user, project)
    except LookupError as exc:
        return JSONResponse({"error": str(exc)}, status_code=404)

    is_htmx = request.headers.get("HX-Request") == "true"

    try:
        add_capex_line(
            project_record=project_record,
            label=label.strip(),
            parent_category_code=parent_category_code,
            amount_keur=amount_keur,
            notes=notes,
            workbook_version=workbook_version,
        )
    except CapexCommandError as exc:
        if is_htmx:
            return _render_capex_sheet(request, project_record, pis, ws, project, field_error=str(exc))
        return _handle_command_error(exc)
    except ValueError as exc:
        if is_htmx:
            return _render_capex_sheet(request, project_record, pis, ws, project, field_error=str(exc))
        return JSONResponse({"error": str(exc)}, status_code=422)

    # Reload workspace state (dirty flag may have changed externally) and re-render.
    from app.persistence.workspace_repository import get_workspace_state
    ws = get_workspace_state(user_id=user.user_id, project_id=project_record.project_id) or ws
    if is_htmx:
        return _render_capex_sheet(request, project_record, pis, ws, project)
    return RedirectResponse(url=f"/v2/workbook?project={project}", status_code=303)


@capex_router.post("/line/update")
async def capex_line_update(
    request: Request,
    project: str = Form(...),
    sub_line_id: str = Form(...),
    label: str = Form(...),
    amount_keur: float = Form(default=0.0),
    notes: str = Form(default=""),
    row_version: str = Form(...),
    workbook_version: str = Form(...),
):
    """Update an existing custom CAPEX row (optimistic-lock on row_version)."""
    user = _get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    try:
        project_record, ws, pis = _load_project_and_ws(user, project)
    except LookupError as exc:
        return JSONResponse({"error": str(exc)}, status_code=404)

    is_htmx = request.headers.get("HX-Request") == "true"

    try:
        update_capex_line(
            project_record=project_record,
            sub_line_id=sub_line_id,
            label=label.strip(),
            amount_keur=amount_keur,
            notes=notes,
            row_version=row_version,
            workbook_version=workbook_version,
        )
    except CapexCommandError as exc:
        if is_htmx:
            err = str(exc)
            if isinstance(exc, CapexConcurrentEditError):
                err = "Row was modified concurrently — values refreshed. Try again."
            return _render_capex_sheet(request, project_record, pis, ws, project, field_error=err)
        return _handle_command_error(exc)
    except ValueError as exc:
        if is_htmx:
            return _render_capex_sheet(request, project_record, pis, ws, project, field_error=str(exc))
        return JSONResponse({"error": str(exc)}, status_code=422)

    from app.persistence.workspace_repository import get_workspace_state
    ws = get_workspace_state(user_id=user.user_id, project_id=project_record.project_id) or ws
    if is_htmx:
        return _render_capex_sheet(request, project_record, pis, ws, project)
    return RedirectResponse(url=f"/v2/workbook?project={project}", status_code=303)


@capex_router.post("/line/deactivate")
async def capex_line_deactivate(
    request: Request,
    project: str = Form(...),
    sub_line_id: str = Form(...),
    row_version: str = Form(...),
    workbook_version: str = Form(...),
):
    """Deactivate (soft-delete) a custom CAPEX row."""
    user = _get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    try:
        project_record, ws, pis = _load_project_and_ws(user, project)
    except LookupError as exc:
        return JSONResponse({"error": str(exc)}, status_code=404)

    is_htmx = request.headers.get("HX-Request") == "true"

    try:
        deactivate_capex_line(
            project_record=project_record,
            sub_line_id=sub_line_id,
            row_version=row_version,
            workbook_version=workbook_version,
        )
    except CapexCommandError as exc:
        if is_htmx:
            err = str(exc)
            if isinstance(exc, CapexConcurrentEditError):
                err = "Row was modified concurrently — values refreshed. Try again."
            return _render_capex_sheet(request, project_record, pis, ws, project, field_error=err)
        return _handle_command_error(exc)

    from app.persistence.workspace_repository import get_workspace_state
    ws = get_workspace_state(user_id=user.user_id, project_id=project_record.project_id) or ws
    if is_htmx:
        return _render_capex_sheet(request, project_record, pis, ws, project)
    return RedirectResponse(url=f"/v2/workbook?project={project}", status_code=303)


@capex_router.post("/line/reorder")
async def capex_line_reorder(
    request: Request,
    project: str = Form(...),
    parent_category_code: str = Form(...),
    ordered_ids: List[str] = Form(default=[]),
    workbook_version: str = Form(...),
):
    """Reorder custom rows within a CAPEX group.

    ``ordered_ids`` is a repeated form field: the first value becomes
    display_order=1, the second display_order=2, etc.
    """
    user = _get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    try:
        project_record, ws, pis = _load_project_and_ws(user, project)
    except LookupError as exc:
        return JSONResponse({"error": str(exc)}, status_code=404)

    is_htmx = request.headers.get("HX-Request") == "true"

    try:
        reorder_capex_lines(
            project_record=project_record,
            parent_category_code=parent_category_code,
            ordered_ids=ordered_ids,
            workbook_version=workbook_version,
        )
    except CapexCommandError as exc:
        if is_htmx:
            return _render_capex_sheet(request, project_record, pis, ws, project, field_error=str(exc))
        return _handle_command_error(exc)

    from app.persistence.workspace_repository import get_workspace_state
    ws = get_workspace_state(user_id=user.user_id, project_id=project_record.project_id) or ws
    if is_htmx:
        return _render_capex_sheet(request, project_record, pis, ws, project)
    return RedirectResponse(url=f"/v2/workbook?project={project}", status_code=303)
