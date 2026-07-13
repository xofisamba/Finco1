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
from app.ui.capex_view_model import build_capex_view_model
from app.ui.inputs_summary import build_inputs_summary
from app.ui.opex_sheet_projection import build_opex_sheet_projection
from app.ui.opex_view_model import build_opex_view_model
from app.ui.project_context import build_project_context_for_record
from app.ui.protected_reference_service import is_protected_reference
from app.workbook.registry import WORKBOOK
from app.workbook.service import WorkbookService
from app.workbook.workbook_identity import assemble_consistent_for_get, assemble_for_workspace
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


def _build_pis_with_composite_identity(ws, project_record, user):
    """Build ProjectInputSet with composite Workbook V2 identity.

    STAB-1B: uses assemble_consistent_for_get to read all four sources
    (workspace snapshot, CAPEX rows, OPEX rows, active scenario) inside a
    single consistent SQLite transaction.  The resulting composite hash is
    injected into the PIS so every form the browser receives carries a
    fully consistent workbook identity token.
    """
    pis = WorkbookService.build_draft_input_set_from_workspace(ws)
    identity = assemble_consistent_for_get(
        user_id=user.user_id,
        project_id=project_record.project_id,
        workbook_version=pis.workbook_version,
    )
    return pis.with_composite_hash(identity.composite_hash)


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


def _build_sheet_fields(sheet_id: str, pis) -> list[dict]:
    """Build the field context list for any registry sheet.

    Returns one dict per FieldSpec ordered by section.order then field.order.
    Values come exclusively from pis.get(field_id).

    binding_label encodes the registry contract:
      "bound"           — BOUND INPUT, editable via the V2 save endpoint
      "partial"         — PARTIAL; partially wired to engine
      "display-only"    — DERIVED_DISPLAY; computed, never user-editable
      "template-locked" — TEMPLATE_LOCKED; frozen at project creation

    Validation metadata (required, min_value, max_value, step, help_text)
    is propagated from FieldSpec so templates can render HTML5 attrs without
    any field-specific knowledge.
    """
    from app.workbook.specs import BindingStatus
    sheet = WORKBOOK.sheet(sheet_id)
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
                "required": fspec.required,
                "min_value": fspec.min_value,
                "max_value": fspec.max_value,
                "step": step,
                "help_text": fspec.description or "",
            })
    return rows


def _build_ps_fields(pis) -> list[dict]:
    """Build project_setup field list — delegates to _build_sheet_fields."""
    return _build_sheet_fields("project_setup", pis)


def _get_inputs_summary(project_record, pis, ws) -> dict:
    """Delegate to the canonical Inputs summary adapter.

    All CAPEX/OPEX aggregation is performed by build_inputs_summary using
    the canonical CapexViewModel and OpexViewModel — the same code paths
    used by the detailed CAPEX and OPEX sheets.  No field lists, no
    formulas, and no ViewModel construction live here.
    """
    return build_inputs_summary(project_record, pis, ws)


def _base_sheet_ctx(request, pis, ws, project_record, project, field_error=""):
    """Shared context dict for both sheet partials."""
    return {
        "request": request,
        "project_code": project,
        "workbook_version": pis.workbook_version,
        "content_hash": pis.content_hash,
        "template_source": pis.template_source,
        "project_editable": not is_protected_reference(project_record),
        "ws_dirty": ws.dirty,
        "has_runtime": bool(ws.last_runtime_snapshot_id),
        "field_error": field_error,
    }


def _render_htmx_sheet(
    request: Request,
    pis,
    ws,
    project_record,
    project: str,
    field_error: str = "",
) -> HTMLResponse:
    """Render the project_setup sheet partial + OOB status banner for HTMX."""
    ctx = _base_sheet_ctx(request, pis, ws, project_record, project, field_error)
    ctx["ps_fields"] = _build_ps_fields(pis)
    sheet_html = _templates.get_template("partials/sheet_project_setup.html").render(ctx)
    banner_html = _templates.get_template("partials/_v2_status_banner.html").render(ctx)
    oob = '<div id="v2-status-banner" hx-swap-oob="true">' + banner_html + "</div>"
    return HTMLResponse(content=sheet_html + "\n" + oob)


