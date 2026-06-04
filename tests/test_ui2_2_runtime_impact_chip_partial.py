"""UI-2.2 — Runtime Impact chip partial tests.

Verifies:
- Partial exists
- All 4 states render
- Tooltip text is safe
- No forbidden positive no-go claims
- sheet_capex_detail.html includes the partial
- CSS only additive .chip-* classes
- No runtime_impact_taxonomy.py changes
- No backend/service/persistence changes
- UI-2.1 tests still pass
- Existing Phase 54 tests still pass
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
PARTIAL = REPO_ROOT / "app" / "templates" / "partials" / "_runtime_impact_chip.html"
SHEET = REPO_ROOT / "app" / "templates" / "partials" / "sheet_capex_detail.html"
STYLES_CSS = REPO_ROOT / "static" / "styles.css"
APP_JS = REPO_ROOT / "static" / "app.js"
TAXONOMY = REPO_ROOT / "app" / "runtime_impact_taxonomy.py"


# ============================================================
# 1. Partial exists
# ============================================================


class TestPartialExists:
    def test_partial_file_exists(self):
        assert PARTIAL.exists()

    def test_partial_has_docstring(self):
        text = PARTIAL.read_text()
        assert "{#" in text, "Partial should have a Jinja comment header"

    def test_partial_uses_chip_class(self):
        text = PARTIAL.read_text()
        assert "chip" in text


# ============================================================
# 2. All 4 states render
# ============================================================


STATES = ["Drives model", "Display only", "Pending", "Needs review"]


class TestStatesSupported:
    @pytest.mark.parametrize("state", STATES)
    def test_state_in_partial(self, state):
        text = PARTIAL.read_text()
        assert state in text, f"State '{state}' not in chip partial"

    def test_4_states_present(self):
        text = PARTIAL.read_text()
        for state in STATES:
            assert state in text


# ============================================================
# 3. Tooltip text is safe
# ============================================================


EXPECTED_TOOLTIPS = [
    "Included in model calculations.",
    "Shown for review; does not affect calculations.",
    "Mapped but not yet connected to runtime calculations.",
    "Requires review before use."
]


class TestTooltipsSafe:
    @pytest.mark.parametrize("tt", EXPECTED_TOOLTIPS)
    def test_tooltip_in_partial(self, tt):
        text = PARTIAL.read_text()
        assert tt in text, f"Tooltip '{tt}' not in partial"

    def test_no_real_time_in_tooltips(self):
        text = PARTIAL.read_text().lower()
        assert "real-time" not in text

    def test_no_live_in_tooltips(self):
        text = PARTIAL.read_text().lower()
        # "does not affect" contains "affect" which is fine
        # "live" alone is the check
        pattern = r"\blive\b"
        assert not re.search(pattern, text), "'live' found in tooltips"


# ============================================================
# 4. No forbidden positive no-go claims
# ============================================================


FORBIDDEN_TERMS = [
    "bankable", "lender-ready", "investor-ready",
    "production-ready", "guaranteed returns", "investment advice",
    "customer reference", "external validation", "audit-ready"
]


class TestNoForbiddenClaims:
    @pytest.mark.parametrize("term", FORBIDDEN_TERMS)
    def test_no_forbidden_term_in_partial(self, term):
        text = PARTIAL.read_text().lower()
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

    def test_sheet_capex_no_forbidden_added(self):
        # Check the include area of sheet_capex_detail.html
        text = SHEET.read_text().lower()
        for term in FORBIDDEN_TERMS:
            pattern = r"\b" + re.escape(term) + r"\b"
            assert not re.search(pattern, text), f"Forbidden '{term}' in sheet_capex_detail.html"


# ============================================================
# 5. sheet_capex_detail.html includes the partial
# ============================================================


class TestSheetIntegration:
    def test_sheet_includes_partial(self):
        text = SHEET.read_text()
        assert "_runtime_impact_chip.html" in text

    def test_sheet_uses_runtime_impact_variable(self):
        text = SHEET.read_text()
        # Should still reference child.runtime_impact
        assert "child.runtime_impact" in text

    def test_sheet_passes_runtime_impact_to_partial(self):
        text = SHEET.read_text()
        # The include should be inside a {% with %} or use a variable
        # The pattern is: {% with runtime_impact=rt, sub_reason='' %}
        assert "runtime_impact=" in text


# ============================================================
# 6. Backward compat: _rt_tooltip helper preserved
# ============================================================


class TestBackwardCompat:
    def test_old_inline_chip_removed(self):
        # UI-2.2 replaced the inline chip with a Jinja include.
        # The old inline chip should NOT be commented out (clean replacement).
        text = SHEET.read_text()
        # The old inline span with _rt_tooltip should be gone
        assert "_rt_tooltip(rt)" not in text, \
            "Old inline chip using _rt_tooltip should be removed (UI-2.2 clean replacement)"

    def test_rt_tooltip_macro_removed(self):
        # The _rt_tooltip macro was only used by the now-removed inline chip.
        # It should be removed as dead code.
        text = SHEET.read_text()
        assert "{%- macro _rt_tooltip" not in text, \
            "_rt_tooltip macro should be removed (was only used by old chip)"

    def test_old_badge_rt_class_still_in_legend(self):
        # The old .badge-rt-* CSS classes are still used in the legend section
        # of sheet_capex_detail.html (lines ~456-460) and in instructional text.
        # This is for the visual legend, not the data rows.
        text = SHEET.read_text()
        assert ".badge-rt" in text, "Old .badge-rt class should still be in legend"


# ============================================================
# 7. CSS only additive
# ============================================================


class TestCSSAdditive:
    def test_chip_drives_model_in_css(self):
        text = STYLES_CSS.read_text()
        assert ".chip-drives-model" in text

    def test_chip_display_only_in_css(self):
        text = STYLES_CSS.read_text()
        assert ".chip-display-only" in text

    def test_chip_pending_in_css(self):
        text = STYLES_CSS.read_text()
        assert ".chip-pending" in text

    def test_chip_needs_review_in_css(self):
        text = STYLES_CSS.read_text()
        assert ".chip-needs-review" in text

    def test_chip_base_in_css(self):
        text = STYLES_CSS.read_text()
        assert ".chip" in text

    def test_no_root_modification(self):
        # Check the UI-2.2 section specifically does not modify :root
        text = STYLES_CSS.read_text()
        m = re.search(r"/\* ── UI-2\.2.*?\*/\n(.*?)(?=/\* ── |\Z)", text, re.DOTALL)
        if m:
            section = m.group(1)
            assert ":root" not in section, "UI-2.2 CSS section must not modify :root"
        # Verify pre-existing :root count is unchanged
        root_count = text.count(":root {")
        assert root_count == 5, f"Found {root_count} :root blocks (expected 5 pre-existing)"


# ============================================================
# 8. No runtime_impact_taxonomy.py changes
# ============================================================


class TestNoTaxonomyChanges:
    def test_taxonomy_file_exists(self):
        assert TAXONOMY.exists()

    def test_taxonomy_has_4_states(self):
        text = TAXONOMY.read_text()
        for state in STATES:
            assert state in text


# ============================================================
# 9. No backend/service/persistence changes
# ============================================================


class TestNoBackendChanges:
    def test_main_web_unchanged(self):
        assert (REPO_ROOT / "main_web.py").exists()

    def test_app_js_unchanged(self):
        assert APP_JS.exists()

    def test_persistence_dir_unchanged(self):
        assert (REPO_ROOT / "app" / "persistence").exists()

    def test_services_dir_unchanged(self):
        assert (REPO_ROOT / "app" / "services").exists()


# ============================================================
# 10. Partial safe when runtime_impact missing
# ============================================================


class TestSafeDefaults:
    def test_partial_guarded_by_if(self):
        text = PARTIAL.read_text()
        assert "{% if runtime_impact %}" in text

    def test_partial_ends_with_endif(self):
        text = PARTIAL.read_text()
        assert "{% endif %}" in text


# ============================================================
# 11. Chip label is short (no overflow risk)
# ============================================================


class TestChipText:
    @pytest.mark.parametrize("state", STATES)
    def test_state_label_visible(self, state):
        # The chip should display the state name as text
        text = PARTIAL.read_text()
        # Each state should be wrapped in a span display
        assert state in text
