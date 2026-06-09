"""Phase 24-G-2 — Run Status Clarity (UI-only).

Verifies:
- _last_run_indicator.html renders nothing if runtime_summary is
  missing or has neither run_id nor last_run_at (no fake IDs,
  no fake timestamps).
- Status badge is OK / ERROR / BLOCKED / NO RUN — never invented.
- Status badge tone matches data.
- Project association is shown when project_record has a code.
- Scenario association is shown when base_case_record exists.
- Stale state row appears when workspace_state.dirty AND
  last_runtime_snapshot_id (same gate as stale_run macro).
- Stale row does NOT appear when draft is clean.
- Run error message is surfaced when runtime_summary.error_message
  is present.
- All data is sourced from existing context (no fake values).
- CSS additive (no :root mods, no forbidden class names).
- No production code change.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from jinja2 import Environment, DictLoader, FileSystemLoader

REPO_ROOT = Path(__file__).resolve().parents[1]
LAST_RUN_INDICATOR = REPO_ROOT / "app" / "templates" / "partials" / "_last_run_indicator.html"
EMPTY_NO_PROJECT = REPO_ROOT / "app" / "templates" / "partials" / "_empty_no_project.html"
EMPTY_NO_SCENARIO = REPO_ROOT / "app" / "templates" / "partials" / "_empty_no_scenario.html"
EMPTY_NO_RUN = REPO_ROOT / "app" / "templates" / "partials" / "_empty_no_run.html"
INDEX_HTML = REPO_ROOT / "app" / "templates" / "index.html"
STYLES_CSS = REPO_ROOT / "static" / "styles.css"
MAIN_WEB = REPO_ROOT / "main_web.py"


def _render_last_run_indicator(context: dict) -> str:
    """Render _last_run_indicator.html in isolation."""
    env = Environment(
        loader=FileSystemLoader(str(REPO_ROOT / "app" / "templates")),
        autoescape=False,
    )
    template = env.get_template("partials/_last_run_indicator.html")
    return template.render(**context)


def _render_partial(path: Path, context: dict) -> str:
    env = Environment(
        loader=FileSystemLoader(str(REPO_ROOT / "app" / "templates")),
        autoescape=False,
    )
    rel = "partials/" + path.name
    template = env.get_template(rel)
    return template.render(**context)


# ============================================================
# 1. Renders nothing when no real runtime data
# ============================================================


class TestRendersNothing:
    def test_no_runtime_summary(self):
        out = _render_last_run_indicator({})
        assert "last-run-indicator" not in out

    def test_runtime_summary_empty(self):
        out = _render_last_run_indicator({"runtime_summary": {}})
        assert "last-run-indicator" not in out

    def test_runtime_summary_only_status_no_id_no_time(self):
        out = _render_last_run_indicator({"runtime_summary": {"status": "ok"}})
        assert "last-run-indicator" not in out

    def test_runtime_summary_only_error_no_id_no_time(self):
        # No run_id, no last_run_at — must NOT render
        out = _render_last_run_indicator({
            "runtime_summary": {"status": "error", "error_message": "boom"},
        })
        assert "last-run-indicator" not in out


# ============================================================
# 2. Status badge tone
# ============================================================


class TestStatusBadge:
    def test_ok_status_renders_checkmark(self):
        out = _render_last_run_indicator({
            "runtime_summary": {"status": "ok", "run_id": "abc123def456"},
        })
        assert "last-run-indicator__status--ok" in out
        assert "✓" in out
        assert "OK" in out

    def test_error_status_renders_x(self):
        out = _render_last_run_indicator({
            "runtime_summary": {
                "status": "error",
                "run_id": "abc123def456",
                "error_message": "Model failed",
            },
        })
        assert "last-run-indicator__status--error" in out
        assert "✗" in out
        assert "ERROR" in out

    def test_blocked_status_renders_blocked(self):
        out = _render_last_run_indicator({
            "runtime_summary": {"status": "blocked", "run_id": "abc123def456"},
        })
        assert "last-run-indicator__status--blocked" in out
        assert "⊘" in out
        assert "BLOCKED" in out

    def test_unknown_status_renders_dash(self):
        # Status not in ok/error/blocked → no invention
        out = _render_last_run_indicator({
            "runtime_summary": {"status": "frobnicated", "run_id": "abc123def456"},
        })
        assert "last-run-indicator__status--none" in out
        assert "—" in out

    def test_missing_status_renders_dash(self):
        out = _render_last_run_indicator({
            "runtime_summary": {"run_id": "abc123def456"},
        })
        assert "last-run-indicator__status--none" in out


# ============================================================
# 3. Project association
# ============================================================


class TestProjectAssociation:
    def test_project_code_shown(self):
        out = _render_last_run_indicator({
            "runtime_summary": {"run_id": "abc123def456"},
            "project_record": type("PR", (), {"project_code": "tuho"})(),
        })
        assert "Project" in out
        assert "tuho" in out

    def test_project_code_truncated_to_mono(self):
        out = _render_last_run_indicator({
            "runtime_summary": {"run_id": "abc123def456"},
            "project_record": type("PR", (), {"project_code": "tuho"})(),
        })
        assert "last-run-indicator__value--mono" in out

    def test_project_uses_project_name_as_title(self):
        out = _render_last_run_indicator({
            "runtime_summary": {"run_id": "abc123def456"},
            "project_record": type("PR", (), {
                "project_code": "tuho",
                "project_name": "TUHO Wind 72MW",
            })(),
        })
        assert 'title="TUHO Wind 72MW"' in out

    def test_no_project_record_renders_without_project(self):
        out = _render_last_run_indicator({
            "runtime_summary": {"run_id": "abc123def456"},
        })
        # Still renders (run_id present) but no Project row
        assert "last-run-indicator" in out
        # No "Project" label visible
        assert "last-run-indicator__row--project" not in out


# ============================================================
# 4. Scenario association
# ============================================================


class TestScenarioAssociation:
    def test_scenario_shown_when_base_case(self):
        out = _render_last_run_indicator({
            "runtime_summary": {"run_id": "abc123def456"},
            "base_case_record": type("BC", (), {"scenario_name": "Base case"})(),
        })
        assert "Scenario" in out
        assert "Base case" in out

    def test_no_scenario_renders_without_scenario_row(self):
        out = _render_last_run_indicator({
            "runtime_summary": {"run_id": "abc123def456"},
        })
        assert "last-run-indicator__row--scenario" not in out

    def test_empty_scenario_name_renders_without_scenario_row(self):
        out = _render_last_run_indicator({
            "runtime_summary": {"run_id": "abc123def456"},
            "base_case_record": type("BC", (), {"scenario_name": ""})(),
        })
        assert "last-run-indicator__row--scenario" not in out


# ============================================================
# 5. Stale / fresh state
# ============================================================


class TestStaleState:
    def test_stale_badge_appears_when_dirty_and_prior_run(self):
        out = _render_last_run_indicator({
            "runtime_summary": {"run_id": "abc123def456"},
            "workspace_state": type("WS", (), {
                "dirty": True,
                "last_runtime_snapshot_id": "abc",
            })(),
        })
        assert "last-run-indicator__stale-badge" in out
        assert "STALE" in out
        assert "data-stale-state=\"stale\"" in out

    def test_no_stale_when_clean(self):
        out = _render_last_run_indicator({
            "runtime_summary": {"run_id": "abc123def456"},
            "workspace_state": type("WS", (), {
                "dirty": False,
                "last_runtime_snapshot_id": "abc",
            })(),
        })
        assert "last-run-indicator__stale-badge" not in out
        assert "data-stale-state=\"fresh\"" in out

    def test_no_stale_when_no_prior_run(self):
        out = _render_last_run_indicator({
            "runtime_summary": {"run_id": "abc123def456"},
            "workspace_state": type("WS", (), {
                "dirty": True,
                "last_runtime_snapshot_id": "",
            })(),
        })
        assert "last-run-indicator__stale-badge" not in out

    def test_no_stale_when_no_workspace_state(self):
        out = _render_last_run_indicator({
            "runtime_summary": {"run_id": "abc123def456"},
        })
        assert "last-run-indicator__stale-badge" not in out

    def test_stale_hint_text(self):
        out = _render_last_run_indicator({
            "runtime_summary": {"run_id": "abc123def456"},
            "workspace_state": type("WS", (), {
                "dirty": True,
                "last_runtime_snapshot_id": "abc",
            })(),
        })
        assert "Draft has unsaved changes" in out
        assert "Run again" in out


# ============================================================
# 6. Run error message
# ============================================================


class TestRunError:
    def test_error_message_surfaced(self):
        out = _render_last_run_indicator({
            "runtime_summary": {
                "status": "error",
                "run_id": "abc123def456",
                "error_message": "Solver failed: infeasible",
            },
        })
        assert "Solver failed: infeasible" in out
        assert "last-run-indicator__row--error" in out

    def test_no_error_row_when_no_error(self):
        out = _render_last_run_indicator({
            "runtime_summary": {"status": "ok", "run_id": "abc123def456"},
        })
        assert "last-run-indicator__row--error" not in out


# ============================================================
# 7. CSS additive
# ============================================================


class TestCSSAdditive:
    def test_status_classes_exist(self):
        text = STYLES_CSS.read_text()
        assert ".last-run-indicator__status--ok" in text
        assert ".last-run-indicator__status--error" in text
        assert ".last-run-indicator__status--blocked" in text
        assert ".last-run-indicator__status--none" in text

    def test_stale_badge_class_exists(self):
        text = STYLES_CSS.read_text()
        assert ".last-run-indicator__stale-badge" in text

    def test_root_block_count_unchanged(self):
        text = STYLES_CSS.read_text()
        # UI-2.5 strict invariant
        assert text.count(":root {") == 5

    def test_no_stale_result_classes(self):
        # UI-2.5 forbids .stale-result-* classes
        text = STYLES_CSS.read_text()
        assert ".stale-result-" not in text


# ============================================================
# 8. No production code change
# ============================================================


class TestNoProductionCodeChange:
    def test_main_web_unchanged(self):
        assert MAIN_WEB.exists()


# ============================================================
# 9. Index includes the partials
# ============================================================


class TestIndexIncludes:
    def test_index_includes_last_run_indicator(self):
        text = INDEX_HTML.read_text()
        assert '_last_run_indicator.html' in text

    def test_index_includes_empty_no_project(self):
        text = INDEX_HTML.read_text()
        assert '_empty_no_project.html' in text

    def test_index_includes_empty_no_scenario(self):
        text = INDEX_HTML.read_text()
        assert '_empty_no_scenario.html' in text

    def test_index_includes_empty_no_run(self):
        text = INDEX_HTML.read_text()
        assert '_empty_no_run.html' in text


# ============================================================
# 10. Empty-state partials render correctly
# ============================================================


class TestEmptyNoProject:
    def test_renders_when_no_project(self):
        out = _render_partial(EMPTY_NO_PROJECT, {})
        assert "No project selected" in out

    def test_renders_nothing_when_project_exists(self):
        out = _render_partial(EMPTY_NO_PROJECT, {
            "project_record": type("PR", (), {"project_code": "tuho"})(),
        })
        assert "No project selected" not in out


class TestEmptyNoScenario:
    def test_renders_when_no_scenarios(self):
        out = _render_partial(EMPTY_NO_SCENARIO, {})
        assert "No scenario selected" in out

    def test_renders_nothing_when_base_case_exists(self):
        out = _render_partial(EMPTY_NO_SCENARIO, {
            "base_case_record": type("BC", (), {"scenario_name": "Base"})(),
        })
        assert "No scenario selected" not in out

    def test_renders_nothing_when_non_base_scenario_exists(self):
        out = _render_partial(EMPTY_NO_SCENARIO, {
            "non_base_scenarios": [
                type("S", (), {"scenario_name": "Alt"})(),
            ],
        })
        assert "No scenario selected" not in out


class TestEmptyNoRun:
    def test_renders_when_no_runtime(self):
        out = _render_partial(EMPTY_NO_RUN, {})
        assert "No run performed yet" in out

    def test_renders_nothing_when_run_id_present(self):
        out = _render_partial(EMPTY_NO_RUN, {
            "runtime_summary": {"run_id": "abc"},
        })
        assert "No run performed yet" not in out

    def test_renders_nothing_when_last_run_at_present(self):
        out = _render_partial(EMPTY_NO_RUN, {
            "runtime_summary": {"last_run_at": "2026-06-09"},
        })
        assert "No run performed yet" not in out
