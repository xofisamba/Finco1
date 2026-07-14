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

import datetime
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


def _fmt_runtime_at(ts: str) -> str:
    """Format an ISO timestamp into a human-readable string for the toolbar."""
    if not ts:
        return ""
    try:
        dt = datetime.datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return dt.strftime("%-d %b %Y, %H:%M")
    except Exception:
        return ts


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
        "last_runtime_at": _fmt_runtime_at(getattr(ws, "last_runtime_at", None) or ""),
        "field_error": field_error,
    }


def _build_run_controls_oob(ctx: dict) -> str:
    """Return OOB HTML to refresh #v2-run-controls with the current composite hash."""
    run_controls_html = _templates.get_template("partials/_v2_run_controls.html").render(ctx)
    return '<div id="v2-run-controls" hx-swap-oob="true">' + run_controls_html + "</div>"


def _build_toolbar_state_oob(ctx: dict) -> str:
    """Return OOB HTML to refresh the toolbar runtime state chip."""
    toolbar_html = _templates.get_template("partials/_v2_toolbar_state.html").render(ctx)
    return '<div id="v2-toolbar-runtime-state" hx-swap-oob="true">' + toolbar_html + "</div>"


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
    if not field_error:
        oob += "\n" + _build_run_controls_oob(ctx)
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
    if not field_error:
        oob += "\n" + _build_run_controls_oob(ctx)
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
    if not field_error:
        oob += "\n" + _build_run_controls_oob(ctx)
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
    if not field_error:
        oob += "\n" + _build_run_controls_oob(ctx)
    return HTMLResponse(content=sheet_html + "\n" + oob)


def _thaw(obj):
    """Recursively convert MappingProxyType to plain dict for Jinja2 iteration."""
    from app.workbook.runtime_projection import thaw_runtime_payload
    return thaw_runtime_payload(obj)


def _build_debt_ctx(pis, ws, projection=None) -> dict:
    """Build Senior Debt sheet context: registry fields + RuntimeResult output.

    When a pre-built WorkbookRuntimeProjection bundle is supplied (GET handler),
    it is reused so that only one get_runtime_result call is made per request.
    When called standalone (HTMX sheet re-render), the bundle is built here.
    """
    from app.workbook.runtime_projection import build_runtime_projection_bundle
    from app.workbook.service import WorkbookService
    if projection is None:
        rr = WorkbookService.get_runtime_result(ws)
        from app.workbook.runtime_projection import build_runtime_projection_bundle
        projection = build_runtime_projection_bundle(rr, ws.dirty)
    d = projection.debt
    return {
        "debt_fields": _build_sheet_fields("debt", pis),
        "debt_state": d.state.value,
        "debt_schedule": d.schedule,
        "debt_operational_periods": d.operational_periods,
        "runtime_summary": d.runtime_summary,
    }


def _render_debt_htmx_sheet(
    request: Request,
    pis,
    ws,
    project_record,
    project: str,
    field_error: str = "",
    projection=None,
) -> HTMLResponse:
    """Render the Senior Debt sheet partial + OOB status banner for HTMX."""
    ctx = _base_sheet_ctx(request, pis, ws, project_record, project, field_error)
    ctx.update(_build_debt_ctx(pis, ws, projection=projection))
    sheet_html = _templates.get_template("partials/sheet_senior_debt.html").render(ctx)
    banner_html = _templates.get_template("partials/_v2_status_banner.html").render(ctx)
    oob = '<div id="v2-status-banner" hx-swap-oob="true">' + banner_html + "</div>"
    if not field_error:
        oob += "\n" + _build_run_controls_oob(ctx)
    return HTMLResponse(content=sheet_html + "\n" + oob)


