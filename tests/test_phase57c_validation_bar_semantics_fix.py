from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from jinja2 import DictLoader, Environment

import main_web


REPO_ROOT = Path(__file__).resolve().parents[1]
PARTIAL = REPO_ROOT / "app" / "templates" / "partials" / "_validation_summary_bar.html"


def _project_record(
    project_code: str,
    *,
    template_source: str | None = None,
    project_origin: str = "factory_template",
) -> SimpleNamespace:
    return SimpleNamespace(
        project_code=project_code,
        project_name=project_code.upper(),
        template_source=template_source,
        project_origin=project_origin,
        baseline_snapshot={"template_source": template_source or project_code},
        governance_state={"g20_status": "BLOCKED", "r99_r102_status": "NOT APPROVED"},
    )


def _render(validation_summary, governance_guard_summary) -> str:
    env = Environment(loader=DictLoader({"partial": PARTIAL.read_text(encoding="utf-8")}), autoescape=False)
    return env.get_template("partial").render(
        validation_summary=validation_summary,
        governance_guard_summary=governance_guard_summary,
    )


def test_tuho_valid_run_not_red_solely_due_to_governance_guards():
    project = _project_record("tuho", template_source="tuho")
    summary = main_web._validation_summary_for_context(project, [])
    guards = main_web._governance_guard_summary_for_context(project)
    html = _render(summary, guards)
    assert summary["fail_count"] == 0
    assert "validation-summary-pass" in html
    assert "G20" in html
    assert "BLOCKED" in html
    assert "R99/R102" in html
    assert "NOT APPROVED" in html
    assert "platform-level" in html.lower()


def test_oborovo_valid_run_not_red_solely_due_to_governance_guards():
    project = _project_record("oborovo", template_source="oborovo")
    summary = main_web._validation_summary_for_context(project, [])
    guards = main_web._governance_guard_summary_for_context(project)
    html = _render(summary, guards)
    assert summary["fail_count"] == 0
    assert "validation-summary-pass" in html
    assert "Governance / Feature Guards" in html


def test_actual_validation_error_still_produces_fail_state():
    project = _project_record("tuho", template_source="tuho")
    summary = main_web._validation_summary_for_context(project, ["Missing required input"])
    guards = main_web._governance_guard_summary_for_context(project)
    html = _render(summary, guards)
    assert summary["fail_count"] == 1
    assert summary["actual_issue_count"] == 1
    assert "validation-summary-fail" in html
    assert "current run/input item" in html


def test_generic_project_is_governance_reference_status_not_validated_parity():
    project = _project_record("generic_solar", template_source="generic_solar")
    summary = main_web._validation_summary_for_context(project, [])
    guards = main_web._governance_guard_summary_for_context(project)
    html = _render(summary, guards)
    assert summary["fail_count"] == 0
    assert any(item["title"] == "Generic project path" for item in guards["items"])
    assert "EXPLORATORY / UNVALIDATED" in html
    assert "trusted TUHO/Oborovo parity evidence" in html


def test_validation_fail_count_means_actual_run_issues_only():
    project = _project_record("tuho", template_source="tuho")
    summary = main_web._validation_summary_for_context(project, [])
    guards = main_web._governance_guard_summary_for_context(project)
    assert summary["fail_count"] == 0
    assert len(guards["items"]) >= 2


def test_governance_guard_helper_keeps_blocked_language():
    project = _project_record("tuho", template_source="tuho")
    guards = main_web._governance_guard_summary_for_context(project)
    statuses = {item["title"]: item["status"] for item in guards["items"]}
    assert statuses["G20"] == "BLOCKED"
    assert statuses["R99/R102"] == "NOT APPROVED"
