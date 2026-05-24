"""Phase 14A reviewer productivity polish tests."""

from __future__ import annotations

import os


def _read(*parts: str) -> str:
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(base, *parts), encoding="utf-8") as handle:
        return handle.read()


def test_reviewer_labels_and_guidance_exist_for_state_boundaries():
    workspace_shell = _read("app", "templates", "partials", "workspace_shell.html")
    scenario_workspace = _read("app", "templates", "partials", "scenario_workspace.html")
    index_html = _read("app", "templates", "index.html")

    assert "Active Scenario" in workspace_shell
    assert "Draft State" in workspace_shell
    assert "Last Runtime Boundary" in workspace_shell
    assert "Runtime Snapshot" in workspace_shell
    assert "Unsaved changes" in workspace_shell
    assert 'id="workspace-state-guidance"' in workspace_shell
    assert "last clean backend run" in workspace_shell.lower()

    assert "Active saved scenario boundary" in scenario_workspace
    assert "Save records a new persisted scenario snapshot but does not run the model." in scenario_workspace
    assert "Revert restores the saved boundary without triggering a run." in scenario_workspace

    assert 'id="reviewer-action-help"' in index_html
    assert "Save creates a persisted scenario snapshot and does not run the model." in index_html
    assert "Workbook export remains backend-authored." in index_html


def test_disabled_action_explanations_and_accessibility_markers_exist():
    index_html = _read("app", "templates", "index.html")
    app_js = _read("static", "app.js")
    styles = _read("static", "styles.css")

    assert 'aria-label="Run model using the last clean saved scenario state"' in index_html
    assert 'aria-label="Compare using the last clean saved scenario state"' in index_html
    assert 'aria-label="Save the current clean run record"' in index_html
    assert 'aria-label="Revert unsaved draft edits back to the saved scenario boundary"' in index_html
    assert 'aria-describedby="reviewer-action-help"' in index_html
    assert 'aria-describedby="reviewer-export-help"' in index_html
    assert 'aria-describedby="reviewer-revert-help"' in index_html

    assert "data-dirty-message=" in index_html
    assert "Disabled because unsaved draft edits exist. Save or revert first." in app_js
    assert "setActionReason" in app_js
    assert "updateReviewerActionHelp" in app_js
    assert "aria-disabled" in app_js
    assert ":focus-visible" in styles
    assert ".reviewer-action-help" in styles
    assert ".workspace-reviewer-note" in styles


def test_existing_editable_grids_gain_labels_without_new_surfaces():
    revenue_html = _read("app", "templates", "partials", "sheet_revenue.html")
    opex_html = _read("app", "templates", "partials", "sheet_opex.html")
    debt_html = _read("app", "templates", "partials", "sheet_senior_debt.html")
    tax_html = _read("app", "templates", "partials", "sheet_tax.html")
    shl_html = _read("app", "templates", "partials", "sheet_shl.html")
    app_js = _read("static", "app.js").lower()

    assert "Draft value (unsaved workspace)" in revenue_html
    assert "Draft value (unsaved workspace)" in opex_html
    assert "Draft value (unsaved workspace)" in debt_html
    assert 'aria-label="Draft PPA tariff in euros per megawatt hour"' in revenue_html
    assert 'aria-label="Draft year one operating expense in thousands of euros"' in opex_html
    assert 'aria-label="Draft target debt service coverage ratio"' in debt_html

    assert "editable-grid-shell" not in tax_html
    assert "editable-grid-shell" not in shl_html

    for marker in ("xirr(", "project_irr =", "equity_irr =", "avg_dscr =", "ebitda ="):
        assert marker not in app_js


def test_docs_reports_and_governance_posture_exist():
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    docs = _read("docs", "phase14a_reviewer_productivity_polish.md")

    assert "Phase 14A" in docs
    assert "`G20` remains `BLOCKED`" in docs
    assert "`R99/R102` remain `NOT APPROVED`" in docs
    assert "No new editable surfaces were added." in docs
    assert "Workbook export remains backend-authored" in docs

    for report_name in (
        "phase14a_reviewer_guidance_matrix.csv",
        "phase14a_accessibility_polish_matrix.csv",
        "phase14a_disabled_action_matrix.csv",
    ):
        assert os.path.exists(os.path.join(base, "reports", report_name))
