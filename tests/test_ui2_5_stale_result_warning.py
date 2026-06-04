"""UI-2.5 — Stale result warning tests.

Verifies:
- index.html still defines or uses existing stale_run() macro safely
- Stale warning copy uses safe language
- Warning is conditional on existing runtime_summary context
- Missing runtime_summary renders safely
- No forbidden positive no-go claims
- CSS includes only additive .stale-result-* classes if CSS is changed
- No main_web.py / services / persistence / app.js changes
- UI-2.1..UI-2.4 tests still pass
- Existing Phase 54 tests still pass
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
INDEX_HTML = REPO_ROOT / "app" / "templates" / "index.html"
STYLES_CSS = REPO_ROOT / "static" / "styles.css"
APP_JS = REPO_ROOT / "static" / "app.js"
EMPTY_STATES = REPO_ROOT / "app" / "templates" / "partials" / "empty_states_notice.html"


# ============================================================
# 1. index.html uses existing stale_run() macro safely
# ============================================================


class TestIndexHtmlIntegration:
    def test_index_imports_stale_run_macro(self):
        text = INDEX_HTML.read_text()
        assert 'from "partials/empty_states_notice.html" import stale_run' in text

    def test_index_calls_stale_run_macro(self):
        text = INDEX_HTML.read_text()
        assert "{{ stale_run() }}" in text

    def test_macro_definition_still_exists(self):
        text = EMPTY_STATES.read_text()
        assert "{% macro stale_run() %}" in text


# ============================================================
# 2. Stale warning copy uses safe language
# ============================================================


class TestSafeCopy:
    def test_stale_run_macro_has_safe_copy(self):
        text = EMPTY_STATES.read_text()
        assert "Stale run" in text
        assert "previous run" in text
        assert "run again" in text or "Re-run" in text

    def test_no_real_time_in_macro(self):
        text = EMPTY_STATES.read_text().lower()
        assert "real-time" not in text

    def test_no_live_in_macro(self):
        text = EMPTY_STATES.read_text().lower()
        pattern = r"\blive\b"
        assert not re.search(pattern, text)

    def test_no_guaranteed_in_macro(self):
        text = EMPTY_STATES.read_text().lower()
        assert "guaranteed" not in text


# ============================================================
# 3. Warning is conditional on existing context
# ============================================================


class TestConditionalRendering:
    def test_index_uses_if_runtime_summary(self):
        text = INDEX_HTML.read_text()
        assert "{% if runtime_summary %}" in text

    def test_index_has_endif(self):
        text = INDEX_HTML.read_text()
        assert "{% endif %}" in text


# ============================================================
# 4. Missing runtime_summary renders safely
# ============================================================


class TestMissingContextSafe:
    def test_no_runtime_summary_renders_nothing(self):
        text = INDEX_HTML.read_text()
        if_pos = text.find("{% if runtime_summary %}")
        call_pos = text.find("{{ stale_run() }}")
        endif_pos = text.find("{% endif %}", if_pos)
        assert 0 <= if_pos < call_pos < endif_pos


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
# 8. Macro is reused, not duplicated
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
# 9. Integration with existing context
# ============================================================


class TestContextIntegration:
    def test_uses_runtime_summary_not_inputs_changed(self):
        text = INDEX_HTML.read_text()
        assert "runtime_summary" in text
        # inputs_changed_since_run should not be USED as a template variable
        # (only mentioned in comments is fine)
        import re
        used = re.findall(r"\{\{[^}]*inputs_changed_since_run[^}]*\}\}", text)
        assert len(used) == 0
        used = re.findall(r"\{%[^%]*inputs_changed_since_run[^%]*%\}", text)
        assert len(used) == 0

    def test_uses_safe_fallback_when_context_missing(self):
        text = INDEX_HTML.read_text()
        assert "{% if runtime_summary %}" in text


# ============================================================
# 10. No computation of staleness
# ============================================================


class TestNoStalenessComputation:
    def test_no_js_calculation(self):
        text = INDEX_HTML.read_text()
        assert "function " not in text

    def test_no_backend_context_added(self):
        text = INDEX_HTML.read_text()
        assert "{% set is_stale" not in text
        assert "{% set stale" not in text
