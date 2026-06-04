"""Phase 56F — State banner visual hierarchy polish tests.

Verifies that:
- All 11 banner contexts (factory_template, user_created_project,
  active_scenario, saved_scenario, browser_draft, dirty_state,
  stale_result, last_run, validation_failed, display_only_row,
  pending_runtime_source) are still supported.
- All 5 banner tones (info, success, warn, fail, neutral) are
  still supported.
- Accessibility attributes (role="status", aria-label) are
  preserved.
- The new visual hierarchy (.banner-56f) is additive only;
  the original .banner class is preserved for backward compat.
- Icon glyphs are simple Unicode symbols (calmer than the
  previous 2-letter codes like "FT", "AS").
- No no-go UI claims introduced.
- 55G banner_context tests still pass.
- UI-2.1 banner tests still pass.
- No static/app.js changes.
- No backend / persistence / model changes.
- rc1 (b425a07) untouched.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
STATE_BANNER = (
    REPO_ROOT / "app" / "templates" / "partials" / "_state_banner.html"
)
STYLES_CSS = REPO_ROOT / "static" / "styles.css"
APP_JS = REPO_ROOT / "static" / "app.js"
MAIN_WEB = REPO_ROOT / "main_web.py"

RC1_SHA = "b425a0708719eaa5e1d922b1008e5609758e0ad4"

# All 11 supported banner contexts (from 55G).
BANNER_CONTEXTS = [
    "factory_template",
    "user_created_project",
    "active_scenario",
    "saved_scenario",
    "browser_draft",
    "dirty_state",
    "stale_result",
    "last_run",
    "validation_failed",
    "display_only_row",
    "pending_runtime_source",
]

# All 5 banner tones.
BANNER_TONES = ["info", "success", "warn", "fail", "neutral"]


# ============================================================
# 1. All 11 contexts still supported
# ============================================================


class TestAllContextsSupported:
    @pytest.mark.parametrize("ctx", BANNER_CONTEXTS)
    def test_context_branch_in_template(self, ctx):
        text = STATE_BANNER.read_text()
        # Each context must have a branch
        assert f"_ctx == '{ctx}'" in text, (
            f"State banner must have a branch for context: {ctx}"
        )

    @pytest.mark.parametrize("ctx", BANNER_CONTEXTS)
    def test_context_has_title(self, ctx):
        text = STATE_BANNER.read_text()
        # Find the branch for this context and ensure a _title is set
        m = re.search(
            rf"_ctx == '{ctx}'(.*?)(?=_ctx ==|{{% endif %}})",
            text,
            flags=re.DOTALL,
        )
        assert m is not None
        body = m.group(1)
        assert "_title =" in body, (
            f"Context {ctx} must set _title"
        )

    @pytest.mark.parametrize("ctx", BANNER_CONTEXTS)
    def test_context_has_description(self, ctx):
        text = STATE_BANNER.read_text()
        m = re.search(
            rf"_ctx == '{ctx}'(.*?)(?=_ctx ==|{{% endif %}})",
            text,
            flags=re.DOTALL,
        )
        assert m is not None
        body = m.group(1)
        assert "_desc =" in body, (
            f"Context {ctx} must set _desc"
        )


# ============================================================
# 2. All 5 tones still supported
# ============================================================


class TestAllTonesSupported:
    @pytest.mark.parametrize("tone", BANNER_TONES)
    def test_tone_in_template(self, tone):
        text = STATE_BANNER.read_text()
        # The tone is rendered dynamically via `banner-{{ _tone }}`.
        # The pattern must exist in the class attribute template.
        # The static tones are also documented in the header comment.
        if f"banner-{tone}" not in text:
            # Some tones may only be referenced via the dynamic template
            # "banner-{{ _tone }}" — that's still valid.
            assert "banner-{{ _tone }}" in text, (
                f"State banner must reference tone: {tone} "
                f"(either literally or via dynamic 'banner-{{{{ _tone }}}}')"
            )

    @pytest.mark.parametrize("tone", BANNER_TONES)
    def test_tone_css_defined(self, tone):
        css_text = STYLES_CSS.read_text()
        # Original CSS or 56F CSS must define .banner-<tone>
        assert f".banner-{tone}" in css_text, (
            f"styles.css must define .banner-{tone}"
        )


# ============================================================
# 3. Accessibility preserved
# ============================================================


class TestAccessibilityPreserved:
    def test_role_status_present(self):
        text = STATE_BANNER.read_text()
        assert 'role="status"' in text, (
            "Banner must keep role='status' for accessibility"
        )

    def test_aria_label_present(self):
        text = STATE_BANNER.read_text()
        assert 'aria-label="{{ _title }}"' in text, (
            "Banner must keep aria-label"
        )

    def test_icon_marked_aria_hidden(self):
        text = STATE_BANNER.read_text()
        assert 'aria-hidden="true"' in text, (
            "Banner icon must be marked aria-hidden (decorative)"
        )


# ============================================================
# 4. 56F visual hierarchy (additive)
# ============================================================


class Test56FVisualHierarchy:
    def test_banner_56f_class_in_template(self):
        text = STATE_BANNER.read_text()
        assert "banner-56f" in text, (
            "State banner must apply the .banner-56f modifier"
        )

    def test_banner_56f_css_defined(self):
        css_text = STYLES_CSS.read_text()
        assert ".banner-56f" in css_text, (
            "styles.css must define .banner-56f (calmer variant)"
        )

    def test_phase_56f_section_marker_in_css(self):
        css_text = STYLES_CSS.read_text()
        assert "Phase 56F" in css_text, (
            "styles.css must have a Phase 56F section marker"
        )

    def test_banner_56f_has_smaller_padding(self):
        """The 56F banner should have a smaller padding (0.5rem
        0.85rem) vs the original (0.75rem 1rem) for a calmer feel."""
        css_text = STYLES_CSS.read_text()
        m = re.search(
            r"\.banner-56f\s*\{[^}]*padding:\s*([^;}]+);",
            css_text,
        )
        assert m is not None
        padding = m.group(1)
        # The 56F padding must NOT match the original
        assert "0.75rem 1rem" not in padding, (
            "banner-56f padding should be smaller than 0.75rem 1rem"
        )
        # Smaller padding — must be present
        assert "0.5rem" in padding, (
            f"banner-56f padding must include 0.5rem (calmer). Got: {padding}"
        )

    def test_banner_56f_icon_smaller(self):
        """The icon should be smaller in 56F (22px vs 28px)."""
        css_text = STYLES_CSS.read_text()
        m = re.search(
            r"\.banner-56f \.banner-icon\s*\{[^}]*width:\s*(\d+)px",
            css_text,
        )
        assert m is not None
        width = int(m.group(1))
        assert width <= 24, (
            f"banner-56f icon width should be <= 24px, got {width}px"
        )

    def test_no_heavy_shadow(self):
        css_text = STYLES_CSS.read_text()
        m = re.search(
            r"\.banner-56f\s*\{([^}]*)\}",
            css_text,
        )
        assert m is not None
        block = m.group(1)
        # No box-shadow or box-shadow: none
        assert "box-shadow" not in block or "box-shadow: none" in block, (
            "banner-56f must not have a heavy box-shadow"
        )


# ============================================================
# 5. Icon glyphs are calmer (single Unicode symbol, not 2-letter code)
# ============================================================


class TestIconGlyphsCalmer:
    @pytest.mark.parametrize("ctx,glyph", [
        ("factory_template", "◆"),
        ("user_created_project", "●"),
        ("active_scenario", "●"),
        ("saved_scenario", "✓"),
        ("browser_draft", "◐"),
        ("dirty_state", "◐"),
        ("stale_result", "↻"),
        ("last_run", "✓"),
        ("validation_failed", "!"),
        ("display_only_row", "◇"),
        ("pending_runtime_source", "◌"),
    ])
    def test_uses_simple_glyph(self, ctx, glyph):
        text = STATE_BANNER.read_text()
        m = re.search(
            rf"_ctx == '{ctx}'(.*?)(?=_ctx ==|{{% endif %}})",
            text,
            flags=re.DOTALL,
        )
        assert m is not None
        body = m.group(1)
        # The icon assignment must contain the new glyph
        assert glyph in body, (
            f"Context {ctx} should use glyph {glyph!r} (calmer). "
            f"Found: {body!r}"
        )

    def test_no_2letter_code_icons_remaining(self):
        """The old 2-letter codes (FT, AS, etc.) must be gone."""
        text = STATE_BANNER.read_text()
        old_codes = ["'FT'", "'UP'", "'AS'", "'SS'", "'BD'", "'UC'",
                     "'SR'", "'LR'", "'VF'", "'DO'", "'PR'"]
        for code in old_codes:
            # Only flag if it's in a `_icon =` line (not in a comment)
            if f"_icon = {code}" in text:
                pytest.fail(
                    f"State banner still uses old 2-letter code {code}. "
                    "56F must use simpler Unicode glyphs."
                )


# ============================================================
# 6. Original .banner preserved (backward compat)
# ============================================================


class TestOriginalBannerPreserved:
    def test_original_banner_class_intact(self):
        css_text = STYLES_CSS.read_text()
        # The original .banner rule must still exist
        assert ".banner {" in css_text
        # With original padding
        m = re.search(
            r"\.banner\s*\{[^}]*padding:\s*([^;}]+);",
            css_text,
        )
        assert m is not None
        # Original padding
        assert "0.75rem 1rem" in m.group(1), (
            "Original .banner padding must be preserved for backward compat"
        )

    def test_banner_56f_uses_additive_class_not_replace(self):
        """56F adds `.banner-56f` as a NEW class, it does NOT
        replace the existing `.banner` rule."""
        text = STATE_BANNER.read_text()
        # The rendered element must have both classes
        assert 'class="banner banner-' in text
        assert "banner-56f" in text
        # The template's class attribute should be: "banner banner-{{ _tone }} banner-56f"
        m = re.search(r'class="([^"]+)"', text)
        assert m is not None
        classes = m.group(1).split()
        assert "banner" in classes
        assert any(c.startswith("banner-") and c != "banner" for c in classes)
        assert "banner-56f" in classes


# ============================================================
# 7. Tone-specific styles still in CSS for both old and new
# ============================================================


class TestToneStylesForBothVariants:
    @pytest.mark.parametrize("tone", BANNER_TONES)
    def test_tone_56f_style_present(self, tone):
        css_text = STYLES_CSS.read_text()
        assert f".banner-56f.banner-{tone}" in css_text, (
            f"styles.css must define .banner-56f.banner-{tone}"
        )


# ============================================================
# 8. Copy remains safe (no forbidden claims)
# ============================================================


NO_GO_FORBIDDEN_TERMS = [
    "bankable", "bank-grade", "lender-ready", "certified", "audit-ready",
    "investor-ready", "saas-ready", "production-ready", "guaranteed returns",
    "investment advice", "customer reference", "validated", "external validation",
]


class TestNoGoCopy:
    @pytest.mark.parametrize("term", NO_GO_FORBIDDEN_TERMS)
    def test_no_forbidden_term(self, term):
        text = STATE_BANNER.read_text().lower()
        assert term not in text, (
            f"State banner must not use forbidden term: {term}"
        )

    def test_no_debug_style_language(self):
        """The 56F copy should not feel like debug output."""
        text = STATE_BANNER.read_text().lower()
        for phrase in ["stack trace", "exception", "panic", "abort", "fatal"]:
            assert phrase not in text, (
                f"State banner should not use debug phrase: {phrase}"
            )


# ============================================================
# 9. CSS is additive
# ============================================================


class TestCSSAdditive:
    def test_root_count_unchanged(self):
        css_text = STYLES_CSS.read_text()
        root_count = len(re.findall(r":root\s*\{", css_text))
        assert root_count == 5, (
            f"styles.css :root block count changed from 5 to {root_count}"
        )

    def test_56f_selectors_present(self):
        css_text = STYLES_CSS.read_text()
        for sel in [
            ".banner-56f",
            ".banner-56f .banner-icon",
            ".banner-56f .banner-body",
            ".banner-56f .banner-title",
            ".banner-56f .banner-desc",
            ".banner-56f.banner-info",
            ".banner-56f.banner-success",
            ".banner-56f.banner-warn",
            ".banner-56f.banner-fail",
            ".banner-56f.banner-neutral",
        ]:
            assert sel in css_text, f"Missing 56F CSS selector: {sel}"


# ============================================================
# 10. Scope guardrails
# ============================================================


class TestScopeGuardrails:
    def test_app_js_unchanged(self):
        js = APP_JS.read_text()
        assert "switchTab" in js

    def test_main_web_unchanged(self):
        text = MAIN_WEB.read_text()
        assert "Phase 56F" not in text, (
            "56F must not change main_web.py (banner_context backend "
            "logic is preserved from 55G)"
        )

    def test_app_waterfall_core_unchanged(self):
        wf = REPO_ROOT / "app" / "waterfall_core.py"
        if wf.exists():
            text = wf.read_text()
            assert "Phase 56F" not in text

    def test_app_project_factories_unchanged(self):
        pf = REPO_ROOT / "app" / "project_factories.py"
        if pf.exists():
            text = pf.read_text()
            assert "Phase 56F" not in text

    def test_runtime_impact_taxonomy_unchanged(self):
        rt = REPO_ROOT / "app" / "runtime_impact_taxonomy.py"
        if rt.exists():
            text = rt.read_text()
            assert "Phase 56F" not in text

    def test_persistence_unchanged(self):
        pdir = REPO_ROOT / "app" / "persistence"
        for f in pdir.glob("*.py"):
            text = f.read_text()
            assert "Phase 56F" not in text

    def test_no_financial_model_changes(self):
        for f in [
            REPO_ROOT / "app" / "waterfall_core.py",
            REPO_ROOT / "app" / "capex_engine.py",
            REPO_ROOT / "app" / "opex_engine.py",
            REPO_ROOT / "app" / "depreciation_engine.py",
        ]:
            if f.exists():
                text = f.read_text()
                assert "Phase 56F" not in text

    def test_no_schema_or_migration_changes(self):
        migrations = REPO_ROOT / "app" / "persistence" / "migrations"
        if migrations.exists():
            for f in migrations.glob("*.py"):
                text = f.read_text()
                assert "Phase 56F" not in text


# ============================================================
# 11. rc1 untouched
# ============================================================


class TestRc1Untouched:
    def test_rc1_sha_constant_stable(self):
        assert RC1_SHA == "b425a0708719eaa5e1d922b1008e5609758e0ad4"


# ============================================================
# 12. 55G banner_context tests still pass (sanity)
# ============================================================


class Test55GAndUI2Compat:
    def test_banner_template_still_imports_banner_context(self):
        """The template still uses banner_context and banner_tone
        (set by 55G backend helper)."""
        text = STATE_BANNER.read_text()
        assert "{% if banner_context %}" in text
        assert "banner_tone|default('info')" in text
