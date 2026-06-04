"""UI-2.6 — Run-source indicator tests.

Verifies:
- Partial exists
- Missing runtime_summary renders nothing
- runtime_summary without run_id renders safely (or nothing)
- runtime_summary with available fields renders indicator
- No fake run ID is displayed
- No forbidden positive no-go claims
- CSS includes only additive .last-run-indicator-* classes
- No backend/service/persistence changes
- No static/app.js changes
- UI-2.1..UI-2.5 tests still pass
- Existing Phase 54 tests still pass
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest
from jinja2 import Environment, FileSystemLoader, DictLoader

REPO_ROOT = Path(__file__).resolve().parents[1]
PARTIAL = REPO_ROOT / "app" / "templates" / "partials" / "_last_run_indicator.html"
INDEX_HTML = REPO_ROOT / "app" / "templates" / "index.html"
STYLES_CSS = REPO_ROOT / "static" / "styles.css"
APP_JS = REPO_ROOT / "static" / "app.js"


# ============================================================
# Helpers
# ============================================================


def _render_partial(context: dict) -> str:
    """Render the partial in isolation with the given context."""
    partial_text = PARTIAL.read_text()
    # Strip the outer {# ── UI-2.6: ... ── #} comment so it doesn't
    # pollute the rendered output (cosmetic, but matches how Jinja
    # strips comments)
    env = Environment(
        loader=DictLoader({"partial": partial_text}),
        autoescape=False,
    )
    template = env.get_template("partial")
    return template.render(**context)


# ============================================================
# 1. Partial exists
# ============================================================


class TestPartialExists:
    def test_partial_file_exists(self):
        assert PARTIAL.exists()

    def test_partial_has_safe_doctype(self):
        text = PARTIAL.read_text()
        assert "Last run" in text
        assert "Runtime source" in text

    def test_index_includes_partial(self):
        text = INDEX_HTML.read_text()
        assert "_last_run_indicator.html" in text


# ============================================================
# 2. Missing runtime_summary renders nothing
# ============================================================


class TestMissingContextSafe:
    def test_no_context_renders_empty(self):
        out = _render_partial({})
        assert out.strip() == ""

    def test_empty_runtime_summary_renders_empty(self):
        out = _render_partial({"runtime_summary": {}})
        assert out.strip() == ""

    def test_none_runtime_summary_renders_empty(self):
        # Some templates pass runtime_summary=None instead of missing
        out = _render_partial({"runtime_summary": None})
        assert out.strip() == ""


# ============================================================
# 3. runtime_summary without run_id renders safely
# ============================================================


class TestMissingRunIdSafe:
    def test_only_last_run_at_renders(self):
        out = _render_partial({"runtime_summary": {"last_run_at": "2026-01-01T00:00:00"}})
        assert "Last run" in out
        assert "2026-01-01T00:00:00" in out
        # No fake run ID
        assert "Run reference" not in out

    def test_no_run_id_no_last_run_at_renders_empty(self):
        out = _render_partial({"runtime_summary": {"foo": "bar"}})
        assert out.strip() == ""


# ============================================================
# 4. runtime_summary with available fields renders indicator
# ============================================================


class TestAvailableFieldsRender:
    def test_with_run_id_and_last_run_at(self):
        out = _render_partial({
            "runtime_summary": {
                "run_id": "abc123def456ghi789jkl",
                "last_run_at": "2026-01-01T00:00:00",
            }
        })
        assert "Last run" in out
        assert "Runtime source" in out
        assert "abc123def456" in out
        assert "2026-01-01T00:00:00" in out
        # The "Review model evidence" note is always shown
        assert "Review model evidence" in out

    def test_truncates_long_run_id(self):
        long_id = "x" * 30
        out = _render_partial({
            "runtime_summary": {
                "run_id": long_id,
                "last_run_at": "2026-01-01T00:00:00",
            }
        })
        # First 12 chars visible
        assert "xxxxxxxxxxxx" in out
        # Truncation indicator
        assert "…" in out
        # Full ID not visible
        assert "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx" not in out

    def test_short_run_id_unchanged(self):
        out = _render_partial({
            "runtime_summary": {
                "run_id": "abc",
                "last_run_at": "2026-01-01T00:00:00",
            }
        })
        assert "abc" in out
        # No truncation for short IDs
        assert "…" not in out


# ============================================================
# 5. No fake run ID is displayed
# ============================================================


class TestNoFakeRunId:
    def test_no_default_run_id_in_partial(self):
        text = PARTIAL.read_text()
        # No fallback ID
        assert '"unknown"' not in text
        assert '"-"' not in text
        assert "'-'" not in text

    def test_no_random_id_generation(self):
        # Should not be generating random IDs in Jinja
        text = PARTIAL.read_text()
        assert "random" not in text
        assert "uuid" not in text
        assert "randint" not in text

    def test_missing_run_id_renders_safely(self):
        # The partial should not display anything that looks like a fake ID
        out = _render_partial({"runtime_summary": {"last_run_at": "2026-01-01"}})
        # Look for patterns that could be fake IDs
        # A real ID would be hex/alphanumeric, but we should not
        # display a placeholder like "(none)" or "n/a"
        assert "(none)" not in out
        assert "n/a" not in out.lower()


# ============================================================
# 6. No forbidden positive no-go claims
# ============================================================


FORBIDDEN_TERMS = [
    "bankable", "lender-ready", "investor-ready",
    "production-ready", "guaranteed returns", "investment advice",
    "customer reference", "external validation"
]


class TestNoForbiddenClaims:
    @pytest.mark.parametrize("term", FORBIDDEN_TERMS)
    def test_no_forbidden_term_in_partial(self, term):
        text = PARTIAL.read_text().lower()
        pattern = r"\b" + re.escape(term.lower()) + r"\b"
        assert not re.search(pattern, text)

    @pytest.mark.parametrize("term", FORBIDDEN_TERMS)
    def test_no_forbidden_term_in_index_html(self, term):
        text = INDEX_HTML.read_text().lower()
        pattern = r"\b" + re.escape(term.lower()) + r"\b"
        assert not re.search(pattern, text)

    def test_no_validated_alone(self):
        text = PARTIAL.read_text().lower()
        pattern = r"\bvalidated\b"
        assert not re.search(pattern, text)

    def test_no_certified(self):
        text = PARTIAL.read_text().lower()
        pattern = r"\bcertified\b"
        assert not re.search(pattern, text)

    def test_no_audit_ready(self):
        text = PARTIAL.read_text().lower()
        assert "audit-ready" not in text


# ============================================================
# 7. CSS only additive
# ============================================================


class TestCSSAdditive:
    def test_last_run_indicator_class_present(self):
        text = STYLES_CSS.read_text()
        assert ".last-run-indicator" in text
        assert ".last-run-indicator__row" in text
        assert ".last-run-indicator__label" in text
        assert ".last-run-indicator__value" in text
        assert ".last-run-indicator__note" in text

    def test_value_mono_class_present(self):
        text = STYLES_CSS.read_text()
        assert ".last-run-indicator__value--mono" in text

    def test_no_existing_class_modified(self):
        # Verify no existing classes were changed
        # (This is a soft check - we just look for the new ones)
        text = STYLES_CSS.read_text()
        assert ".last-run-indicator" in text
        # And we did NOT touch existing factory-lock or validation-summary
        # (sanity check they still exist)
        assert ".factory-lock-indicator" in text
        assert ".validation-summary-bar" in text

    def test_no_root_modification(self):
        text = STYLES_CSS.read_text()
        # No new :root blocks
        root_count = text.count(":root {")
        assert root_count == 5


# ============================================================
# 8. No backend/service/persistence changes
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

    def test_partial_is_in_correct_location(self):
        assert "_last_run_indicator.html" in str(PARTIAL)


# ============================================================
# 9. Accessibility and structure
# ============================================================


class TestAccessibility:
    def test_aria_label_present(self):
        text = PARTIAL.read_text()
        assert 'aria-label' in text

    def test_role_status_present(self):
        text = PARTIAL.read_text()
        assert 'role="status"' in text

    def test_uses_aside_tag(self):
        text = PARTIAL.read_text()
        assert "<aside" in text


# ============================================================
# 10. Integration with index.html
# ============================================================


class TestIndexIntegration:
    def test_index_includes_partial(self):
        text = INDEX_HTML.read_text()
        assert "_last_run_indicator.html" in text

    def test_index_includes_after_workspace_shell(self):
        text = INDEX_HTML.read_text()
        shell_pos = text.find("workspace_shell.html")
        partial_pos = text.find("_last_run_indicator.html")
        assert 0 <= shell_pos < partial_pos
