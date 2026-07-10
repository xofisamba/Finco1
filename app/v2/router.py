"""
app.v2.router — Workbook V2 feature-flagged routes.

Mounted at ``/v2`` in main_web.py when ``FINCO_WORKBOOK_V2`` is truthy.
All routes require the same authentication as the legacy stack.

Authentication
--------------
Uses the canonical ``get_current_user`` helper from ``app.auth`` (cookie →
``decode_session_token`` → ``SessionData``).  The authenticated user is a
``SessionData`` instance; its ``user_id`` attribute is used to scope DB
lookups, matching the legacy convention in all other routes.

Current routes
--------------
GET /v2/workbook
    Single-sheet workbook shell.  Accepts the same ``?project=`` query
    parameter as the legacy ``GET /``.  Returns a minimal HTML page built
    from the V2 template skeleton.  Schedule data is hydrated via the
    RuntimeResult sessionStorage script so the page loads without a model
    re-run.

    The Project Setup sheet (identity + technical sections) is rendered
    as a read-only projection using values sourced exclusively from
    ProjectInputSet, keyed by semantic field_id.

POST /v2/workbook/update
    Canonical V2 field edit endpoint.  Accepts a single field_id + value
    plus optimistic-concurrency token (content_hash).  Full pipeline:

      semantic field_id
      → WorkbookUpdateService.validate_field_update()
      → ProjectInputSet.with_value()
      → save_workspace_state(draft_snapshot=…)
      → redirect to GET /v2/workbook?project=…

    No legacy snapshot keys may appear in the request body.
    Protected references (TUHO/Oborovo) are rejected with 409.
    Stale content_hash is rejected with 409.

Scope constraints
-----------------
- No engine calls, no formula logic, no parity changes.
- No legacy ``_collect_form_snapshot`` / ``_strip_empty_fields`` helpers.
- No reuse of ``build_input_set_from_workspace`` (removed in PR 4).
"""
from __future__ import annotations

import os
from typing import Optional

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.auth import COOKIE_NAME, decode_session_token
from app.workbook.registry import WORKBOOK
from app.workbook.service import WorkbookService
from app.workbook.update_service import (
    FieldValidationError,
    NonEditableFieldError,
    ProtectedReferenceError,
    StaleContentError,
    UnknownFieldError,
    WorkbookUpdateService,
)

router = APIRouter()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "app", "templates", "v2"))


def _get_current_user(request: Request):
    """Return the authenticated SessionData, or None.

    Uses the canonical app.auth mechanism: reads the finco_session cookie,
    decodes and validates the signed token, and returns a SessionData object
    (with .user_id and .username attributes) — the same shape that all legacy
    routes receive from get_current_user() in main_web.py.
    """
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return None
    return decode_session_token(token)


def _build_ps_fields(pis) -> list[dict]:
    """Build the project_setup field context list for the template.

    Returns one dict per FieldSpec in the project_setup sheet, ordered by
    section then field.order.  Values come exclusively from pis.get(field_id)
    — never from snapshot keys or any other source.

    All fields are rendered read-only in this PR (read-only projection).
    Editing arrives in a subsequent PR once a V2 draft-update endpoint and
    round-trip persistence tests exist.

    binding_label encodes the registry contract for display:
      "bound"           — BOUND INPUT, will be editable once save endpoint exists
      "partial"         — PARTIAL; not yet fully wired to engine
      "display-only"    — DERIVED_DISPLAY; computed, never user-editable
      "template-locked" — TEMPLATE_LOCKED; frozen at project creation
    """
    from app.workbook.specs import BindingStatus, FieldKind, SourceOfTruth
    sheet = WORKBOOK.sheet("project_setup")
    rows: list[dict] = []
    for section in sorted(sheet.sections, key=lambda s: s.order):
        for fspec in sorted(section.fields, key=lambda f: f.order):
            bs = fspec.binding_status
            if bs == BindingStatus.DISPLAY_ONLY:
                binding_label = "display-only"
            elif bs == BindingStatus.TEMPLATE_LOCKED:
                binding_label = "template-locked"
            elif bs == BindingStatus.PARTIAL:
                binding_label = "partial"
            else:
                binding_label = "bound"

            value = pis.get(fspec.field_id)
            rows.append({
                "field_id": fspec.field_id,
                "label": fspec.label,
                "unit": fspec.unit,
                "field_type": fspec.field_type.value,
                "binding_label": binding_label,
                "options": list(fspec.options),
                "section_id": section.section_id,
                "section_label": section.label,
                "value": value,
            })
    return rows


