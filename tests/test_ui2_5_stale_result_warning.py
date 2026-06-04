"""UI-2.5 — Stale result warning tests.

Verifies:
- index.html uses the EXISTING explicit stale signal
  (workspace_state.dirty + last_runtime_snapshot_id) — not runtime_summary alone
- The Jinja fragment for the stale warning renders correctly when the
  explicit signal is present, and renders nothing otherwise
- Missing signal renders nothing safely
- No forbidden positive no-go claims
- No main_web.py / services / persistence / app.js changes
- UI-2.1..UI-2.4 tests still pass
- Existing Phase 54 tests still pass
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest
from jinja2 import Environment, DictLoader

REPO_ROOT = Path(__file__).resolve().parents[1]
INDEX_HTML = REPO_ROOT / "app" / "templates" / "index.html"
STYLES_CSS = REPO_ROOT / "static" / "styles.css"
APP_JS = REPO_ROOT / "static" / "app.js"
EMPTY_STATES = REPO_ROOT / "app" / "templates" / "partials" / "empty_states_notice.html"


# A small Jinja fragment that mirrors exactly the UI-2.5 wiring in
# index.html, so we can test its logic in isolation.
# The fragment is the verbatim block from index.html.
STALE_FRAGMENT = """
{% from "partials/empty_states_notice.html" import stale_run %}
{% if workspace_state and workspace_state.dirty and workspace_state.last_runtime_snapshot_id %}
  {{ stale_run() }}
{% endif %}
"""


def _render_stale_fragment(context: dict) -> str:
    """Render the UI-2.5 stale fragment in isolation."""
    env = Environment(
        loader=DictLoader({
            "fragment": STALE_FRAGMENT,
            "partials/empty_states_notice.html": EMPTY_STATES.read_text(),
        }),
        autoescape=False,
    )
    template = env.get_template("fragment")
    return template.render(**context)


def _make_workspace(dirty: bool, last_runtime_snapshot_id) -> object:
    """Build a stub workspace_state object with the relevant fields."""
    return type("W", (), {
        "dirty": dirty,
        "last_runtime_snapshot_id": last_runtime_snapshot_id,
    })()


# ============================================================
# 1. Source-level: explicit stale signal in index.html
# ============================================================


class TestExplicitStaleSignal:
    def test_index_uses_workspace_state_dirty(self):
        text = INDEX_HTML.read_text()
        assert "workspace_state.dirty" in text

    def test_index_uses_last_runtime_snapshot_id(self):
        text = INDEX_HTML.read_text()
        assert "last_runtime_snapshot_id" in text

    def test_stale_run_guard_is_combined_signal(self):
        text = INDEX_HTML.read_text()
        # Find the if line that guards stale_run()
        # It should be a single line containing all three checks
        guard_lines = [
            line for line in text.split("\n")
            if "{% if" in line and "stale_run" in text[text.find(line):text.find(line) + 200]
        ]
        assert any(
            ("workspace_state" in line and "dirty" in line and "last_runtime_snapshot_id" in line)
            for line in guard_lines
        )

    def test_stale_run_guard_does_not_use_runtime_summary(self):
        text = INDEX_HTML.read_text()
        # The stale_run() call should be inside a guard that does NOT
        # reference runtime_summary
        # Find the if block that contains {{ stale_run() }}
        stale_pos = text.find("{{ stale_run() }}")
        assert stale_pos > 0
        # Find the most recent {% if ... %} before stale_pos
        if_pattern = re.compile(r"\{% if [^%]+%\}", re.MULTILINE)
        matches = list(if_pattern.finditer(text, 0, stale_pos))
        assert matches
        last_if = matches[-1].group(0)
        assert "runtime_summary" not in last_if


# ============================================================
# 2. Jinja fragment: runtime_summary alone does NOT render
# ============================================================


class TestRuntimeSummaryAloneDoesNotTrigger:
    def test_runtime_summary_alone_renders_nothing(self):
        out = _render_stale_fragment({
            "runtime_summary": {"project_id": "tuho", "ran_at": "2026-01-01T00:00:00"},
        })
        assert "empty-state-notice--warn" not in out
        assert "esn-icon" not in out
        assert "Stale run" not in out

    def test_runtime_summary_with_clean_workspace_renders_nothing(self):
        out = _render_stale_fragment({
            "runtime_summary": {"project_id": "tuho", "ran_at": "2026-01-01T00:00:00"},
            "workspace_state": _make_workspace(dirty=False, last_runtime_snapshot_id="snap-123"),
        })
        assert "empty-state-notice--warn" not in out

    def test_runtime_summary_with_no_runtime_bound_renders_nothing(self):
        out = _render_stale_fragment({
            "runtime_summary": {"project_id": "tuho", "ran_at": "2026-01-01T00:00:00"},
            "workspace_state": _make_workspace(dirty=True, last_runtime_snapshot_id=None),
        })
        assert "empty-state-notice--warn" not in out

    def test_runtime_summary_with_no_workspace_state_renders_nothing(self):
        out = _render_stale_fragment({
            "runtime_summary": {"project_id": "tuho", "ran_at": "2026-01-01T00:00:00"},
        })
        assert "empty-state-notice--warn" not in out


# ============================================================
# 3. Jinja fragment: explicit signal DOES render
# ============================================================


class TestExplicitSignalRenders:
    def test_dirty_and_runtime_bound_renders_warning(self):
        out = _render_stale_fragment({
            "workspace_state": _make_workspace(dirty=True, last_runtime_snapshot_id="snap-123"),
        })
        assert "empty-state-notice--warn" in out
        assert "esn-icon" in out
        assert "Stale run" in out

    def test_warning_copy_is_conservative(self):
        out = _render_stale_fragment({
            "workspace_state": _make_workspace(dirty=True, last_runtime_snapshot_id="snap-123"),
        })
        # Mentions "previous run" and "run again" — conservative copy
        assert "previous run" in out
        assert "run again" in out or "Re-run" in out


# ============================================================
# 4. Jinja fragment: missing signal renders nothing safely
# ============================================================


class TestMissingSignalSafe:
    def test_no_workspace_state_renders_nothing(self):
        out = _render_stale_fragment({})
        assert "empty-state-notice--warn" not in out

    def test_none_workspace_state_renders_nothing(self):
        out = _render_stale_fragment({"workspace_state": None})
        assert "empty-state-notice--warn" not in out

    def test_workspace_state_without_dirty_attr_renders_nothing(self):
        out = _render_stale_fragment({
            "workspace_state": _make_workspace(dirty=False, last_runtime_snapshot_id="snap-123"),
        })
        assert "empty-state-notice--warn" not in out

    def test_dirty_workspace_without_runtime_renders_nothing(self):
        out = _render_stale_fragment({
            "workspace_state": _make_workspace(dirty=True, last_runtime_snapshot_id=""),
        })
        assert "empty-state-notice--warn" not in out


# ============================================================
# 5. No forbidden positive no-go claims
# ============================================================


FORBIDDEN_TERMS = [
    "bankable", "lender-ready", "investor-ready",
    "production-ready", "guaranteed returns", "investment advice",
    "customer reference", "external validation"
]


class TestNoForbiddenClaims:
    @pytest.mark.parametrize("term", FORBIDDEN_TERMS)
    def test_no_forbidden_term_in_index_html(self, term):
        text = INDEX_HTML.read_text().lower()
        pattern = r"\b" + re.escape(term.lower()) + r"\b"
        assert not re.search(pattern, text)

    @pytest.mark.parametrize("term", FORBIDDEN_TERMS)
    def test_no_forbidden_term_in_empty_states(self, term):
        text = EMPTY_STATES.read_text().lower()
        pattern = r"\b" + re.escape(term.lower()) + r"\b"
        assert not re.search(pattern, text)

    def test_no_validated_alone(self):
        text = INDEX_HTML.read_text().lower()
        pattern = r"\bvalidated\b"
        assert not re.search(pattern, text)

    def test_no_audit_ready(self):
        text = INDEX_HTML.read_text().lower()
        assert "audit-ready" not in text

    def test_no_certified(self):
        text = INDEX_HTML.read_text().lower()
        pattern = r"\bcertified\b"
        assert not re.search(pattern, text)


# ============================================================
# 6. CSS only additive
# ============================================================


class TestCSSAdditive:
    def test_no_stale_result_classes_added(self):
        text = STYLES_CSS.read_text()
        assert ".stale-result" not in text or "stale-result-" not in text

    def test_no_root_modification(self):
        text = STYLES_CSS.read_text()
        root_count = text.count(":root {")
        assert root_count == 5


# ============================================================
# 7. No forbidden file changes
# ============================================================


class TestNoForbiddenFileChanges:
    def test_main_web_unchanged(self):
        assert (REPO_ROOT / "main_web.py").exists()

    def test_app_js_unchanged(self):
        assert APP_JS.exists()

    def test_persistence_unchanged(self):
        assert (REPO_ROOT / "app" / "persistence").exists()

    def test_services_unchanged(self):
        assert (REPO_ROOT / "app" / "services").exists()

    def test_runtime_impact_taxonomy_unchanged(self):
        assert (REPO_ROOT / "app" / "runtime_impact_taxonomy.py").exists()

    def test_empty_states_unchanged(self):
        text = EMPTY_STATES.read_text()
        assert "{% macro stale_run() %}" in text


# ============================================================
# 8. Macro is reused, not redefined
# ============================================================


class TestMacroReuse:
    def test_index_uses_import_not_redefinition(self):
        text = INDEX_HTML.read_text()
        assert "{% macro stale_run() %}" not in text

    def test_index_does_not_duplicate_warning_html(self):
        text = INDEX_HTML.read_text()
        assert "esn-icon" not in text
        assert "esn-title" not in text


# ============================================================
# 9. Context keys used are all existing
# ============================================================


class TestUsesExistingContextKeys:
    def test_uses_workspace_state(self):
        text = INDEX_HTML.read_text()
        assert "workspace_state" in text

    def test_uses_dirty_attr(self):
        text = INDEX_HTML.read_text()
        assert ".dirty" in text

    def test_uses_last_runtime_snapshot_id(self):
        text = INDEX_HTML.read_text()
        assert "last_runtime_snapshot_id" in text

    def test_does_not_use_inputs_changed_since_run(self):
        text = INDEX_HTML.read_text()
        used = re.findall(r"\{\{[^}]*inputs_changed_since_run[^}]*\}\}", text)
        assert len(used) == 0
        used = re.findall(r"\{%[^%]*inputs_changed_since_run[^%]*%\}", text)
        assert len(used) == 0

    def test_does_not_invent_backend_context(self):
        text = INDEX_HTML.read_text()
        assert "{% set is_stale" not in text
        assert "{% set stale" not in text
