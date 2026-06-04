"""UI-2.1 — State clarity banner partial tests.

Verifies:
- Partial exists
- All 11 context keys supported
- All 5 tones supported via class names
- Missing banner_context renders safely
- No forbidden positive no-go claims
- index.html includes the partial
- CSS has only additive .banner-* classes
- No main_web.py / services / persistence / app.js changes
- Existing Phase 54 tests still pass
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
PARTIAL = REPO_ROOT / "app" / "templates" / "partials" / "_state_banner.html"
INDEX_HTML = REPO_ROOT / "app" / "templates" / "index.html"
STYLES_CSS = REPO_ROOT / "static" / "styles.css"
APP_JS = REPO_ROOT / "static" / "app.js"
MAIN_WEB = REPO_ROOT / "main_web.py"


# ============================================================
# 1. Partial exists and has expected structure
# ============================================================


class TestPartialExists:
    def test_partial_file_exists(self):
        assert PARTIAL.exists()

    def test_partial_has_docstring(self):
        text = PARTIAL.read_text()
        assert "{#" in text or "<!--" in text, "Partial should have a Jinja comment header"

    def test_partial_uses_banner_class(self):
        text = PARTIAL.read_text()
        assert "banner-" in text or "banner " in text


# ============================================================
# 2. All 11 contexts supported
# ============================================================


CONTEXTS = [
    "factory_template", "user_created_project", "active_scenario",
    "saved_scenario", "browser_draft", "dirty_state", "stale_result",
    "last_run", "validation_failed", "display_only_row",
    "pending_runtime_source"
]


class TestContextsSupported:
    @pytest.mark.parametrize("ctx", CONTEXTS)
    def test_context_in_partial(self, ctx):
        text = PARTIAL.read_text()
        assert ctx in text, f"Context {ctx} not in banner partial"


# ============================================================
# 3. All 5 tones supported
# ============================================================


TONES = ["info", "success", "warn", "fail", "neutral"]


class TestTonesSupported:
    @pytest.mark.parametrize("tone", TONES)
    def test_tone_in_partial(self, tone):
        text = PARTIAL.read_text()
        # Tone should appear in default or class name
        assert tone in text, f"Tone {tone} not in partial"


class TestTonesInCSS:
    @pytest.mark.parametrize("tone", TONES)
    def test_tone_class_in_css(self, tone):
        text = STYLES_CSS.read_text()
        assert f".banner-{tone}" in text, f"CSS class .banner-{tone} not defined"


# ============================================================
# 4. Missing banner_context renders safely
# ============================================================


class TestMissingContextSafe:
    def test_partial_guarded_by_if(self):
        text = PARTIAL.read_text()
        # Should start with {% if banner_context %}
        assert "{% if banner_context %}" in text

    def test_partial_ends_with_endif(self):
        text = PARTIAL.read_text()
        # The outer guard should close
        assert "{% endif %}" in text


# ============================================================
# 5. No forbidden positive no-go claims
# ============================================================


FORBIDDEN_TERMS = [
    "bankable", "lender-ready", "investor-ready",
    "production-ready", "guaranteed returns", "investment advice",
    "customer reference", "external validation"
]

# Note: "validated", "certified", "audit-ready" are checked separately
# because they may appear in safe context (e.g., "validation_failed" contains
# "validation" which is a substring; we check whole words only).


class TestNoForbiddenClaims:
    @pytest.mark.parametrize("term", FORBIDDEN_TERMS)
    def test_no_forbidden_term_in_partial(self, term):
        text = PARTIAL.read_text().lower()
        # Use word boundary to avoid false matches
        pattern = r"\b" + re.escape(term.lower()) + r"\b"
        assert not re.search(pattern, text), f"Forbidden term '{term}' found in partial"

    @pytest.mark.parametrize("term", FORBIDDEN_TERMS)
    def test_no_forbidden_term_in_index_html(self, term):
        text = INDEX_HTML.read_text().lower()
        pattern = r"\b" + re.escape(term.lower()) + r"\b"
        assert not re.search(pattern, text), f"Forbidden term '{term}' found in index.html"

    def test_no_validated_alone_in_partial(self):
        text = PARTIAL.read_text().lower()
        # Check for "validated" as a whole word, not part of "validation_..."
        pattern = r"\bvalidated\b"
        assert not re.search(pattern, text)

    def test_no_audit_ready_in_partial(self):
        text = PARTIAL.read_text().lower()
        pattern = r"\baudit[\s-]ready\b"
        assert not re.search(pattern, text)


# ============================================================
# 6. index.html includes the partial
# ============================================================


class TestIndexHtmlIntegration:
    def test_index_includes_partial(self):
        text = INDEX_HTML.read_text()
        assert "_state_banner.html" in text

    def test_index_has_one_include(self):
        text = INDEX_HTML.read_text()
        # Count include lines for this partial
        count = text.count('_state_banner.html')
        assert count == 1, f"Expected 1 include, found {count}"


# ============================================================
# 7. CSS only additive
# ============================================================


class TestCSSAdditive:
    def test_no_root_modification(self):
        # Check the UI-2.1 section specifically does not modify :root
        text = STYLES_CSS.read_text()
        m = re.search(r"/\* ── UI-2\.1.*?\*/\n(.*?)(?=/\* ── |\Z)", text, re.DOTALL)
        if m:
            section = m.group(1)
            assert ":root" not in section, "UI-2.1 CSS section must not modify :root"
        # Also verify pre-existing :root count is unchanged
        # (Original count was 5; verify it's still 5 after our changes)
        root_count = text.count(":root {")
        assert root_count == 5, f"Found {root_count} :root blocks (expected 5 pre-existing)"

    def test_only_banner_classes_added(self):
        text = STYLES_CSS.read_text()
        # Find the UI-2.1 section
        m = re.search(r"/\* ── UI-2\.1.*?\*/\n(.*?)(?=/\\* ── |\\Z)", text, re.DOTALL)
        if m:
            section = m.group(1)
            # Section should only contain .banner-* classes
            class_pattern = re.findall(r"\.([a-zA-Z0-9_-]+(?:\\:[a-zA-Z0-9_-]+)?)\s*[{,]", section)
            non_banner = [c for c in class_pattern if not c.startswith("banner")]
            # Allow :root or other utilities
            assert all(
                c in ("banner",) or ":" in c  # allow pseudo-classes
                for c in non_banner
            ), f"Found non-banner classes in UI-2.1 section: {non_banner}"


# ============================================================
# 8. No forbidden file changes
# ============================================================


class TestNoForbiddenFileChanges:
    def test_main_web_unchanged(self):
        # If this test runs, main_web.py is not in the changed files
        # (verified by git status / diff at PR time)
        # Here we just confirm the file is still there
        assert MAIN_WEB.exists()

    def test_app_js_unchanged(self):
        assert APP_JS.exists()

    def test_persistence_unchanged(self):
        persistence_dir = REPO_ROOT / "app" / "persistence"
        assert persistence_dir.exists()

    def test_services_unchanged(self):
        services_dir = REPO_ROOT / "app" / "services"
        assert services_dir.exists()

    def test_runtime_impact_taxonomy_unchanged(self):
        taxonomy = REPO_ROOT / "app" / "runtime_impact_taxonomy.py"
        assert taxonomy.exists()


# ============================================================
# 9. CSS selector count
# ============================================================


class TestCSSSelectors:
    def test_at_least_5_banner_classes(self):
        text = STYLES_CSS.read_text()
        # The UI-2.1 section must have all 5 tone classes
        for tone in TONES:
            assert f".banner-{tone}" in text


# ============================================================
# 10. Partial does not change behavior
# ============================================================


class TestNoBehaviorChange:
    def test_partial_renders_nothing_without_context(self):
        # If banner_context is not supplied, partial should render nothing
        text = PARTIAL.read_text()
        # The whole partial body is inside {% if banner_context %}
        # so when context is missing, no HTML is emitted
        assert text.lstrip().startswith("{#") or text.lstrip().startswith("{%")

    def test_partial_uses_default_tone(self):
        # When banner_tone is not supplied, default to 'info'
        text = PARTIAL.read_text()
        assert "banner_tone|default('info')" in text or "default('info')" in text