@router.get("/workbook", response_class=HTMLResponse)
async def v2_workbook(request: Request, project: Optional[str] = None):
    """Workbook V2 shell page.

    Renders the V2 template skeleton and injects a sessionStorage hydration
    script from the persisted RuntimeResult (if one exists), so schedule
    data is available to the page on load without a model re-run.

    Query parameters
    ----------------
    project : str, optional
        Project code (e.g. ``tuho``, ``oborovo``).  When absent, redirects
        to the project home.
    """
    user = _get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    if not project:
        return RedirectResponse(url="/", status_code=302)

    # Resolve project record by slug → then workspace by UUID project_id.
    # project_code (slug) and project_id (UUID) are distinct; passing the slug
    # directly to get_workspace_state would always miss.
    from app.persistence.projects_repository import get_project_record
    from app.persistence.workspace_repository import get_workspace_state

    project_record = get_project_record(user_id=user.user_id, project_code=project)
    if project_record is None:
        return RedirectResponse(url="/", status_code=302)

    ws = get_workspace_state(user_id=user.user_id, project_id=project_record.project_id)
    if ws is None:
        return RedirectResponse(url="/", status_code=302)

    # Build the draft input set — UI display path, not a run boundary.
    pis = WorkbookService.build_draft_input_set_from_workspace(ws)

    # Build the sessionStorage hydration script from persisted RuntimeResult.
    # Empty string when no run has been persisted; safe to embed directly.
    hydration_script = WorkbookService.runtime_hydration_script(ws)

    # Build project_setup sheet context — values from ProjectInputSet only.
    ps_fields = _build_ps_fields(pis)

    context = {
        "project_code": project,
        "workbook_version": pis.workbook_version,
        "content_hash": pis.content_hash,
        "template_source": pis.template_source,
        "hydration_script": hydration_script,
        "ps_fields": ps_fields,
        "user": user,
    }
    return _templates.TemplateResponse(request=request, name="workbook.html", context=context)


@router.post("/workbook/update")
async def v2_workbook_update(
    request: Request,
    field_id: str = Form(...),
    value: Optional[str] = Form(default=""),
    project: str = Form(...),
    workbook_version: str = Form(...),
    content_hash: str = Form(...),
):
    """V2 field edit endpoint — canonical edit pipeline.

    Accepts a single field update identified by semantic field_id (never a
    legacy snapshot key).  Applies optimistic concurrency via content_hash.

    On success: redirects to GET /v2/workbook?project=<project>.
    On 409 (stale / protected): JSON error body with "error" key.
    On 422 (unknown field / validation error): JSON error body.
    """
    user = _get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    from app.persistence.projects_repository import get_project_record
    from app.persistence.workspace_repository import get_workspace_state

    project_record = get_project_record(user_id=user.user_id, project_code=project)
    if project_record is None:
        return JSONResponse({"error": f"Project {project!r} not found."}, status_code=404)

    ws = get_workspace_state(user_id=user.user_id, project_id=project_record.project_id)
    if ws is None:
        return JSONResponse({"error": "Workspace not found."}, status_code=404)

    try:
        updated_pis = WorkbookUpdateService.apply_draft_update(
            ws=ws,
            field_id=field_id,
            raw_value=value or "",
            content_hash=content_hash,
            project_record=project_record,
        )
    except ProtectedReferenceError as exc:
        return JSONResponse({"error": str(exc)}, status_code=409)
    except StaleContentError as exc:
        return JSONResponse({"error": str(exc)}, status_code=409)
    except (UnknownFieldError, NonEditableFieldError) as exc:
        return JSONResponse({"error": str(exc)}, status_code=422)
    except FieldValidationError as exc:
        return JSONResponse({"error": str(exc)}, status_code=422)

    return RedirectResponse(
        url=f"/v2/workbook?project={project}",
        status_code=303,
    )
