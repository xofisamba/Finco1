"""Phase 13D editable-grid closeout review tests."""

import os


def _base() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read(*parts: str) -> str:
    return open(os.path.join(_base(), *parts), encoding="utf-8").read()


def test_closeout_review_artifacts_exist():
    base = _base()
    required = [
        ("docs", "phase13_editable_grid_closeout_review.md"),
        ("reports", "phase13_editable_grid_authority_closeout.csv"),
        ("reports", "phase13_editable_grid_regression_inventory.csv"),
        ("reports", "phase13_editable_grid_known_limitations.csv"),
    ]
    for parts in required:
        assert os.path.exists(os.path.join(base, *parts))


def test_closeout_confirms_authority_boundaries_and_no_new_surfaces():
    closeout_doc = _read("docs", "phase13_editable_grid_closeout_review.md")
    surface_map = _read("reports", "phase13_editable_grid_surface_map.csv")
    authority_report = _read("reports", "phase13_editable_grid_authority_closeout.csv")

    assert "draft-only input surfaces" in closeout_doc
    assert "saved scenarios remain explicit persisted boundaries" in closeout_doc
    assert "last runtime results remain bound to the last clean backend snapshot" in closeout_doc
    assert "No new editable surfaces were added in Phase 13D." in closeout_doc

    # Current editable surface count remains Phase 13B baseline only.
    rows = [line for line in surface_map.strip().splitlines()[1:] if line.strip()]
    assert len(rows) == 3
    assert "Workspace draft,no,workspace only,yes,confirmed" in authority_report
    assert "Frontend JavaScript,no,no,mirror only,confirmed" in authority_report


def test_htmx_and_runtime_guard_assumptions_are_documented():
    hardening_report = _read("reports", "phase13_htmx_refresh_state_matrix.csv")
    runtime_guard_report = _read("reports", "phase13_runtime_snapshot_guard_matrix.csv")
    regression_inventory = _read("reports", "phase13_editable_grid_regression_inventory.csv")

    assert "Rebinding remains idempotent after swaps" in regression_inventory
    assert "Mirror inputs resync from canonical fields" in hardening_report
    assert "Run/compare/save-run reflect dirty state" in hardening_report
    assert "Later edits do not mutate prior runtime meaning" in runtime_guard_report


def test_frontend_still_does_not_calculate_financial_outputs():
    app_js = _read("static", "app.js").lower()
    forbidden = [
        "xirr(",
        "project_irr =",
        "equity_irr =",
        "avg_dscr =",
        "min_dscr =",
        "ebitda =",
        "debt service =",
    ]
    for marker in forbidden:
        assert marker not in app_js


def test_governance_posture_and_known_limitations_are_explicit():
    closeout_doc = _read("docs", "phase13_editable_grid_closeout_review.md")
    limitations = _read("reports", "phase13_editable_grid_known_limitations.csv")
    hardening_doc = _read("docs", "phase13_editable_grid_hardening.md")
    ux_doc = _read("docs", "phase13_editable_grid_ux.md")
    state_doc = _read("docs", "phase13_editable_grid_state_controls.md")

    for text in (
        "`G20` remains `BLOCKED`",
        "`R99/R102` remain `NOT APPROVED`",
    ):
        assert text in closeout_doc
        assert text in hardening_doc
        assert text in ux_doc
    assert "G20 remains `BLOCKED`" in state_doc
    assert "R99/R102 remain `NOT APPROVED`" in state_doc or "R99/R102 remain `NOT APPROVED`".replace("`", "") in state_doc

    assert "No spreadsheet-style formula editing" in limitations
    assert "No replay engine" in limitations
    assert "No alternate mobile calculation path" in limitations
