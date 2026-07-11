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

    Protected reference projects (TUHO/Oborovo factory_template origin)
    render in read-only mode with a working-copy CTA.  All other projects
    show live edit controls for the six BOUND Project Setup fields.

POST /v2/workbook/update
    Canonical V2 field edit endpoint.  Accepts a single field_id + value
    plus optimistic-concurrency token (content_hash).  Full pipeline:

      semantic field_id
      → WorkbookUpdateService.validate_field_update()
      → ProjectInputSet.with_value()
      → v2_atomic_draft_update() (BEGIN EXCLUSIVE)
      → HTMX partial response OR 303 redirect

    No legacy snapshot keys may appear in the request body.
    Protected references (TUHO/Oborovo) are rejected with 409.
    Stale content_hash is rejected with 409.

HTMX behaviour
--------------
If the POST carries ``HX-Request: true``:
  - success: returns the re-rendered #v2-sheet-project-setup partial
    (all forms carry the new content_hash) plus an OOB status banner.
  - validation / stale / version error: returns the same partial with
    the fresh state and an error message in the OOB status banner.
Non-HTMX fallback: 303 redirect on success; redirect with ?v2_err=… on error.

Scope constraints
-----------------
- No engine calls, no formula logic, no parity changes.
- No legacy ``_collect_form_snapshot`` / ``_strip_empty_fields`` helpers.
- No reuse of ``build_input_set_from_workspace`` (removed in PR 4).
"""
from __future__ import annotations

import os
import urllib.parse
from typing import Optional

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.auth import COOKIE_NAME, decode_session_token
from app.ui.protected_reference_service import is_protected_reference
from app.workbook.registry import WORKBOOK
from app.workbook.service import WorkbookService
from app.workbook.update_service import (
    FieldValidationError,
    NonEditableFieldError,
    ProtectedReferenceError,
    StaleContentError,
    UnknownFieldError,
    VersionMismatchError,
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

    binding_label encodes the registry contract for display:
      "bound"           — BOUND INPUT, editable via the V2 save endpoint
      "partial"         — PARTIAL; not yet fully wired to engine
      "display-only"    — DERIVED_DISPLAY; computed, never user-editable
      "template-locked" — TEMPLATE_LOCKED; frozen at project creation

    Validation metadata (required, min_value, max_value, step, help_text)
    is propagated from the FieldSpec so the macro can render HTML5 attrs
    without hard-coding any field-specific knowledge.
    """
    from app.workbook.specs import BindingStatus
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

            field_type = fspec.field_type.value

            # Derive HTML step from registry decimals + field type.
            # Integer-typed fields always use step=1 regardless of decimals.
            if field_type in ("months", "years", "int"):
                step = "1"
            elif fspec.decimals is not None:
                if fspec.decimals == 0:
                    step = "1"
                else:
                    step = str(round(10 ** (-fspec.decimals), fspec.decimals))
            else:
                step = "any"

            value = pis.get(fspec.field_id)
            rows.append({
                "field_id": fspec.field_id,
                "label": fspec.label,
                "unit": fspec.unit,
                "field_type": field_type,
                "binding_label": binding_label,
                "options": list(fspec.options),
                "section_id": section.section_id,
                "section_label": section.label,
                "value": value,
                # HTML5 validation metadata from registry
                "required": fspec.required,
                "min_value": fspec.min_value,
                "max_value": fspec.max_value,
                "step": step,
                "help_text": fspec.description or "",
            })
    return rows


def _render_htmx_sheet(
    request: Request,
    pis,
    ws,
    project_record,
    project: str,
    field_error: str = "",
) -> HTMLResponse:
    """Render the sheet partial + OOB status banner for an HTMX response.

    Used by the POST handler on both success and error paths so every
    HTMX response returns fresh state with the current content_hash.
    """

    project_editable = not is_protected_reference(project_record)
    ps_fields = _build_ps_fields(pis)
    ctx = {
        "request": request,
        "ps_fields": ps_fields,
        "project_code": project,
        "workbook_version": pis.workbook_version,
        "content_hash": pis.content_hash,
        "template_source": pis.template_source,
        "project_editable": project_editable,
        "ws_dirty": ws.dirty,
        "has_runtime": bool(ws.last_runtime_snapshot_id),
        "field_error": field_error,
    }
    sheet_html = _templates.get_template(
        "partials/sheet_project_setup.html"
    ).render(ctx)
    banner_html = _templates.get_template(
        "partials/_v2_status_banner.html"
    ).render(ctx)
    oob = (
        '<div id="v2-status-banner" hx-swap-oob="true">'
        + banner_html
        + "</div>"
    )
    return HTMLResponse(content=sheet_html + "\n" + oob)