def _build_capex_vm_ctx(project_record, pis) -> dict:
    """Build CapexViewModel context for the CAPEX sheet.

    Returns capex_vm, capex_group_to_field, and capex_section_fields.
    All CAPEX financial totals come exclusively from CapexViewModel.
    No field lists, formulas, or aggregation are computed here.
    """
    from app.persistence.capex_sub_lines import CAPEX_CATEGORY_TO_FIELD

    snapshot = pis.to_snapshot()
    project_ctx = build_project_context_for_record(
        project_code=project_record.project_code,
        project_name=project_record.project_name,
        project_type=project_record.project_type,
        project_origin=project_record.project_origin,
        template_source=project_record.template_source,
        baseline_snapshot=snapshot,
    )
    is_user = not (
        project_record.project_origin == "factory_template"
        and (project_record.template_source or "").strip().lower() in ("tuho", "oborovo")
    )

    # Load active user-added sub-lines and inject into CapexViewModel so that
    # group subtotals, hard CAPEX, and total CAPEX reflect custom rows.
    from app.persistence.capex_sub_lines import get_active_sub_lines_for_project
    sub_lines = get_active_sub_lines_for_project(project_record.project_id)
    capex_vm = build_capex_view_model(project_ctx, is_user_project=is_user, sub_lines=sub_lines)

    # Registry field list for capex; keyed by short name for group mapping
    capex_fields = _build_sheet_fields("capex", pis)
    fields_by_key = {f["field_id"].split(".")[-1]: f for f in capex_fields}

    # Mapping: Excel group code → registry field dict.
    # C.08 and C.11 share the same registry field (capex.D.audit_legal).
    # The FIRST occurrence (C.08) gets the editable render_field form.
    # The SECOND occurrence (C.11) gets a read-only alias row that clearly
    # labels it as a shared field so neither group is silently hidden.
    #
    # capex_alias_groups: group code → {"owner": first_group_code, "field": field_dict}
    # Template uses this to render the SHARED FIELD badge on the alias group.
    seen_field_keys: dict[str, str] = {}   # field_key → first group code that owns it
    capex_group_to_field: dict[str, dict | None] = {}
    capex_alias_groups: dict[str, dict] = {}  # alias code → {owner, field}
    for code, field_key in CAPEX_CATEGORY_TO_FIELD.items():
        if field_key in seen_field_keys:
            # This group is an alias — the field is owned by an earlier group
            capex_group_to_field[code] = None
            capex_alias_groups[code] = {
                "owner": seen_field_keys[field_key],
                "field": fields_by_key.get(field_key),
            }
        else:
            capex_group_to_field[code] = fields_by_key.get(field_key)
            seen_field_keys[field_key] = code

    # Mapping: registry section_id → list of field dicts
    capex_section_fields: dict[str, list] = {}
    for f in capex_fields:
        capex_section_fields.setdefault(f["section_id"], []).append(f)

    return {
        "capex_vm": capex_vm,
        "capex_group_to_field": capex_group_to_field,
        "capex_section_fields": capex_section_fields,
        "capex_alias_groups": capex_alias_groups,
    }


def _render_capex_htmx_sheet(
    request: Request,
    pis,
    ws,
    project_record,
    project: str,
    field_error: str = "",
) -> HTMLResponse:
    """Render the CAPEX sheet partial + OOB status banner for HTMX."""
    ctx = _base_sheet_ctx(request, pis, ws, project_record, project, field_error)
    ctx.update(_build_capex_vm_ctx(project_record, pis))
    sheet_html = _templates.get_template("partials/sheet_capex.html").render(ctx)
    banner_html = _templates.get_template("partials/_v2_status_banner.html").render(ctx)
    oob = '<div id="v2-status-banner" hx-swap-oob="true">' + banner_html + "</div>"
    return HTMLResponse(content=sheet_html + "\n" + oob)


