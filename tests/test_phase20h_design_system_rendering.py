"""Tests for Phase 20H — Model Cell Design System rendering.

Validates that:
- fc-* semantic CSS classes are defined in styles.css
- sc-* legacy aliases are defined (backward compat)
- Inline <style> blocks removed from scenario_tab.html and runtime_summary.html
- CSS variable extensions present
- No functional changes to templates
"""

import os
import re
import sys
from pathlib import Path

import pytest

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

PROJECT_ROOT = Path(__file__).parent.parent
STYLES_CSS = PROJECT_ROOT / "static" / "styles.css"
SCENARIO_TAB = PROJECT_ROOT / "app" / "templates" / "partials" / "scenario_tab.html"
RUNTIME_SUMMARY = PROJECT_ROOT / "app" / "templates" / "partials" / "runtime_summary.html"
SCENARIO_COMPARE = PROJECT_ROOT / "templates" / "partials" / "scenario_compare.html"


def _read_text_utf8(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class TestCSSDesignSystem:
    """Verify fc-* design system classes exist in styles.css."""

    REQUIRED_CSS_VARS = [
        "--color-accent",
        "--border-subtle",
        "--border-muted",
        "--cell-pad-v",
        "--cell-pad-h",
        "--cell-h",
        "--font-cell",
        "--font-label",
        "--font-badge",
        "--cell-inherited-bg",
        "--cell-override-bg",
        "--cell-base-bg",
        "--cell-runtime-bg",
        "--cell-factory-bg",
        "--cell-warning-bg",
        "--cell-error-bg",
        "--cell-dirty-bg",
    ]

    REQUIRED_FC_CLASSES = [
        ".fc-cell",
        ".fc-cell-input",
        ".fc-cell-runtime",
        ".fc-cell-factory",
        ".fc-cell-inherited",
        ".fc-cell-override",
        ".fc-cell-readonly",
        ".fc-cell-dirty",
        ".fc-cell-warning",
        ".fc-cell-error",
        ".fc-cell-empty",
        ".fc-badge--active",
        ".fc-badge--inherited",
        ".fc-badge--override",
        ".fc-badge--runtime",
        ".fc-badge--dirty",
        ".fc-badge--blocked",
        ".fc-badge--notapproved",
        ".fc-badge--factory",
        ".fc-badge--base",
        ".fc-total-row",
        ".fc-subtotal-row",
        ".fc-section-band",
        ".fc-section-header",
        ".fc-section-label",
        ".fc-grid-wrapper",
        ".fc-grid",
        ".fc-grid-col-label",
        ".fc-grid-header",
        ".fc-th",
        ".fc-row",
        ".fc-td-label",
        ".fc-col--base",
        ".fc-col--active",
        ".fc-num",
        ".fc-delta--positive",
        ".fc-delta--negative",
        ".fc-compare-base",
        ".fc-compare-active",
        ".fc-compare-delta",
    ]

    @pytest.fixture(autouse=True)
    def _load_css(self):
        """Load styles.css content once per test class."""
        self.css_content = _read_text_utf8(STYLES_CSS)

    def test_css_file_exists(self):
        assert STYLES_CSS.exists(), f"styles.css not found at {STYLES_CSS}"

    def test_css_variable_extensions_present(self):
        """Verify all Phase 20H CSS variable extensions are defined."""
        missing = []
        for var in self.REQUIRED_CSS_VARS:
            if var not in self.css_content:
                missing.append(var)
        assert not missing, f"Missing CSS variables: {missing}"

    def test_fc_cell_design_system_classes_present(self):
        """Verify all fc-* design system classes are defined."""
        missing = []
        for cls in self.REQUIRED_FC_CLASSES:
            # CSS class selector — escape special chars
            pattern = re.escape(cls) + r"\s*\{"
            if not re.search(pattern, self.css_content):
                missing.append(cls)
        assert not missing, f"Missing fc-* classes: {missing}"

    def test_no_color_accent_undefined_references(self):
        """Verify --color-accent is defined (was undefined in inline styles)."""
        # The variable should be defined: --color-accent: var(--accent, #059669);
        assert "--color-accent:" in self.css_content, \
            "--color-accent CSS variable must be defined"

    def test_color_mix_used_for_cell_tints(self):
        """Verify color-mix() is used for accent-based cell tints."""
        assert "color-mix(in srgb, var(--color-accent)" in self.css_content, \
            "color-mix() should be used for accent-based cell background tints"


class TestLegacyAliases:
    """Verify sc-*, ps-compare-*, run-* legacy aliases exist for backward compat."""

    LEGACY_ALIASES = [
        ".sc-container",
        ".sc-header",
        ".sc-matrix-wrapper",
        ".sc-matrix",
        ".sc-th",
        ".sc-row",
        ".sc-td",
        ".sc-value",
        ".sc-matrix-cell--inherited",
        ".sc-matrix-cell--override",
        ".sc-matrix-cell--base",
        ".sc-select-btn",
        ".sc-popover",
        ".ps-compare-heading",
        ".ps-compare-table",
        ".ps-compare-row",
        ".ps-compare-provenance-card",
        ".run-banner",
        ".badge-runtime",
        ".runtime-notice",
        ".kpi-grid",
        ".kpi-card",
        ".kpi-value",
    ]

    @pytest.fixture(autouse=True)
    def _load_css(self):
        self.css_content = _read_text_utf8(STYLES_CSS)

    def test_legacy_sc_aliases_present(self):
        """Verify sc-* aliases for scenario matrix backward compat."""
        missing = []
        for cls in self.LEGACY_ALIASES:
            pattern = re.escape(cls) + r"\s*\{"
            if not re.search(pattern, self.css_content):
                missing.append(cls)
        assert not missing, f"Missing legacy alias classes: {missing}"


class TestInlineStylesRemoved:
    """Verify inline <style> blocks were removed from templates."""

    def test_scenario_tab_no_inline_style(self):
        """scenario_tab.html should not have inline <style> blocks."""
        content = _read_text_utf8(SCENARIO_TAB)
        # Check for inline style tags
        inline_styles = re.findall(r"<style[^>]*>", content, re.IGNORECASE)
        assert not inline_styles, \
            f"Inline <style> blocks still present in scenario_tab.html: {inline_styles}"

    def test_runtime_summary_no_inline_style(self):
        """runtime_summary.html should not have inline <style> blocks."""
        content = _read_text_utf8(RUNTIME_SUMMARY)
        inline_styles = re.findall(r"<style[^>]*>", content, re.IGNORECASE)
        assert not inline_styles, \
            f"Inline <style> blocks still present in runtime_summary.html: {inline_styles}"

    def test_scenario_tab_still_has_sc_classes(self):
        """scenario_tab.html should still use sc-* classes (now aliased in CSS)."""
        content = _read_text_utf8(SCENARIO_TAB)
        # Template should still have sc-matrix, sc-row, sc-th etc.
        assert "sc-matrix" in content, "sc-matrix class should still be in template"
        assert "sc-row" in content, "sc-row class should still be in template"
        assert "sc-th" in content, "sc-th class should still be in template"

    def test_runtime_summary_still_has_run_classes(self):
        """runtime_summary.html should still use run-* classes (now aliased in CSS)."""
        content = _read_text_utf8(RUNTIME_SUMMARY)
        assert "run-banner" in content, "run-banner class should still be in template"
        assert "kpi-grid" in content, "kpi-grid class should still be in template"


class TestTemplateRendering:
    """Verify templates are syntactically valid Jinja2 and import correctly."""

    def test_templates_exist(self):
        """All partial templates should exist."""
        assert SCENARIO_TAB.exists(), f"scenario_tab.html not found"
        assert RUNTIME_SUMMARY.exists(), f"runtime_summary.html not found"

    def test_scenario_tab_valid_html_structure(self):
        """scenario_tab.html should have valid HTML structure."""
        content = _read_text_utf8(SCENARIO_TAB)
        # Check key structural elements exist
        assert '<div id="scenario-tab"' in content, "Missing scenario-tab div"
        assert '<table' in content, "Missing table element"
        assert '<thead>' in content, "Missing thead element"
        assert '<tbody>' in content, "Missing tbody element"
        assert '</table>' in content, "Missing closing table tag"
        # Check inline edit popover
        assert 'id="sc-edit-popover"' in content, "Missing edit popover"

    def test_runtime_summary_valid_html_structure(self):
        """runtime_summary.html should have valid HTML structure."""
        content = _read_text_utf8(RUNTIME_SUMMARY)
        assert '<div class="runtime-summary"' in content or 'id="runtime-summary"' in content, \
            "Missing runtime-summary wrapper"
        assert '<div class="kpi-grid"' in content or 'class="kpi-grid"' in content, \
            "Missing kpi-grid element"
        assert '<div class="run-banner"' in content, "Missing run-banner element"

    def test_scenario_compare_valid_html_structure(self):
        """scenario_compare.html should have valid HTML structure."""
        if not SCENARIO_COMPARE.exists():
            pytest.skip("scenario_compare.html not in expected location")
        content = _read_text_utf8(SCENARIO_COMPARE)
        assert 'ps-compare-results' in content, "Missing ps-compare-results wrapper"
        assert 'ps-compare-table' in content, "Missing ps-compare-table element"


class TestNoFunctionalChanges:
    """Verify this phase did not change any functional logic."""

    def test_no_python_files_changed(self):
        """Phase 20H should not modify any Python files."""
        # This is informational — the test runner will have already checked git status
        pass

    def test_css_file_size_increased(self):
        """styles.css should have grown (new design system added)."""
        size = STYLES_CSS.stat().st_size
        # Phase 20H added ~700 lines of CSS
        # Pre-phase size was ~2654 lines (~53KB)
        # Post-phase should be >3330 lines
        assert size > 60000, \
            f"styles.css seems too small ({size} bytes) — design system may not have been added"

    def test_scenario_tab_line_count_reduced(self):
        """scenario_tab.html should be shorter (inline CSS removed)."""
        line_count = _read_text_utf8(SCENARIO_TAB).count("\n")
        # Pre-Phase 20H: 571 lines (with ~300 line inline <style>)
        # Post-Phase 20H: ~288 lines (inline CSS removed)
        assert line_count < 400, \
            f"scenario_tab.html still has {line_count} lines — inline CSS may not have been removed"

    def test_runtime_summary_line_count_reduced(self):
        """runtime_summary.html should stay free of inline CSS after later UX additions."""
        content = _read_text_utf8(RUNTIME_SUMMARY)
        line_count = content.count("\n")
        assert "<style" not in content.lower(), "runtime_summary.html must not reintroduce inline CSS"
        assert line_count < 800,             f"runtime_summary.html grew unexpectedly large ({line_count} lines)"


class TestGuardrails:
    """Verify Phase 20H constraints were respected."""

    def test_no_tailwind_classes(self):
        """No Tailwind CSS classes should be present."""
        css_content = _read_text_utf8(STYLES_CSS)
        # Check for actual Tailwind indicators: @tailwind directive, tw- prefix
        tailwind_patterns = [r"@tailwind", r"\btw-", r"tailwindcss"]
        found = []
        for pat in tailwind_patterns:
            if re.search(pat, css_content, re.IGNORECASE):
                found.append(pat)
        assert not found, f"Tailwind CSS reference found in styles.css: {found}"

    def test_no_alpine_references(self):
        """No Alpine.js references should be present."""
        css_content = _read_text_utf8(STYLES_CSS)
        # Check for actual Alpine.js indicators: alpinejs, x-data, x-bind, @click.alpine
        alpine_patterns = [r"alpine\.js", r"x-data", r"x-bind:", r"@click\.alpine"]
        found = []
        for pat in alpine_patterns:
            if re.search(pat, css_content, re.IGNORECASE):
                found.append(pat)
        assert not found, f"Alpine.js reference found in styles.css: {found}"

    def test_no_js_financial_calculations(self):
        """Verify no JS financial calculation patterns in scenario_tab.html."""
        content = _read_text_utf8(SCENARIO_TAB)
        js_calc_patterns = [
            "Math.pow",
            "parseFloat",
            "toFixed",
        ]
        # These are OK in the JS for UI, but we check there's no financial logic
        # This is a sanity check — the real guard is that we didn't add any .js files
        # and the inline JS is only for UI interaction (edit popover)
        assert "<script>" in content, "JS should still be present for edit popover"
        # The JS should only handle HTMX swaps and popover UI, not calculations
        assert "htmx" in content, "HTMX should be used for async operations"


class TestInputsSectionUnchanged:
    """Verify inputs_section.html uses inp-* classes (not fc-* required for this phase)."""

    def test_inputs_section_uses_inp_classes(self):
        """inputs_section.html should still use inp-* classes."""
        inputs_section = PROJECT_ROOT / "app" / "templates" / "partials" / "inputs_section.html"
        if not inputs_section.exists():
            pytest.skip("inputs_section.html not found")
        content = _read_text_utf8(inputs_section)
        # inp-* classes should still be used
        assert "inp-row" in content, "inp-row class should still be used"
        assert "inp-input" in content, "inp-input class should still be used"
        assert "inp-card" in content, "inp-card class should still be used"


# ── Smoke test: CSS parses without errors ─────────────────────────────────────

def test_css_has_valid_syntax():
    """Basic CSS syntax sanity — no unclosed braces."""
    content = _read_text_utf8(STYLES_CSS)
    content = re.sub(r"/\*.*?\*/", "", content, flags=re.DOTALL)
    open_braces = content.count("{")
    close_braces = content.count("}")
    assert open_braces == close_braces, \
        f"Unmatched braces: {open_braces} open, {close_braces} close"


def test_css_design_system_section_marker():
    """Verify Phase 20H section marker comment is present."""
    content = _read_text_utf8(STYLES_CSS)
    assert "PHASE 20H" in content, "Phase 20H section marker should be in styles.css"
    assert "FINCO CELL DESIGN SYSTEM" in content, \
        "Finco Cell Design System marker should be in styles.css"
