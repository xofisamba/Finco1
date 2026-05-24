from __future__ import annotations

import os


def _read(*parts: str) -> str:
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(base, *parts), encoding="utf-8") as handle:
        return handle.read()


def test_compare_ui_includes_source_clarity_and_timestamps():
    compare_partial = _read("app", "templates", "partials", "scenario_compare.html")
    scenario_workspace = _read("app", "templates", "partials", "scenario_workspace.html")
    main_web = _read("main_web.py")

    assert "Scenario compare is descriptive only." in compare_partial
    assert "saved scenario snapshots and saved runtime summaries" in compare_partial
    assert "Compare generated at" in compare_partial
    assert "Saved snapshot timestamp:" in compare_partial
    assert "Runtime timestamp:" in compare_partial
    assert "Runtime snapshot ID:" in compare_partial
    assert "Runtime origin:" in compare_partial
    assert "Compare does not auto-save and does not auto-run." in compare_partial

    assert "Unsaved browser draft edits are not part of the comparison unless you save them first." in scenario_workspace
    assert "_build_compare_ui_context" in main_web
    assert "pending / unavailable" in main_web
    assert "not_applicable" in main_web


def test_compare_honesty_guardrails_and_governance_statements_exist():
    docs = _read("docs", "phase14_scenario_compare_honesty.md")
    styles = _read("static", "styles.css")
    main_web = _read("main_web.py")

    assert "Scenario compare is descriptive only." in docs
    assert "Compare does not auto-save and does not auto-run." in docs
    assert "Pending, unavailable, and `not_applicable` markers are intentional" in docs
    assert "`audit_economic_mode` remains audit/reconciliation-only." in docs
    assert "`runtime_economic_mode` remains the only explicit runtime staging path." in docs
    assert "`G20` remains `BLOCKED`." in docs
    assert "`R99/R102` remain `NOT APPROVED`." in docs

    assert ".ps-compare-banner" in styles
    assert ".ps-compare-context-grid" in styles
    assert "compare_scenarios(user.user_id, left_scenario_id, right_scenario_id)" in main_web


def test_reports_exist_and_capture_compare_honesty_rules():
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for report_name in (
        "phase14_scenario_compare_source_matrix.csv",
        "phase14_scenario_compare_missing_metric_matrix.csv",
        "phase14_scenario_compare_guardrail_matrix.csv",
    ):
        assert os.path.exists(os.path.join(base, "reports", report_name))

    source_matrix = _read("reports", "phase14_scenario_compare_source_matrix.csv")
    missing_matrix = _read("reports", "phase14_scenario_compare_missing_metric_matrix.csv")
    guardrails = _read("reports", "phase14_scenario_compare_guardrail_matrix.csv")

    assert "saved scenario snapshots and saved runtime summaries only" in source_matrix
    assert "missing_metric,\"pending / unavailable\"" in missing_matrix
    assert "missing_delta,\"not_applicable\"" in missing_matrix
    assert "compare_does_not_auto_save,confirmed" in guardrails
    assert "compare_does_not_auto_run,confirmed" in guardrails
    assert "missing_values_not_shown_as_zero,confirmed" in guardrails
    assert "g20_blocked,confirmed" in guardrails
    assert "r99_r102_not_approved,confirmed" in guardrails