def _build_opex_vm_ctx(project_record, pis) -> dict:
    """Build OpexViewModel context for the OPEX sheet.

    Delegates B.01–B.13 canonical structure to build_opex_sheet_projection()
    in app.ui.opex_sheet_projection.  The router owns no OPEX domain mappings.

    Returns opex_vm and opex_sheet_groups (always 13 OpexSheetGroup objects
    in canonical order — present for every project regardless of ViewModel
    group coverage).
    """
    snapshot = pis.to_snapshot()
    project_ctx = build_project_context_for_record(
        project_code=project_record.project_code,
        project_name=project_record.project_name,
        project_type=project_record.project_type,
        project_origin=project_record.project_origin,
        template_source=project_record.template_source,
        baseline_snapshot=snapshot,
    )
    is_user = not (
        project_record.project_origin == "factory_template"
        and (project_record.template_source or "").strip().lower() in ("tuho", "oborovo")
    )
    from app.persistence.opex_sub_lines import get_active_sub_lines_for_project as _get_opex_sub_lines
    opex_sub_lines = _get_opex_sub_lines(project_record.project_id)
    opex_vm = build_opex_view_model(project_ctx, is_user_project=is_user, sub_lines=opex_sub_lines)
    opex_fields = _build_sheet_fields("opex", pis)
    opex_sheet_groups = build_opex_sheet_projection(opex_vm, opex_fields)

    # Summary section fields (e.g. opex.summary.total_y1 PARTIAL) rendered separately
    # at the bottom of the sheet so PARTIAL fields are never silently filtered out.
    opex_summary_fields = [f for f in opex_fields if f["section_id"] == "summary"]

    return {
        "opex_vm": opex_vm,
        "opex_sheet_groups": opex_sheet_groups,
        "opex_summary_fields": opex_summary_fields,
    }


def _render_opex_htmx_sheet(
    request: Request,
    pis,
    ws,
    project_record,
    project: str,
    field_error: str = "",
) -> HTMLResponse:
    """Render the OPEX sheet partial + OOB status banner for HTMX."""
    ctx = _base_sheet_ctx(request, pis, ws, project_record, project, field_error)
    ctx.update(_build_opex_vm_ctx(project_record, pis))
    sheet_html = _templates.get_template("partials/sheet_opex.html").render(ctx)
    banner_html = _templates.get_template("partials/_v2_status_banner.html").render(ctx)
    oob = '<div id="v2-status-banner" hx-swap-oob="true">' + banner_html + "</div>"
    return HTMLResponse(content=sheet_html + "\n" + oob)


def _render_revenue_htmx_sheet(
    request: Request,
    pis,
    ws,
    project_record,
    project: str,
    field_error: str = "",
) -> HTMLResponse:
    """Render the revenue sheet partial + OOB status banner for HTMX."""
    ctx = _base_sheet_ctx(request, pis, ws, project_record, project, field_error)
    ctx["revenue_fields"] = _build_sheet_fields("revenue", pis)
    sheet_html = _templates.get_template("partials/sheet_revenue.html").render(ctx)
    banner_html = _templates.get_template("partials/_v2_status_banner.html").render(ctx)
    oob = '<div id="v2-status-banner" hx-swap-oob="true">' + banner_html + "</div>"
    return HTMLResponse(content=sheet_html + "\n" + oob)


