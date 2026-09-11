"""R6/F07 — ONE post-run UI projection authority.

A completed canonical Workbook V2 Run must produce ONE coherent post-run
browser state.  ``build_post_run_ui_state`` is constructed ONLY after:

1. the canonical Run succeeded;
2. runtime evidence was persisted (``v2_atomic_run_commit``);
3. fresh workspace state was re-read (``ws_fresh``);

and renders every runtime-dependent visible surface from that single
workspace read and a single runtime projection — no partial re-runs, no
independent KPI derivation, no financial arithmetic in templates/JS:

    canonical Run
        → persisted runtime evidence (ws_fresh)
        → RuntimeResult + RuntimeProjectionBundle
        → post-run OOB fragments
        → every runtime-dependent visible surface

Surfaces refreshed (all runtime-dependent):
    #v2-run-controls            authoritative composite hash (immediate re-edit/re-run)
    #v2-status-banner           dirty/stale → current post-run state
    #v2-toolbar-runtime-state   current/stale chip + last runtime timestamp
    #v2-sheet-overview          KPI strip + decision dashboard (F07: previously stale)
    #v2-sheet-senior-debt       debt runtime bar + coverage presentation
    #v2-sheet-tax               tax runtime bar (R4 typed country-tax semantics preserved)
    #v2-sheet-financial-statements  FS runtime state (canonical unavailable stays unavailable)
    #v2-sheet-scenarios         per-scenario last-run status (persisted in run step 12b)

Inputs-only sheets (project_setup, inputs, revenue, CAPEX, OPEX) are NOT
refreshed by a Run — they hold no runtime-derived values.
"""
from __future__ import annotations

from typing import Any, Optional


def build_post_run_ui_state(
    *,
    request: Any,
    ws_fresh,
    project_record,
    project: str,
    workspace_owner: str,
) -> str:
    """Build the complete post-run HTMX response for one completed Run.

    Every fragment is rendered from the same single ``ws_fresh`` read and the
    same ``RuntimeProjectionBundle`` — one completed canonical Run produces
    one post-run UI state.
    """
    from app.workbook.runtime_projection import build_runtime_projection_bundle
    from app.workbook.service import WorkbookService
    from app.v2.overview_projection import build_overview_projection

    from app.v2.router import (  # local import: router owns template helpers
        _base_sheet_ctx,
        _build_pis_with_composite_identity,
        _build_run_controls_oob,
        _build_toolbar_state_oob,
        _scenario_list_html,
        _templates,
        _build_debt_ctx,
        _build_tax_ctx,
        _build_financial_statements_ctx,
    )

    pis_fresh = _build_pis_with_composite_identity(
        ws_fresh, project_record, workspace_owner)
    rr = WorkbookService.get_runtime_result(ws_fresh)
    projection = (
        build_runtime_projection_bundle(rr, ws_fresh.dirty) if rr is not None else None
    )
    ctx = _base_sheet_ctx(request, pis_fresh, ws_fresh, project_record, project)

    fragments: list[str] = []

    # A. Run controls — authoritative composite hash for immediate re-edit.
    fragments.append(_build_run_controls_oob(ctx))

    # B. Status banner — dirty/stale transitions to the post-run state.
    banner_html = _templates.get_template(
        "partials/_v2_status_banner.html").render(ctx)
    fragments.append(
        '<div id="v2-status-banner" hx-swap-oob="true">' + banner_html + "</div>")

    # D. Toolbar runtime state chip.
    fragments.append(_build_toolbar_state_oob(ctx))

    # A. Overview — runtime KPIs/status from THIS run (F07 defect surface).
    ov = build_overview_projection(
        rr, ws_fresh.dirty, pis_fresh,
        active_scenario_name=getattr(ws_fresh, "active_scenario_name", None) or "",
    )
    ov_ctx = {
        "overview": ov,
        "project_code": project,
        "project_name": getattr(project_record, "project_name", "") or project,
        "project_type": getattr(project_record, "project_type", "") or "",
        "ws_dirty": getattr(ws_fresh, "dirty", True),
        "has_runtime": bool(getattr(ws_fresh, "last_runtime_snapshot_id", None)),
    }
    ov_html = _templates.get_template("partials/sheet_overview.html").render(ov_ctx)
    fragments.append(_as_oob(ov_html, "v2-sheet-overview"))

    # E. Senior Debt runtime presentation.
    ctx.update(_build_debt_ctx(pis_fresh, ws_fresh, projection=projection))
    debt_html = _templates.get_template("partials/sheet_senior_debt.html").render(ctx)
    fragments.append(_as_oob(debt_html, "v2-sheet-senior-debt"))

    # F. Tax runtime presentation (R4 typed country-tax semantics preserved).
    ctx.update(_build_tax_ctx(pis_fresh, ws_fresh, projection=projection))
    tax_html = _templates.get_template("partials/sheet_tax.html").render(ctx)
    fragments.append(_as_oob(tax_html, "v2-sheet-tax"))

    # G. Financial Statements runtime presentation (canonical unavailable
    #    stays typed-unavailable — never manufactured).
    ctx.update(_build_financial_statements_ctx(pis_fresh, ws_fresh, projection=projection))
    fs_html = _templates.get_template(
        "partials/sheet_financial_statements.html").render(ctx)
    fragments.append(_as_oob(fs_html, "v2-sheet-financial-statements"))

    # H. Scenario last-run statuses (persisted during run step 12b).
    scenarios_html = _scenario_list_html(
        workspace_owner, project_record.project_id, project, ws_fresh)
    fragments.append(_as_oob(scenarios_html, "v2-sheet-scenarios"))

    return "\n".join(fragments)


def _as_oob(html: str, dom_id: str) -> str:
    """Attach ``hx-swap-oob`` to a sheet partial's own root element (the
    existing workbook convention — avoids duplicate wrapper DOM IDs)."""
    marker = f'<div id="{dom_id}"'
    if marker not in html:
        return html
    return html.replace(marker, marker + ' hx-swap-oob="true"', 1)
