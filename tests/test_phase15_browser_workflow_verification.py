from __future__ import annotations

import os
import re


def _read(*parts: str) -> str:
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(base, *parts), encoding="utf-8") as handle:
        return handle.read()


def test_browser_smoke_surfaces_keep_dirty_state_and_export_honesty_visible():
    index_html = _read("app", "templates", "index.html")
    project_selector = _read("app", "templates", "partials", "project_selector.html")
    workspace_shell = _read("app", "templates", "partials", "workspace_shell.html")
    scenario_workspace = _read("app", "templates", "partials", "scenario_workspace.html")
    scenario_compare = _read("app", "templates", "partials", "scenario_compare.html")

    assert "TUHO" in project_selector
    assert "Oborovo" in project_selector
    assert 'id="workspace-unsaved-banner"' in workspace_shell
    assert "Unsaved changes" in workspace_shell
    assert "Runtime cards and exported outputs reflect the last clean backend run" in workspace_shell
    assert 'id="export-lineage-panel"' in workspace_shell
    assert "Reviewer-facing lineage only." in workspace_shell
    assert "Values-only Excel Export (.xlsx)" in workspace_shell
    assert "Runtime Summary CSV" in workspace_shell
    assert "Institutional Workbook" in workspace_shell

    assert "Run, compare, and save-run are disabled because unsaved draft edits exist." in index_html
    assert "Save creates a persisted scenario snapshot and does not run the model." in index_html
    assert "Workbook export remains backend-authored." in index_html
    assert "Current draft is newer than the last clean runtime snapshot." in index_html
    assert "Revert restores the last saved scenario boundary and clears draft-only edits. It does not run the model." in index_html

    assert "Compare reads saved scenario snapshots and saved runtime summaries only." in scenario_workspace
    assert "Unsaved browser draft edits are not part of the comparison unless you save them first." in scenario_workspace
    assert "Scenario compare is descriptive only." in scenario_compare
    assert "Compare does not auto-save and does not auto-run." in scenario_compare
    assert "pending values for zero" in scenario_compare


def test_browser_state_hooks_remain_idempotent_and_non_authoritative():
    app_js = _read("static", "app.js")
    revenue = _read("app", "templates", "partials", "sheet_revenue.html")
    opex = _read("app", "templates", "partials", "sheet_opex.html")
    debt = _read("app", "templates", "partials", "sheet_senior_debt.html")

    assert "function bindDraftPersistenceFields(root)" in app_js
    assert "function bindEditableGridInputs(root)" in app_js
    assert "window.syncEditableGridMirrors = function()" in app_js
    assert "window.applyWorkspaceStateMeta = function(meta)" in app_js
    assert "field.dataset.draftBound = '1'" in app_js
    assert "input.dataset.gridBound = '1'" in app_js
    assert "document.addEventListener('htmx:afterSwap'" in app_js
    assert app_js.count("document.addEventListener('htmx:afterSwap'") == 1
    assert "['btn-run-model', 'btn-compare-draft', 'btn-save-run']" in app_js
    assert "Unsaved draft edits are active. Runtime-backed exports remain tied to the last clean backend snapshot until you save and run again." in app_js

    for partial in (revenue, opex, debt):
        assert "data-grid-source" in partial
        assert "Draft only" in partial
        assert "editable-grid-scroll" in partial

    lowered_js = app_js.lower()
    for marker in ("xirr(", "project_irr =", "equity_irr =", "avg_dscr =", "ebitda =", "debt service ="):
        assert marker not in lowered_js


def test_browser_hook_targets_exist_in_templates_and_grid_partials():
    app_js = _read("static", "app.js")
    index_html = _read("app", "templates", "index.html")
    workspace_shell = _read("app", "templates", "partials", "workspace_shell.html")
    scenario_workspace = _read("app", "templates", "partials", "scenario_workspace.html")
    revenue = _read("app", "templates", "partials", "sheet_revenue.html")
    opex = _read("app", "templates", "partials", "sheet_opex.html")
    debt = _read("app", "templates", "partials", "sheet_senior_debt.html")

    for element_id in ("btn-run-model", "btn-compare-draft", "btn-save-run"):
        assert element_id in app_js
        assert f'id="{element_id}"' in index_html

    for element_id in (
        "workspace-unsaved-banner",
        "workspace-strip-active-scenario",
        "workspace-strip-dirty",
        "workspace-strip-runtime-origin",
        "workspace-strip-runtime-snapshot",
        "workspace-active-scenario-name",
        "workspace-dirty-label",
        "workspace-runtime-origin-label",
        "workspace-runtime-snapshot-id",
        "export-lineage-panel",
    ):
        assert f'id="{element_id}"' in workspace_shell or f'id="{element_id}"' in scenario_workspace

    for partial in (revenue, opex, debt):
        assert partial.count("data-grid-source") >= 1
        assert "editable-grid-scroll" in partial
        assert "Draft only" in partial


def test_mobile_browser_smoke_hooks_and_compare_labels_exist():
    styles = _read("static", "styles.css")
    workspace_shell = _read("app", "templates", "partials", "workspace_shell.html")
    scenario_compare = _read("app", "templates", "partials", "scenario_compare.html")

    assert ".editable-grid-scroll" in styles
    assert "overflow-x: auto;" in styles
    assert ".workspace-state-banner" in styles
    assert ".workspace-state-strip" in styles
    assert ".ps-compare-context-grid" in styles
    assert ".editable-grid-input:focus-visible" in styles
    assert "@media (max-width: 900px)" in styles

    assert "G20 BLOCKED" in workspace_shell
    assert "R99/R102 NOT APPROVED" in workspace_shell
    assert "Runtime timestamp:" in scenario_compare
    assert "Runtime snapshot ID:" in scenario_compare
    assert "Runtime origin:" in scenario_compare


def test_docs_and_reports_honestly_describe_browser_verification_scope():
    requirements = _read("requirements.txt")
    docs = _read("docs", "phase15_browser_workflow_verification.md")
    workflow = _read("reports", "phase15_browser_workflow_matrix.csv")
    htmx = _read("reports", "phase15_htmx_browser_verification_matrix.csv")
    mobile = _read("reports", "phase15_mobile_browser_smoke_matrix.csv")
    gaps = _read("reports", "phase15_browser_workflow_remaining_gaps.csv")

    assert "playwright" not in requirements.lower()
    assert "selenium" not in requirements.lower()

    assert "strongest-available browser smoke substitute" in docs
    assert "Real Playwright or Selenium automation was **not** added in this branch." in docs
    assert "Frontend/browser state does not become runtime authority." in docs
    assert "Save does not auto-run runtime." in docs
    assert "Export does not auto-run runtime." in docs
    assert "Compare does not auto-save and does not auto-run." in docs
    assert "Dirty drafts are not exported or compared as runtime truth." in docs
    assert "`G20` remains `BLOCKED`." in docs
    assert "`R99/R102` remain `NOT APPROVED`." in docs

    assert "editable_grid_dirty_state,template_and_js_smoke,covered" in workflow
    assert "htmx_partial_refresh_behavior,js_hook_smoke,covered" in workflow
    assert "real_browser_download_event,live_browser_automation_gap,pending" in workflow
    assert "listener_stacking_guard,data-draft-bound_and_data-grid-bound,confirmed" in htmx
    assert "editable_grid_scroll,.editable-grid-scroll overflow-x auto,confirmed" in mobile
    assert "playwright_or_selenium_stack,not_added" in gaps
    assert "real_mobile_browser_device_validation,not_covered" in gaps