def _thaw(obj):
    """Recursively convert MappingProxyType to plain dict for Jinja2 iteration."""
    from types import MappingProxyType
    if isinstance(obj, MappingProxyType):
        return {k: _thaw(v) for k, v in obj.items()}
    if isinstance(obj, dict):
        return {k: _thaw(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_thaw(i) for i in obj]
    return obj


def _build_debt_ctx(pis, ws) -> dict:
    """Build Senior Debt sheet context: registry fields + RuntimeResult output.

    Operational-period filtering is done here, not in the template.
    ``debt_operational_periods`` contains only periods where is_operation is
    True, in their original order from the schedule.  Construction draw-down
    periods (is_operation=False) are excluded before the template receives the
    list.  When no runtime exists the value is None and the template renders the
    truthful empty state.
    """
    from app.workbook.service import WorkbookService
    rr = WorkbookService.get_runtime_result(ws)
    schedule = _thaw(rr.debt_schedule) if rr and rr.debt_schedule else None
    op_periods = None
    if schedule is not None:
        raw = schedule.get("periods") or []
        op_periods = [p for p in raw if p.get("is_operation")]
    return {
        "debt_fields": _build_sheet_fields("debt", pis),
        "debt_schedule": schedule,
        "debt_operational_periods": op_periods,
        "runtime_summary": _thaw(rr.runtime_summary) if rr and rr.runtime_summary else None,
    }


def _render_debt_htmx_sheet(
    request: Request,
    pis,
    ws,
    project_record,
    project: str,
    field_error: str = "",
) -> HTMLResponse:
    """Render the Senior Debt sheet partial + OOB status banner for HTMX."""
    ctx = _base_sheet_ctx(request, pis, ws, project_record, project, field_error)
    ctx.update(_build_debt_ctx(pis, ws))
    sheet_html = _templates.get_template("partials/sheet_senior_debt.html").render(ctx)
    banner_html = _templates.get_template("partials/_v2_status_banner.html").render(ctx)
    oob = '<div id="v2-status-banner" hx-swap-oob="true">' + banner_html + "</div>"
    return HTMLResponse(content=sheet_html + "\n" + oob)


def _build_tax_ctx(pis, ws) -> dict:
    """Build Tax sheet context from RuntimeResult output.

    Tax assumptions (cit_rate_pct, loss_carryforward_years) are NOT yet
    persisted as Workbook Registry snapshot keys — they come from TaxParams
    set at project creation time.  Section A is therefore all placeholders;
    no BOUND tax fields exist in the registry.

    ``tax_operational_periods`` is filtered server-side (is_operation=True
    only) before the template receives the list, matching the debt-sheet
    pattern.  None means no runtime exists yet.
    """
    from app.workbook.service import WorkbookService
    rr = WorkbookService.get_runtime_result(ws)
    schedule = _thaw(rr.tax_schedule) if rr and rr.tax_schedule else None
    op_periods = None
    if schedule is not None:
        raw = schedule.get("periods") or []
        op_periods = [p for p in raw if p.get("is_operation")]
    return {
        "tax_schedule": schedule,
        "tax_operational_periods": op_periods,
        "runtime_summary": _thaw(rr.runtime_summary) if rr and rr.runtime_summary else None,
    }


def _render_tax_htmx_sheet(
    request: Request,
    pis,
    ws,
    project_record,
    project: str,
    field_error: str = "",
) -> HTMLResponse:
    """Render the Tax sheet partial + OOB status banner for HTMX."""
    ctx = _base_sheet_ctx(request, pis, ws, project_record, project, field_error)
    ctx.update(_build_tax_ctx(pis, ws))
    sheet_html = _templates.get_template("partials/sheet_tax.html").render(ctx)
    banner_html = _templates.get_template("partials/_v2_status_banner.html").render(ctx)
    oob = '<div id="v2-status-banner" hx-swap-oob="true">' + banner_html + "</div>"
    return HTMLResponse(content=sheet_html + "\n" + oob)


def _render_inputs_htmx_sheet(
    request: Request,
    pis,
    ws,
    project_record,
    project: str,
    field_error: str = "",
) -> HTMLResponse:
    """Render the inputs sheet partial + OOB status banner for HTMX."""
    ctx = _base_sheet_ctx(request, pis, ws, project_record, project, field_error)
    ctx.update({
        "technical_fields": _build_sheet_fields("project_setup", pis),
        "revenue_fields": _build_sheet_fields("revenue", pis),
        "capex_fields": _build_sheet_fields("capex", pis),
        "opex_fields": _build_sheet_fields("opex", pis),
        "debt_fields": _build_sheet_fields("debt", pis),
        "inputs_summary": _get_inputs_summary(project_record, pis, ws),
    })
    sheet_html = _templates.get_template("partials/sheet_inputs.html").render(ctx)
    banner_html = _templates.get_template("partials/_v2_status_banner.html").render(ctx)
    oob = '<div id="v2-status-banner" hx-swap-oob="true">' + banner_html + "</div>"
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

    pis = _build_pis_with_composite_identity(ws, project_record, user)
    hydration_script = WorkbookService.runtime_hydration_script(ws)

    project_editable = not is_protected_reference(project_record)

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
        "ps_fields": _build_ps_fields(pis),
        "technical_fields": _build_sheet_fields("project_setup", pis),
        "revenue_fields": _build_sheet_fields("revenue", pis),
        "capex_fields": _build_sheet_fields("capex", pis),
        "opex_fields": _build_sheet_fields("opex", pis),
        "debt_fields": _build_sheet_fields("debt", pis),
        "inputs_summary": _get_inputs_summary(project_record, pis, ws),
        "user": user,
        "project_editable": project_editable,
        "ws_dirty": ws.dirty,
        "has_runtime": bool(ws.last_runtime_snapshot_id),
        "flash_error": flash_error,
        "field_error": "",
    }
    context.update(_build_capex_vm_ctx(project_record, pis))
    context.update(_build_opex_vm_ctx(project_record, pis))
    context.update(_build_debt_ctx(pis, ws))
    context.update(_build_tax_ctx(pis, ws))
    return _templates.TemplateResponse(request=request, name="workbook.html", context=context)