def _build_tax_ctx(pis, ws, projection=None) -> dict:
    """Build Tax sheet context: registry fields + RuntimeResult output.

    ``tax_fields`` contains the two BOUND Tax registry fields rendered in
    Section A via the render_field macro (cit_rate_pct, loss_carryforward_years).

    Option B hydration fills None values from pis.to_projectinputs().tax
    without calling the engine or writing to the snapshot.

    When a pre-built WorkbookRuntimeProjection bundle is supplied (GET handler),
    it is reused so that only one get_runtime_result call is made per request.
    """
    from app.workbook.runtime_projection import build_runtime_projection_bundle
    from app.workbook.service import WorkbookService
    if projection is None:
        rr = WorkbookService.get_runtime_result(ws)
        projection = build_runtime_projection_bundle(rr, ws.dirty)
    t = projection.tax
    raw_fields = _build_sheet_fields("tax", pis)

    # Option B — effective-value projection.
    # When a Tax snapshot key is absent, pis.get(field_id) returns None even
    # though the engine would use a concrete factory default.  Project the
    # canonical effective value from pis.to_projectinputs().tax so the first
    # load shows real defaults rather than empty fields.
    # This path never calls the engine, never hard-codes a rate, never
    # writes to the snapshot, and never marks the workspace dirty.
    if any(f["value"] is None for f in raw_fields):
        effective_tax = pis.to_projectinputs().tax
        _TAX_FIELD_MAP = {
            "tax.assumptions.cit_rate_pct": lambda tx: round(tx.corporate_rate * 100, 10),
            "tax.assumptions.loss_carryforward_years": lambda tx: tx.loss_carryforward_years,
        }
        for f in raw_fields:
            if f["value"] is None:
                proj_fn = _TAX_FIELD_MAP.get(f["field_id"])
                if proj_fn is not None:
                    f["value"] = proj_fn(effective_tax)

    return {
        "tax_fields": raw_fields,
        "tax_state": t.state.value,
        "tax_schedule": t.schedule,
        "tax_operational_periods": t.operational_periods,
        "runtime_summary": t.runtime_summary,
    }


def _render_tax_htmx_sheet(
    request: Request,
    pis,
    ws,
    project_record,
    project: str,
    field_error: str = "",
    projection=None,
) -> HTMLResponse:
    """Render the Tax sheet partial + OOB status banner for HTMX."""
    ctx = _base_sheet_ctx(request, pis, ws, project_record, project, field_error)
    ctx.update(_build_tax_ctx(pis, ws, projection=projection))
    sheet_html = _templates.get_template("partials/sheet_tax.html").render(ctx)
    banner_html = _templates.get_template("partials/_v2_status_banner.html").render(ctx)
    oob = '<div id="v2-status-banner" hx-swap-oob="true">' + banner_html + "</div>"
    if not field_error:
        oob += "\n" + _build_run_controls_oob(ctx)
    return HTMLResponse(content=sheet_html + "\n" + oob)


# ── Legacy re-exports kept for backward compatibility with existing tests ──── #
# The canonical implementations live in app.workbook.runtime_projection.
from app.workbook.runtime_projection import (  # noqa: E402
    FS_PNL_ROW_DEFS    as _FS_PNL_ROW_DEFS,
    FS_PF_CF_ROW_DEFS  as _FS_PF_CF_ROW_DEFS,
    FS_BS_ROW_DEFS     as _FS_BS_ROW_DEFS,
    project_rows       as _fs_project_rows,
    project_period_labels as _fs_period_labels,
    fs_classify_statement as _fs_classify,
)

_FS_STATE_NOT_RUN        = "NOT_RUN"
_FS_STATE_CLEAN          = "CLEAN"
_FS_STATE_STALE          = "STALE"
_FS_STATE_FS_UNAVAILABLE = "FS_UNAVAILABLE"