@router.get("/workbook", response_class=HTMLResponse)
async def v2_workbook(request: Request, project: Optional[str] = None):
    """Workbook V2 shell page.

    Renders the V2 template skeleton and injects a sessionStorage hydration
    script from the persisted RuntimeResult (if one exists), so schedule
    data is available to the page on load without a model re-run.

    Protected reference projects (TUHO/Oborovo factory_template origin)
    render all fields read-only with a working-copy CTA.

    Query parameters
    ----------------
    project : str, optional
        Project code.  When absent, redirects to the project home.
    v2_err : str, optional
        URL-encoded error message from a failed non-HTMX POST.  Shown as
        a flash error in the status banner.
    """
    user = _get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    if not project:
        return RedirectResponse(url="/", status_code=302)

    from app.persistence.projects_repository import get_project_record
    from app.persistence.workspace_repository import get_workspace_state

    project_record = get_project_record(user_id=user.user_id, project_code=project)
    if project_record is None:
        return RedirectResponse(url="/", status_code=302)

    ws = get_workspace_state(user_id=user.user_id, project_id=project_record.project_id)
    if ws is None:
        return RedirectResponse(url="/", status_code=302)

    pis = WorkbookService.build_draft_input_set_from_workspace(ws)
    hydration_script = WorkbookService.runtime_hydration_script(ws)
    ps_fields = _build_ps_fields(pis)

    project_editable = not is_protected_reference(project_record)

    # Decode flash error from a failed non-HTMX POST.
    flash_error = ""
    raw_err = request.query_params.get("v2_err", "")
    if raw_err:
        try:
            flash_error = urllib.parse.unquote_plus(raw_err)[:500]
        except Exception:
            pass

    context = {
        "project_code": project,
        "workbook_version": pis.workbook_version,
        "content_hash": pis.content_hash,
        "template_source": pis.template_source,
        "hydration_script": hydration_script,
        "ps_fields": ps_fields,
        "user": user,
        "project_editable": project_editable,
        "ws_dirty": ws.dirty,
        "has_runtime": bool(ws.last_runtime_snapshot_id),
        "flash_error": flash_error,
        "field_error": "",
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

    HTMX (HX-Request: true):
        success → re-rendered sheet partial + OOB status banner (HTTP 200)
        error   → re-rendered sheet partial with error in status banner (HTTP 200)
    Non-HTMX:
        success → 303 redirect to GET /v2/workbook?project=<project>
        error   → 303 redirect with ?v2_err=<encoded message>
    """
    user = _get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    is_htmx = request.headers.get("HX-Request") == "true"

    from app.persistence.projects_repository import get_project_record
    from app.persistence.workspace_repository import get_workspace_state

    project_record = get_project_record(user_id=user.user_id, project_code=project)
    if project_record is None:
        return JSONResponse({"error": f"Project {project!r} not found."}, status_code=404)

    ws = get_workspace_state(user_id=user.user_id, project_id=project_record.project_id)
    if ws is None:
        return JSONResponse({"error": "Workspace not found."}, status_code=404)

    def _redirect_with_error(message: str) -> RedirectResponse:
        """Non-HTMX error: redirect to GET with flash message in ?v2_err."""
        err_param = urllib.parse.quote_plus(message)
        return RedirectResponse(
            url=f"/v2/workbook?project={project}&v2_err={err_param}",
            status_code=303,
        )

    try:
        updated_pis = WorkbookUpdateService.apply_draft_update(
            ws=ws,
            field_id=field_id,
            raw_value=value or "",
            content_hash=content_hash,
            workbook_version=workbook_version,
            project_record=project_record,
        )
    except ProtectedReferenceError as exc:
        # Defense-in-depth: UI already hides forms for protected refs.
        if is_htmx:
            pis = WorkbookService.build_draft_input_set_from_workspace(ws)
            return _render_htmx_sheet(
                request, pis, ws, project_record, project,
                field_error=str(exc),
            )
        return JSONResponse({"error": str(exc)}, status_code=409)
    except StaleContentError as exc:
        # Re-render with fresh state; user can retry.
        if is_htmx:
            pis = WorkbookService.build_draft_input_set_from_workspace(ws)
            return _render_htmx_sheet(
                request, pis, ws, project_record, project,
                field_error=(
                    "Draft changed since page loaded — values refreshed. "
                    "Please try your edit again."
                ),
            )
        return _redirect_with_error(str(exc))
    except VersionMismatchError as exc:
        # Always return 409 JSON (HTMX or not) — the browser must reload.
        return JSONResponse({"error": str(exc), "reload": True}, status_code=409)
    except (UnknownFieldError, NonEditableFieldError) as exc:
        # API-level errors: 422 JSON (not user-facing validation).
        return JSONResponse({"error": str(exc)}, status_code=422)
    except FieldValidationError as exc:
        if is_htmx:
            pis = WorkbookService.build_draft_input_set_from_workspace(ws)
            return _render_htmx_sheet(
                request, pis, ws, project_record, project,
                field_error=str(exc),
            )
        return _redirect_with_error(str(exc))

    # Success path.
    if is_htmx:
        # Re-read workspace so ws.dirty reflects the committed write.
        updated_ws = get_workspace_state(
            user_id=user.user_id, project_id=project_record.project_id
        )
        return _render_htmx_sheet(
            request, updated_pis, updated_ws or ws, project_record, project,
        )

    return RedirectResponse(
        url=f"/v2/workbook?project={project}",
        status_code=303,
    )
