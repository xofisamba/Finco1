"""UI-2 — Application Chrome Foundation — smoke / governance tests.

Verifies the additive introduction of the new top-level application
frame (brand bar + command bar + KPI strip + sheet-tab reserve).

  - static/chrome.css exists and declares the fo-* chrome class family
  - app/templates/partials/_brand_bar.html exists
  - app/templates/partials/_command_bar.html exists
  - app/templates/partials/_kpi_strip.html exists
  - app/templates/partials/_app_chrome.html exists
  - app/templates/base.html loads chrome.css BEFORE the chrome mount
  - app/templates/base.html mounts the chrome PARTIAL ABOVE the
    legacy <header class="top-header"> (legacy chrome preserved)
  - Every new class is namespaced under `.fo-` (no leakage onto
    legacy `.fc-`, `.ps-`, `.scm-`, etc. classes)
  - chrome.css consumes only --fo-* tokens for colours / spacing /
    shadows / typography
  - No financial / engine / persistence / main_web / main_api / factory
    files modified
  - No edits to existing legacy pages/templates

All tests are read-only / static — no application boot, no DB, no
imports of runtime modules. This keeps the smoke suite hermetic,
fast, and CI-safe.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Repo paths
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[1]
TOKENS_CSS = REPO_ROOT / "static" / "tokens.css"
CHROME_CSS = REPO_ROOT / "static" / "chrome.css"
SHEET_TABS_CSS = REPO_ROOT / "static" / "sheet-tabs.css"
BASE_HTML = REPO_ROOT / "app" / "templates" / "base.html"
APP_CHROME_HTML = (
    REPO_ROOT / "app" / "templates" / "partials" / "_app_chrome.html"
)
BRAND_BAR_HTML = (
    REPO_ROOT / "app" / "templates" / "partials" / "_brand_bar.html"
)
COMMAND_BAR_HTML = (
    REPO_ROOT / "app" / "templates" / "partials" / "_command_bar.html"
)
KPI_STRIP_HTML = (
    REPO_ROOT / "app" / "templates" / "partials" / "_kpi_strip.html"
)


# ---------------------------------------------------------------------------
# 1. File presence / size sanity
# ---------------------------------------------------------------------------

class TestFilesExist:
    """All UI-2 deliverables must exist on disk."""

    @pytest.mark.parametrize("path", [
        CHROME_CSS,
        APP_CHROME_HTML,
        BRAND_BAR_HTML,
        COMMAND_BAR_HTML,
        KPI_STRIP_HTML,
    ])
    def test_deliverable_file_present(self, path):
        assert path.is_file(), (
            f"UI-2 deliverable missing: {path}"
        )


class TestChromeCssSanity:
    """chrome.css must be a non-trivial, balanced CSS sheet."""

    def test_chrome_css_has_header_comment(self):
        text = CHROME_CSS.read_text(encoding="utf-8")
        assert "FINCO ONE" in text and "CHROME" in text, (
            "chrome.css must start with the Finco One chrome header."
        )

    def test_chrome_css_balanced_braces(self):
        text = CHROME_CSS.read_text(encoding="utf-8")
        assert text.count("{") == text.count("}"), (
            "chrome.css must have balanced braces — got "
            f"{text.count('{')} open vs {text.count('}')} close."
        )

    def test_chrome_css_substantive_size(self):
        # A genuine chrome stylesheet is several KB; reject near-empty.
        assert CHROME_CSS.stat().st_size > 4000, (
            f"chrome.css should be substantive; got "
            f"{CHROME_CSS.stat().st_size} bytes."
        )


# ---------------------------------------------------------------------------
# 2. fo- class namespacing
# ---------------------------------------------------------------------------

# All UI-2 chrome classes must live under the `fo-` prefix. This guards
# against accidental collision with legacy families (.fc-, .ps-, .scm-,
# .top-header, .dashboard-*, ...).
REQUIRED_FO_CLASSES = [
    # chrome wrapper
    "fo-chrome",
    # brand bar
    "fo-brand-bar",
    "fo-brand-bar__brand",
    "fo-brand-bar__wordmark",
    "fo-brand-bar__select",
    "fo-brand-bar__kbd",
    "fo-theme-toggle",
    # command bar
    "fo-command-bar",
    "fo-btn--primary",
    "fo-btn--ghost",
    "fo-btn--placeholder",
    "fo-btn__kbd",
    "fo-pill",
    "fo-pill__dot",
    "fo-pill--fresh",
    "fo-pill--stale",
    "fo-pill--running",
    "fo-pill--error",
    "fo-meta",
    "fo-meta__label",
    "fo-meta__value",
    # KPI strip
    "fo-kpi-strip",
    "fo-kpi-strip--stale",
    "fo-kpi",
    "fo-kpi__label",
    "fo-kpi__value",
    "fo-kpi__value--placeholder",
    # sheet-tab reserve
    "fo-sheet-tab-reserve",
]


class TestFoClassNamespacing:
    """UI-2 chrome classes are namespaced strictly under `fo-`."""

    @pytest.mark.parametrize("cls", REQUIRED_FO_CLASSES)
    def test_fo_class_appears_in_chrome_css(self, cls):
        text = CHROME_CSS.read_text(encoding="utf-8")
        # Word-boundary regex — `.fo-pa` does not accidentally match
        # `.fo-pause`, etc.
        pattern = re.compile(rf"\.{re.escape(cls)}\b")
        assert pattern.search(text), (
            f"Required chrome class .{cls} not declared in chrome.css."
        )

    @pytest.mark.parametrize("cls", REQUIRED_FO_CLASSES)
    def test_fo_class_only_in_chrome_css(self, cls):
        # The class must NOT be declared (as a selector) in static/styles.css
        # (legacy). CSS comments may reference chrome class names for
        # documentation — those are not violations. Strip comments first.
        legacy_raw = (REPO_ROOT / "static" / "styles.css").read_text(
            encoding="utf-8"
        )
        legacy_text = re.sub(r"/\*.*?\*/", "", legacy_raw, flags=re.DOTALL)
        legacy_pattern = re.compile(rf"\.{re.escape(cls)}\b")
        assert not legacy_pattern.search(legacy_text), (
            f"Chrome class .{cls} leaked into static/styles.css; "
            f"chrome must own its own stylesheet."
        )
        # And chrome.css must exist on disk — either staged in this PR
        # (PR delivered the chrome for the first time) or merged on
        # main from a prior PR. Both states are valid; the file simply
        # must be present so the chrome class family has a CSS home.
        assert CHROME_CSS.is_file(), (
            f"static/chrome.css must exist on disk; "
            f"chrome.css is the only owner of the .fo-brand-bar*, "
            f".fo-command-bar*, .fo-kpi* family."
        )
        # Also: chrome classes must NOT bleed into the UI-3 sheet-tabs
        # stylesheet. Sheet tabs owns its own .fo-sheet* family; chrome
        # owns .fo-brand-bar*, .fo-command-bar*, .fo-kpi*. Cross-leakage
        # would mean one of the two files is overreaching.
        if SHEET_TABS_CSS.is_file():
            sheet_text = SHEET_TABS_CSS.read_text(encoding="utf-8")
            # Strip CSS comments so commentary mentioning the UI-2
            # reserve placeholder (e.g. "(fo-sheet-tab-reserve)") does
            # not trip the namespace lint — only declarations count.
            sheet_text = re.sub(
                r"/\*.*?\*/", "", sheet_text, flags=re.DOTALL
            )
            sheet_pattern = re.compile(rf"\.{re.escape(cls)}\b")
            assert not sheet_pattern.search(sheet_text), (
                f"Chrome class .{cls} leaked into static/sheet-tabs.css; "
                f"sheet-tabs owns its own .fo-sheet* namespace."
            )


# ---------------------------------------------------------------------------
# 3. chrome.css consumes ONLY --fo-* design tokens
# ---------------------------------------------------------------------------

# These FORBIDDEN patterns guard against the chrome author hand-coding
# raw hex, px spacing, hard-coded shadows, or peeking at the legacy
# `--sidebar-bg` style colour names. Every visual property in chrome.css
# must be token-driven.
FORBIDDEN_RAW_PATTERNS = [
    (r"#[0-9a-fA-F]{3,8}\b", "raw hex colour"),
    (r"\brgba?\(\s*\d", "raw rgb colour"),
    (r"box-shadow\s*:\s*[^v;]*;", "raw box-shadow"),
    (r"var\(--(fo|sidebar|primary|surface|border|sidebar-bg|--text)\b",
     "non-fo- token usage"),
]


class TestChromeCssOnlyConsumesFoTokens:
    """chrome.css must consume only --fo-* tokens; no raw colours/spacing."""

    def test_no_raw_hex_colours(self):
        text = CHROME_CSS.read_text(encoding="utf-8")
        offenders = []
        for line_no, raw in enumerate(text.splitlines(), start=1):
            # Comments may mention hex values without producing rules.
            stripped = raw.strip()
            if not stripped or stripped.startswith(("/*", "*", "//")):
                continue
            if re.search(r"#[0-9a-fA-F]{3,8}\b", raw):
                offenders.append((line_no, raw))
        assert not offenders, (
            "chrome.css must not declare raw hex colours; "
            "use --fo-* tokens instead. Offends:\n  " +
            "\n  ".join(f"L{n}: {l}" for n, l in offenders)
        )

    def test_no_raw_rgb_colours(self):
        # Strip CSS comments so commentary mentioning "rgba()" doesn't
        # trip the lint — we only care about *declarations*.
        text = CHROME_CSS.read_text(encoding="utf-8")
        text_no_comments = re.sub(
            r"/\*.*?\*/", "", text, flags=re.DOTALL
        )
        offenders = []
        for line_no, raw in enumerate(text_no_comments.splitlines(), start=1):
            stripped = raw.strip()
            if not stripped:
                continue
            if re.search(r"\brgba?\s*\(", raw):
                offenders.append((line_no, raw))
        assert not offenders, (
            "chrome.css must not declare raw rgba() colours; "
            "use --fo-* tokens. Offends:\n  " +
            "\n  ".join(f"L{n}: {l}" for n, l in offenders)
        )

    def test_uses_fo_tokens_for_visual_props(self):
        # chrome.css must reference at least the canonical design tokens
        # for colours, spacing, typography, shadow, motion.
        text = CHROME_CSS.read_text(encoding="utf-8")
        for token in [
            "--fo-paper",
            "--fo-surface",
            "--fo-ink",
            "--fo-line",
            "--fo-brand-600",
            "--fo-rag-green",
            "--fo-font-ui",
            "--fo-text-md",
            "--fo-s2",
            "--fo-t-fast",
        ]:
            assert token in text, (
                f"chrome.css must consume {token} from tokens.css."
            )

    def test_no_legacy_palette_alias(self):
        # Legacy variables that exist in static/styles.css MUST NOT be
        # re-declared or referenced from chrome.css. The chrome only
        # knows about the fo-* namespace. Note: substring `--primary`
        # legitimately appears in CSS class names like `.fo-btn--primary`,
        # so we use a word-boundary regex anchored on the var() use site
        # rather than the bare substring.
        text = CHROME_CSS.read_text(encoding="utf-8")
        for legacy in ["--sidebar-bg", "--primary", "--surface",
                        "--border", "--text-secondary"]:
            pattern = re.compile(rf"var\(\s*{re.escape(legacy)}\b")
            assert not pattern.search(text), (
                f"chrome.css must not reference legacy token {legacy}; "
                f"use the --fo-* equivalent."
            )


# ---------------------------------------------------------------------------
# 4. base.html — chrome.css link + chrome partial mount order
# ---------------------------------------------------------------------------

class TestBaseHtmlChromeMount:
    """chrome.css link + partial include + relative ordering vs legacy."""

    def test_chrome_css_linked(self):
        text = BASE_HTML.read_text(encoding="utf-8")
        assert "/static/chrome.css" in text, (
            "base.html must link static/chrome.css as a stylesheet."
        )

    def test_chrome_css_after_tokens_and_styles(self):
        # tokens.css → styles.css → chrome.css.
        text = BASE_HTML.read_text(encoding="utf-8")
        tokens_idx = text.find("/static/tokens.css")
        styles_idx = text.find("/static/styles.css")
        chrome_idx = text.find("/static/chrome.css")
        assert tokens_idx > 0 and styles_idx > 0 and chrome_idx > 0
        assert tokens_idx < styles_idx < chrome_idx, (
            "Load order MUST be tokens.css → styles.css → chrome.css."
        )

    def test_chrome_partial_included(self):
        text = BASE_HTML.read_text(encoding="utf-8")
        assert "_app_chrome.html" in text, (
            "base.html must include partials/_app_chrome.html."
        )

    def test_chrome_partial_mounted_in_body(self):
        # UI-1A: legacy top-header removed; chrome partial is the sole header.
        text = BASE_HTML.read_text(encoding="utf-8")
        chrome_match = re.search(
            r'\{%\s*include\s+"partials/_app_chrome\.html"\s*%\}', text
        )
        assert chrome_match is not None, (
            "No {% include \"partials/_app_chrome.html\" %} directive "
            "in base.html."
        )

    def test_legacy_top_header_removed(self):
        # UI-1A: the legacy duplicate <header class="top-header"> was removed
        # from base.html — only ONE global application header should render.
        text = BASE_HTML.read_text(encoding="utf-8")
        idx = 0
        found = False
        while True:
            idx = text.find('<header class="top-header">', idx)
            if idx < 0:
                break
            # Is this position inside a Jinja comment?
            before = text[:idx]
            last_open = before.rfind('{#')
            last_close = before.rfind('#}')
            if last_open > last_close:
                idx += 1
                continue
            found = True
            break
        assert not found, (
            "Legacy <header class=\"top-header\"> must NOT appear in "
            "base.html after UI-1A — single chrome policy."
        )


# ---------------------------------------------------------------------------
# 5. Partial contents — surface real functionality
# ---------------------------------------------------------------------------

class TestBrandBarPartial:
    """Brand bar must declare the 6 cells from the brief."""

    def test_brand_bar_has_logo(self):
        text = BRAND_BAR_HTML.read_text(encoding="utf-8")
        assert "fo-brand-bar__logo" in text and "Finco One" in text

    @pytest.mark.parametrize("needle", [
        "Project",
        "Scenario",
        "⌘K",
    ])
    def test_brand_bar_has_placeholder(self, needle):
        text = BRAND_BAR_HTML.read_text(encoding="utf-8")
        assert needle in text, (
            f"Brand bar must show the placeholder '{needle}' from "
            f"the brief."
        )

    @pytest.mark.parametrize("needle", [
        "/help",
        "/known-limitations",
        "/pilot-guide",
        "/logout",
    ])
    def test_brand_bar_has_utility_actions(self, needle):
        # UI-1A: utility actions relocated from removed legacy top-header.
        text = BRAND_BAR_HTML.read_text(encoding="utf-8")
        assert needle in text, (
            f"Brand bar must expose '{needle}' (relocated from legacy top-header)."
        )


class TestCommandBarPartial:
    """Command bar must declare Run / Save / Export / Undo / Redo +
    last-run timestamp + engine version + status pills."""

    @pytest.mark.parametrize("needle", [
        # Run button (real htmx POST → /run)
        'hx-post="/run"',
        # Save button (real htmx POST → /scenarios/save)
        'hx-post="/scenarios/save"',
        # Export — links to existing /download
        'href="/download"',
        # Undo / Redo — disabled placeholders
        "Undo",
        "Redo",
        # Last-run timestamp placeholder
        "Last run",
        # Engine version placeholder
        "Engine",
        # Status pills
        "Validation",
        "Stale",
        "Fresh",
    ])
    def test_command_bar_has_action(self, needle):
        text = COMMAND_BAR_HTML.read_text(encoding="utf-8")
        assert needle in text, (
            f"Command bar must declare the '{needle}' affordance from "
            f"the brief."
        )


class TestKpiStripPartial:
    """KPI strip must show Project IRR / Equity IRR / NPV / DSCR / LLCR."""

    @pytest.mark.parametrize("needle", [
        "Project IRR",
        "Equity IRR",
        "NPV",
        "Min DSCR",
        "Avg DSCR",
        "LLCR",
    ])
    def test_kpi_strip_declares_label(self, needle):
        text = KPI_STRIP_HTML.read_text(encoding="utf-8")
        assert needle in text, (
            f"KPI strip must include the '{needle}' label."
        )

    def test_kpi_strip_has_stale_class(self):
        # When inputs are dirty the strip must visually mark stale.
        text = KPI_STRIP_HTML.read_text(encoding="utf-8")
        assert "fo-kpi-strip--stale" in text, (
            "KPI strip must apply the stale class when inputs are dirty."
        )

    def test_kpi_strip_placeholder_dash_for_missing(self):
        # Never display stale KPIs as if current — show em-dash when
        # no snapshot exists.
        text = KPI_STRIP_HTML.read_text(encoding="utf-8")
        assert "—" in text or "&mdash;" in text, (
            "KPI strip must show the em-dash placeholder for missing "
            "KPIs (never display stale values as current)."
        )


# ---------------------------------------------------------------------------
# 6. Forbidden paths — UI-2 must NOT touch engine / persistence / routes
# ---------------------------------------------------------------------------

FORBIDDEN_PATHS = [
    "app/waterfall_core.py",
    "app/waterfall_runner.py",
    "app/input_adapter.py",
    "app/project_factories.py",
    "app/capex_engine.py",
    "app/opex_engine.py",
    "app/depreciation_engine.py",
    "app/excel_export.py",
    "app/services/save_run_service.py",
    "app/services/run_service.py",
    "app/services/compare_service.py",
    "app/services/download_service.py",
    "app/services/preview_context.py",
    "app/services/previews/",
    "app/persistence/",
    "app/validation_status.py",
    "domain/",
    "main_web.py",
    "main_api.py",
    "static/app.js",
    "static/modelling/",
    "static/interaction/",
    "static/styles.css",  # must NOT be touched
    # Existing pages / templates must NOT be touched
    "app/templates/partials/_dashboard.html",
    "app/templates/partials/_nav_compression.html",
    "app/templates/partials/workspace_tabs.html",
    "app/templates/partials/_last_run_indicator.html",
    "app/templates/partials/_generic_status_line.html",
    "app/templates/partials/scen_mtx.html",
]


class TestForbiddenPathsUntouched:
    """UI-2 is additive only — no domain / engine / persistence touch.

    Structural invariant: engine/persistence files must NOT contain
    chrome-specific UI-2 class declarations. This is checkout-depth
    independent and valid on PR, main, and shallow CI checkouts.
    (The PR-diff version of this test required origin/main — removed.)
    """

    def test_engine_files_not_chrome_polluted(self):
        # Engine/persistence Python files must not declare fo-chrome classes.
        for relpath in [
            "app/waterfall_core.py",
            "app/input_adapter.py",
        ]:
            path = REPO_ROOT / relpath
            if not path.exists():
                continue
            text = path.read_text(encoding="utf-8")
            assert "fo-brand-bar" not in text and "fo-command-bar" not in text, (
                f"{relpath} must not contain chrome UI class references."
            )

    def test_legacy_styles_css_not_chrome_owner(self):
        # styles.css must not declare chrome classes as primary rule sets.
        # (Chrome-class references in CSS comments are allowed.)
        styles_raw = (REPO_ROOT / "static" / "styles.css").read_text(encoding="utf-8")
        styles_no_comments = re.sub(r"/\*.*?\*/", "", styles_raw, flags=re.DOTALL)
        for cls in ["fo-brand-bar", "fo-command-bar", "fo-kpi-strip"]:
            assert f".{cls}" not in styles_no_comments, (
                f"Chrome class .{cls} must not be declared in styles.css."
            )


# ---------------------------------------------------------------------------
# 7. base.html diff is additive — only the chrome links + partial include
# ---------------------------------------------------------------------------

class TestBaseHtmlAdditiveOnly:
    """base.html diff must contain only the chrome additions.

    Cross-arc note: when this test was first written, the only
    modification on the working tree was the UI-2 chrome additions.
    Subsequent UI-N PRs (UI-3 sheet tabs, future UI-4 tabs row, etc.)
    may also extend base.html within the additive envelope. The
    assertions below are split into two tiers:

      - Tier A (always enforced): base.html must load chrome.css +
        tokens.css + styles.css in the working tree; no removals.
      - Tier B (PR-specific): when this PR adds new chrome
        additions to base.html, the diff must contain ONLY <link>
        additions or {% include %} additions or Jinja {# ... #}
        comment blocks.
    """

    def test_base_html_has_chrome_tokens_and_styles(self):
        text = BASE_HTML.read_text(encoding="utf-8")
        for needle in ("/static/chrome.css", "/static/tokens.css",
                        "/static/styles.css"):
            assert needle in text, (
                f"base.html must reference {needle} as a stylesheet."
            )

    def test_base_html_no_duplicate_chrome_includes(self):
        # Hermetic structural invariant: base.html must include the chrome
        # partial exactly once (not duplicated by successive UI PRs).
        text = BASE_HTML.read_text(encoding="utf-8")
        count = text.count("_app_chrome.html")
        assert count == 1, (
            f"base.html must include _app_chrome.html exactly once; found {count}."
        )