def _build_financial_statements_ctx(pis, ws, projection=None) -> dict:
    """Build Financial Statements sheet context from persisted RuntimeResult.

    When a pre-built WorkbookRuntimeProjection bundle is supplied (GET handler),
    it is reused so that only one get_runtime_result call is made per request.
    """
    from app.workbook.runtime_projection import build_runtime_projection_bundle
    from app.workbook.service import WorkbookService
    if projection is None:
        rr = WorkbookService.get_runtime_result(ws)
        projection = build_runtime_projection_bundle(rr, ws.dirty)
    f = projection.fs
    # Map the FS UNAVAILABLE state to the legacy template key for backward compat
    fs_state = f.state.value if f.state.value != "UNAVAILABLE" else "FS_UNAVAILABLE"
    return {
        "fs_state": fs_state,
        "fs_available": f.fs_available,
        "fs_pnl_rows": f.pnl_rows,
        "fs_bs_rows": f.bs_rows,
        "fs_pf_cf_rows": f.pf_cf_rows,
        "fs_pnl_period_labels": f.pnl_period_labels,
        "fs_bs_period_labels": f.bs_period_labels,
        "fs_pf_cf_period_labels": f.pf_cf_period_labels,
        "fs_pnl_classification": f.pnl_classification,
        "fs_bs_classification": f.bs_classification,
        "fs_pf_cf_classification": f.pf_cf_classification,
        "runtime_summary": f.runtime_summary,
    }


def _build_all_oob(ws) -> str:
    """Build combined OOB for debt, tax, and fs runtime bars after a mutation.

    Called from every HTMX success response that does NOT re-render one of
    the three runtime-bar sheets directly.  Must NOT be appended on
    validation-error responses — those never mutate state.
    """
    from app.workbook.runtime_projection import build_runtime_projection_bundle
    from app.v2.runtime_projection_views import build_all_runtime_bar_oob
    from app.workbook.service import WorkbookService
    rr = WorkbookService.get_runtime_result(ws)
    projection = build_runtime_projection_bundle(rr, ws.dirty)
    return build_all_runtime_bar_oob(projection)


# Legacy alias so tests that imported the old helper continue to pass.
def _build_fs_runtime_bar_oob(ws) -> str:
    from app.workbook.runtime_projection import build_runtime_projection_bundle
    from app.v2.runtime_projection_views import build_fs_bar_oob
    from app.workbook.service import WorkbookService
    rr = WorkbookService.get_runtime_result(ws)
    projection = build_runtime_projection_bundle(rr, ws.dirty)
    return build_fs_bar_oob(projection)


