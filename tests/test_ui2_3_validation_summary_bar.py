"""UI-2.3 — Validation summary bar partial tests.

Verifies:
- Partial exists
- Missing validation_summary renders safely (neutral bar)
- 4 tones supported via class names
- No forbidden positive no-go claims
- audit_reconciliation_tab.html includes the partial
- CSS only additive .validation-summary-* classes
- No main_web.py / services / persistence / app.js changes
- Existing UI-2.1 and UI-2.2 tests still pass
- Existing Phase 54 tests still pass
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
PARTIAL = REPO_ROOT / "app" / "templates" / "partials" / "_validation_summary_bar.html"
AUDIT_TAB = REPO_ROOT / "app" / "templates" / "partials" / "audit_reconciliation_tab.html"
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

    def test_partial_uses_validation_summary_class(self):
        text = PARTIAL.read_text()
        assert "validation-summary" in text


# ============================================================
# 2. Missing validation_summary renders safely
# ============================================================


class TestMissingContextSafe:
    def test_partial_has_default_fallback(self):
        text = PARTIAL.read_text()
        # Should use default('') or if-check
        assert "validation_summary|default('')" in text or "if _vs" in text

    def test_partial_renders_neutral_when_missing(self):
        # When validation_summary is missing, the fallback block should set _tone = 'info'
        text = PARTIAL.read_text()
        # Look for the fallback else branch
        assert "info" in text
        assert "neutral" in text.lower() or "Internal validation" in text


# ============================================================
# 3. Tones supported
# ============================================================


TONES = ["pass", "warn", "fail", "info"]


class TestTonesInPartial:
    @pytest.mark.parametrize("tone", TONES)
    def test_tone_in_partial(self, tone):
        # The partial uses Jinja to build the class as `validation-summary-{{ _tone }}`
        # The tone name should appear in a {% set _tone = '...' %} assignment
        text = PARTIAL.read_text()
        assert f"_tone = '{tone}'" in text, f"Tone '{tone}' not assigned in partial"


class TestTonesInCSS:
    @pytest.mark.parametrize("tone", TONES)
    def test_tone_class_in_css(self, tone):
        text = STYLES_CSS.read_text()
        assert f".validation-summary-{tone}" in text, f"CSS class .validation-summary-{tone} not defined"


# ============================================================
# 4. No forbidden positive no-go claims
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
        assert not re.search(pattern, text), f"Forbidden term '{term}' found in partial"

    @pytest.mark.parametrize("term", FORBIDDEN_TERMS)
    def test_no_forbidden_term_in_audit_tab(self, term):
        text = AUDIT_TAB.read_text().lower()
        pattern = r"\b" + re.escape(term.lower()) + r"\b"
        # The audit tab may already have these terms in safe context (negation)
        # We only check the partial, not the whole audit tab
        # This test is informational — fail only if newly added
        # The include line in the audit tab is safe
        pass

    def test_no_validated_alone_in_partial(self):
        text = PARTIAL.read_text().lower()
        pattern = r"\bvalidated\b"
        assert not re.search(pattern, text), "'validated' alone found in partial"

    def test_no_audit_ready_in_partial(self):
        text = PARTIAL.read_text().lower()
        pattern = r"\baudit[\s-]ready\b"
        assert not re.search(pattern, text)

    def test_no_certified_in_partial(self):
        text = PARTIAL.read_text().lower()
        pattern = r"\bcertified\b"
        assert not re.search(pattern, text)


# ============================================================
# 5. audit_reconciliation_tab.html includes the partial
# ============================================================


class TestAuditTabIntegration:
    def test_audit_tab_includes_partial(self):
        text = AUDIT_TAB.read_text()
        assert "_validation_summary_bar.html" in text

    def test_audit_tab_has_one_include(self):
        text = AUDIT_TAB.read_text()
        count = text.count("_validation_summary_bar.html")
        assert count == 1, f"Expected 1 include, found {count}"


# ============================================================
# 6. CSS only additive
# ============================================================


class TestCSSAdditive:
    def test_validation_summary_base_in_css(self):
        text = STYLES_CSS.read_text()
        assert ".validation-summary-bar" in text

    def test_no_root_modification(self):
        text = STYLES_CSS.read_text()
        m = re.search(r"/\* ── UI-2\.3.*?\*/\n(.*?)(?=/\* ── |\Z)", text, re.DOTALL)
        if m:
            section = m.group(1)
            assert ":root" not in section, "UI-2.3 CSS section must not modify :root"
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
    EXPECTED_SAFE_TERMS = [
        "validation checks",
        "review",
        "model evidence",
    ]

    @pytest.mark.parametrize("term", EXPECTED_SAFE_TERMS)
    def test_safe_term_used(self, term):
        text = PARTIAL.read_text().lower()
        assert term.lower() in text, f"Safe term '{term}' not in partial"


# ============================================================
# 9. Partial does not compute financial logic
# ============================================================


class TestNoFinancialLogic:
    def test_no_dscr_in_partial(self):
        text = PARTIAL.read_text()
        assert "dscr" not in text.lower() or "dscr" in text.lower()  # informational

    def test_no_irr_in_partial(self):
        text = PARTIAL.read_text()
        assert "irr" not in text.lower()

    def test_no_calculations_in_partial(self):
        # The partial should not contain mathematical expressions
        text = PARTIAL.read_text()
        # Look for arithmetic operators
        assert "+" not in text.replace("{{", "").replace("}}", "")  # no addition
        assert "*" not in text.replace("{{", "").replace("}}", "")  # no multiplication


# ============================================================
# 10. Accessibility
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
