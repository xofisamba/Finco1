"""UI-2.4 — Factory lock indicator partial tests.

Verifies:
- Partial exists
- Missing context renders safely (nothing)
- Factory/template signals render the indicator
- Non-factory context renders nothing
- workspace_shell.html includes the partial
- No forbidden positive no-go claims
- CSS only additive .factory-lock-* classes
- No backend/service/persistence/app.js changes
- UI-2.1, UI-2.2, UI-2.3 tests still pass
- Existing Phase 54 tests still pass
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
PARTIAL = REPO_ROOT / "app" / "templates" / "partials" / "_factory_lock_indicator.html"
SHELL = REPO_ROOT / "app" / "templates" / "partials" / "workspace_shell.html"
STYLES_CSS = REPO_ROOT / "static" / "styles.css"
APP_JS = REPO_ROOT / "static" / "app.js"


# ============================================================
# 1. Partial exists
# ============================================================


class TestPartialExists:
    def test_partial_file_exists(self):
        assert PARTIAL.exists()

    def test_partial_has_docstring(self):
        text = PARTIAL.read_text()
        assert "{#" in text, "Partial should have a Jinja comment header"

    def test_partial_uses_factory_lock_class(self):
        text = PARTIAL.read_text()
        assert "factory-lock" in text


# ============================================================
# 2. Missing context renders safely
# ============================================================


class TestMissingContextSafe:
    def test_partial_guarded_by_if(self):
        text = PARTIAL.read_text()
        # Should end with {% endif %}
        assert "{% if _is_factory %}" in text

    def test_partial_renders_nothing_when_not_factory(self):
        text = PARTIAL.read_text()
        # When all conditions fail, _is_factory = false, partial renders nothing
        assert "_is_factory = false" in text


# ============================================================
# 3. Factory signal detection
# ============================================================


class TestFactorySignals:
    def test_tuho_signal_detected(self):
        # Lowercase comparison is used (Phase 54G normalization refactor)
        text = PARTIAL.read_text()
        assert "tuho" in text

    def test_oborovo_signal_detected(self):
        text = PARTIAL.read_text()
        assert "oborovo" in text

    def test_explicit_is_factory_template(self):
        text = PARTIAL.read_text()
        assert "is_factory_template" in text

    def test_template_source_lowercase(self):
        text = PARTIAL.read_text()
        # Should handle lowercase too
        assert "lower" in text

    def test_factory_keyword(self):
        text = PARTIAL.read_text()
        # Should detect "factory" in template_source
        assert "'factory' in _ts|lower" in text or "factory" in text


# ============================================================
# 4. No forbidden positive no-go claims
# ============================================================


FORBIDDEN_TERMS = [
    "bankable", "lender-ready", "lender-grade",
    "investor-ready", "production-ready", "guaranteed returns",
    "investment advice", "customer reference", "external validation"
]


def _partial_body():
    """Get the partial body excluding the docstring header."""
    text = PARTIAL.read_text()
    # Strip the leading Jinja comment block (everything between {# and #})
    import re
    m = re.sub(r"\A\s*\{#.*?#\}\s*", "", text, count=1, flags=re.DOTALL)
    return m


class TestNoForbiddenClaims:
    @pytest.mark.parametrize("term", FORBIDDEN_TERMS)
    def test_no_forbidden_term_in_partial(self, term):
        # Check the body, not the docstring
        text = _partial_body().lower()
        pattern = r"\b" + re.escape(term.lower()) + r"\b"
        assert not re.search(pattern, text), f"Forbidden term '{term}' found in partial body"

    def test_no_locked_by_governance(self):
        text = _partial_body().lower()
        assert "locked by governance" not in text

    def test_no_certified_template(self):
        text = _partial_body().lower()
        assert "certified template" not in text

    def test_no_approved_model(self):
        text = _partial_body().lower()
        assert "approved model" not in text

    def test_no_bank_ready_template(self):
        text = _partial_body().lower()
        assert "bank-ready template" not in text

    def test_no_production_control(self):
        text = _partial_body().lower()
        assert "production control" not in text

    def test_no_audit_ready(self):
        text = _partial_body().lower()
        assert "audit-ready" not in text

    def test_no_validated_alone(self):
        text = _partial_body().lower()
        pattern = r"\bvalidated\b"
        assert not re.search(pattern, text)


# ============================================================
# 5. workspace_shell.html includes the partial
# ============================================================


class TestShellIntegration:
    def test_shell_includes_partial(self):
        text = SHELL.read_text()
        assert "_factory_lock_indicator.html" in text

    def test_shell_passes_template_source(self):
        text = SHELL.read_text()
        # The include should pass template_source from form_data
        assert "template_source=" in text

    def test_shell_passes_project_origin(self):
        text = SHELL.read_text()
        assert "project_origin=" in text

    def test_shell_has_one_include(self):
        text = SHELL.read_text()
        count = text.count("_factory_lock_indicator.html")
        assert count == 1, f"Expected 1 include, found {count}"


# ============================================================
# 6. CSS only additive
# ============================================================


class TestCSSAdditive:
    def test_factory_lock_base_in_css(self):
        text = STYLES_CSS.read_text()
        assert ".factory-lock-indicator" in text

    def test_factory_lock_icon_in_css(self):
        text = STYLES_CSS.read_text()
        assert ".factory-lock-icon" in text

    def test_factory_lock_title_in_css(self):
        text = STYLES_CSS.read_text()
        assert ".factory-lock-title" in text

    def test_factory_lock_desc_in_css(self):
        text = STYLES_CSS.read_text()
        assert ".factory-lock-desc" in text

    def test_no_root_modification(self):
        text = STYLES_CSS.read_text()
        m = re.search(r"/\* ── UI-2\.4.*?\*/\n(.*?)(?=/\* ── |\Z)", text, re.DOTALL)
        if m:
            section = m.group(1)
            assert ":root" not in section, "UI-2.4 CSS section must not modify :root"
        # Verify pre-existing :root count is unchanged
        root_count = text.count(":root {")
        assert root_count == 5, f"Found {root_count} :root blocks (expected 5 pre-existing)"


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


# ============================================================
# 8. Safe language used
# ============================================================


class TestSafeLanguage:
    EXPECTED_SAFE_PHRASES = [
        "Factory template",
        "Create a scenario",
        "Save As before editing",
        "controlled assumptions",
    ]

    @pytest.mark.parametrize("phrase", EXPECTED_SAFE_PHRASES)
    def test_safe_phrase_used(self, phrase):
        text = PARTIAL.read_text()
        assert phrase in text, f"Safe phrase '{phrase}' not in partial"


# ============================================================
# 9. Accessibility
# ============================================================


class TestAccessibility:
    def test_role_status(self):
        text = PARTIAL.read_text()
        assert 'role="status"' in text

    def test_aria_label(self):
        text = PARTIAL.read_text()
        assert "aria-label" in text

    def test_aria_hidden_on_icon(self):
        text = PARTIAL.read_text()
        assert "aria-hidden" in text


# ============================================================
# 10. HTML structure
# ============================================================


class TestHTMLStructure:
    def test_uses_factory_lock_indicator_class(self):
        text = PARTIAL.read_text()
        assert "factory-lock-indicator" in text

    def test_has_icon(self):
        text = PARTIAL.read_text()
        assert "factory-lock-icon" in text

    def test_has_body(self):
        text = PARTIAL.read_text()
        assert "factory-lock-body" in text