def _render_financial_statements_htmx_sheet(
    request: Request,
    pis,
    ws,
    project_record,
    project: str,
    field_error: str = "",
) -> HTMLResponse:
    """Render the Financial Statements sheet partial + OOB status banner for HTMX."""
    ctx = _base_sheet_ctx(request, pis, ws, project_record, project, field_error)
    ctx.update(_build_financial_statements_ctx(pis, ws))
    sheet_html = _templates.get_template("partials/sheet_financial_statements.html").render(ctx)
    banner_html = _templates.get_template("partials/_v2_status_banner.html").render(ctx)
    oob = '<div id="v2-status-banner" hx-swap-oob="true">' + banner_html + "</div>"
    if not field_error:
        oob += "\n" + _build_run_controls_oob(ctx)
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
    if not field_error:
        oob += "\n" + _build_run_controls_oob(ctx)
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
        "project_name": project_record.project_name or project,
        "project_type": (project_record.project_type or "").capitalize(),
        "active_scenario_name": ws.active_scenario_name or "",
        "last_runtime_at": _fmt_runtime_at(getattr(ws, "last_runtime_at", None) or ""),
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
    # Build projection bundle once; pass it to all three sheet context builders.
    from app.workbook.runtime_projection import build_runtime_projection_bundle
    _rr = WorkbookService.get_runtime_result(ws)
    _projection = build_runtime_projection_bundle(_rr, ws.dirty)
    context.update(_build_debt_ctx(pis, ws, projection=_projection))
    context.update(_build_tax_ctx(pis, ws, projection=_projection))
    context.update(_build_financial_statements_ctx(pis, ws, projection=_projection))
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
        if sheet_id == "financial_statements":
            return _render_financial_statements_htmx_sheet(
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
        # Dispatch to the correct sheet renderer.
        if sheet_id == "inputs":
            resp = _render_inputs_htmx_sheet(
                request, updated_pis, updated_ws_after, project_record, project,
            )
        elif sheet_id == "revenue":
            resp = _render_revenue_htmx_sheet(
                request, updated_pis, updated_ws_after, project_record, project,
            )
        elif sheet_id == "capex":
            resp = _render_capex_htmx_sheet(
                request, updated_pis, updated_ws_after, project_record, project,
            )
        elif sheet_id == "opex":
            resp = _render_opex_htmx_sheet(
                request, updated_pis, updated_ws_after, project_record, project,
            )
        elif sheet_id == "debt":
            # Build projection once — pass to both sheet renderer and OOB bars.
            from app.workbook.runtime_projection import build_runtime_projection_bundle
            from app.v2.runtime_projection_views import build_all_runtime_bar_oob
            from app.workbook.service import WorkbookService
            _rr = WorkbookService.get_runtime_result(updated_ws_after)
            _proj = build_runtime_projection_bundle(_rr, updated_ws_after.dirty)
            resp = _render_debt_htmx_sheet(
                request, updated_pis, updated_ws_after, project_record, project,
                projection=_proj,
            )
            return HTMLResponse(content=resp.body.decode() + "\n" + build_all_runtime_bar_oob(_proj))
        elif sheet_id == "tax":
            from app.workbook.runtime_projection import build_runtime_projection_bundle
            from app.v2.runtime_projection_views import build_all_runtime_bar_oob
            from app.workbook.service import WorkbookService
            _rr = WorkbookService.get_runtime_result(updated_ws_after)
            _proj = build_runtime_projection_bundle(_rr, updated_ws_after.dirty)
            resp = _render_tax_htmx_sheet(
                request, updated_pis, updated_ws_after, project_record, project,
                projection=_proj,
            )
            return HTMLResponse(content=resp.body.decode() + "\n" + build_all_runtime_bar_oob(_proj))
        elif sheet_id == "financial_statements":
            # Full sheet re-render already contains #fs-runtime-bar; no OOB needed.
            return _render_financial_statements_htmx_sheet(
                request, updated_pis, updated_ws_after, project_record, project,
            )
        else:
            resp = _render_htmx_sheet(
                request, updated_pis, updated_ws_after, project_record, project,
            )
        # Append OOB refresh of all three runtime bars so that editing any
        # sheet immediately reflects the dirty/clean state on Debt, Tax, and
        # Financial Statements without a full page reload.
        all_bars_oob = _build_all_oob(updated_ws_after)
        return HTMLResponse(content=resp.body.decode() + "\n" + all_bars_oob)

    return RedirectResponse(
        url=f"/v2/workbook?project={project}",
        status_code=303,
    )


@router.post("/workbook/run")
async def v2_workbook_run(
    request: Request,
    project: str = Form(...),
    content_hash: str = Form(...),
    workbook_version: str = Form(...),
):
    """V2 Run endpoint — canonical engine orchestration for Workbook V2.

    Pipeline (all checks fail-closed):
      1.  Auth
      2.  Load project_record + workspace_state
      3.  Runtime guard: check_runtime_allowed(ws, ws.draft_snapshot)
      4.  Version check: workbook_version must match WORKBOOK.version
      5.  Pre-engine identity CAS: content_hash must match current composite hash
      6.  Project type validation: Solar→"Solar", Wind→"Wind", else error
      7.  Materialise: build_draft_input_set_from_workspace(ws).to_projectinputs()
          (draft_snapshot is the canonical V2 run boundary after V2 edits)
      8.  Scenario resolution via get_scenario — fail closed on error
      9.  CAPEX fold (replace-semantics)
      10. OPEX fold (additive)
      11. run_project(project_type, scenario_name, project_inputs_override=override)
      12. v2_atomic_run_commit: final CAS + promote draft→saved + dirty=False
          Raises V2RunCommitConflictError if workbook changed during engine run
      13. ws_fresh = get_workspace_state(...); rr = WorkbookService.get_runtime_result(ws_fresh)
      14. build_runtime_projection_bundle(rr, ws_fresh.dirty)
      15. HTMX response: #v2-run-controls + #v2-status-banner + three sheet OOBs

    HTMX: always responds with 200 + HTML fragments (success or user-safe error).
    Non-HTMX: 303 redirect on success; redirect with ?v2_err=... on error.

    Scope constraints — NO engine formula modifications, NO parity changes.
    """
    from datetime import datetime, timezone

    from app.api.project_runner import run_project
    from app.persistence.projects_repository import get_project_record
    from app.persistence.workspace_repository import (
        V2RunCommitConflictError,
        get_workspace_state,
        v2_atomic_run_commit,
    )
    from app.services.capex_sub_lines_integration import apply_user_sub_lines_replacing_base
    from app.services.opex_sub_lines_integration import apply_user_sub_lines_to_opex
    from app.workbook.registry import WORKBOOK
    from app.workbook.runtime_projection import build_runtime_projection_bundle
    from app.workbook.workbook_identity import WorkbookIdentityError

    def _utc_compact() -> str:
        return datetime.now(timezone.utc).isoformat().replace(":", "").replace("-", "")

    user = _get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=302)

    is_htmx = request.headers.get("HX-Request") == "true"

    def _htmx_error(msg: str, ws_for_render=None) -> HTMLResponse:
        ctx: dict = {
            "ws_dirty": getattr(ws_for_render, "dirty", True),
            "has_runtime": bool(
                getattr(ws_for_render, "last_runtime_snapshot_id", None)
            ) if ws_for_render else False,
            "field_error": msg,
            "flash_error": "",
        }
        banner_html = _templates.get_template(
            "partials/_v2_status_banner.html"
        ).render(ctx)
        oob = '<div id="v2-status-banner" hx-swap-oob="true">' + banner_html + "</div>"
        return HTMLResponse(content=oob)

    def _non_htmx_error(msg: str) -> RedirectResponse:
        return RedirectResponse(
            url=f"/v2/workbook?project={project}&v2_err={urllib.parse.quote_plus(msg)}",
            status_code=303,
        )

    project_record = get_project_record(user_id=user.user_id, project_code=project)
    if project_record is None:
        msg = f"Project {project!r} not found."
        return _htmx_error(msg) if is_htmx else _non_htmx_error(msg)

    ws = get_workspace_state(user_id=user.user_id, project_id=project_record.project_id)
    if ws is None:
        msg = "Workspace not found."
        return _htmx_error(msg) if is_htmx else _non_htmx_error(msg)

    # ── Step 3: V2 runtime origin ──────────────────────────────────────────── #
    # V2 runs always materialise from draft_snapshot and promote it to
    # saved_snapshot atomically.  The legacy runtime_guard_for_snapshot blocks
    # dirty workspaces (designed for the legacy saved-state-only run path).
    # V2 uses CAS-based locking (content_hash + final CAS) instead, so we
    # skip the legacy guard and assign the origin directly.
    runtime_origin = "v2_run"

    # ── Step 4: version check ──────────────────────────────────────────────── #
    pis_draft = WorkbookService.build_draft_input_set_from_workspace(ws)
    if pis_draft.workbook_version != workbook_version:
        msg = "Workbook version mismatch — please reload the page."
        return _htmx_error(msg, ws) if is_htmx else _non_htmx_error(msg)

    # ── Step 5: pre-engine identity CAS ───────────────────────────────────── #
    try:
        current_identity = assemble_consistent_for_get(
            user_id=user.user_id,
            project_id=project_record.project_id,
            workbook_version=pis_draft.workbook_version,
        )
    except WorkbookIdentityError:
        msg = "Could not verify workbook identity — please reload."
        return _htmx_error(msg, ws) if is_htmx else _non_htmx_error(msg)
    if current_identity.composite_hash != content_hash:
        msg = (
            "Draft changed since page loaded — values refreshed. "
            "Please run again."
        )
        if not is_htmx:
            return _non_htmx_error(msg)
        # Return both the banner and refreshed run controls (with the current hash).
        stale_ctx: dict = {
            "ws_dirty": getattr(ws, "dirty", True),
            "has_runtime": bool(getattr(ws, "last_runtime_snapshot_id", None)),
            "field_error": msg,
            "flash_error": "",
            "project_code": project,
            "workbook_version": workbook_version,
            "content_hash": current_identity.composite_hash,
        }
        stale_banner_html = _templates.get_template(
            "partials/_v2_status_banner.html"
        ).render(stale_ctx)
        stale_banner_oob = (
            '<div id="v2-status-banner" hx-swap-oob="true">' + stale_banner_html + "</div>"
        )
        stale_controls_html = _templates.get_template(
            "partials/_v2_run_controls.html"
        ).render(stale_ctx)
        stale_controls_oob = (
            '<div id="v2-run-controls" hx-swap-oob="true">' + stale_controls_html + "</div>"
        )
        return HTMLResponse(content=stale_banner_oob + "\n" + stale_controls_oob)

    # ── Step 6: project type validation ───────────────────────────────────── #
    project_type_raw = (project_record.project_type or "").strip().lower()
    if project_type_raw == "solar":
        runtime_project_key = "Solar"
    elif project_type_raw == "wind":
        runtime_project_key = "Wind"
    else:
        msg = (
            f"Unsupported project type {project_record.project_type!r}. "
            "Only Solar and Wind projects can be run from Workbook V2."
        )
        return _htmx_error(msg, ws) if is_htmx else _non_htmx_error(msg)

    # ── Step 7: materialise from draft snapshot ────────────────────────────── #
    # draft_snapshot is the V2 canonical run boundary: it contains the exact
    # scalar values the user saw and approved when they clicked Run.
    try:
        override = WorkbookService.to_projectinputs(pis_draft)
    except Exception:
        import logging
        logging.getLogger(__name__).exception(
            "v2_workbook_run: build_project_inputs failed project=%s user=%s",
            project, user.user_id,
        )
        msg = "Could not build project inputs — please reload and try again."
        return _htmx_error(msg, ws) if is_htmx else _non_htmx_error(msg)

    # ── Step 8: scenario resolution ────────────────────────────────────────── #
    active_scenario_id = ws.active_scenario_id
    active_scenario_name = ws.active_scenario_name
    scenario_name = active_scenario_name or "Base"
    _scenario_overrides_for_fold = None

    if active_scenario_id:
        import logging as _log
        from app.persistence.scenarios_repository import get_scenario
        sc_rec = get_scenario(scenario_id=active_scenario_id, user_id=user.user_id)
        if sc_rec is None:
            msg = "Active scenario could not be found. Please re-select a scenario and try again."
            return _htmx_error(msg, ws) if is_htmx else _non_htmx_error(msg)
        if sc_rec.archived:
            msg = "Active scenario has been archived. Please re-select a scenario and try again."
            return _htmx_error(msg, ws) if is_htmx else _non_htmx_error(msg)
        if sc_rec.project_id != project_record.project_id:
            _log.getLogger(__name__).warning(
                "v2_workbook_run: scenario project_id mismatch "
                "scenario=%s scenario.project_id=%s expected=%s user=%s",
                active_scenario_id, sc_rec.project_id, project_record.project_id, user.user_id,
            )
            msg = "Active scenario does not belong to this project. Please re-select and try again."
            return _htmx_error(msg, ws) if is_htmx else _non_htmx_error(msg)
        _scenario_overrides_for_fold = sc_rec.overrides
        # Keep display name for provenance only; engine always receives "Base"
        # so the legacy ScenarioManager is never activated by a user-created name.
        scenario_name = sc_rec.scenario_name or scenario_name  # provenance / metadata only

    # ── Steps 9–10: CAPEX and OPEX fold ───────────────────────────────────── #
    from dataclasses import replace as _dc_replace
    folded_capex = apply_user_sub_lines_replacing_base(
        override.capex,
        project_id=project_record.project_id,
        scenario_overrides=_scenario_overrides_for_fold,
    )
    if folded_capex is not override.capex:
        override = _dc_replace(override, capex=folded_capex)

    folded_opex = apply_user_sub_lines_to_opex(
        override.opex,
        project_id=project_record.project_id,
        scenario_overrides=_scenario_overrides_for_fold,
    )
    if folded_opex is not override.opex:
        override = _dc_replace(override, opex=folded_opex)

    # ── Step 11: run the engine ────────────────────────────────────────────── #
    try:
        result = run_project(
            runtime_project_key,
            "Base",  # Contract A: always "Base"; display name must not activate legacy ScenarioManager
            project_inputs_override=override,
        )
    except Exception as exc:
        import logging
        logging.getLogger(__name__).exception("v2_workbook_run: engine failure")
        msg = "Engine run failed — please try again or contact support."
        return _htmx_error(msg, ws) if is_htmx else _non_htmx_error(msg)

    # ── Step 12: atomic commit (final CAS + promote + dirty=False) ────────── #
    runtime_snapshot_id = _utc_compact()
    ran_at = datetime.now(timezone.utc)
    try:
        ws_committed = v2_atomic_run_commit(
            user_id=user.user_id,
            project_id=project_record.project_id,
            project_code=project_record.project_code,
            expected_composite_hash=content_hash,
            runtime_snapshot_id=runtime_snapshot_id,
            runtime_origin=runtime_origin or "v2_run",
            runtime_summary=result["kpis"],
            financial_statements=result.get("financial_statements"),
            debt_schedule=result.get("debt_schedule"),
            tax_schedule=result.get("tax_schedule"),
            distribution_schedule=result.get("distribution_schedule"),
            sponsor_schedule=result.get("sponsor_schedule"),
            active_scenario_id=active_scenario_id,
            active_scenario_name=active_scenario_name,
            last_runtime_scenario_id=active_scenario_id,
            ran_at=ran_at,
        )
    except V2RunCommitConflictError:
        msg = (
            "Workbook changed while the engine was running — values refreshed. "
            "Please run again."
        )
        if not is_htmx:
            return _non_htmx_error(msg)
        # Re-fetch workspace to get the current hash for the run controls.
        ws_conflict = get_workspace_state(
            user_id=user.user_id, project_id=project_record.project_id
        ) or ws
        pis_conflict = WorkbookService.build_draft_input_set_from_workspace(ws_conflict)
        try:
            conflict_identity = assemble_consistent_for_get(
                user_id=user.user_id,
                project_id=project_record.project_id,
                workbook_version=pis_conflict.workbook_version,
            )
            conflict_hash = conflict_identity.composite_hash
        except WorkbookIdentityError:
            conflict_hash = ""
        conflict_ctx: dict = {
            "ws_dirty": getattr(ws_conflict, "dirty", True),
            "has_runtime": bool(getattr(ws_conflict, "last_runtime_snapshot_id", None)),
            "field_error": msg,
            "flash_error": "",
            "project_code": project,
            "workbook_version": workbook_version,
            "content_hash": conflict_hash,
        }
        conflict_banner_html = _templates.get_template(
            "partials/_v2_status_banner.html"
        ).render(conflict_ctx)
        conflict_banner_oob = (
            '<div id="v2-status-banner" hx-swap-oob="true">' + conflict_banner_html + "</div>"
        )
        conflict_controls_html = _templates.get_template(
            "partials/_v2_run_controls.html"
        ).render(conflict_ctx)
        conflict_controls_oob = (
            '<div id="v2-run-controls" hx-swap-oob="true">' + conflict_controls_html + "</div>"
        )
        return HTMLResponse(content=conflict_banner_oob + "\n" + conflict_controls_oob)
    except Exception as exc:
        import logging
        logging.getLogger(__name__).exception("v2_workbook_run: persistence failure")
        msg = "Run completed but could not be saved — please try again."
        return _htmx_error(msg, ws) if is_htmx else _non_htmx_error(msg)

    # ── Step 13–14: project from the persisted RuntimeResult ──────────────── #
    ws_fresh = ws_committed or get_workspace_state(
        user_id=user.user_id, project_id=project_record.project_id
    )
    if ws_fresh is None:
        msg = "Run committed but workspace could not be reloaded."
        return _htmx_error(msg) if is_htmx else _non_htmx_error(msg)
    rr = WorkbookService.get_runtime_result(ws_fresh)
    if rr is None:
        msg = "Run committed but the persisted RuntimeResult could not be reconstructed."
        return _htmx_error(msg) if is_htmx else _non_htmx_error(msg)
    projection = build_runtime_projection_bundle(rr, ws_fresh.dirty)

    # ── Step 15: HTMX response ────────────────────────────────────────────── #
    if not is_htmx:
        return RedirectResponse(
            url=f"/v2/workbook?project={project}",
            status_code=303,
        )

    pis_fresh = _build_pis_with_composite_identity(ws_fresh, project_record, user)
    ctx = _base_sheet_ctx(request, pis_fresh, ws_fresh, project_record, project)

    # #v2-run-controls OOB — refreshes the Run form with the new composite hash.
    run_controls_html = _templates.get_template(
        "partials/_v2_run_controls.html"
    ).render(ctx)
    run_controls_oob = (
        '<div id="v2-run-controls" hx-swap-oob="true">' + run_controls_html + "</div>"
    )

    # #v2-status-banner OOB.
    banner_html = _templates.get_template(
        "partials/_v2_status_banner.html"
    ).render(ctx)
    banner_oob = (
        '<div id="v2-status-banner" hx-swap-oob="true">' + banner_html + "</div>"
    )

    # Three sheet OOBs — attach hx-swap-oob="true" to the sheet root element
    # (not a wrapper) to avoid nested duplicate DOM IDs.
    ctx.update(_build_debt_ctx(pis_fresh, ws_fresh, projection=projection))
    debt_html = _templates.get_template("partials/sheet_senior_debt.html").render(ctx)
    debt_oob = debt_html.replace(
        '<div id="v2-sheet-senior-debt"',
        '<div id="v2-sheet-senior-debt" hx-swap-oob="true"',
        1,
    )

    ctx.update(_build_tax_ctx(pis_fresh, ws_fresh, projection=projection))
    tax_html = _templates.get_template("partials/sheet_tax.html").render(ctx)
    tax_oob = tax_html.replace(
        '<div id="v2-sheet-tax"',
        '<div id="v2-sheet-tax" hx-swap-oob="true"',
        1,
    )

    ctx.update(_build_financial_statements_ctx(pis_fresh, ws_fresh, projection=projection))
    fs_html = _templates.get_template(
        "partials/sheet_financial_statements.html"
    ).render(ctx)
    fs_oob = fs_html.replace(
        '<div id="v2-sheet-financial-statements"',
        '<div id="v2-sheet-financial-statements" hx-swap-oob="true"',
        1,
    )

    # Each full sheet OOB already includes its runtime bar; do not add standalone bar OOBs
    # here — that would create duplicate DOM IDs (debt-runtime-bar, tax-runtime-bar, fs-runtime-bar).
    toolbar_state_oob = _build_toolbar_state_oob(ctx)
    combined = "\n".join([run_controls_oob, banner_oob, toolbar_state_oob, debt_oob, tax_oob, fs_oob])
    return HTMLResponse(content=combined)
