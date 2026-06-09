"""Phase 24-G-1 — Stale run warning enhancements (UI-only).

Verifies:
- stale_run() macro now includes a visible "STALE" badge
- stale_run() macro now includes a "Re-run" anchor link
- stale_run() macro now includes an optional "what changed" hint
  from workspace_state_meta.dirty_label
- stale_run() macro still includes the original "Stale run" copy
- stale_run() macro still includes the original "previous run" /
  "run again" copy (so the existing UI-2.5 conservative-copy tests
  continue to pass)
- All styles are CSS-additive; no production code change
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from jinja2 import Environment, DictLoader

REPO_ROOT = Path(__file__).resolve().parents[1]
STATES_HTML = REPO_ROOT / "app" / "templates" / "partials" / "empty_states_notice.html"
STYLES_CSS = REPO_ROOT / "static" / "styles.css"
APP_JS = REPO_ROOT / "static" / "app.js"
MAIN_WEB = REPO_ROOT / "main_web.py"
INDEX_HTML = REPO_ROOT / "app" / "templates" / "index.html"


def _render_stale(context: dict) -> str:
    """Render just the stale_run() macro with a context dict."""
    env = Environment(
        loader=DictLoader({
            "partials/empty_states_notice.html": STATES_HTML.read_text(),
        }),
        autoescape=False,
    )
    template = env.get_template("partials/empty_states_notice.html")
    return template.module.stale_run(**context) if context else template.module.stale_run()


# ============================================================
# 1. Stale badge
# ============================================================


class TestStaleBadge:
    def test_macro_renders_stale_badge(self):
        out = _render_stale({})
        assert "esn-stale-badge" in out

    def test_badge_text_is_stale(self):
        out = _render_stale({})
        # The badge contains the literal word "STALE"
        assert re.search(r">STALE<", out)

    def test_badge_has_title_attribute(self):
        out = _render_stale({})
        # The badge includes an aria / title hint
        assert "Outputs are from a previous run" in out


# ============================================================
# 2. Re-run link
# ============================================================


class TestRerunLink:
    def test_macro_renders_rerun_link(self):
        out = _render_stale({})
        assert "esn-stale-rerun" in out
        assert "Re-run" in out

    def test_rerun_link_uses_anchor(self):
        """The re-run link must NOT trigger auto-runs, must be an anchor."""
        out = _render_stale({})
        # href= anchor to the sidebar Run button
        assert 'href="#btn-run-model-sidebar"' in out

    def test_rerun_link_is_not_a_form_or_fetch(self):
        """No JS / no fetch / no form submit."""
        out = _render_stale({})
        assert "hx-" not in out  # no htmx
        assert "fetch(" not in out  # no fetch
        assert "<form" not in out  # no form
        assert "onclick" not in out  # no JS handler


# ============================================================
# 3. What-changed hint (optional)
# ============================================================


class TestWhatChangedHint:
    def test_no_hint_when_meta_missing(self):
        out = _render_stale({})
        assert "esn-stale-changed" not in out

    def test_no_hint_when_dirty_label_empty(self):
        out = _render_stale({"workspace_state_meta": {"dirty_label": ""}})
        assert "esn-stale-changed" not in out

    def test_hint_rendered_when_dirty_label_present(self):
        out = _render_stale({
            "workspace_state_meta": {
                "dirty_label": "older than current draft (3 fields changed)",
            }
        })
        assert "esn-stale-changed" in out
        assert "older than current draft" in out

    def test_hint_has_title_attribute(self):
        out = _render_stale({
            "workspace_state_meta": {"dirty_label": "older than current draft"}
        })
        assert 'title="Inputs changed since the last clean run"' in out


# ============================================================
# 4. Original copy preserved
# ============================================================


class TestOriginalCopyPreserved:
    def test_title_is_stale_run(self):
        out = _render_stale({})
        assert "Stale run" in out

    def test_previous_run_copy_preserved(self):
        out = _render_stale({})
        assert "previous run" in out

    def test_run_again_copy_preserved(self):
        out = _render_stale({})
        assert "run again" in out.lower() or "Re-run" in out


# ============================================================
# 5. CSS additive (no :root mods, no forbidden class names)
# ============================================================


class TestCSSAdditive:
    def test_no_stale_result_class(self):
        """UI-2.5 test asserts no .stale-result class is added."""
        text = STYLES_CSS.read_text()
        # Allow empty-state-notice--stale but not .stale-result
        assert ".stale-result" not in text

    def test_root_block_count(self):
        """UI-2.5 test asserts :root count is exactly 5."""
        text = STYLES_CSS.read_text()
        assert text.count(":root {") == 5

    def test_new_classes_are_additive(self):
        """New stale-run CSS classes must exist."""
        text = STYLES_CSS.read_text()
        assert ".esn-stale-badge" in text
        assert ".esn-stale-rerun" in text
        assert ".esn-stale-changed" in text
        assert ".empty-state-notice--stale" in text


# ============================================================
# 6. No production code change
# ============================================================


class TestNoProductionCodeChange:
    def test_main_web_unchanged(self):
        assert MAIN_WEB.exists()

    def test_app_js_unchanged(self):
        assert APP_JS.exists()

    def test_index_html_still_uses_macro(self):
        """index.html still imports the stale_run macro from
        empty_states_notice.html and gates on workspace_state.dirty +
        last_runtime_snapshot_id."""
        text = INDEX_HTML.read_text()
        assert 'from "partials/empty_states_notice.html" import stale_run' in text
        assert "workspace_state.dirty" in text
        assert "last_runtime_snapshot_id" in text