@router.post("/workbook/update")
async def v2_workbook_update(
    request: Request,
    field_id: str = Form(...),
    value: Optional[str] = Form(default=""),
    project: str = Form(...),
    workbook_version: str = Form(...),
    content_hash: str = Form(...),
    sheet_id: str = Form(default="project_setup"),
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

    def _htmx_error(pis_for_render, field_error: str) -> HTMLResponse:
        if sheet_id == "inputs":
            return _render_inputs_htmx_sheet(
                request, pis_for_render, ws, project_record, project,
                field_error=field_error,
            )
        if sheet_id == "revenue":
            return _render_revenue_htmx_sheet(
                request, pis_for_render, ws, project_record, project,
                field_error=field_error,
            )
        if sheet_id == "capex":
            return _render_capex_htmx_sheet(
                request, pis_for_render, ws, project_record, project,
                field_error=field_error,
            )
        if sheet_id == "opex":
            return _render_opex_htmx_sheet(
                request, pis_for_render, ws, project_record, project,
                field_error=field_error,
            )
        if sheet_id == "debt":
            return _render_debt_htmx_sheet(
                request, pis_for_render, ws, project_record, project,
                field_error=field_error,
            )
        if sheet_id == "tax":
            return _render_tax_htmx_sheet(
                request, pis_for_render, ws, project_record, project,
                field_error=field_error,
            )
        return _render_htmx_sheet(
            request, pis_for_render, ws, project_record, project,
            field_error=field_error,
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
        if is_htmx:
            pis = _build_pis_with_composite_identity(ws, project_record, user)
            return _htmx_error(pis, str(exc))
        return JSONResponse({"error": str(exc)}, status_code=409)
    except StaleContentError as exc:
        if is_htmx:
            pis = _build_pis_with_composite_identity(ws, project_record, user)
            return _htmx_error(
                pis,
                "Draft changed since page loaded — values refreshed. "
                "Please try your edit again.",
            )
        return _redirect_with_error(str(exc))
    except VersionMismatchError as exc:
        return JSONResponse({"error": str(exc), "reload": True}, status_code=409)
    except (UnknownFieldError, NonEditableFieldError) as exc:
        return JSONResponse({"error": str(exc)}, status_code=422)
    except FieldValidationError as exc:
        if is_htmx:
            pis = _build_pis_with_composite_identity(ws, project_record, user)
            return _htmx_error(pis, str(exc))
        return _redirect_with_error(str(exc))

    # Success path — reload workspace and assemble composite identity consistently
    # so the re-rendered sheet carries a hash over the full post-mutation state.
    updated_ws_after = get_workspace_state(
        user_id=user.user_id, project_id=project_record.project_id
    ) or ws
    try:
        updated_identity = assemble_consistent_for_get(
            user_id=user.user_id,
            project_id=project_record.project_id,
            workbook_version=updated_pis.workbook_version,
        )
        updated_pis = updated_pis.with_composite_hash(updated_identity.composite_hash)
    except Exception:
        pass  # scalar hash already set by v2_atomic_draft_update; best-effort only

    if is_htmx:
        if sheet_id == "inputs":
            return _render_inputs_htmx_sheet(
                request, updated_pis, updated_ws_after, project_record, project,
            )
        if sheet_id == "revenue":
            return _render_revenue_htmx_sheet(
                request, updated_pis, updated_ws_after, project_record, project,
            )
        if sheet_id == "capex":
            return _render_capex_htmx_sheet(
                request, updated_pis, updated_ws_after, project_record, project,
            )
        if sheet_id == "opex":
            return _render_opex_htmx_sheet(
                request, updated_pis, updated_ws_after, project_record, project,
            )
        if sheet_id == "debt":
            return _render_debt_htmx_sheet(
                request, updated_pis, updated_ws_after, project_record, project,
            )
        if sheet_id == "tax":
            return _render_tax_htmx_sheet(
                request, updated_pis, updated_ws_after, project_record, project,
            )
        return _render_htmx_sheet(
            request, updated_pis, updated_ws_after, project_record, project,
        )

    return RedirectResponse(
        url=f"/v2/workbook?project={project}",
        status_code=303,
    )
